"""SCIM provisioning services (business logic).

Two services translate between SCIM resources and the internal domain:

* :class:`ScimUserService` — SCIM ``User`` ↔ :class:`om.db.models.User`.
* :class:`ScimGroupService` — SCIM ``Group`` ↔ internal **Team** (Contract 1),
  with membership held in the ``user__team`` association table.

Resource ``id`` is the internal primary key (User UUID / Team id) as a string;
``externalId`` is the IdP's own identifier, persisted in the mapping tables. The
services own transaction commits and emit structured audit logs.

Attribute mapping (documented in README):
  userName  ↔ User.email (unique key)
  active    ↔ User.is_active   (DELETE = deactivate + unlink; soft deprovision)
  displayName ↔ User.personal_name (name.formatted as fallback)
  Group.displayName ↔ Team.name ; Group.members ↔ user__team rows.

``Team`` and the ``user__team`` table are imported lazily because they are landed
by WS-B; this module imports cleanly before that integration.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func
from sqlalchemy import insert as sa_insert
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from om.auth.schemas import UserRole
from om.db.models import User
from om.db.scim import ScimRepository
from om.server.scim import constants
from om.server.scim import scim_logging
from om.server.scim.errors import ScimError
from om.server.scim.filters import parse_filter
from om.server.scim.patch_ops import apply_patch
from om.server.scim.resources import ScimGroupResource
from om.server.scim.resources import ScimListResponse
from om.server.scim.resources import ScimPatchOperation
from om.server.scim.resources import ScimUserResource

# --------------------------------------------------------------------------
# Password hashing for provisioned (SSO-managed) users
# --------------------------------------------------------------------------
try:
    from fastapi_users.password import PasswordHelper

    _password_helper = PasswordHelper()

    def _random_password_hash() -> str:
        return _password_helper.hash(_password_helper.generate())

except Exception:  # pragma: no cover - fallback if helper unavailable

    def _random_password_hash() -> str:
        return ""


def _clamp_count(count: int | None) -> int:
    if count is None:
        return constants.DEFAULT_PAGE_SIZE
    return max(0, min(count, constants.MAX_PAGE_SIZE))


def _paginate(
    resources: list[dict[str, Any]], start_index: int, count: int
) -> dict[str, Any]:
    """Build a SCIM ListResponse with 1-based ``startIndex`` (RFC 7644 §3.4.2)."""
    total = len(resources)
    start = max(1, start_index)
    if count == 0:
        page: list[dict[str, Any]] = []
    else:
        page = resources[start - 1 : start - 1 + count]
    return ScimListResponse(
        total_results=total,
        start_index=start,
        items_per_page=len(page),
        resources=page,
    ).model_dump(by_alias=True)


# ==========================================================================
# Users
# ==========================================================================
class ScimUserService:
    def __init__(self, db: Session, *, actor_user_id: str, base_url: str) -> None:
        self.db = db
        self.repo = ScimRepository(db)
        self.actor_user_id = actor_user_id
        self.base_url = base_url

    # ---- serialization ----
    def _to_scim(self, user: User, external_id: str | None) -> dict[str, Any]:
        resource: dict[str, Any] = {
            "schemas": [constants.SCHEMA_USER],
            "id": str(user.id),
            "userName": user.email,
            "active": bool(user.is_active),
            "displayName": user.personal_name or user.email,
            "emails": [
                {"value": user.email, "type": "work", "primary": True}
            ],
            "meta": {
                "resourceType": constants.RESOURCE_TYPE_USER,
                "location": f"{self.base_url}/Users/{user.id}",
            },
        }
        if user.personal_name:
            resource["name"] = {"formatted": user.personal_name}
        if external_id is not None:
            resource["externalId"] = external_id
        return resource

    def _get_user_or_404(self, user_id: str) -> User:
        try:
            uid = UUID(user_id)
        except ValueError:
            raise ScimError.not_found(f"User '{user_id}' not found.")
        user = self.db.get(User, uid)
        if user is None:
            raise ScimError.not_found(f"User '{user_id}' not found.")
        return user

    def _external_id_for(self, user_id: UUID) -> str | None:
        mapping = self.repo.get_user_mapping_by_user_id(user_id)
        return mapping.external_id if mapping else None

    # ---- operations ----
    def create(self, resource: ScimUserResource) -> dict[str, Any]:
        with scim_logging.scim_operation(
            event=scim_logging.EVENT_USER_PROVISIONED,
            entity=scim_logging.ENTITY_USER,
            action="create",
            actor_user_id=self.actor_user_id,
        ) as op:
            if not resource.user_name:
                raise ScimError.invalid_value("'userName' is required.")
            email = resource.user_name.strip()

            # externalId uniqueness
            if resource.external_id and self.repo.get_user_mapping_by_external_id(
                resource.external_id
            ):
                raise ScimError.uniqueness(
                    f"A user with externalId '{resource.external_id}' already exists."
                )
            display = resource.display_name or (
                resource.name.formatted if resource.name else None
            )

            # userName (email) uniqueness. A previously deprovisioned user
            # (is_active=False, mapping deleted) is reactivated in place so
            # re-provisioning is idempotent (RFC-friendly deactivate→reactivate
            # cycle); any active or still-mapped collision is a 409.
            # .unique() is required because User has joined-eager collections.
            existing_user = (
                self.db.scalars(
                    select(User).where(func.lower(User.email) == email.lower())
                )
                .unique()
                .first()
            )
            if existing_user is not None:
                if existing_user.is_active or self.repo.get_user_mapping_by_user_id(
                    existing_user.id
                ):
                    raise ScimError.uniqueness(
                        f"A user with userName '{email}' already exists."
                    )
                return self._reactivate(existing_user, resource, display, op)
            user = User(
                email=email,
                hashed_password=_random_password_hash(),
                is_active=resource.active if resource.active is not None else True,
                is_verified=True,
                is_superuser=False,
                role=UserRole.BASIC,
                personal_name=display,
            )
            self.db.add(user)
            try:
                self.db.flush()
                if resource.external_id:
                    self.repo.create_user_mapping(
                        external_id=resource.external_id, user_id=user.id
                    )
                self.db.commit()
            except IntegrityError:
                # Backstop for the check-then-insert race (unique userName/externalId).
                self.db.rollback()
                raise ScimError.uniqueness(
                    f"A user with userName '{email}' already exists."
                )
            op.entity_id = str(user.id)
            return self._to_scim(user, resource.external_id)

    def get(self, user_id: str) -> dict[str, Any]:
        user = self._get_user_or_404(user_id)
        return self._to_scim(user, self._external_id_for(user.id))

    def replace(self, user_id: str, resource: ScimUserResource) -> dict[str, Any]:
        with scim_logging.scim_operation(
            event=scim_logging.EVENT_USER_UPDATED,
            entity=scim_logging.ENTITY_USER,
            action="update",
            actor_user_id=self.actor_user_id,
        ) as op:
            user = self._get_user_or_404(user_id)
            op.entity_id = str(user.id)
            try:
                if resource.user_name:
                    user.email = resource.user_name.strip()
                if resource.active is not None:
                    user.is_active = resource.active
                display = resource.display_name or (
                    resource.name.formatted if resource.name else None
                )
                if display is not None:
                    user.personal_name = display
                self._sync_external_id(user.id, resource.external_id)
                self.db.commit()
            except IntegrityError:
                # A userName rename that collides with another user's email
                # violates the unique constraint (may surface at autoflush or
                # commit) → SCIM 409, not a 500.
                self.db.rollback()
                raise ScimError.uniqueness(
                    f"A user with userName '{resource.user_name}' already exists."
                )
            return self._to_scim(user, self._external_id_for(user.id))

    def patch(self, user_id: str, operations: list[ScimPatchOperation]) -> dict[str, Any]:
        with scim_logging.scim_operation(
            event=scim_logging.EVENT_USER_UPDATED,
            entity=scim_logging.ENTITY_USER,
            action="update",
            actor_user_id=self.actor_user_id,
        ) as op:
            user = self._get_user_or_404(user_id)
            op.entity_id = str(user.id)
            current = self._to_scim(user, self._external_id_for(user.id))
            patched = apply_patch(current, operations)
            # Re-validate through the resource model (coerces "active" strings, etc.).
            updated = ScimUserResource(**patched)

            try:
                if updated.user_name:
                    user.email = updated.user_name.strip()
                if updated.active is not None:
                    user.is_active = updated.active
                display = updated.display_name or (
                    updated.name.formatted if updated.name else None
                )
                if display is not None:
                    user.personal_name = display
                self._sync_external_id(user.id, updated.external_id)
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                raise ScimError.uniqueness(
                    f"A user with userName '{updated.user_name}' already exists."
                )
            return self._to_scim(user, self._external_id_for(user.id))

    def _reactivate(
        self,
        user: User,
        resource: ScimUserResource,
        display: str | None,
        op: "scim_logging._OperationHandle",
    ) -> dict[str, Any]:
        """Re-provision a previously deprovisioned (inactive, unmapped) user in
        place: reactivate, refresh display, and relink the SCIM mapping."""
        user.is_active = resource.active if resource.active is not None else True
        if display is not None:
            user.personal_name = display
        try:
            if resource.external_id:
                self._sync_external_id(user.id, resource.external_id)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ScimError.uniqueness(
                f"A user with userName '{user.email}' already exists."
            )
        op.entity_id = str(user.id)
        return self._to_scim(user, self._external_id_for(user.id))

    def deprovision(self, user_id: str) -> None:
        """SCIM DELETE → soft deprovision: deactivate the user and unlink the
        SCIM mapping. Retains the user's owned data; a later POST with the same
        userName reactivates this row in place (see ``_reactivate``)."""
        with scim_logging.scim_operation(
            event=scim_logging.EVENT_USER_DEPROVISIONED,
            entity=scim_logging.ENTITY_USER,
            action="delete",
            actor_user_id=self.actor_user_id,
        ) as op:
            user = self._get_user_or_404(user_id)
            op.entity_id = str(user.id)
            user.is_active = False
            mapping = self.repo.get_user_mapping_by_user_id(user.id)
            if mapping:
                self.repo.delete_user_mapping(mapping)
            self.db.commit()

    def list_users(
        self, *, filter_str: str | None, start_index: int, count: int | None
    ) -> dict[str, Any]:
        count = _clamp_count(count)
        if not filter_str:
            # Fast path: page in SQL (LIMIT/OFFSET) and batch-load only the
            # page's externalId mappings — no full-table scan.
            return self._list_users_paged(start_index, count)
        # Filtered path: SCIM filters are evaluated in memory over the full set
        # (arbitrary filters are not translated to SQL). IdPs use this less than
        # plain paging; kept correct rather than fast.
        # .unique() is required because User has joined-eager collections.
        users = list(
            self.db.scalars(select(User).order_by(User.email)).unique().all()
        )
        external_ids = {
            m.user_id: m.external_id for m in self.repo.list_user_mappings()
        }
        resources = [
            self._to_scim(user, external_ids.get(user.id)) for user in users
        ]
        node = parse_filter(filter_str)
        resources = [r for r in resources if node.evaluate(r)]
        return _paginate(resources, start_index, count)

    def _list_users_paged(self, start_index: int, count: int) -> dict[str, Any]:
        total = self.db.scalar(select(func.count()).select_from(User)) or 0
        start = max(1, start_index)
        if count == 0:
            page_users: list[User] = []
        else:
            # .unique() is required because User has joined-eager collections.
            page_users = list(
                self.db.scalars(
                    select(User)
                    .order_by(User.email)
                    .offset(start - 1)
                    .limit(count)
                )
                .unique()
                .all()
            )
        external_ids = {
            m.user_id: m.external_id
            for m in self.repo.list_user_mappings_for([u.id for u in page_users])
        }
        resources = [
            self._to_scim(user, external_ids.get(user.id)) for user in page_users
        ]
        return ScimListResponse(
            total_results=int(total),
            start_index=start,
            items_per_page=len(resources),
            resources=resources,
        ).model_dump(by_alias=True)

    # ---- helpers ----
    def _sync_external_id(self, user_id: UUID, external_id: str | None) -> None:
        if external_id is None:
            return
        existing = self.repo.get_user_mapping_by_user_id(user_id)
        if existing is None:
            # Guard cross-user externalId reuse.
            other = self.repo.get_user_mapping_by_external_id(external_id)
            if other is not None and other.user_id != user_id:
                raise ScimError.uniqueness(
                    f"externalId '{external_id}' is already in use."
                )
            self.repo.create_user_mapping(external_id=external_id, user_id=user_id)
        elif existing.external_id != external_id:
            self.repo.update_user_mapping_external_id(existing, external_id)


# ==========================================================================
# Groups → Teams (Contract 1)
# ==========================================================================
class ScimGroupService:
    def __init__(self, db: Session, *, actor_user_id: str, base_url: str) -> None:
        self.db = db
        self.repo = ScimRepository(db)
        self.actor_user_id = actor_user_id
        self.base_url = base_url

    # ---- lazy references to WS-B-owned schema ----
    @staticmethod
    def _team_model() -> Any:
        import om.db.models as models

        # Team is landed by WS-B (Contract 1). Resolve dynamically: this worktree
        # predates the Team model, and getattr keeps both this worktree and the
        # integrated tree type-clean (a `type: ignore` would become unused — and
        # thus an error under warn_unused_ignores — once WS-B lands Team).
        return getattr(models, "Team")

    @staticmethod
    def _membership_table() -> Any:
        from om.db.models import Base

        return Base.metadata.tables["user__team"]

    # ---- serialization ----
    def _member_entry(self, user: User) -> dict[str, Any]:
        return {
            "value": str(user.id),
            "display": user.email,
            "$ref": f"{self.base_url}/Users/{user.id}",
            "type": "User",
        }

    def _member_entries(self, team_id: int) -> list[dict[str, Any]]:
        membership = self._membership_table()
        rows = self.db.execute(
            select(membership.c.user_id).where(membership.c.team_id == team_id)
        ).all()
        user_ids = [row[0] for row in rows]
        if not user_ids:
            return []
        # .unique() is required because User has joined-eager collections.
        users = self.db.scalars(
            select(User).where(User.id.in_(user_ids))  # type: ignore
        ).unique().all()
        return [self._member_entry(user) for user in users]

    def _member_entries_bulk(
        self, team_ids: list[int]
    ) -> dict[int, list[dict[str, Any]]]:
        """Member entries for a set of teams in two queries (no per-team N+1)."""
        if not team_ids:
            return {}
        membership = self._membership_table()
        rows = self.db.execute(
            select(membership.c.team_id, membership.c.user_id).where(
                membership.c.team_id.in_(team_ids)
            )
        ).all()
        user_ids_by_team: dict[int, list[Any]] = {}
        all_user_ids: set[Any] = set()
        for team_id, user_id in rows:
            user_ids_by_team.setdefault(team_id, []).append(user_id)
            all_user_ids.add(user_id)
        users_by_id: dict[Any, User] = {}
        if all_user_ids:
            # .unique() is required because User has joined-eager collections.
            users = (
                self.db.scalars(
                    select(User).where(User.id.in_(all_user_ids))  # type: ignore
                )
                .unique()
                .all()
            )
            users_by_id = {user.id: user for user in users}
        result: dict[int, list[dict[str, Any]]] = {}
        for team_id in team_ids:
            entries = [
                self._member_entry(users_by_id[uid])
                for uid in user_ids_by_team.get(team_id, [])
                if uid in users_by_id
            ]
            result[team_id] = entries
        return result

    def _to_scim(
        self,
        team: Any,
        external_id: str | None,
        *,
        include_members: bool = True,
        members: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        resource: dict[str, Any] = {
            "schemas": [constants.SCHEMA_GROUP],
            "id": str(team.id),
            "displayName": team.name,
            "meta": {
                "resourceType": constants.RESOURCE_TYPE_GROUP,
                "location": f"{self.base_url}/Groups/{team.id}",
            },
        }
        if include_members:
            # Prefer a precomputed (batch-loaded) member list to avoid an N+1
            # query when serializing a page of groups.
            resource["members"] = (
                members if members is not None else self._member_entries(team.id)
            )
        if external_id is not None:
            resource["externalId"] = external_id
        return resource

    def _get_team_or_404(self, team_id: str) -> Any:
        try:
            tid = int(team_id)
        except ValueError:
            raise ScimError.not_found(f"Group '{team_id}' not found.")
        team = self.db.get(self._team_model(), tid)
        if team is None:
            raise ScimError.not_found(f"Group '{team_id}' not found.")
        return team

    def _external_id_for(self, team_id: int) -> str | None:
        mapping = self.repo.get_team_mapping_by_team_id(team_id)
        return mapping.external_id if mapping else None

    # ---- operations ----
    def create(self, resource: ScimGroupResource) -> dict[str, Any]:
        with scim_logging.scim_operation(
            event=scim_logging.EVENT_GROUP_SYNCED,
            entity=scim_logging.ENTITY_TEAM,
            action="create",
            actor_user_id=self.actor_user_id,
        ) as op:
            if not resource.display_name:
                raise ScimError.invalid_value("'displayName' is required.")
            name = resource.display_name.strip()

            if resource.external_id and self.repo.get_team_mapping_by_external_id(
                resource.external_id
            ):
                raise ScimError.uniqueness(
                    f"A group with externalId '{resource.external_id}' already exists."
                )
            team_model = self._team_model()
            if self.db.scalar(select(team_model.id).where(team_model.name == name)):
                raise ScimError.uniqueness(
                    f"A group named '{name}' already exists."
                )

            team = team_model(
                name=name, is_up_to_date=False, is_up_for_deletion=False
            )
            self.db.add(team)
            try:
                self.db.flush()
                if resource.external_id:
                    self.repo.create_team_mapping(
                        external_id=resource.external_id, team_id=team.id
                    )
                if resource.members:
                    self._replace_members(team.id, self._member_ids(resource.members))
                self.db.commit()
            except IntegrityError:
                # Backstop for the check-then-insert race (unique name/externalId).
                self.db.rollback()
                raise ScimError.uniqueness(
                    f"A group named '{name}' already exists."
                )
            op.entity_id = str(team.id)
            return self._to_scim(team, resource.external_id)

    @staticmethod
    def _include_members(excluded_attributes: str | None) -> bool:
        """Honor ``excludedAttributes=members`` (Entra sends this on Group reads)."""
        if not excluded_attributes:
            return True
        excluded = {a.strip().lower() for a in excluded_attributes.split(",")}
        return "members" not in excluded

    def get(self, team_id: str, *, excluded_attributes: str | None = None) -> dict[str, Any]:
        team = self._get_team_or_404(team_id)
        return self._to_scim(
            team,
            self._external_id_for(team.id),
            include_members=self._include_members(excluded_attributes),
        )

    def replace(self, team_id: str, resource: ScimGroupResource) -> dict[str, Any]:
        with scim_logging.scim_operation(
            event=scim_logging.EVENT_GROUP_SYNCED,
            entity=scim_logging.ENTITY_TEAM,
            action="update",
            actor_user_id=self.actor_user_id,
        ) as op:
            team = self._get_team_or_404(team_id)
            op.entity_id = str(team.id)
            try:
                if resource.display_name:
                    team.name = resource.display_name.strip()
                if resource.members is not None:
                    self._replace_members(team.id, self._member_ids(resource.members))
                self._sync_external_id(team.id, resource.external_id)
                self.db.commit()
            except IntegrityError:
                # A displayName rename colliding with another Team's name → 409.
                self.db.rollback()
                raise ScimError.uniqueness(
                    f"A group named '{resource.display_name}' already exists."
                )
            return self._to_scim(team, self._external_id_for(team.id))

    def patch(self, team_id: str, operations: list[ScimPatchOperation]) -> dict[str, Any]:
        with scim_logging.scim_operation(
            event=scim_logging.EVENT_GROUP_SYNCED,
            entity=scim_logging.ENTITY_TEAM,
            action="update",
            actor_user_id=self.actor_user_id,
        ) as op:
            team = self._get_team_or_404(team_id)
            op.entity_id = str(team.id)
            current = self._to_scim(team, self._external_id_for(team.id))
            patched = apply_patch(current, operations)
            updated = ScimGroupResource(**patched)

            try:
                if updated.display_name:
                    team.name = updated.display_name.strip()
                # Reconcile membership only if the PATCH actually changed it — a
                # displayName-only PATCH must not touch (or re-validate) members.
                current_member_ids = {
                    m.get("value") for m in current.get("members", []) if m.get("value")
                }
                patched_member_ids = {
                    str(m.value) for m in (updated.members or []) if m.value
                }
                if patched_member_ids != current_member_ids:
                    self._replace_members(
                        team.id, self._member_ids(updated.members or [])
                    )
                self._sync_external_id(team.id, updated.external_id)
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                raise ScimError.uniqueness(
                    f"A group named '{updated.display_name}' already exists."
                )
            return self._to_scim(team, self._external_id_for(team.id))

    def delete(self, team_id: str) -> None:
        with scim_logging.scim_operation(
            event=scim_logging.EVENT_GROUP_DEPROVISIONED,
            entity=scim_logging.ENTITY_TEAM,
            action="delete",
            actor_user_id=self.actor_user_id,
        ) as op:
            team = self._get_team_or_404(team_id)
            op.entity_id = str(team.id)
            membership = self._membership_table()
            self.db.execute(
                sa_delete(membership).where(membership.c.team_id == team.id)
            )
            mapping = self.repo.get_team_mapping_by_team_id(team.id)
            if mapping:
                self.repo.delete_team_mapping(mapping)
            self.db.delete(team)
            self.db.commit()

    def list_groups(
        self,
        *,
        filter_str: str | None,
        start_index: int,
        count: int | None,
        excluded_attributes: str | None = None,
    ) -> dict[str, Any]:
        count = _clamp_count(count)
        include_members = self._include_members(excluded_attributes)
        if not filter_str:
            # Fast path: page in SQL and batch-load the page's mappings +
            # memberships (no full-table scan, no per-team membership N+1).
            return self._list_groups_paged(start_index, count, include_members)
        # Filtered path: evaluate in memory over the full set.
        team_model = self._team_model()
        # .unique() guards against joined-eager collections on the Team model.
        teams = list(
            self.db.scalars(select(team_model).order_by(team_model.name)).unique().all()
        )
        external_ids = {
            m.team_id: m.external_id for m in self.repo.list_team_mappings()
        }
        members_by_team = (
            self._member_entries_bulk([team.id for team in teams])
            if include_members
            else {}
        )
        resources = [
            self._to_scim(
                team,
                external_ids.get(team.id),
                include_members=include_members,
                members=members_by_team.get(team.id, []),
            )
            for team in teams
        ]
        node = parse_filter(filter_str)
        resources = [r for r in resources if node.evaluate(r)]
        return _paginate(resources, start_index, count)

    def _list_groups_paged(
        self, start_index: int, count: int, include_members: bool
    ) -> dict[str, Any]:
        team_model = self._team_model()
        total = self.db.scalar(select(func.count()).select_from(team_model)) or 0
        start = max(1, start_index)
        if count == 0:
            page_teams: list[Any] = []
        else:
            # .unique() guards against joined-eager collections on Team.
            page_teams = list(
                self.db.scalars(
                    select(team_model)
                    .order_by(team_model.name)
                    .offset(start - 1)
                    .limit(count)
                )
                .unique()
                .all()
            )
        team_ids = [team.id for team in page_teams]
        external_ids = {
            m.team_id: m.external_id
            for m in self.repo.list_team_mappings_for(team_ids)
        }
        members_by_team = (
            self._member_entries_bulk(team_ids) if include_members else {}
        )
        resources = [
            self._to_scim(
                team,
                external_ids.get(team.id),
                include_members=include_members,
                members=members_by_team.get(team.id, []),
            )
            for team in page_teams
        ]
        return ScimListResponse(
            total_results=int(total),
            start_index=start,
            items_per_page=len(resources),
            resources=resources,
        ).model_dump(by_alias=True)

    # ---- membership helpers ----
    def _member_ids(self, members: list[Any]) -> list[UUID]:
        """Resolve SCIM member entries (``value`` = User id) to validated UUIDs.

        Existence is validated in a single query (no per-member round trip).
        Order is preserved; duplicates are collapsed by ``_replace_members``.
        """
        resolved: list[UUID] = []
        for member in members:
            value = member.value if hasattr(member, "value") else member.get("value")
            if not value:
                continue
            try:
                resolved.append(UUID(str(value)))
            except ValueError:
                raise ScimError.invalid_value(f"Invalid member id: {value!r}")
        if resolved:
            existing = set(
                self.db.scalars(
                    select(User.id).where(User.id.in_(resolved))  # type: ignore
                ).all()
            )
            missing = [str(uid) for uid in resolved if uid not in existing]
            if missing:
                raise ScimError.invalid_value(
                    f"Unknown member user(s): {', '.join(missing)}"
                )
        return resolved

    def _replace_members(self, team_id: int, user_ids: list[UUID]) -> None:
        membership = self._membership_table()
        self.db.execute(sa_delete(membership).where(membership.c.team_id == team_id))
        seen: set[UUID] = set()
        for uid in user_ids:
            if uid in seen:
                continue
            seen.add(uid)
            self.db.execute(
                sa_insert(membership).values(team_id=team_id, user_id=uid)
            )

    def _sync_external_id(self, team_id: int, external_id: str | None) -> None:
        if external_id is None:
            return
        existing = self.repo.get_team_mapping_by_team_id(team_id)
        if existing is None:
            other = self.repo.get_team_mapping_by_external_id(external_id)
            if other is not None and other.team_id != team_id:
                raise ScimError.uniqueness(
                    f"externalId '{external_id}' is already in use."
                )
            self.repo.create_team_mapping(external_id=external_id, team_id=team_id)
        elif existing.external_id != external_id:
            self.repo.update_team_mapping_external_id(existing, external_id)
