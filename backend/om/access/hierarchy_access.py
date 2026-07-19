"""External-team principals for hierarchy browse filtering.

A user's hierarchy-browse view is filtered by public / email-list /
group-overlap predicates (see ``om.db.hierarchy``). The group-overlap side needs
the set of external-team ids the user belongs to; this module resolves it.
"""

from sqlalchemy.orm import Session

from om.db.external_perm import fetch_external_teams_for_user
from om.db.models import User


def get_user_external_group_ids(db_session: Session, user: User | None) -> list[str]:
    """The external-team ids (source-synced group memberships) a user belongs to.

    Signature kept stable for the hierarchy browse callers; the returned values
    are the team-namespaced ``external_team_id`` strings.
    """
    if user is None:
        return []
    memberships = fetch_external_teams_for_user(db_session, user.id)
    return [membership.external_team_id for membership in memberships]
