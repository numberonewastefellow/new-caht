"""Access rules for Pulse schedules (shared by the API and the worker).

A schedule may run only if:
  * its owner still exists, is active, is not LIMITED, is verified (when required) and
    has an unexpired OIDC session (same gates as `current_user` for API requests),
  * the workflow exists (not deleted), has steps, and is public or owned by the owner
    (same rule as POST /workflow/{id}/run),
  * the owner can use the workflow's wrapper agent.
The worker re-checks this on every run, so revoking access stops a schedule.
Step agents are not individually re-checked — identical to interactive workflow runs,
where a workflow's steps run as part of the workflow the user may use.
"""

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from uuid import UUID

from sqlalchemy.orm import Session

from om.auth.schemas import UserRole
from om.db.agent import get_agent_by_id
from om.db.models import Agent
from om.db.models import AgentWorkflow
from om.db.models import User
from om.db.users import fetch_user_by_id
from om.db.workflow import _get_workflow_agent
from om.db.workflow import create_or_update_workflow_agent
from om.db.workflow import get_workflow_by_id


class PulseAccessError(Exception):
    """The schedule's owner can no longer run its workflow. Message is user-facing."""

    def __init__(self, message: str, *, workflow_deleted: bool = False) -> None:
        super().__init__(message)
        self.workflow_deleted = workflow_deleted


@dataclass
class ResolvedRunContext:
    user: User
    workflow: AgentWorkflow
    agent: Agent


def user_can_use_workflow(workflow: AgentWorkflow, user_id: UUID) -> bool:
    return bool(workflow.is_public or workflow.user_id == user_id)


def get_accessible_workflow(
    db_session: Session, workflow_id: int, user_id: UUID
) -> AgentWorkflow:
    workflow = get_workflow_by_id(db_session=db_session, workflow_id=workflow_id)
    if workflow is None:
        raise PulseAccessError("Workflow not found or deleted", workflow_deleted=True)
    if not user_can_use_workflow(workflow, user_id):
        raise PulseAccessError("You no longer have access to this workflow")
    if not workflow.steps:
        raise PulseAccessError("Workflow has no steps configured")
    return workflow


def check_owner_can_run(user: User | None) -> User:
    """Same gates the API applies to an interactive request (`current_user` /
    `double_check_user`), so a headless run never outlives the owner's access."""
    from om.auth.users import user_needs_to_be_verified

    if user is None or not user.is_active:
        raise PulseAccessError("The schedule owner is no longer active")
    if user.role == UserRole.LIMITED:
        raise PulseAccessError("The schedule owner's role no longer allows running workflows")
    if user_needs_to_be_verified() and not user.is_verified:
        raise PulseAccessError("The schedule owner is not verified")
    if user.oidc_expiry and user.oidc_expiry < datetime.now(timezone.utc):
        raise PulseAccessError(
            "The schedule owner's login has expired; sign in again and resume the schedule"
        )
    return user


def resolve_run_context(
    db_session: Session, *, workflow_id: int, owner_id: UUID
) -> ResolvedRunContext:
    user = check_owner_can_run(fetch_user_by_id(db_session, owner_id))

    workflow = get_accessible_workflow(db_session, workflow_id, owner_id)

    wrapper = _get_workflow_agent(db_session, workflow.id)
    if wrapper is None:
        # Older workflows may predate wrapper agents; create it on demand.
        wrapper = create_or_update_workflow_agent(db_session, workflow)
        db_session.commit()

    try:
        agent = get_agent_by_id(
            wrapper.id, user, db_session, include_deleted=False, is_for_edit=False
        )
    except ValueError:
        raise PulseAccessError("You no longer have access to this workflow's agent")

    return ResolvedRunContext(user=user, workflow=workflow, agent=agent)
