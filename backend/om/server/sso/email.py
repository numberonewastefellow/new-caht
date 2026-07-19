"""Email extraction from a SAML assertion.

Different IdPs surface the user's email under different attribute keys (Entra
uses the ``.../claims/emailaddress`` URI, Okta often ``email`` or ``User.email``,
Shibboleth the LDAP ``urn:oid`` form, ADFS the WS-* claim URIs). We probe an
ordered, case-insensitive key list — configurable per tenant, with a sensible
built-in default — and fall back to the NameID when it is itself an email.
"""

from __future__ import annotations

from collections.abc import Iterable

from email_validator import EmailNotValidError
from email_validator import validate_email

from om.server.sso.config_store import SamlConfigData
from om.utils.logger import setup_logger

logger = setup_logger()

# Ordered default probe list, covering the common IdPs. Compared case-insensitively.
DEFAULT_EMAIL_ATTRIBUTE_KEYS: tuple[str, ...] = (
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "http://schemas.microsoft.com/identity/claims/emailaddress",
    "email",
    "emailaddress",
    "mail",
    "user.email",
    "urn:oid:0.9.2342.19200300.100.1.3",  # LDAP mail
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
)


def _normalize_email(raw: str) -> str | None:
    """Validate + normalize (lowercased) or return None."""
    if not raw or not isinstance(raw, str):
        return None
    try:
        info = validate_email(raw.strip(), check_deliverability=False)
    except EmailNotValidError:
        return None
    normalized = info.normalized or info.email
    return normalized.lower() if normalized else None


def _iter_attribute_values(value: object) -> Iterable[str]:
    """SAML attributes are typically ``list[str]`` but tolerate scalars too."""
    if value is None:
        return
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            if isinstance(item, str):
                yield item


def extract_email(
    attributes: dict[str, object] | None,
    name_id: str | None,
    config: SamlConfigData,
) -> str | None:
    """Best-effort email from assertion ``attributes`` then the ``name_id``.

    Returns a normalized, lowercased address or ``None`` if nothing valid found.
    """
    keys: tuple[str, ...] = tuple(
        config.email_attribute_keys or DEFAULT_EMAIL_ATTRIBUTE_KEYS
    )

    if attributes:
        # Build a case-insensitive view of the assertion attributes.
        lowered: dict[str, object] = {}
        for attr_key, attr_value in attributes.items():
            if isinstance(attr_key, str):
                lowered.setdefault(attr_key.lower(), attr_value)

        for key in keys:
            values = lowered.get(key.lower())
            for raw in _iter_attribute_values(values):
                email = _normalize_email(raw)
                if email:
                    return email

    # Fallback: NameID is frequently the email (emailAddress NameID format).
    email = _normalize_email(name_id) if name_id else None
    if email:
        return email

    logger.warning(
        "SAML assertion contained no usable email (probed %d attribute keys)",
        len(keys),
    )
    return None
