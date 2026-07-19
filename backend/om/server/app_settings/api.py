"""Application settings API (clean-room replacement for enterprise-settings).

Serves the ``enterpriseSettings`` object the web reads for gating/whitelabel,
backed by the typed ``app_settings`` table instead of a KV blob. Paths mirror the
prior enterprise-settings surface so the web boot / gating flow is unaffected:

- ``GET  /enterprise-settings``                        (public read for gating)
- ``PUT  /admin/enterprise-settings``                  (admin)
- ``GET  /enterprise-settings/custom-analytics-script`` (public)
- ``PUT  /admin/enterprise-settings/custom-analytics-script`` (admin)
- ``GET  /enterprise-settings/logo`` / ``/logotype``   (public branding)
- ``PUT  /admin/enterprise-settings/logo``             (admin)

Public GET endpoints carry no auth dependency (branding must load pre-login in
single-tenant); they are declared in the public-endpoint spec (see the auth_check
snippet in the module README). In multi-tenant mode the tenant-bound
``get_session`` dependency 401s an unauthenticated caller, which the web tolerates.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Response
from fastapi import UploadFile
from sqlalchemy.orm import Session

from om.auth.users import current_admin_user
from om.db.engine.sql_engine import get_session
from om.db.models import User
from om.server.analytics.structured_logging import log_structured_event
from om.server.app_settings.logo import fetch_logo_response
from om.server.app_settings.logo import save_logo
from om.server.app_settings.models import AppSettingsSchema
from om.server.app_settings.models import CustomAnalyticsScriptPayload
from om.server.app_settings.service import AppSettingsService

admin_router = APIRouter(prefix="/admin/enterprise-settings")
basic_router = APIRouter(prefix="/enterprise-settings")


# --------------------------------------------------------------------------- #
# Settings blob
# --------------------------------------------------------------------------- #
@basic_router.get("")
def fetch_settings(
    db_session: Session = Depends(get_session),
) -> AppSettingsSchema:
    return AppSettingsService(db_session).load()


@admin_router.put("")
def update_settings(
    settings: AppSettingsSchema,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> AppSettingsSchema:
    return AppSettingsService(db_session).save(settings, actor_user_id=str(user.id))


# --------------------------------------------------------------------------- #
# Custom analytics script
# --------------------------------------------------------------------------- #
@basic_router.get("/custom-analytics-script")
def fetch_custom_analytics_script(
    db_session: Session = Depends(get_session),
) -> str | None:
    return AppSettingsService(db_session).get_custom_analytics_script()


@admin_router.put("/custom-analytics-script")
def update_custom_analytics_script(
    payload: CustomAnalyticsScriptPayload,
    user: User = Depends(current_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    AppSettingsService(db_session).set_custom_analytics_script(
        payload.script, actor_user_id=str(user.id)
    )


# --------------------------------------------------------------------------- #
# Logo assets
# --------------------------------------------------------------------------- #
@admin_router.put("/logo")
def upload_logo(
    file: UploadFile,
    is_logotype: bool = False,
    user: User = Depends(current_admin_user),
) -> None:
    save_logo(file, is_logotype)
    log_structured_event(
        event="settings_updated",
        entity="app_settings",
        action="update",
        actor_user_id=str(user.id),
        field="logotype" if is_logotype else "logo",
    )


@basic_router.get("/logo")
def get_logo(is_logotype: bool = False) -> Response:
    return fetch_logo_response(is_logotype)


@basic_router.get("/logotype")
def get_logotype() -> Response:
    return fetch_logo_response(is_logotype=True)
