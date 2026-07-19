"""Isolation-core unit tests for WS-M (multi-tenant data isolation).

Two layers:

* :class:`TestSchemaSafety` — pure schema-name / tenant-id validation. These guard the
  single most safety-critical property: a value that will be interpolated as a Postgres
  schema name (and reach ``CREATE``/``DROP SCHEMA``) can never be ``public`` or contain
  injection characters. They run anywhere (no heavy deps).
* :class:`TestTenantResolution` — the middleware's request→tenant precedence and its
  rejection of malformed identifiers. These import the middleware, which pulls the full
  app dependency set, so they ``importorskip`` when run outside the container.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from om.tenancy import schema as schema_mod


# ---------------------------------------------------------------------------------------
# Pure schema-name / tenant-id safety (runs everywhere)
# ---------------------------------------------------------------------------------------
class TestSchemaSafety:
    def test_safe_schema_name_accepts_expected(self) -> None:
        assert schema_mod.is_safe_schema_name("public")
        assert schema_mod.is_safe_schema_name("tenant_abc-123")

    @pytest.mark.parametrize(
        "bad",
        ["", "bad;drop", "a b", "schema.name", 'x"y', "a'b", "a/b", "a(b)"],
    )
    def test_safe_schema_name_rejects_injection(self, bad: str) -> None:
        # Loose allow-list is [A-Za-z0-9_-]+ — hyphens/underscores are fine (they are
        # legal identifier chars); anything that could break out of a quoted identifier
        # (quotes, spaces, punctuation, semicolons) must be rejected.
        assert not schema_mod.is_safe_schema_name(bad)

    def test_is_tenant_id_accepts_uuid_and_instance_forms(self) -> None:
        uuid_tid = f"tenant_{'0' * 8}-{'0' * 4}-{'0' * 4}-{'0' * 4}-{'0' * 12}"
        assert schema_mod.is_tenant_id(uuid_tid)
        assert schema_mod.is_tenant_id("tenant_i-0a1b2c3d")

    @pytest.mark.parametrize(
        "bad",
        ["public", "tenant_", "tenant_not-a-uuid", "random", "tenant_ i-1"],
    )
    def test_is_tenant_id_rejects_non_tenant(self, bad: str) -> None:
        assert not schema_mod.is_tenant_id(bad)

    def test_assert_tenant_id_blocks_public(self) -> None:
        # The most important guarantee: provisioning/drop can never resolve to `public`.
        with pytest.raises(ValueError):
            schema_mod.assert_tenant_id("public")

    def test_new_tenant_id_round_trips(self) -> None:
        tid = schema_mod.new_tenant_id()
        assert schema_mod.is_tenant_id(tid)
        assert schema_mod.is_safe_schema_name(tid)
        # Two mints are distinct.
        assert schema_mod.new_tenant_id() != schema_mod.new_tenant_id()


# ---------------------------------------------------------------------------------------
# Middleware request → tenant precedence (needs full app deps → importorskip in CI only)
# ---------------------------------------------------------------------------------------
def _fake_request(cookies: dict[str, str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(headers={}, cookies=cookies or {})


def _resolve(mw: object, request: object) -> str:
    return asyncio.run(mw.resolve_tenant_id(request))


@pytest.fixture
def mw() -> object:
    """The middleware module, or skip this test when its deps aren't installed."""
    return pytest.importorskip("om.tenancy.middleware")


