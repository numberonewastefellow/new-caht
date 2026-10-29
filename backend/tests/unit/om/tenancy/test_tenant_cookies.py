import asyncio
from unittest.mock import MagicMock

import pytest

from om.configs.constants import ANONYMOUS_USER_COOKIE_NAME
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


def test_cookie_names_are_om_named() -> None:
    assert TENANT_ID_COOKIE_NAME == "om_tid"
    assert ANONYMOUS_USER_COOKIE_NAME == "om_anonymous_user"


def test_tenant_cookie_is_read() -> None:
    assert asyncio.run(middleware.resolve_tenant_id(_request({"om_tid": "tenant_abc"}))) == "tenant_abc"


def test_old_tenant_cookie_name_is_ignored() -> None:
    # falls through to the default schema
    assert asyncio.run(middleware.resolve_tenant_id(_request({"onyx_tid": "tenant_abc"}))) != "tenant_abc"


def test_anonymous_cookie_is_decoded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(middleware, "ALLOW_ANONYMOUS_TENANT_ACCESS", True)
    monkeypatch.setattr(middleware, "decode_anonymous_user_jwt_token", lambda c: {"tenant_id": "tenant_anon"})
    assert asyncio.run(middleware.resolve_tenant_id(_request({"om_anonymous_user": "jwt"}))) == "tenant_anon"
