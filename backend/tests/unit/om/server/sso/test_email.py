"""Unit tests for SAML assertion email extraction."""

from om.server.sso.config_store import SamlConfigData
from om.server.sso.email import extract_email

ENTRA_EMAIL_KEY = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"


def _config(email_keys: list[str] | None = None) -> SamlConfigData:
    return SamlConfigData(
        enabled=True,
        idp_entity_id="idp",
        idp_sso_url="https://idp/sso",
        idp_slo_url=None,
        idp_x509_cert="cert",
        sp_entity_id="sp",
        sp_acs_url="https://sp/acs",
        sp_slo_url=None,
        sp_x509_cert=None,
        sp_private_key=None,
        want_assertions_signed=True,
        want_messages_signed=False,
        want_name_id_encrypted=False,
        authn_requests_signed=False,
        email_attribute_keys=tuple(email_keys) if email_keys else None,
        first_name_attribute_key=None,
        last_name_attribute_key=None,
    )


def test_entra_claim_key() -> None:
    attrs = {ENTRA_EMAIL_KEY: ["Alice@Example.com"]}
    assert extract_email(attrs, None, _config()) == "alice@example.com"


def test_plain_email_key() -> None:
    assert extract_email({"email": ["bob@example.com"]}, None, _config()) == (
        "bob@example.com"
    )


def test_okta_user_email_and_mail_keys() -> None:
    assert extract_email({"User.email": ["c@x.io"]}, None, _config()) == "c@x.io"
    assert extract_email({"mail": ["d@x.io"]}, None, _config()) == "d@x.io"


def test_case_insensitive_attribute_key() -> None:
    assert extract_email({"EMAIL": ["e@x.io"]}, None, _config()) == "e@x.io"


def test_first_valid_of_multiple_values() -> None:
    attrs = {"email": ["not-an-email", "valid@x.io"]}
    assert extract_email(attrs, None, _config()) == "valid@x.io"


def test_nameid_fallback_when_no_attributes() -> None:
    assert extract_email({}, "fromnameid@x.io", _config()) == "fromnameid@x.io"
    assert extract_email(None, "fromnameid@x.io", _config()) == "fromnameid@x.io"


def test_invalid_attribute_falls_back_to_nameid() -> None:
    attrs = {"email": ["garbage"]}
    assert extract_email(attrs, "nid@x.io", _config()) == "nid@x.io"


def test_returns_none_when_nothing_valid() -> None:
    assert extract_email({"email": ["garbage"]}, "also-garbage", _config()) is None
    assert extract_email(None, None, _config()) is None
    assert extract_email({}, "", _config()) is None


def test_custom_config_keys_override_defaults() -> None:
    # Only look at "corp_mail"; the default keys are ignored.
    cfg = _config(email_keys=["corp_mail"])
    assert extract_email({"corp_mail": ["z@x.io"]}, None, cfg) == "z@x.io"
    # A default key that is NOT in the custom list is not consulted.
    assert extract_email({"email": ["ignored@x.io"]}, "nid@x.io", cfg) == "nid@x.io"


def test_precedence_follows_key_order() -> None:
    cfg = _config(email_keys=["primary", "secondary"])
    attrs = {"secondary": ["second@x.io"], "primary": ["first@x.io"]}
    assert extract_email(attrs, None, cfg) == "first@x.io"


def test_scalar_attribute_value_tolerated() -> None:
    # Some toolkits hand back a bare string instead of a list.
    assert extract_email({"email": "scalar@x.io"}, None, _config()) == "scalar@x.io"
