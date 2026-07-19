"""Clean-room enterprise RBAC for Om.

A centralized, testable authorization layer around **Teams**:

* :mod:`om.access.rbac.permissions` — the permission vocabulary and the
  least-privilege role -> permission matrix (pure data).
* :mod:`om.access.rbac.repository` — team/membership/grant queries (tenant-safe).
* :mod:`om.access.rbac.service` — :class:`PermissionService`, the single Policy
  Decision Point every route enforces against.

See ``README.md`` for the model and the research it is grounded in.
"""

from om.access.rbac.models import AccessDecision
from om.access.rbac.models import PermissionDenied
from om.access.rbac.permissions import Permission
from om.access.rbac.permissions import ResourceType
from om.access.rbac.permissions import ROLE_PERMISSION_MATRIX
from om.access.rbac.permissions import TeamRole
from om.access.rbac.repository import TeamRepository
from om.access.rbac.service import permission_service
from om.access.rbac.service import PermissionService

__all__ = [
    "AccessDecision",
    "Permission",
    "PermissionDenied",
    "PermissionService",
    "ResourceType",
    "ROLE_PERMISSION_MATRIX",
    "TeamRepository",
    "TeamRole",
    "permission_service",
]
