"""RelayState / return-to sanitization — open-redirect protection.

The SAML ``RelayState`` (and the ``next`` query param on ``/authorize``) is
attacker-influenceable: the IdP echoes it back verbatim to the ACS, and if we
blindly redirect to it an attacker can send freshly-authenticated users to a
phishing origin. Per the OWASP SAML Security Cheat Sheet we treat it as a URL
that must resolve to *our own origin* — anything else collapses to a safe
default. This mirrors (defense-in-depth) the check the web ACS route also runs.
"""

from __future__ import annotations

from urllib.parse import unquote
from urllib.parse import urlsplit

from om.configs.app_configs import WEB_DOMAIN
from om.utils.logger import setup_logger

logger = setup_logger()

DEFAULT_REDIRECT = "/"


def _has_control_chars(value: str) -> bool:
    return any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)


def _looks_protocol_relative(path: str) -> bool:
    """True for ``//host`` style values, including encoded/backslash variants."""
    candidates = {path, unquote(path)}
    for candidate in candidates:
        collapsed = candidate.replace("\\", "/")
        if collapsed.startswith("//"):
            return True
    return False


def sanitize_relay_state(
    candidate: str | None, *, default: str = DEFAULT_REDIRECT
) -> str:
    """Return a safe same-origin redirect target, or ``default`` (``"/"``).

    Accepts:
      * relative paths beginning with a single ``/`` (e.g. ``/chat?x=1``); or
      * absolute ``http(s)`` URLs whose host matches ``WEB_DOMAIN``.
    Everything else — protocol-relative URLs, foreign origins, ``javascript:``
    and other schemes, malformed input — falls back to ``default``.
    """
    if not candidate or not isinstance(candidate, str):
        return default

    value = candidate.strip()
    if not value or _has_control_chars(value):
        return default

    # Backslashes are normalized to forward slashes by many browsers; treat them
    # as such when deciding whether the value is protocol-relative.
    normalized = value.replace("\\", "/")

    # Case 1 — relative path on our origin.
    if normalized.startswith("/"):
        if _looks_protocol_relative(value):
            logger.warning("Rejected protocol-relative RelayState")
            return default
        return normalized

    # Case 2 — absolute URL: only same origin as WEB_DOMAIN is allowed.
    parsed = urlsplit(value)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        web = urlsplit(WEB_DOMAIN)
        if web.netloc and parsed.netloc.lower() == web.netloc.lower():
            return value
        logger.warning("Rejected cross-origin RelayState (host=%s)", parsed.netloc)
        return default

    # Anything else (bare host, non-web scheme, garbage) is unsafe.
    logger.warning("Rejected unsafe RelayState")
    return default
