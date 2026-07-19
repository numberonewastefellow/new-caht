"""PermissionService — the centralized Policy Decision Point (PDP).

Every authorization question about teams and team-scoped resources is answered
here, in ONE place, so the logic is uniform, auditable, and unit-testable (OWASP
A01: "implement access control once and reuse it"). Route handlers are thin
Policy Enforcement Points: they call a ``decide_*`` / ``require_*`` method and
enforce the returned :class:`AccessDecision` — they never re-derive policy.

Decision model (deny-by-default):

1. ``user is None`` -> auth is disabled; the caller is the implicit single admin
   -> allow. (Same convention the rest of the app uses.)
2. Otherwise the user's coarse ``UserRole`` must hold the permission *in
   principle* (``ROLE_PERMISSION_MATRIX``); if not -> deny.
3. For team-scoped permissions the user must additionally be *in scope* for the
   target team: admins are in scope for every team; global-curators for teams
   they are a **member** of; curators for teams they are a **curator** of.

Multi-tenant-safe: all DB access goes through the caller-supplied tenant-bound
session via :class:`TeamRepository`.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from om.access.rbac.models import AccessDecision
from om.access.rbac.models import PermissionDenied
from om.access.rbac.permissions import global_permissions_for
from om.access.rbac.permissions import Permission
from om.access.rbac.permissions import ResourceType
from om.access.rbac.repository import TeamRepository
from om.auth.schemas import UserRole
from om.db.models import User
from om.utils.logger import setup_logger

logger = setup_logger()


# Which permission is required to curate each kind of team-scoped resource.
_RESOURCE_CURATE_PERMISSION: dict[ResourceType, Permission] = {
    ResourceType.DOCUMENT_SET: Permission.DOCUMENT_SET_CURATE,
    ResourceType.CONNECTOR: Permission.CONNECTOR_CURATE,
    ResourceType.CREDENTIAL: Permission.CREDENTIAL_CURATE,
    ResourceType.AGENT: Permission.AGENT_CURATE,
    ResourceType.MCP_SERVER: Permission.MCP_SERVER_MANAGE,
}


class PermissionService:
    """Stateless PDP. Safe to instantiate per-request or reuse as a singleton."""

    def __init__(self, repository: TeamRepository | None = None) -> None:
        self._repo = repository or TeamRepository()

    # ------------------------------------------------------------------ raw ---

    @staticmethod
    def _role(user: User | None) -> UserRole | None:
        if user is None:
            return None
        # ``user.role`` is a UserRole column.
        return user.role

    def is_instance_admin(self, user: User | None) -> bool:
        return user is None or user.role == UserRole.ADMIN

    def has_global_permission(self, user: User | None, permission: Permission) -> bool:
        """Does the user's coarse role hold ``permission`` in principle?"""
        if user is None:
            return True
        if getattr(user, "is_anonymous", False):
            return False
        return permission in global_permissions_for(user.role)

    # ------------------------------------------------------------- decisions ---

    def _allow(self, permission: Permission, reason: str, scope_id: int | None) -> AccessDecision:
        return AccessDecision(True, permission, reason, scope_id)

    def _deny(self, permission: Permission, reason: str, scope_id: int | None) -> AccessDecision:
        decision = AccessDecision(False, permission, reason, scope_id)
        logger.debug(
            "rbac deny: permission=%s scope=%s reason=%s",
            permission.value,
            scope_id,
            reason,
        )
        return decision

    def _in_team_scope(
        self, user: User, team_id: int, db: Session
    ) -> bool:
        """Is a (non-admin) user in administrative scope for ``team_id``?

        global_curator -> member of the team; curator -> curator of the team.
        """
        if user.role == UserRole.GLOBAL_CURATOR:
            return self._repo.is_member(db, user.id, team_id)
        if user.role == UserRole.CURATOR:
            return self._repo.is_curator(db, user.id, team_id)
        return False

    def decide_team_permission(
        self,
        user: User | None,
        permission: Permission,
        team_id: int,
        db: Session,
    ) -> AccessDecision:
        """General team-scoped decision: role holds the permission AND is in
        scope for the target team."""
        if user is None:
            return self._allow(permission, "auth-disabled admin", team_id)
        if not self.has_global_permission(user, permission):
            return self._deny(permission, f"role {user.role.value} lacks permission", team_id)
        if user.role == UserRole.ADMIN:
            return self._allow(permission, "instance admin", team_id)
        if self._in_team_scope(user, team_id, db):
            return self._allow(permission, f"in-scope {user.role.value}", team_id)
        return self._deny(permission, f"{user.role.value} not in scope for team", team_id)

    # -- team lifecycle --------------------------------------------------------

    def can_view_teams(self, user: User | None) -> bool:
        return self.has_global_permission(user, Permission.TEAM_VIEW)

    def decide_create_team(self, user: User | None) -> AccessDecision:
        # Instance-level (no team scope): matrix restricts TEAM_CREATE to admins.
        if self.has_global_permission(user, Permission.TEAM_CREATE):
            return self._allow(Permission.TEAM_CREATE, "authorized", None)
        return self._deny(Permission.TEAM_CREATE, "only instance admins create teams", None)

    def decide_delete_team(self, user: User | None) -> AccessDecision:
        if self.has_global_permission(user, Permission.TEAM_DELETE):
            return self._allow(Permission.TEAM_DELETE, "authorized", None)
        return self._deny(Permission.TEAM_DELETE, "only instance admins delete teams", None)

    def decide_edit_team(self, user: User | None, team_id: int, db: Session) -> AccessDecision:
        return self.decide_team_permission(user, Permission.TEAM_UPDATE, team_id, db)

    def decide_manage_members(
        self, user: User | None, team_id: int, db: Session
    ) -> AccessDecision:
        return self.decide_team_permission(user, Permission.TEAM_MANAGE_MEMBERS, team_id, db)

    def decide_manage_curators(
        self, user: User | None, team_id: int, db: Session
    ) -> AccessDecision:
        return self.decide_team_permission(user, Permission.TEAM_MANAGE_CURATORS, team_id, db)

    # -- resource-scoped curation ---------------------------------------------

    def decide_curate_resource(
        self,
        user: User | None,
        resource_type: ResourceType,
        owning_team_ids: Iterable[int],
        db: Session,
    ) -> AccessDecision:
        """May the user curate a resource that is granted to ``owning_team_ids``?

        The user must hold the resource's curate permission AND administer at
        least one team the resource belongs to (admins bypass the scope check).
        """
        permission = _RESOURCE_CURATE_PERMISSION.get(resource_type)
        if permission is None:
            return self._deny(Permission.RESOURCE_GRANT_TO_TEAM, f"{resource_type.value} not curatable", None)
        if user is None:
            return self._allow(permission, "auth-disabled admin", None)
        if not self.has_global_permission(user, permission):
            return self._deny(permission, f"role {user.role.value} lacks permission", None)
        if user.role == UserRole.ADMIN:
            return self._allow(permission, "instance admin", None)

        owning = set(owning_team_ids)
        if not owning:
            # A resource attached to no team is instance-scoped -> admin only.
            return self._deny(permission, "resource not team-scoped; admin only", None)
        if user.role == UserRole.GLOBAL_CURATOR:
            scope = self._repo.member_team_ids(db, user.id)
        else:  # CURATOR
            scope = self._repo.curated_team_ids(db, user.id)
        if owning & scope:
            return self._allow(permission, f"curates owning team", None)
        return self._deny(permission, "does not administer any owning team", None)

    # -- scoping for list endpoints -------------------------------------------

    def administerable_team_ids(self, user: User | None, db: Session) -> set[int] | None:
        """Team ids the user may administer. ``None`` means "all" (admin)."""
        if user is None or user.role == UserRole.ADMIN:
            return None
        if user.role == UserRole.GLOBAL_CURATOR:
            return self._repo.member_team_ids(db, user.id)
        if user.role == UserRole.CURATOR:
            return self._repo.curated_team_ids(db, user.id)
        return set()

    # ------------------------------------------------------------ enforce ---

    @staticmethod
    def require(decision: AccessDecision) -> None:
        """Enforce a decision (PEP helper). Raises on deny."""
        if not decision.allowed:
            raise PermissionDenied(decision)


# A ready-to-use singleton for the common case.
permission_service = PermissionService()
