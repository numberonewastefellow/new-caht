"""Persistence for externally-synced group memberships.

Connectors that sync source-system permissions yield :class:`ExternalUserGroup`
objects (an external IdP/source "group" + its member emails). Those are stored,
namespaced per source, as **external-team** principals:

* ``user__external_team_id`` — (user, external_team_id, cc_pair) membership rows.
* ``public_external_team``   — external groups that grant "anyone" access.

At query time :func:`fetch_external_teams_for_user` expands a user into their
external-team principals, which :func:`om.access.access.get_acl_for_user` renders
as ``external_team:<id>`` and matches against each document's ACL.
"""

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import Session

from om.access.utils import build_ext_team_name_for_om
from om.configs.constants import DocumentSource
from om.db.models import PublicExternalTeam
from om.db.models import User
from om.db.models import User__ExternalTeamId
from om.db.users import batch_add_ext_perm_user_if_not_exists
from om.db.users import get_user_by_email
from om.utils.logger import setup_logger

logger = setup_logger()


class ExternalUserGroup(BaseModel):
    """An external source/IdP group ingested by a connector's group-sync."""

    id: str
    user_emails: list[str]
    # `True` e.g. for a Google Drive folder giving domain-wide / "anyone with
    # link" access. When set, `user_emails` is irrelevant and the group is stored
    # as a public-external-team row rather than a membership set.
    gives_anyone_access: bool = False


def delete_user__ext_team_for_user__no_commit(db_session: Session, user_id: UUID) -> None:
    db_session.execute(
        delete(User__ExternalTeamId).where(User__ExternalTeamId.user_id == user_id)
    )


def delete_user__ext_team_for_cc_pair__no_commit(
    db_session: Session, cc_pair_id: int
) -> None:
    db_session.execute(
        delete(User__ExternalTeamId).where(User__ExternalTeamId.cc_pair_id == cc_pair_id)
    )


def delete_public_external_team_for_cc_pair__no_commit(
    db_session: Session, cc_pair_id: int
) -> None:
    db_session.execute(
        delete(PublicExternalTeam).where(PublicExternalTeam.cc_pair_id == cc_pair_id)
    )


def mark_old_external_groups_as_stale(db_session: Session, cc_pair_id: int) -> None:
    db_session.execute(
        update(User__ExternalTeamId)
        .where(User__ExternalTeamId.cc_pair_id == cc_pair_id)
        .values(stale=True)
    )
    db_session.execute(
        update(PublicExternalTeam)
        .where(PublicExternalTeam.cc_pair_id == cc_pair_id)
        .values(stale=True)
    )


def upsert_external_groups(
    db_session: Session,
    cc_pair_id: int,
    external_groups: list[ExternalUserGroup],
    source: DocumentSource,
) -> None:
    """Upsert external-team membership (and public-external-team) rows, clearing
    the ``stale`` flag on rows that are still present so a later
    :func:`remove_stale_external_groups` sweep only removes departed ones.
    """
    if not external_groups:
        return

    all_member_emails: set[str] = set()
    for external_group in external_groups:
        all_member_emails.update(external_group.user_emails)

    members: list[User] = batch_add_ext_perm_user_if_not_exists(
        db_session=db_session, emails=list(all_member_emails)
    )
    email_to_id = {user.email.lower(): user.id for user in members}

    for external_group in external_groups:
        external_team_id = build_ext_team_name_for_om(
            external_group_name=external_group.id, source=source
        )

        for user_email in external_group.user_emails:
            user_id = email_to_id.get(user_email.lower())
            if user_id is None:
                logger.warning(
                    "User %s in group %s not found", user_email, external_group.id
                )
                continue

            existing = db_session.scalar(
                select(User__ExternalTeamId).where(
                    User__ExternalTeamId.user_id == user_id,
                    User__ExternalTeamId.external_team_id == external_team_id,
                    User__ExternalTeamId.cc_pair_id == cc_pair_id,
                )
            )
            if existing:
                existing.stale = False
            else:
                db_session.add(
                    User__ExternalTeamId(
                        user_id=user_id,
                        external_team_id=external_team_id,
                        cc_pair_id=cc_pair_id,
                        stale=False,
                    )
                )

        if external_group.gives_anyone_access:
            existing_public = db_session.scalar(
                select(PublicExternalTeam).where(
                    PublicExternalTeam.external_team_id == external_team_id,
                    PublicExternalTeam.cc_pair_id == cc_pair_id,
                )
            )
            if existing_public:
                existing_public.stale = False
            else:
                db_session.add(
                    PublicExternalTeam(
                        external_team_id=external_team_id,
                        cc_pair_id=cc_pair_id,
                        stale=False,
                    )
                )

    db_session.commit()


def remove_stale_external_groups(db_session: Session, cc_pair_id: int) -> None:
    db_session.execute(
        delete(User__ExternalTeamId).where(
            User__ExternalTeamId.cc_pair_id == cc_pair_id,
            User__ExternalTeamId.stale.is_(True),
        )
    )
    db_session.execute(
        delete(PublicExternalTeam).where(
            PublicExternalTeam.cc_pair_id == cc_pair_id,
            PublicExternalTeam.stale.is_(True),
        )
    )
    db_session.commit()


def fetch_external_teams_for_user(
    db_session: Session, user_id: UUID
) -> Sequence[User__ExternalTeamId]:
    return db_session.scalars(
        select(User__ExternalTeamId).where(User__ExternalTeamId.user_id == user_id)
    ).all()


def fetch_external_teams_for_user_email_and_team_ids(
    db_session: Session,
    user_email: str,
    team_ids: list[str],
) -> list[User__ExternalTeamId]:
    user = get_user_by_email(db_session=db_session, email=user_email)
    if user is None:
        return []
    return list(
        db_session.scalars(
            select(User__ExternalTeamId).where(
                User__ExternalTeamId.user_id == user.id,
                User__ExternalTeamId.external_team_id.in_(team_ids),
            )
        ).all()
    )


def fetch_public_external_team_ids(db_session: Session) -> list[str]:
    return list(db_session.scalars(select(PublicExternalTeam.external_team_id)).all())
