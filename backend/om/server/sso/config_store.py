"""Repository for the typed SAML SSO config table (``sso_saml_config``).

Exposes a decrypted, framework-independent :class:`SamlConfigData` snapshot for
the SAML runtime, plus ORM-level get/upsert/view helpers for the admin API. All
DB access is caller-supplied, tenant-scoped ``Session`` (Contract 3) — this layer
never opens its own session or hardcodes a schema.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from om.configs.app_configs import WEB_DOMAIN
from om.db.models import SsoSamlConfig
from om.server.sso.schemas import SamlConfigUpsertRequest
from om.server.sso.schemas import SamlConfigView

# Public, IdP-facing ACS path (the web ACS route that proxies to the backend).
# Kept stable so existing IdP registrations continue to resolve.
DEFAULT_ACS_PATH = "/auth/saml/callback"


def default_sp_acs_url() -> str:
    return f"{WEB_DOMAIN.rstrip('/')}{DEFAULT_ACS_PATH}"


def default_sp_entity_id() -> str:
    return WEB_DOMAIN.rstrip("/")


@dataclass(frozen=True)
class SamlConfigData:
    """Decrypted, immutable snapshot of the SAML config for the SAML runtime."""

    enabled: bool

    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: str | None
    idp_x509_cert: str

    sp_entity_id: str
    sp_acs_url: str
    sp_slo_url: str | None
    sp_x509_cert: str | None
    sp_private_key: str | None

    want_assertions_signed: bool
    want_messages_signed: bool
    want_name_id_encrypted: bool
    authn_requests_signed: bool

    email_attribute_keys: tuple[str, ...] | None
    first_name_attribute_key: str | None
    last_name_attribute_key: str | None

    def is_usable(self) -> bool:
        """True when the minimum fields for an SP-initiated flow are present."""
        return bool(
            self.enabled
            and self.idp_entity_id
            and self.idp_sso_url
            and self.idp_x509_cert
        )


def get_saml_config_row(db_session: Session) -> SsoSamlConfig | None:
    """Return the singleton config row for the current tenant, or None."""
    return db_session.scalars(
        select(SsoSamlConfig).order_by(SsoSamlConfig.id).limit(1)
    ).first()


def _decrypt_private_key(row: SsoSamlConfig) -> str | None:
    if row.sp_private_key is None:
        return None
    return row.sp_private_key.get_value(apply_mask=False)


def load_saml_config(db_session: Session) -> SamlConfigData | None:
    """Load the decrypted config snapshot, or None if unconfigured."""
    row = get_saml_config_row(db_session)
    if row is None:
        return None

    keys = tuple(row.email_attribute_keys) if row.email_attribute_keys else None
    return SamlConfigData(
        enabled=row.enabled,
        idp_entity_id=row.idp_entity_id or "",
        idp_sso_url=row.idp_sso_url or "",
        idp_slo_url=row.idp_slo_url,
        idp_x509_cert=row.idp_x509_cert or "",
        sp_entity_id=row.sp_entity_id or default_sp_entity_id(),
        sp_acs_url=row.sp_acs_url or default_sp_acs_url(),
        sp_slo_url=row.sp_slo_url,
        sp_x509_cert=row.sp_x509_cert,
        sp_private_key=_decrypt_private_key(row),
        want_assertions_signed=row.want_assertions_signed,
        want_messages_signed=row.want_messages_signed,
        want_name_id_encrypted=row.want_name_id_encrypted,
        authn_requests_signed=row.authn_requests_signed,
        email_attribute_keys=keys,
        first_name_attribute_key=row.first_name_attribute_key,
        last_name_attribute_key=row.last_name_attribute_key,
    )


def upsert_saml_config(
    db_session: Session, request: SamlConfigUpsertRequest
) -> SsoSamlConfig:
    """Create or update the singleton SAML config row for the current tenant.

    ``sp_private_key`` follows leave-unchanged semantics (see
    :class:`SamlConfigUpsertRequest`). Commits the transaction.
    """
    row = get_saml_config_row(db_session)
    if row is None:
        row = SsoSamlConfig()
        db_session.add(row)

    row.enabled = request.enabled

    row.idp_entity_id = request.idp_entity_id.strip()
    row.idp_sso_url = request.idp_sso_url.strip()
    row.idp_slo_url = (request.idp_slo_url or "").strip() or None
    row.idp_x509_cert = request.idp_x509_cert.strip()

    row.sp_entity_id = (request.sp_entity_id or "").strip() or default_sp_entity_id()
    row.sp_acs_url = (request.sp_acs_url or "").strip() or default_sp_acs_url()
    row.sp_slo_url = (request.sp_slo_url or "").strip() or None
    row.sp_x509_cert = (request.sp_x509_cert or "").strip() or None

    # Write-only secret with leave-unchanged (None) / clear ("") / replace semantics.
    if request.sp_private_key is not None:
        stripped_key = request.sp_private_key.strip()
        row.sp_private_key = stripped_key or None  # type: ignore[assignment]

    row.want_assertions_signed = request.want_assertions_signed
    row.want_messages_signed = request.want_messages_signed
    row.want_name_id_encrypted = request.want_name_id_encrypted
    row.authn_requests_signed = request.authn_requests_signed

    row.email_attribute_keys = (
        [k.strip() for k in request.email_attribute_keys if k.strip()]
        if request.email_attribute_keys
        else None
    )
    row.first_name_attribute_key = (
        request.first_name_attribute_key or ""
    ).strip() or None
    row.last_name_attribute_key = (
        request.last_name_attribute_key or ""
    ).strip() or None

    db_session.commit()
    db_session.refresh(row)
    return row


def to_view(row: SsoSamlConfig | None) -> SamlConfigView:
    """Build a secret-masked view. A missing row renders sensible defaults."""
    if row is None:
        return SamlConfigView(
            enabled=False,
            idp_entity_id="",
            idp_sso_url="",
            idp_slo_url=None,
            idp_x509_cert="",
            sp_entity_id=default_sp_entity_id(),
            sp_acs_url=default_sp_acs_url(),
            sp_slo_url=None,
            sp_x509_cert=None,
            sp_private_key_set=False,
            want_assertions_signed=True,
            want_messages_signed=False,
            want_name_id_encrypted=False,
            authn_requests_signed=False,
            email_attribute_keys=None,
            first_name_attribute_key=None,
            last_name_attribute_key=None,
        )

    return SamlConfigView(
        enabled=row.enabled,
        idp_entity_id=row.idp_entity_id or "",
        idp_sso_url=row.idp_sso_url or "",
        idp_slo_url=row.idp_slo_url,
        idp_x509_cert=row.idp_x509_cert or "",
        sp_entity_id=row.sp_entity_id or default_sp_entity_id(),
        sp_acs_url=row.sp_acs_url or default_sp_acs_url(),
        sp_slo_url=row.sp_slo_url,
        sp_x509_cert=row.sp_x509_cert,
        sp_private_key_set=row.sp_private_key is not None,
        want_assertions_signed=row.want_assertions_signed,
        want_messages_signed=row.want_messages_signed,
        want_name_id_encrypted=row.want_name_id_encrypted,
        authn_requests_signed=row.authn_requests_signed,
        email_attribute_keys=(
            list(row.email_attribute_keys) if row.email_attribute_keys else None
        ),
        first_name_attribute_key=row.first_name_attribute_key,
        last_name_attribute_key=row.last_name_attribute_key,
    )
