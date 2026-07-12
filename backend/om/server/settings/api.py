from typing import cast

from fastapi import APIRouter
from fastapi import Depends
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from om.configs.app_configs import LICENSE_ENFORCEMENT_ENABLED
from om.auth.users import current_admin_user
from om.auth.users import current_user
from om.auth.users import is_user_admin
from om.configs.app_configs import DISABLE_VECTOR_DB
from om.configs.app_configs import ENTERPRISE_EDITION_ENABLED
from om.configs.constants import KV_REINDEX_KEY
from om.configs.constants import NotificationType
from om.db.engine.sql_engine import get_session
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.license import get_cached_license_metadata
from om.db.license import refresh_license_cache
from om.db.models import User
from om.db.notification import dismiss_all_notifications
from om.db.notification import get_notifications
from om.db.notification import update_notification_last_shown
from om.key_value_store.factory import get_kv_store
from om.key_value_store.interface import KvKeyNotFoundError
from om.server.features.build.utils import is_onyx_craft_enabled
from om.server.settings.models import ApplicationStatus
from om.server.settings.models import Notification
from om.server.settings.models import Settings
from om.server.settings.models import UserSettings
from om.server.settings.store import load_settings
from om.server.settings.store import store_settings
from om.utils.logger import setup_logger
from om.utils.variable_functionality import (
    fetch_versioned_implementation_with_fallback,
)
from shared_configs.configs import MULTI_TENANT
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()

# Only GATED_ACCESS actually blocks access - other statuses are for notifications
_BLOCKING_STATUS = ApplicationStatus.GATED_ACCESS

admin_router = APIRouter(prefix="/admin/settings")
basic_router = APIRouter(prefix="/settings")


@admin_router.put("")
def admin_put_settings(
    settings: Settings, _: User = Depends(current_admin_user)
) -> None:
    store_settings(settings)


def check_ee_features_enabled() -> bool:
    """Checks if EE features should be available.

    Returns True if:
    - LICENSE_ENFORCEMENT_ENABLED is False (legacy/rollout mode)
    - Cloud mode (MULTI_TENANT) - cloud handles its own gating
    - Self-hosted with a valid (non-expired) license

    Returns False if:
    - Self-hosted with no license (never subscribed)
    - Self-hosted with expired license
    """
    if not LICENSE_ENFORCEMENT_ENABLED:
        # License enforcement disabled - allow EE features (legacy behavior)
        return True

    if MULTI_TENANT:
        # Cloud mode - EE features always available (gating handled by is_tenant_gated)
        return True

    # Self-hosted with enforcement - check for valid license
    tenant_id = get_current_tenant_id()
    try:
        metadata = get_cached_license_metadata(tenant_id)
        if not metadata:
            # Cache miss — warm from DB so cold-start doesn't block EE features
            try:
                with get_session_with_current_tenant() as db_session:
                    metadata = refresh_license_cache(db_session, tenant_id)
            except SQLAlchemyError as db_error:
                logger.warning(f"Failed to load license from DB: {db_error}")

        if metadata and metadata.status != _BLOCKING_STATUS:
            # Has a valid license (GRACE_PERIOD/PAYMENT_REMINDER still allow EE features)
            return True
    except RedisError as e:
        logger.warning(f"Failed to check license for EE features: {e}")
        # Fail closed - if Redis is down, other things will break anyway
        return False

    # No license or GATED_ACCESS - no EE features
    return False


