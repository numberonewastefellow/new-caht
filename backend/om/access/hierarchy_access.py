from sqlalchemy.orm import Session

from om.db.external_perm import fetch_external_groups_for_user
from om.db.models import User
from om.utils.variable_functionality import fetch_versioned_implementation


def _get_user_external_group_ids(db_session: Session, user: User) -> list[str]:
    if not user:
        return []
    external_groups = fetch_external_groups_for_user(db_session, user.id)
    return [external_group.external_user_group_id for external_group in external_groups]


def get_user_external_group_ids(db_session: Session, user: User) -> list[str]:
    versioned_get_user_external_group_ids = fetch_versioned_implementation(
        "om.access.hierarchy_access", "_get_user_external_group_ids"
    )
    return versioned_get_user_external_group_ids(db_session, user)
