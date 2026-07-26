from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.db.enums import MembershipSource
from om.db.enums import TeamRole
from om.db.models import Team as TeamModel
from om.db.models import User
from om.db.models import User__Team
from om.server.documents.models import ConnectorCredentialPairDescriptor
from om.server.documents.models import ConnectorSnapshot
from om.server.documents.models import CredentialSnapshot
from om.server.features.document_set.models import DocumentSet
from om.server.features.agent.models import AgentSnapshot
from om.server.manage.models import UserInfo
from om.server.manage.models import UserPreferences


def _display_name(user: User) -> str:
    """Best-effort human name: the user's personal name if set, else the local
    part of their email (which always exists)."""
    if user.personal_name:
        return user.personal_name
    return user.email.split("@")[0]


class TeamMemberSnapshot(BaseModel):
    """A single team membership joined with its user (see contract `members`)."""

    id: str
    name: str
    email: str
    role: TeamRole
    joined_at: datetime | None
    source: MembershipSource


class TeamOwnerSnapshot(BaseModel):
    id: str
    name: str
    email: str

    @classmethod
    def from_user(cls, user: User) -> "TeamOwnerSnapshot":
        return cls(id=str(user.id), name=_display_name(user), email=user.email)


class Team(BaseModel):
    id: int
    name: str
    description: str | None
    is_public: bool
    tags: list[str]
    owner: TeamOwnerSnapshot | None
    member_count: int
    kb_count: int
    members: list[TeamMemberSnapshot]
    # Back-compat: legacy member list consumed by the old Teams pages
    # (TeamsTable, [teamId]/GroupDisplay) + the Resources tab. Superset of
    # `members`; remove once those pages are retired.
    users: list[UserInfo]
    default_member_role: TeamRole
    allow_guest_access: bool
    curator_ids: list[UUID]
    cc_pairs: list[ConnectorCredentialPairDescriptor]
    document_sets: list[DocumentSet]
    agents: list[AgentSnapshot]
    is_up_to_date: bool
    is_up_for_deletion: bool

    @classmethod
    def from_model(cls, team_model: TeamModel, db_session: Session) -> "Team":
        # ONE query joins each membership row to its user (avoids N+1 across the
        # member list).
        # .unique() is required because User.oauth_accounts is a joined
        # eager-load collection, which duplicates the joined rows.
        member_rows = (
            db_session.execute(
                select(User__Team, User)
                .join(User, User.id == User__Team.user_id)
                .where(User__Team.team_id == team_model.id)
            )
            .unique()
            .all()
        )
        members = [
            TeamMemberSnapshot(
                id=str(user.id),
                name=_display_name(user),
                email=user.email,
                role=TeamRole(membership.role),
                joined_at=membership.joined_at,
                source=MembershipSource(membership.source),
            )
            for membership, user in member_rows
        ]

        document_sets = [DocumentSet.from_model(ds) for ds in team_model.document_sets]

        return cls(
            id=team_model.id,
            name=team_model.name,
            description=team_model.description,
            is_public=team_model.is_public,
            tags=team_model.tags or [],
            owner=(
                TeamOwnerSnapshot.from_user(team_model.owner)
                if team_model.owner is not None
                else None
            ),
            member_count=len(members),
            kb_count=len(document_sets),
            members=members,
            users=[
                UserInfo(
                    id=str(user.id),
                    email=user.email,
                    is_active=user.is_active,
                    is_superuser=user.is_superuser,
                    is_verified=user.is_verified,
                    role=user.role,
                    preferences=UserPreferences(
                        default_model=user.default_model,
                        chosen_assistants=user.chosen_assistants,
                    ),
                )
                for user in team_model.users
            ],
            default_member_role=TeamRole(team_model.default_member_role),
            allow_guest_access=team_model.allow_guest_access,
            curator_ids=[
                membership.user_id
                for membership in team_model.team_relationships
                if membership.is_curator and membership.user_id is not None
            ],
            cc_pairs=[
                ConnectorCredentialPairDescriptor(
                    id=cc_pair_relationship.cc_pair.id,
                    name=cc_pair_relationship.cc_pair.name,
                    connector=ConnectorSnapshot.from_connector_db_model(
                        cc_pair_relationship.cc_pair.connector
                    ),
                    credential=CredentialSnapshot.from_credential_db_model(
                        cc_pair_relationship.cc_pair.credential
                    ),
                    access_type=cc_pair_relationship.cc_pair.access_type,
                )
                for cc_pair_relationship in team_model.cc_pair_relationships
                if cc_pair_relationship.is_current
            ],
            document_sets=document_sets,
            agents=[
                AgentSnapshot.from_model(agent)
                for agent in team_model.agents
                if not agent.deleted
            ],
            is_up_to_date=team_model.is_up_to_date,
            is_up_for_deletion=team_model.is_up_for_deletion,
        )


class MinimalTeamSnapshot(BaseModel):
    id: int
    name: str

    @classmethod
    def from_model(cls, team_model: TeamModel) -> "MinimalTeamSnapshot":
        return cls(
            id=team_model.id,
            name=team_model.name,
        )


class TeamCreate(BaseModel):
    name: str
    user_ids: list[UUID]
    cc_pair_ids: list[int]
    description: str | None = None
    is_public: bool = False
    tags: list[str] | None = None


class TeamUpdate(BaseModel):
    # All optional: only fields explicitly supplied are applied (partial update).
    user_ids: list[UUID] | None = None
    cc_pair_ids: list[int] | None = None
    description: str | None = None
    is_public: bool | None = None
    tags: list[str] | None = None
    default_member_role: TeamRole | None = None
    allow_guest_access: bool | None = None


class AddUsersToTeamRequest(BaseModel):
    user_ids: list[UUID]
    role: TeamRole | None = None


class SetCuratorRequest(BaseModel):
    user_id: UUID
    is_curator: bool


class SetRoleRequest(BaseModel):
    user_id: UUID
    role: TeamRole
