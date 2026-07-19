"""Subscription detection for Build Mode rate limiting."""

from sqlalchemy.orm import Session

from om.configs.app_configs import DEV_MODE
from om.db.models import User


def is_user_subscribed(user: User | None, db_session: Session) -> bool:  # noqa: ARG001
    """Whether a user gets full (non-trial) Build-mode rate-limit access.

    This is a self-hosted deployment with no billing/subscriptions, so every
    authenticated user is treated as fully subscribed; only an unauthenticated
    user (``user is None``) is not. ``DEV_MODE`` always grants full access.
    """
    if DEV_MODE:
        return True

    return user is not None
