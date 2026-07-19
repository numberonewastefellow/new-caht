"""Repository for the SAML SSO session ledger (``sso_saml_session``).

Maps an issued session cookie → user with an expiry so SAML sessions are
auditable and revocable. Unlike the dead legacy ``saml`` table, this ledger is
actually written on ACS login and expired on SP logout. Caller supplies a
tenant-scoped ``Session`` (Contract 3).
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import Session

from om.configs.app_configs import SESSION_EXPIRE_TIME_SECONDS
from om.db.models import SsoSamlSession
from om.db.models import User


def upsert_saml_session(
    db_session: Session,
    user_id: uuid.UUID,
    cookie: str,
    expiration_offset_seconds: int = SESSION_EXPIRE_TIME_SECONDS,
) -> datetime.datetime:
    """Record (or refresh) the cookie↔user mapping. Returns the expiry.

    A user has at most one active SAML session row (``user_id`` is unique); a new
    login overwrites the previous cookie and pushes the expiry forward. Commits.
    """
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        seconds=expiration_offset_seconds
    )

    row = db_session.scalars(
        select(SsoSamlSession).where(SsoSamlSession.user_id == user_id)
    ).first()
    if row is None:
        row = SsoSamlSession(
            user_id=user_id,
            encrypted_cookie=cookie,
            expires_at=expires_at,
        )
        db_session.add(row)
    else:
        row.encrypted_cookie = cookie
        row.expires_at = expires_at

    db_session.commit()
    return expires_at


def get_last_saml_session(
    db_session: Session,
) -> tuple[str, datetime.datetime] | None:
    """Return ``(email, updated_at)`` of the most recently touched SAML session.

    The ledger row is only written on a successful ACS login, so its presence is
    proof that SAML login has worked at least once for this tenant.
    """
    row = db_session.execute(
        select(User.email, SsoSamlSession.updated_at)
        .join(User, User.id == SsoSamlSession.user_id)
        .order_by(SsoSamlSession.updated_at.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    return row[0], row[1]


def expire_saml_sessions_for_user(db_session: Session, user_id: uuid.UUID) -> int:
    """Mark all of a user's SAML sessions expired (logout). Returns rows touched."""
    result = db_session.execute(
        update(SsoSamlSession)
        .where(SsoSamlSession.user_id == user_id)
        .values(expires_at=func.now())
    )
    db_session.commit()
    return result.rowcount or 0
