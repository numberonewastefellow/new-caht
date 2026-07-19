"""Data-access layer for teams and team-scoped grants.

Every method takes a caller-supplied, already tenant-bound :class:`Session`
(from ``om.tenancy.context``). It never opens its own session and never reads the
tenant from anywhere global — so it is **multi-tenant-safe by construction**:
whatever schema the caller's session is bound to is the only data it can touch.

This is the repository half of the services/repositories split — pure queries,
no policy. Policy lives in :class:`om.access.rbac.service.PermissionService`.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from om.db.models import Agent__Team
from om.db.models import Credential__Team
from om.db.models import DocumentSet__Team
from om.db.models import LLMProvider__Team
from om.db.models import Team
from om.db.models import Team__ConnectorCredentialPair
from om.db.models import User__Team


class TeamRepository:
    """Read queries for teams, memberships, and resource -> team grant edges."""

    # ---- teams ---------------------------------------------------------------

    def get(self, db: Session, team_id: int) -> Team | None:
        return db.scalar(select(Team).where(Team.id == team_id))

    def get_by_name(self, db: Session, name: str) -> Team | None:
        return db.scalar(select(Team).where(Team.name == name))

    def list_all(self, db: Session) -> list[Team]:
        return list(db.scalars(select(Team).order_by(Team.name)))

    def list_by_ids(self, db: Session, team_ids: Sequence[int]) -> list[Team]:
        if not team_ids:
            return []
        return list(db.scalars(select(Team).where(Team.id.in_(team_ids))))

    # ---- memberships ---------------------------------------------------------

    def teams_for_user(self, db: Session, user_id: UUID) -> list[Team]:
        """All teams the user belongs to (member or curator)."""
        stmt = (
            select(Team)
            .join(User__Team, User__Team.team_id == Team.id)
            .where(User__Team.user_id == user_id)
            .order_by(Team.name)
        )
        return list(db.scalars(stmt))

    def member_team_ids(self, db: Session, user_id: UUID) -> set[int]:
        stmt = select(User__Team.team_id).where(User__Team.user_id == user_id)
        return set(db.scalars(stmt))

    def curated_team_ids(self, db: Session, user_id: UUID) -> set[int]:
        """Teams for which the user has the team-scoped curator flag set."""
        stmt = select(User__Team.team_id).where(
            User__Team.user_id == user_id,
            User__Team.is_curator.is_(True),
        )
        return set(db.scalars(stmt))

    def is_member(self, db: Session, user_id: UUID, team_id: int) -> bool:
        stmt = select(User__Team.team_id).where(
            User__Team.user_id == user_id, User__Team.team_id == team_id
        )
        return db.scalar(stmt) is not None

    def is_curator(self, db: Session, user_id: UUID, team_id: int) -> bool:
        stmt = select(User__Team.team_id).where(
            User__Team.user_id == user_id,
            User__Team.team_id == team_id,
            User__Team.is_curator.is_(True),
        )
        return db.scalar(stmt) is not None

    def member_ids(self, db: Session, team_id: int) -> set[UUID]:
        stmt = select(User__Team.user_id).where(User__Team.team_id == team_id)
        return {uid for uid in db.scalars(stmt) if uid is not None}

    # ---- resource -> team grant edges ---------------------------------------
    # "Which teams is this resource granted to?" Used to decide whether a curator
    # (who curates one of those teams) may act on the resource.

    def teams_for_document_set(self, db: Session, document_set_id: int) -> set[int]:
        stmt = select(DocumentSet__Team.team_id).where(
            DocumentSet__Team.document_set_id == document_set_id
        )
        return set(db.scalars(stmt))

    def teams_for_cc_pair(self, db: Session, cc_pair_id: int) -> set[int]:
        stmt = select(Team__ConnectorCredentialPair.team_id).where(
            Team__ConnectorCredentialPair.cc_pair_id == cc_pair_id
        )
        return set(db.scalars(stmt))

    def teams_for_credential(self, db: Session, credential_id: int) -> set[int]:
        stmt = select(Credential__Team.team_id).where(
            Credential__Team.credential_id == credential_id
        )
        return set(db.scalars(stmt))

    def teams_for_agent(self, db: Session, agent_id: int) -> set[int]:
        stmt = select(Agent__Team.team_id).where(Agent__Team.agent_id == agent_id)
        return set(db.scalars(stmt))

    def teams_for_llm_provider(self, db: Session, llm_provider_id: int) -> set[int]:
        stmt = select(LLMProvider__Team.team_id).where(
            LLMProvider__Team.llm_provider_id == llm_provider_id
        )
        return set(db.scalars(stmt))
