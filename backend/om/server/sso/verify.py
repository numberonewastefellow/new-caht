"""Structural verification of a saved SAML config (no live IdP round-trip).

Runs a set of cheap, deterministic checks so an admin gets actionable feedback
at setup time — before discovering a bad cert or missing URL the hard way (a
failed login). This is *structural* validation: it confirms the config produces
valid python3-saml settings and that the IdP certificate parses; it does NOT
contact the IdP.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone

from cryptography import x509
from onelogin.saml2.settings import (  # type: ignore[import-untyped]
    OneLogin_Saml2_Settings,
)
from onelogin.saml2.utils import OneLogin_Saml2_Utils  # type: ignore[import-untyped]

from om.server.sso.config_store import SamlConfigData
from om.server.sso.saml_settings import build_saml_settings
from om.server.sso.schemas import SamlVerifyCheck
from om.utils.logger import setup_logger

logger = setup_logger()


def _check(key: str, label: str, status: str, detail: str) -> SamlVerifyCheck:
    return SamlVerifyCheck(key=key, label=label, status=status, detail=detail)  # type: ignore[arg-type]


def _cert_status(cert: str) -> tuple[str, str]:
    """Return ``(status, detail)`` for an X.509 cert string.

    ``format_cert`` only normalizes the PEM; actual parsing/expiry needs
    ``cryptography``. Expiry is surfaced as a warning (structurally valid but
    unusable), a parse failure as an error.
    """
    if not cert or not cert.strip():
        return "error", "No certificate provided."
    try:
        formatted = OneLogin_Saml2_Utils.format_cert(cert)
        parsed = x509.load_pem_x509_certificate(formatted.encode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any parse failure is a bad cert
        return "error", f"Certificate could not be parsed ({type(exc).__name__})."

    try:
        not_after = getattr(parsed, "not_valid_after_utc", None) or parsed.not_valid_after
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=timezone.utc)
        if not_after < datetime.now(timezone.utc):
            return (
                "warning",
                f"Certificate is valid X.509 but expired on {not_after.date()}.",
            )
    except Exception:  # noqa: BLE001 - expiry is best-effort
        pass
    return "ok", "Certificate parses as a valid X.509 certificate."


def run_checks(config: SamlConfigData) -> list[SamlVerifyCheck]:
    """Produce the ordered list of diagnostic checks for ``config``."""
    checks: list[SamlVerifyCheck] = []

    # 1. Enabled.
    checks.append(
        _check(
            "enabled",
            "SAML SSO enabled",
            "ok" if config.enabled else "warning",
            (
                "SAML single sign-on is enabled."
                if config.enabled
                else "Saved but not enabled — users will not see the SSO login option "
                "until you tick Enable."
            ),
        )
    )

    # 2. Required IdP fields.
    missing_idp = [
        name
        for name, value in (
            ("IdP Entity ID", config.idp_entity_id),
            ("IdP Sign-On URL", config.idp_sso_url),
            ("IdP Certificate", config.idp_x509_cert),
        )
        if not value.strip()
    ]
    checks.append(
        _check(
            "idp_fields",
            "Identity Provider fields",
            "error" if missing_idp else "ok",
            (
                "Missing required field(s): " + ", ".join(missing_idp)
                if missing_idp
                else "All required IdP fields are present."
            ),
        )
    )

    # 3. IdP certificate parses (and is not expired).
    cert_status, cert_detail = _cert_status(config.idp_x509_cert)
    checks.append(_check("idp_cert", "IdP certificate", cert_status, cert_detail))

    # 4. Required SP fields.
    missing_sp = [
        name
        for name, value in (
            ("SP Entity ID", config.sp_entity_id),
            ("ACS URL", config.sp_acs_url),
        )
        if not value.strip()
    ]
    checks.append(
        _check(
            "sp_fields",
            "Service Provider fields",
            "error" if missing_sp else "ok",
            (
                "Missing required field(s): " + ", ".join(missing_sp)
                if missing_sp
                else "All required SP fields are present."
            ),
        )
    )

    # 5. Signing consistency.
    if config.authn_requests_signed and not config.sp_private_key:
        checks.append(
            _check(
                "signing",
                "Request signing",
                "error",
                "'Sign AuthnRequests' is enabled but no SP private key is configured.",
            )
        )
    else:
        checks.append(
            _check(
                "signing",
                "Request signing",
                "ok",
                (
                    "SP signing key is configured."
                    if config.authn_requests_signed
                    else "Request signing is off (no SP key required)."
                ),
            )
        )

    # 6. Comprehensive python3-saml settings validation (catch-all).
    try:
        OneLogin_Saml2_Settings(build_saml_settings(config))
        checks.append(
            _check(
                "settings",
                "SAML settings validation",
                "ok",
                "python3-saml accepts the generated settings.",
            )
        )
    except Exception as exc:  # noqa: BLE001 - surface the toolkit's error keys
        checks.append(
            _check(
                "settings",
                "SAML settings validation",
                "error",
                f"python3-saml rejected the settings: {exc}",
            )
        )

    return checks


def verify_saml_config(config: SamlConfigData) -> tuple[bool, list[SamlVerifyCheck]]:
    """Return ``(valid, checks)``. ``valid`` is False if any check is an error."""
    checks = run_checks(config)
    valid = not any(check.status == "error" for check in checks)
    return valid, checks
