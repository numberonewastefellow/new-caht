"""RBAC permission vocabulary + the least-privilege role -> permission matrix.

Design (see ``README.md`` for the research this is grounded in):

* **Two role planes.** A coarse, instance-wide plane (the existing ``UserRole``:
  admin / global_curator / curator / basic / limited / ...) and a fine-grained,
  **team-scoped** plane (``TeamRole``: curator / member, from the
  ``user__team.is_curator`` flag). This is the hybrid RBAC + relationship-based
  model — coarse tiers for instance capabilities, team-scoped grants for the
  resource-instance middle (NIST hierarchical RBAC; Zanzibar-style relations).

* **Deny-by-default.** A role has ONLY the permissions explicitly listed for it
  in the matrix below; everything else is denied. Adding a new permission does
  not silently widen any role (OWASP A01 — implement once, deny by default).

* **Separation of duties.** Content curation (curate resources, manage team
  membership) is deliberately split from instance administration (manage users,
  manage LLM providers, delete teams). A curator can never escalate to instance
  admin, and only admins / global-curators may mint new curators.

The matrices here answer "does role R *in principle* hold permission P?". Whether
R holds P *for a specific team/resource* (member-of / curator-of scoping) is the
job of :class:`om.access.rbac.service.PermissionService` — this module is pure,
importable data with no DB or request dependency (trivially unit-testable).
"""

from __future__ import annotations

from enum import Enum

from om.auth.schemas import UserRole


class ResourceType(str, Enum):
    """Kinds of resource whose access can be scoped to a team."""

    TEAM = "team"
    DOCUMENT_SET = "document_set"
    CONNECTOR = "connector"  # connector_credential_pair
    CREDENTIAL = "credential"
    AGENT = "agent"
    LLM_PROVIDER = "llm_provider"
    MCP_SERVER = "mcp_server"
    USER = "user"


class TeamRole(str, Enum):
    """A user's role *within a single team* (from ``user__team.is_curator``)."""

    CURATOR = "curator"
    MEMBER = "member"


class Permission(str, Enum):
    """Atomic, checkable capabilities. Value is ``"{resource}:{action}"``."""

    # --- team lifecycle ---
    TEAM_VIEW = "team:view"
    TEAM_CREATE = "team:create"
    TEAM_UPDATE = "team:update"
    TEAM_DELETE = "team:delete"
    TEAM_MANAGE_MEMBERS = "team:manage_members"
    TEAM_MANAGE_CURATORS = "team:manage_curators"

    # --- resource-scoped curation (a resource attached to a team) ---
    DOCUMENT_SET_CURATE = "document_set:curate"
    CONNECTOR_CURATE = "connector:curate"
    CREDENTIAL_CURATE = "credential:curate"
    AGENT_CURATE = "agent:curate"
    MCP_SERVER_MANAGE = "mcp_server:manage"
    # attach/detach a resource to/from a team (a grant edge)
    RESOURCE_GRANT_TO_TEAM = "resource:grant_to_team"

    # --- instance administration (never delegated to curators) ---
    LLM_PROVIDER_MANAGE = "llm_provider:manage"
    USER_MANAGE = "user:manage"
    INSTANCE_ADMIN = "instance:admin"


# Every permission an admin implicitly holds (the full vocabulary).
ALL_PERMISSIONS: frozenset[Permission] = frozenset(Permission)

# Permissions that curators (global or team-scoped) may exercise *within scope*.
# These are the "content curation" capabilities — never instance administration.
_CURATOR_SCOPED_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.TEAM_VIEW,
        Permission.TEAM_UPDATE,
        Permission.TEAM_MANAGE_MEMBERS,
        Permission.DOCUMENT_SET_CURATE,
        Permission.CONNECTOR_CURATE,
        Permission.CREDENTIAL_CURATE,
        Permission.AGENT_CURATE,
        Permission.MCP_SERVER_MANAGE,
        Permission.RESOURCE_GRANT_TO_TEAM,
    }
)

# Global-curators additionally may mint/remove curators (SoD: plain curators may
# NOT — that would let a curator manufacture peers and escalate laterally).
_GLOBAL_CURATOR_PERMISSIONS: frozenset[Permission] = _CURATOR_SCOPED_PERMISSIONS | {
    Permission.TEAM_MANAGE_CURATORS,
}


# The coarse, instance-wide matrix: UserRole -> the permissions it may hold *at
# all*. Team/resource scoping is applied on top by PermissionService. Roles not
# listed (slack_user, ext_perm_user, and any future role) get the empty set =
# fully denied, by construction.
ROLE_PERMISSION_MATRIX: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: ALL_PERMISSIONS,
    UserRole.GLOBAL_CURATOR: _GLOBAL_CURATOR_PERMISSIONS,
    UserRole.CURATOR: _CURATOR_SCOPED_PERMISSIONS,
    # Basic users can see the teams they belong to (for sharing UIs) but hold no
    # administrative capability.
    UserRole.BASIC: frozenset({Permission.TEAM_VIEW}),
    UserRole.LIMITED: frozenset(),
    UserRole.SLACK_USER: frozenset(),
    UserRole.EXT_PERM_USER: frozenset(),
}

# What a team-scoped role grants *for the team it applies to*. A team CURATOR is
# a curator only of that team; a MEMBER can view and use but not administer.
TEAM_ROLE_PERMISSION_MATRIX: dict[TeamRole, frozenset[Permission]] = {
    TeamRole.CURATOR: _CURATOR_SCOPED_PERMISSIONS,
    TeamRole.MEMBER: frozenset({Permission.TEAM_VIEW}),
}

def global_permissions_for(role: UserRole) -> frozenset[Permission]:
    """The in-principle permission set for a coarse role (deny-by-default)."""
    return ROLE_PERMISSION_MATRIX.get(role, frozenset())


def team_permissions_for(team_role: TeamRole) -> frozenset[Permission]:
    """The in-principle permission set granted by a team-scoped role."""
    return TEAM_ROLE_PERMISSION_MATRIX.get(team_role, frozenset())
