"""Subscription detection for Build Mode rate limiting."""

from sqlalchemy.orm import Session

from om.configs.app_configs import DEV_MODE
from om.db.models import User
from om.server.usage_limits import is_tenant_on_trial_fn
from om.utils.logger import setup_logger
from shared_configs.configs import MULTI_TENANT
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()


def is_user_subscribed(user: User, db_session: Session) -> bool:  # noqa: ARG001
    """
    Check whether a user should be treated as having full (non-trial) access.

    WS-A: billing/subscriptions were removed (no external billing/control plane),
    so ``is_tenant_on_trial_fn`` now always reports "not on trial". Every
    authenticated user is therefore treated as subscribed; only an unauthenticated
    user (``user is None``) is non-subscribed. WS-F owns any future usage/trial
    redesign that would change this.

    Args:
        user: The user object (None for unauthenticated users)
        db_session: Database session

    Returns:
        True if the user should get full access, False otherwise
    """
    if DEV_MODE:
        return True

    if user is None:
        return False

    if MULTI_TENANT:
        # WS-A: billing removed — is_tenant_on_trial_fn always reports "not on
        # trial", so every authenticated MT user is treated as subscribed.
        tenant_id = get_current_tenant_id()
        try:
            on_trial = is_tenant_on_trial_fn(tenant_id)
            # Subscribed = NOT on trial
            return not on_trial
        except Exception as e:
            logger.warning(f"Subscription check failed for tenant {tenant_id}: {e}")
            # Default to non-subscribed (safer/more restrictive)
            return False

    return True
