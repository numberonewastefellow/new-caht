"""Admin API for Teams (Contract 1 base path ``/teams``).

Thin Policy-Enforcement-Point: each handler resolves the caller, asks the
:class:`PermissionService` (PDP) for a decision, enforces it, then delegates the
mutation to :mod:`om.db.team` (which emits the structured audit log).
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from om.access.rbac import AccessDecision
from om.access.rbac import permission_service
from om.auth.users import current_curator_or_admin_user
from om.auth.users import current_user
from om.configs.constants import PUBLIC_API_TAGS
from om.db.team import add_users_to_team
from om.db.team import fetch_teams
from om.db.team import fetch_teams_for_user
from om.db.team import insert_team
from om.db.team import prepare_team_for_deletion
from om.db.team import update_team
from om.db.team import update_user_curator_relationship
from om.db.models import User
from om.db.models import UserRole
from om.server.team.models import AddUsersToTeamRequest
from om.server.team.models import MinimalTeamSnapshot
from om.server.team.models import SetCuratorRequest
from om.server.team.models import Team
from om.server.team.models import TeamCreate
from om.server.team.models import TeamUpdate
from om.tenancy.context import get_tenant_session_dependency
from om.utils.logger import setup_logger

logger = setup_logger()

router = APIRouter(prefix="/teams", tags=PUBLIC_API_TAGS)


def _enforce(decision: AccessDecision) -> None:
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)


@router.get("")
def list_teams(
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> list[Team]:
    if user.role == UserRole.ADMIN:
        teams = fetch_teams(db_session, only_up_to_date=False)
    else:
        teams = fetch_teams_for_user(
            db_session=db_session,
            user_id=user.id,
            only_curator_teams=user.role == UserRole.CURATOR,
        )
    return [Team.from_model(team) for team in teams]


@router.get("/minimal")
def list_minimal_teams(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> list[MinimalTeamSnapshot]:
    if user.role == UserRole.ADMIN:
        teams = fetch_teams(db_session, only_up_to_date=False)
    else:
        teams = fetch_teams_for_user(db_session=db_session, user_id=user.id)
    return [MinimalTeamSnapshot.from_model(team) for team in teams]


@router.post("")
def create_team(
    team: TeamCreate,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> Team:
    _enforce(permission_service.decide_create_team(user))
    try:
        db_team = insert_team(
            db_session,
            name=team.name,
            user_ids=team.user_ids,
            cc_pair_ids=team.cc_pair_ids,
            actor_user_id=str(user.id),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail=f"A team named '{team.name}' already exists. Choose a different name.",
        )
    return Team.from_model(db_team)


@router.patch("/{team_id}")
def patch_team(
    team_id: int,
    team_update: TeamUpdate,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> Team:
    _enforce(permission_service.decide_edit_team(user, team_id, db_session))
    try:
        return Team.from_model(
            update_team(
                db_session=db_session,
                team_id=team_id,
                user_ids=team_update.user_ids,
                cc_pair_ids=team_update.cc_pair_ids,
                actor_user_id=str(user.id),
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{team_id}/add-users")
def add_users(
    team_id: int,
    add_users_request: AddUsersToTeamRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> Team:
    _enforce(permission_service.decide_manage_members(user, team_id, db_session))
    try:
        return Team.from_model(
            add_users_to_team(
                db_session=db_session,
                team_id=team_id,
                user_ids=add_users_request.user_ids,
                actor_user_id=str(user.id),
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{team_id}/set-curator")
def set_user_curator(
    team_id: int,
    set_curator_request: SetCuratorRequest,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> None:
    _enforce(permission_service.decide_manage_curators(user, team_id, db_session))
    try:
        update_user_curator_relationship(
            db_session=db_session,
            team_id=team_id,
            user_id=set_curator_request.user_id,
            is_curator=set_curator_request.is_curator,
            actor_user_id=str(user.id),
        )
    except ValueError as e:
        logger.error("Error setting team curator: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}")
def delete_team_endpoint(
    team_id: int,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_tenant_session_dependency),
) -> None:
    _enforce(permission_service.decide_delete_team(user))
    try:
        prepare_team_for_deletion(db_session, team_id, actor_user_id=str(user.id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
