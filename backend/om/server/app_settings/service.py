"""Application-settings service (branding + feature toggles).

Loads/saves the typed ``app_settings`` singleton and translates between the ORM
row and the ``AppSettingsSchema`` the web app consumes. Emits a structured
``settings_updated`` event on every write (CONTRACTS Standard 9).
"""

from sqlalchemy.orm import Session

from om.db.models import AppSettings
from om.server.analytics.structured_logging import timed_event
from om.server.app_settings.models import AppSettingsSchema
from om.server.app_settings.models import LogoDisplayStyle
from om.server.app_settings.models import NavigationItem
from om.server.app_settings.repository import AppSettingsRepository


class AppSettingsService:
    def __init__(self, db_session: Session) -> None:
        self._repo = AppSettingsRepository(db_session)

    # ------------------------------------------------------------------ #
    # Settings blob
    # ------------------------------------------------------------------ #
    def load(self) -> AppSettingsSchema:
        return self._to_schema(self._repo.get_or_create())

    def save(
        self, settings: AppSettingsSchema, actor_user_id: str | None = None
    ) -> AppSettingsSchema:
        # Partial update: only patch fields the caller actually sent. This keeps a
        # partial PUT (e.g. the branding editor, which omits feature_flags) from
        # wiping columns it did not touch. Column names match schema field names,
        # and mode="json" renders the enum + nested nav items as DB-ready values.
        values = settings.model_dump(exclude_unset=True, mode="json")
        with timed_event(
            event="settings_updated",
            entity="app_settings",
            action="update",
            actor_user_id=actor_user_id,
            fields=sorted(values.keys()),
        ) as ctx:
            row = self._repo.update(values)
            ctx["entity_id"] = row.id
        return self._to_schema(row)

    # ------------------------------------------------------------------ #
    # Custom analytics script
    # ------------------------------------------------------------------ #
    def get_custom_analytics_script(self) -> str | None:
        return self._repo.get_or_create().custom_analytics_script

    def set_custom_analytics_script(
        self, script: str | None, actor_user_id: str | None = None
    ) -> None:
        with timed_event(
            event="settings_updated",
            entity="app_settings",
            action="update",
            actor_user_id=actor_user_id,
            field="custom_analytics_script",
        ) as ctx:
            row = self._repo.update({"custom_analytics_script": script})
            ctx["entity_id"] = row.id

    # ------------------------------------------------------------------ #
    # Mapping helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_schema(row: AppSettings) -> AppSettingsSchema:
        nav_items = [NavigationItem(**item) for item in (row.custom_nav_items or [])]
        return AppSettingsSchema(
            application_name=row.application_name,
            use_custom_logo=row.use_custom_logo,
            use_custom_logotype=row.use_custom_logotype,
            logo_display_style=(
                LogoDisplayStyle(row.logo_display_style)
                if row.logo_display_style
                else None
            ),
            custom_nav_items=nav_items,
            two_lines_for_chat_header=row.two_lines_for_chat_header,
            custom_lower_disclaimer_content=row.custom_lower_disclaimer_content,
            custom_header_content=row.custom_header_content,
            custom_popup_header=row.custom_popup_header,
            custom_popup_content=row.custom_popup_content,
            enable_consent_screen=row.enable_consent_screen,
            consent_screen_prompt=row.consent_screen_prompt,
            show_first_visit_notice=row.show_first_visit_notice,
            custom_greeting_message=row.custom_greeting_message,
            feature_flags=row.feature_flags or {},
        )
