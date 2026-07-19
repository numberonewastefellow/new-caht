"""Unit tests for RelayState open-redirect sanitization."""

import pytest

from om.server.sso import relay_state as rs
from om.server.sso.relay_state import sanitize_relay_state


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "   ",
        # protocol-relative → foreign origin
        "//evil.com",
        "//evil.com/path",
        "/\\evil.com",
        "/\\/\\evil.com",
        "/%2F%2Fevil.com",
        "/%2f%2fevil.com",
        # non-web schemes
        "javascript:alert(1)",
        "data:text/html,<script>",
        # bare / foreign hosts
        "evil.com",
        "evil.com/path",
        "https://evil.com",
        "https://evil.com/callback",
        "http://evil.com",
        # control chars
        "/path\nSet-Cookie: x=y",
    ],
)
def test_unsafe_values_collapse_to_default(value: str | None) -> None:
    assert sanitize_relay_state(value) == "/"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("/", "/"),
        ("/chat", "/chat"),
        ("/admin/auth/sso", "/admin/auth/sso"),
        ("/chat?foo=bar&baz=1", "/chat?foo=bar&baz=1"),
        ("/path#frag", "/path#frag"),
    ],
)
def test_relative_paths_pass_through(value: str, expected: str) -> None:
    assert sanitize_relay_state(value) == expected


def test_custom_default_is_used() -> None:
    assert sanitize_relay_state(None, default="/home") == "/home"
    assert sanitize_relay_state("//evil.com", default="/home") == "/home"


def test_same_origin_absolute_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rs, "WEB_DOMAIN", "https://app.example.com")
    ok = "https://app.example.com/dashboard"
    assert sanitize_relay_state(ok) == ok


def test_cross_origin_absolute_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rs, "WEB_DOMAIN", "https://app.example.com")
    assert sanitize_relay_state("https://app.evil.com/dashboard") == "/"
    # different scheme, same host is still same netloc → allowed by host match
    assert (
        sanitize_relay_state("http://app.example.com/x") == "http://app.example.com/x"
    )
