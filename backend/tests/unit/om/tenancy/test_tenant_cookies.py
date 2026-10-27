import asyncio
from unittest.mock import MagicMock

import pytest

from om.configs.constants import ANONYMOUS_USER_COOKIE_NAME
from om.configs.constants import LEGACY_ANONYMOUS_USER_COOKIE_NAME
from om.configs.constants import LEGACY_TENANT_ID_COOKIE_NAME
from om.configs.constants import TENANT_ID_COOKIE_NAME
from om.tenancy import middleware


def _request(cookies: dict[str, str]) -> MagicMock:
    req = MagicMock()
    req.cookies = cookies
    req.headers = {}
    return req


@pytest.fixture(autouse=True)
def _no_session(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _none(_: object) -> None:
        return None

    monkeypatch.setattr(middleware, "extract_tenant_from_auth_header", lambda r: None)
    monkeypatch.setattr(middleware, "retrieve_auth_token_data_from_redis", _none)


def test_cookie_names_are_om_and_legacy_names_are_kept_for_reading() -> None:
    assert TENANT_ID_COOKIE_NAME == "om_tid"
    assert ANONYMOUS_USER_COOKIE_NAME == "om_anonymous_user"
    assert LEGACY_TENANT_ID_COOKIE_NAME == "onyx_tid"
    assert LEGACY_ANONYMOUS_USER_COOKIE_NAME == "onyx_anonymous_user"


@pytest.mark.parametrize("name", ["om_tid", "onyx_tid"])
def test_tenant_cookie_is_read_under_either_name(name: str) -> None:
    assert asyncio.run(middleware.resolve_tenant_id(_request({name: "tenant_abc"}))) == "tenant_abc"


def test_new_tenant_cookie_wins_over_the_legacy_one() -> None:
    cookies = {"om_tid": "tenant_new", "onyx_tid": "tenant_old"}
    assert asyncio.run(middleware.resolve_tenant_id(_request(cookies))) == "tenant_new"


@pytest.mark.parametrize("name", ["om_anonymous_user", "onyx_anonymous_user"])
def test_anonymous_cookie_is_decoded_under_either_name(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setattr(middleware, "ALLOW_ANONYMOUS_TENANT_ACCESS", True)
    monkeypatch.setattr(middleware, "decode_anonymous_user_jwt_token", lambda c: {"tenant_id": "tenant_anon"})
    assert asyncio.run(middleware.resolve_tenant_id(_request({name: "jwt"}))) == "tenant_anon"