class TestTenantResolution:
    def test_api_key_wins_over_everything(
        self, mw: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            mw, "extract_tenant_from_auth_header", lambda request: "tenant_fromapikey"
        )

        async def _redis(request: object) -> dict:
            return {"tenant_id": "tenant_fromsession"}

        monkeypatch.setattr(mw, "retrieve_auth_token_data_from_redis", _redis)
        assert _resolve(mw, _fake_request()) == "tenant_fromapikey"

    def test_session_token_used_when_no_api_key(
        self, mw: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            mw, "extract_tenant_from_auth_header", lambda request: None
        )

        async def _redis(request: object) -> dict:
            return {"tenant_id": "tenant_fromsession"}

        monkeypatch.setattr(mw, "retrieve_auth_token_data_from_redis", _redis)
        assert _resolve(mw, _fake_request()) == "tenant_fromsession"

    def test_tenant_cookie_used_when_no_api_key_or_session(
        self, mw: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            mw, "extract_tenant_from_auth_header", lambda request: None
        )

        async def _redis(request: object) -> None:
            return None

        monkeypatch.setattr(mw, "retrieve_auth_token_data_from_redis", _redis)
        req = _fake_request(cookies={mw.TENANT_ID_COOKIE_NAME: "tenant_fromcookie"})
        assert _resolve(mw, req) == "tenant_fromcookie"

    def test_falls_back_to_default_schema(
        self, mw: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            mw, "extract_tenant_from_auth_header", lambda request: None
        )

        async def _redis(request: object) -> None:
            return None

        monkeypatch.setattr(mw, "retrieve_auth_token_data_from_redis", _redis)
        assert _resolve(mw, _fake_request()) == mw.POSTGRES_DEFAULT_SCHEMA

    def test_redis_failure_does_not_crash_resolution(
        self, mw: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            mw, "extract_tenant_from_auth_header", lambda request: None
        )

        async def _boom(request: object) -> dict:
            raise RuntimeError("redis down")

        monkeypatch.setattr(mw, "retrieve_auth_token_data_from_redis", _boom)
        # A Redis hiccup must degrade to the default schema, never 500 the request.
        assert _resolve(mw, _fake_request()) == mw.POSTGRES_DEFAULT_SCHEMA

    def test_malformed_tenant_is_rejected(
        self, mw: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            mw,
            "extract_tenant_from_auth_header",
            lambda request: "bad;DROP SCHEMA public",
        )
        with pytest.raises(mw.InvalidTenantError):
            _resolve(mw, _fake_request())


# ---------------------------------------------------------------------------------------
# Login tenant-routing (get_login_tenant_id) — needs full app deps → importorskip in CI
# ---------------------------------------------------------------------------------------
@pytest.fixture
def prov() -> object:
    """The provisioning module, or skip when its deps aren't installed."""
    return pytest.importorskip("om.tenancy.provisioning")


class TestLoginTenantRouting:
    def test_single_tenant_returns_default_schema_without_db(
        self, prov: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Self-hosted (MULTI_TENANT off): login must resolve to the default schema and must
        # NOT touch the mapping table (guarding the single-tenant-login regression).
        monkeypatch.setattr(prov, "MULTI_TENANT", False)

        def _boom(email: str) -> str:
            raise AssertionError("resolve_or_activate must not run in single-tenant mode")

        monkeypatch.setattr(
            prov.TenantMappingRepository, "resolve_or_activate", staticmethod(_boom)
        )
        assert (
            prov.get_login_tenant_id("anyone@example.com")
            == prov.POSTGRES_DEFAULT_SCHEMA
        )

    def test_multi_tenant_delegates_to_repository(
        self, prov: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(prov, "MULTI_TENANT", True)
        monkeypatch.setattr(
            prov.TenantMappingRepository,
            "resolve_or_activate",
            staticmethod(lambda email: "tenant_fromdb"),
        )
        assert prov.get_login_tenant_id("user@example.com") == "tenant_fromdb"

    def test_multi_tenant_unknown_email_returns_none(
        self, prov: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # An unknown email must NOT be provisioned as a side effect of a login attempt.
        monkeypatch.setattr(prov, "MULTI_TENANT", True)
        monkeypatch.setattr(
            prov.TenantMappingRepository,
            "resolve_or_activate",
            staticmethod(lambda email: None),
        )
        assert prov.get_login_tenant_id("stranger@example.com") is None
