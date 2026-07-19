"""Unit tests for structural SAML config verification."""

from datetime import datetime
from datetime import timedelta
from datetime import timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from om.server.sso.config_store import SamlConfigData
from om.server.sso.schemas import SamlVerifyCheck
from om.server.sso.verify import verify_saml_config


def _make_cert(valid_from_days: int, valid_to_days: int) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "idp.example.com")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now + timedelta(days=valid_from_days))
        .not_valid_after(now + timedelta(days=valid_to_days))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


# Generated once (RSA keygen is the slow part).
VALID_CERT = _make_cert(-1, 365)
EXPIRED_CERT = _make_cert(-30, -1)


def _config(**overrides: object) -> SamlConfigData:
    base: dict[str, object] = dict(
        enabled=True,
        idp_entity_id="https://idp.example.com/metadata",
        idp_sso_url="https://idp.example.com/sso",
        idp_slo_url=None,
        idp_x509_cert=VALID_CERT,
        sp_entity_id="https://app.example.com",
        sp_acs_url="https://app.example.com/auth/saml/callback",
        sp_slo_url=None,
        sp_x509_cert=None,
        sp_private_key=None,
        want_assertions_signed=True,
        want_messages_signed=False,
        want_name_id_encrypted=False,
        authn_requests_signed=False,
        email_attribute_keys=None,
        first_name_attribute_key=None,
        last_name_attribute_key=None,
    )
    base.update(overrides)
    return SamlConfigData(**base)  # type: ignore[arg-type]


def _by_key(checks: list[SamlVerifyCheck], key: str) -> SamlVerifyCheck:
    return next(c for c in checks if c.key == key)


def test_valid_config_passes() -> None:
    valid, checks = verify_saml_config(_config())
    assert valid is True
    assert all(c.status == "ok" for c in checks), [
        (c.key, c.status) for c in checks
    ]


def test_missing_idp_fields() -> None:
    valid, checks = verify_saml_config(
        _config(idp_entity_id="", idp_sso_url="")
    )
    assert valid is False
    assert _by_key(checks, "idp_fields").status == "error"


def test_missing_idp_cert() -> None:
    valid, checks = verify_saml_config(_config(idp_x509_cert=""))
    assert valid is False
    assert _by_key(checks, "idp_cert").status == "error"


def test_garbage_cert() -> None:
    valid, checks = verify_saml_config(_config(idp_x509_cert="not-a-certificate"))
    assert valid is False
    assert _by_key(checks, "idp_cert").status == "error"


def test_expired_cert_is_warning_not_error() -> None:
    valid, checks = verify_saml_config(_config(idp_x509_cert=EXPIRED_CERT))
    cert_check = _by_key(checks, "idp_cert")
    assert cert_check.status == "warning"
    assert "expired" in cert_check.detail.lower()
    # A warning must not flip overall validity.
    assert valid is True


def test_signing_without_sp_key_errors() -> None:
    valid, checks = verify_saml_config(
        _config(authn_requests_signed=True, sp_private_key=None)
    )
    assert _by_key(checks, "signing").status == "error"
    assert valid is False


def test_signing_with_sp_key_ok() -> None:
    checks = verify_saml_config(
        _config(authn_requests_signed=True, sp_private_key="dummy-key")
    )[1]
    # Only the signing consistency check is asserted here (the toolkit may still
    # reject a non-PEM dummy key at the settings stage — that is a separate check).
    assert _by_key(checks, "signing").status == "ok"


def test_disabled_is_warning() -> None:
    valid, checks = verify_saml_config(_config(enabled=False))
    assert _by_key(checks, "enabled").status == "warning"
    # Everything else is still structurally valid.
    assert valid is True
