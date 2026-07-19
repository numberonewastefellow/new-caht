"""Clean-room tests for SCIM token generation/hashing and bearer authentication."""

import hashlib

import pytest
from starlette.requests import Request

from om.server.scim import auth
from om.server.scim.constants import SCIM_TOKEN_PREFIX
from om.server.scim.errors import ScimError


def _make_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


def test_generate_and_hash_single_tenant() -> None:
    raw = auth.generate_scim_token()
    assert raw.startswith(SCIM_TOKEN_PREFIX)
    assert auth.hash_scim_token(raw) == hashlib.sha256(raw.encode()).hexdigest()


def test_token_display_masks_all_but_last_four() -> None:
    raw = auth.generate_scim_token()
    display = auth.build_scim_token_display(raw)
    assert display == f"{SCIM_TOKEN_PREFIX}****{raw[-4:]}"
    assert raw[4:-4] not in display  # the secret body is not leaked


def test_two_tokens_are_unique() -> None:
    assert auth.generate_scim_token() != auth.generate_scim_token()


def test_hash_rejects_bad_prefix() -> None:
    with pytest.raises(ScimError):
        auth.hash_scim_token("not-a-scim-token")


def test_tokens_match_is_constant_time_equal() -> None:
    raw = auth.generate_scim_token()
    h = auth.hash_scim_token(raw)
    assert auth.tokens_match(h, h)
    assert not auth.tokens_match(h, "0" * 64)


def test_multi_tenant_embeds_and_parses_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "MULTI_TENANT", True)
    raw = auth.generate_scim_token("tenant_acme")
    assert raw.startswith(f"{SCIM_TOKEN_PREFIX}tenant_acme.")
    assert auth.parse_tenant_from_token(raw) == "tenant_acme"


def test_multi_tenant_url_encodes_special_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "MULTI_TENANT", True)
    raw = auth.generate_scim_token("t/e n@t")
    assert auth.parse_tenant_from_token(raw) == "t/e n@t"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer "},
        {"Authorization": "Bearer notscim_123"},
    ],
)
def test_verify_scim_token_rejects_bad_auth(headers: dict[str, str]) -> None:
    gen = auth.verify_scim_token(_make_request(headers))
    with pytest.raises(ScimError) as exc_info:
        next(gen)
    gen.close()
    assert exc_info.value.status_code == 401
