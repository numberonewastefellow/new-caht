"""Pydantic request/response models for the SAML SSO API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class SamlAuthorizeResponse(BaseModel):
    """Response of ``GET /sso/saml/authorize`` — the IdP redirect URL."""

    authorization_url: str


CheckStatus = Literal["ok", "warning", "error"]


class SamlVerifyCheck(BaseModel):
    """One diagnostic check produced by the verify endpoint."""

    key: str
    label: str
    status: CheckStatus
    detail: str


class SamlLastLogin(BaseModel):
    email: str
    at: str  # ISO-8601 timestamp


class SamlVerifyResult(BaseModel):
    """Response of ``GET /admin/sso/saml/verify`` — a structural, no-round-trip
    diagnostic of the *saved* config plus the SP details to register at the IdP."""

    valid: bool
    checks: list[SamlVerifyCheck]
    sp_entity_id: str
    sp_acs_url: str
    sp_metadata_url: str
    last_successful_login: SamlLastLogin | None = None


class SamlConfigUpsertRequest(BaseModel):
    """Admin ``PUT /admin/sso/saml/config`` payload.

    ``sp_private_key`` is write-only and follows leave-unchanged semantics:
      * ``None``  → keep whatever key is already stored (default on every save);
      * ``""``    → clear the stored key;
      * non-empty → replace the stored key.
    """

    enabled: bool = False

    # Identity Provider
    idp_entity_id: str = ""
    idp_sso_url: str = ""
    idp_slo_url: str | None = None
    idp_x509_cert: str = ""

    # Service Provider
    sp_entity_id: str = ""
    # If omitted, the server defaults it to ``{WEB_DOMAIN}/auth/saml/callback``.
    sp_acs_url: str | None = None
    sp_slo_url: str | None = None
    sp_x509_cert: str | None = None
    sp_private_key: str | None = None

    # Security toggles
    want_assertions_signed: bool = True
    want_messages_signed: bool = False
    want_name_id_encrypted: bool = False
    authn_requests_signed: bool = False

    # Attribute mapping
    email_attribute_keys: list[str] | None = None
    first_name_attribute_key: str | None = None
    last_name_attribute_key: str | None = None


class SamlConfigView(BaseModel):
    """Admin ``GET /admin/sso/saml/config`` response.

    Secrets are never returned: ``sp_private_key`` is replaced by the boolean
    ``sp_private_key_set`` so the UI can show whether a key is configured.
    """

    enabled: bool

    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: str | None
    idp_x509_cert: str

    sp_entity_id: str
    sp_acs_url: str
    sp_slo_url: str | None
    sp_x509_cert: str | None
    sp_private_key_set: bool = Field(
        description="True when an SP private key is stored (value never returned)."
    )

    want_assertions_signed: bool
    want_messages_signed: bool
    want_name_id_encrypted: bool
    authn_requests_signed: bool

    email_attribute_keys: list[str] | None
    first_name_attribute_key: str | None
    last_name_attribute_key: str | None
