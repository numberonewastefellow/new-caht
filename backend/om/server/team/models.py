from uuid import UUID

from pydantic import BaseModel

from om.db.models import Team as TeamModel
from om.server.documents.models import ConnectorCredentialPairDescriptor
from om.server.documents.models import ConnectorSnapshot
from om.server.documents.models import CredentialSnapshot
from om.server.features.document_set.models import DocumentSet
from om.server.features.agent.models import AgentSnapshot
from om.server.manage.models import UserInfo
from om.server.manage.models import UserPreferences


class Team(BaseModel):
    id: int
    name: str
    users: list[UserInfo]
    curator_ids: list[UUID]
    cc_pairs: list[ConnectorCredentialPairDescriptor]
    document_sets: list[DocumentSet]
    agents: list[AgentSnapshot]
    is_up_to_date: bool
    is_up_for_deletion: bool

    @classmethod
    def from_model(cls, team_model: TeamModel) -> "Team":
        return cls(
            id=team_model.id,
            name=team_model.name,
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
            curator_ids=[
                user.user_id
                for user in team_model.team_relationships
                if user.is_curator and user.user_id is not None
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
            document_sets=[
                DocumentSet.from_model(ds) for ds in team_model.document_sets
            ],
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


class TeamUpdate(BaseModel):
    user_ids: list[UUID]
    cc_pair_ids: list[int]


class AddUsersToTeamRequest(BaseModel):
    user_ids: list[UUID]


class SetCuratorRequest(BaseModel):
    user_id: UUID
    is_curator: bool
