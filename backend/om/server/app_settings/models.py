"""Pydantic schemas for application settings.

Field names deliberately mirror the frontend ``EnterpriseSettings`` interface so
the public GET endpoint is a drop-in for the object the web ``SettingsProvider``
consumes for gating and whitelabelling.
"""

from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class LogoDisplayStyle(str, Enum):
    LOGO_AND_NAME = "logo_and_name"
    LOGO_ONLY = "logo_only"
    NAME_ONLY = "name_only"


class NavigationItem(BaseModel):
    """A custom sidebar navigation entry (either an icon name or an inline SVG)."""

    link: str
    title: str
    icon: str | None = None
    # Inline SVG string (width/height must be omitted so it scales). Kept in the
    # settings blob rather than as a separate stored asset.
    svg_logo: str | None = None


class AppSettingsSchema(BaseModel):
    """The application-level settings object read by the web app for gating."""

    # --- Branding / whitelabel ---
    application_name: str | None = None
    use_custom_logo: bool = False
    use_custom_logotype: bool = False
    logo_display_style: LogoDisplayStyle | None = None
    custom_nav_items: list[NavigationItem] = Field(default_factory=list)

    # --- Chat / UI customization ---
    two_lines_for_chat_header: bool | None = None
    custom_lower_disclaimer_content: str | None = None
    custom_header_content: str | None = None
    custom_popup_header: str | None = None
    custom_popup_content: str | None = None
    enable_consent_screen: bool | None = None
    consent_screen_prompt: str | None = None
    show_first_visit_notice: bool | None = None
    custom_greeting_message: str | None = None

    # --- Extensible feature toggles driving frontend gating ---
    # e.g. {"analytics": true, "query_history": true, "reports": true}
    feature_flags: dict[str, bool] = Field(default_factory=dict)


class CustomAnalyticsScriptPayload(BaseModel):
    """Admin payload to set the injected custom analytics ``<script>``."""

    script: str | None = None
