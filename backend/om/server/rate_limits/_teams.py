"""Team-membership resolution bridge (Contract 1).

TEAM-scoped policies need the set of teams a user belongs to, resolved via the
``user__team`` association (``team_id``). We resolve through the ORM model (never raw
SQL) so the tenant ``schema_translate_map`` applies and the query stays inside the
tenant schema (Contract 3).
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from om.db.models import User__Team as _UserTeamLink

_TEAM_ID_ATTR = "team_id"


def team_ids_for_user(db_session: Session, user_id: UUID) -> Sequence[int]:
    """Return the ids of every team the user is a member of (empty if none)."""
    team_id_column = getattr(_UserTeamLink, _TEAM_ID_ATTR)
    rows = db_session.execute(
        select(team_id_column).where(_UserTeamLink.user_id == user_id)
    ).all()
    return [row[0] for row in rows]
