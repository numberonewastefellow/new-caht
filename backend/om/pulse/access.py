"""Access rules for Pulse schedules (shared by the API and the worker).

A schedule may run only if:
  * its owner still exists and is active,
  * the workflow exists (not deleted), has steps, and is public or owned by the owner
    (same rule as POST /workflow/{id}/run),
  * the owner can use the workflow's wrapper agent.
The worker re-checks this on every run, so revoking access stops a schedule.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

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


def resolve_run_context(
    db_session: Session, *, workflow_id: int, owner_id: UUID
) -> ResolvedRunContext:
    user = fetch_user_by_id(db_session, owner_id)
    if user is None or not user.is_active:
        raise PulseAccessError("The schedule owner is no longer active")

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
