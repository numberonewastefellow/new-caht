"""Domain types for RBAC decisions.

Kept free of any web-framework import so the PDP stays a pure decision engine.
The server layer (PEP) translates :class:`PermissionDenied` into an HTTP 403.
"""

from __future__ import annotations

from dataclasses import dataclass

from om.access.rbac.permissions import Permission


@dataclass(frozen=True)
class AccessDecision:
    """The result of a single policy evaluation.

    ``reason`` is a short, log-safe explanation used for the structured decision
    log (auditability — "why was this allowed/denied?").
    """

    allowed: bool
    permission: Permission
    reason: str
    # Optional scope the decision was evaluated against (team id / resource id).
    scope_id: int | None = None

    def __bool__(self) -> bool:  # allow `if decision:`
        return self.allowed


class PermissionDenied(Exception):
    """Raised by the service when a required permission is not held.

    Carries the decision so the PEP can log/return a meaningful message without
    re-deriving it.
    """

    def __init__(self, decision: AccessDecision) -> None:
        self.decision = decision
        super().__init__(
            f"permission denied: {decision.permission.value} "
            f"(scope={decision.scope_id}): {decision.reason}"
        )