def apply_license_status_to_settings(settings: Settings) -> Settings:
    """Checks license status for self-hosted deployments.

    For self-hosted, looks up license metadata and overrides application_status
    if the license indicates GATED_ACCESS (fully expired).

    Also sets ee_features_enabled based on license status to control
    visibility of EE features in the UI.

    For multi-tenant (cloud), the settings already have the correct status
    from the control plane, so no override is needed.

    If LICENSE_ENFORCEMENT_ENABLED is false, ee_features_enabled is set to True
    (since EE code was loaded via ENABLE_PAID_ENTERPRISE_EDITION_FEATURES).
    """
    if not LICENSE_ENFORCEMENT_ENABLED:
        # License enforcement disabled - EE code is loaded via
        # ENABLE_PAID_ENTERPRISE_EDITION_FEATURES, so EE features are on
        settings.ee_features_enabled = True
        return settings

    if MULTI_TENANT:
        # Cloud mode - EE features always available (gating handled by is_tenant_gated)
        settings.ee_features_enabled = True
        return settings

    tenant_id = get_current_tenant_id()
    try:
        metadata = get_cached_license_metadata(tenant_id)
        if not metadata:
            # Cache miss (e.g. after TTL expiry). Fall back to DB so
            # the /settings request doesn't falsely return GATED_ACCESS
            # while the cache is cold.
            try:
                with get_session_with_current_tenant() as db_session:
                    metadata = refresh_license_cache(db_session, tenant_id)
            except SQLAlchemyError as db_error:
                logger.warning(
                    f"Failed to load license from DB for settings: {db_error}"
                )

        if metadata:
            if metadata.status == _BLOCKING_STATUS:
                settings.application_status = metadata.status
                settings.ee_features_enabled = False
            else:
                # Has a valid license (GRACE_PERIOD/PAYMENT_REMINDER still allow EE features)
                settings.ee_features_enabled = True
        else:
            # No license found in cache or DB.
            if ENTERPRISE_EDITION_ENABLED:
                # Legacy EE flag is set → prior EE usage (e.g. permission
                # syncing) means indexed data may need protection.
                settings.application_status = _BLOCKING_STATUS
            settings.ee_features_enabled = False
    except RedisError as e:
        logger.warning(f"Failed to check license metadata for settings: {e}")
        # Fail closed - disable EE features if we can't verify license
        settings.ee_features_enabled = False

    return settings


@basic_router.get("")
def fetch_settings(
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
) -> UserSettings:
    """Settings and notifications are stuffed into this single endpoint to reduce number of
    Postgres calls"""
    general_settings = load_settings()
    settings_notifications = get_settings_notifications(user, db_session)

    try:
        kv_store = get_kv_store()
        needs_reindexing = cast(bool, kv_store.load(KV_REINDEX_KEY))
    except KvKeyNotFoundError:
        needs_reindexing = False

    apply_fn = fetch_versioned_implementation_with_fallback(
        "om.server.settings.api",
        "apply_license_status_to_settings",
        apply_license_status_to_settings,
    )
    general_settings = apply_fn(general_settings)

    # Check if Onyx Craft is enabled for this user (used for server-side redirects)
    onyx_craft_enabled_for_user = is_onyx_craft_enabled(user) if user else False

    return UserSettings(
        **general_settings.model_dump(),
        notifications=settings_notifications,
        needs_reindexing=needs_reindexing,
        onyx_craft_enabled=onyx_craft_enabled_for_user,
        vector_db_enabled=not DISABLE_VECTOR_DB,
    )


def get_settings_notifications(user: User, db_session: Session) -> list[Notification]:
    """Get notifications for settings page, including product gating and reindex notifications"""
    # Check for product gating notification
    product_notif = get_notifications(
        user=None,
        notif_type=NotificationType.TRIAL_ENDS_TWO_DAYS,
        db_session=db_session,
    )
    notifications = [Notification.from_model(product_notif[0])] if product_notif else []

    # Only show reindex notifications to admins
    if not is_user_admin(user):
        return notifications

    # Check if reindexing is needed
    kv_store = get_kv_store()
    try:
        needs_index = cast(bool, kv_store.load(KV_REINDEX_KEY))
        if not needs_index:
            dismiss_all_notifications(
                notif_type=NotificationType.REINDEX, db_session=db_session
            )
            return notifications
    except KvKeyNotFoundError:
        # If something goes wrong and the flag is gone, better to not start a reindexing
        # it's a heavyweight long running job and maybe this flag is cleaned up later
        logger.warning("Could not find reindex flag")
        return notifications

    try:
        # Need a transaction in order to prevent under-counting current notifications
        reindex_notifs = get_notifications(
            user=user, notif_type=NotificationType.REINDEX, db_session=db_session
        )

        if len(reindex_notifs) > 1:
            logger.error("User has multiple reindex notifications")
        elif not reindex_notifs:
            return notifications

        reindex_notif = reindex_notifs[0]
        update_notification_last_shown(
            notification=reindex_notif, db_session=db_session
        )

        db_session.commit()
        notifications.append(Notification.from_model(reindex_notif))
        return notifications
    except SQLAlchemyError:
        logger.exception("Error while processing notifications")
        db_session.rollback()
        return notifications
