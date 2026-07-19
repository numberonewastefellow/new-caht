"""Repository (data-access layer) for the SCIM-owned tables.

Clean-room reimplementation. This layer is deliberately narrow: it reads/writes
only the three SCIM tables (``scim_token``, ``scim_user_mapping``,
``scim_team_mapping``). All ``User`` / ``Team`` access lives in the service layer
(``om.server.scim.service``) so this repository has no coupling to the RBAC
models — it deals in plain ids. Callers own the transaction boundary (commit).
"""

from __future__ import annotations

import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import Session

from om.db.models import ScimTeamMapping
from om.db.models import ScimToken
from om.db.models import ScimUserMapping


class ScimRepository:
    """Data access for SCIM tokens and external-id ↔ internal-id mappings."""

    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    # ------------------------------------------------------------------
    # Tokens
    # ------------------------------------------------------------------
    def create_token(
        self,
        *,
        name: str,
        hashed_token: str,
        token_display: str,
        created_by: UUID,
    ) -> ScimToken:
        token = ScimToken(
            name=name,
            hashed_token=hashed_token,
            token_display=token_display,
            created_by=created_by,
            is_active=True,
        )
        self.db.add(token)
        self.db.flush()
        return token

    def get_active_token_by_hash(self, hashed_token: str) -> ScimToken | None:
        return self.db.scalar(
            select(ScimToken).where(
                ScimToken.hashed_token == hashed_token,
                ScimToken.is_active.is_(True),
            )
        )

    def get_token(self, token_id: int) -> ScimToken | None:
        return self.db.get(ScimToken, token_id)

    def list_tokens(self, *, include_inactive: bool = True) -> list[ScimToken]:
        stmt = select(ScimToken).order_by(ScimToken.created_at.desc())
        if not include_inactive:
            stmt = stmt.where(ScimToken.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def count_active_tokens(self) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(ScimToken)
                .where(ScimToken.is_active.is_(True))
            )
            or 0
        )

    def touch_token_last_used(self, token_id: int) -> None:
        self.db.execute(
            update(ScimToken)
            .where(ScimToken.id == token_id)
            .values(last_used_at=datetime.datetime.now(datetime.timezone.utc))
        )

    def revoke_token(self, token_id: int) -> bool:
        """Soft-disable a token. Returns False if it did not exist."""
        token = self.get_token(token_id)
        if token is None:
            return False
        token.is_active = False
        self.db.flush()
        return True

    # ------------------------------------------------------------------
    # User mappings
    # ------------------------------------------------------------------
    def create_user_mapping(
        self, *, external_id: str, user_id: UUID
    ) -> ScimUserMapping:
        mapping = ScimUserMapping(external_id=external_id, user_id=user_id)
        self.db.add(mapping)
        self.db.flush()
        return mapping

    def get_user_mapping_by_external_id(
        self, external_id: str
    ) -> ScimUserMapping | None:
        return self.db.scalar(
            select(ScimUserMapping).where(ScimUserMapping.external_id == external_id)
        )

    def get_user_mapping_by_user_id(self, user_id: UUID) -> ScimUserMapping | None:
        return self.db.scalar(
            select(ScimUserMapping).where(ScimUserMapping.user_id == user_id)
        )

    def update_user_mapping_external_id(
        self, mapping: ScimUserMapping, external_id: str
    ) -> ScimUserMapping:
        mapping.external_id = external_id
        self.db.flush()
        return mapping

    def delete_user_mapping(self, mapping: ScimUserMapping) -> None:
        self.db.delete(mapping)
        self.db.flush()

    def list_user_mappings(self) -> list[ScimUserMapping]:
        return list(self.db.scalars(select(ScimUserMapping)).all())

    def list_user_mappings_for(
        self, user_ids: list[UUID]
    ) -> list[ScimUserMapping]:
        """Mappings for a specific set of users (batch lookup for a page)."""
        if not user_ids:
            return []
        return list(
            self.db.scalars(
                select(ScimUserMapping).where(ScimUserMapping.user_id.in_(user_ids))
            ).all()
        )

    def count_user_mappings(self) -> int:
        return self.db.scalar(select(func.count()).select_from(ScimUserMapping)) or 0

    # ------------------------------------------------------------------
    # Team mappings (SCIM Groups → Teams, Contract 1)
    # ------------------------------------------------------------------
    def create_team_mapping(self, *, external_id: str, team_id: int) -> ScimTeamMapping:
        mapping = ScimTeamMapping(external_id=external_id, team_id=team_id)
        self.db.add(mapping)
        self.db.flush()
        return mapping

    def get_team_mapping_by_external_id(
        self, external_id: str
    ) -> ScimTeamMapping | None:
        return self.db.scalar(
            select(ScimTeamMapping).where(ScimTeamMapping.external_id == external_id)
        )

    def get_team_mapping_by_team_id(self, team_id: int) -> ScimTeamMapping | None:
        return self.db.scalar(
            select(ScimTeamMapping).where(ScimTeamMapping.team_id == team_id)
        )

    def update_team_mapping_external_id(
        self, mapping: ScimTeamMapping, external_id: str
    ) -> ScimTeamMapping:
        mapping.external_id = external_id
        self.db.flush()
        return mapping

    def delete_team_mapping(self, mapping: ScimTeamMapping) -> None:
        self.db.delete(mapping)
        self.db.flush()

    def list_team_mappings(self) -> list[ScimTeamMapping]:
        return list(self.db.scalars(select(ScimTeamMapping)).all())

    def list_team_mappings_for(
        self, team_ids: list[int]
    ) -> list[ScimTeamMapping]:
        """Mappings for a specific set of teams (batch lookup for a page)."""
        if not team_ids:
            return []
        return list(
            self.db.scalars(
                select(ScimTeamMapping).where(ScimTeamMapping.team_id.in_(team_ids))
            ).all()
        )

    def count_team_mappings(self) -> int:
        return self.db.scalar(select(func.count()).select_from(ScimTeamMapping)) or 0
