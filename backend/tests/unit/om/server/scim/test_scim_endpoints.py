"""Clean-room tests for the SCIM HTTP layer: auth-gating, routing, status codes,
body parsing and query passthrough. DB persistence is integrator-verified (needs
WS-B Team + Postgres); here the services are faked and the auth dep is overridden.
"""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from om.server.scim import constants, groups_api, users_api
from om.server.scim.api import scim_router
from om.server.scim.auth import ScimContext, verify_scim_token
from om.server.scim.service import ScimUserService


class _FakeUserService:
    last: dict = {}

    def __init__(self, db, *, actor_user_id, base_url):
        _FakeUserService.last["actor"] = actor_user_id

    def create(self, r):
        _FakeUserService.last["create"] = r
        return {"id": "u1", "userName": r.user_name, "schemas": [constants.SCHEMA_USER]}

    def get(self, uid):
        return {"id": uid, "schemas": [constants.SCHEMA_USER]}

    def replace(self, uid, r):
        return {"id": uid, "schemas": [constants.SCHEMA_USER]}

    def patch(self, uid, ops):
        _FakeUserService.last["patch_ops"] = ops
        return {"id": uid, "schemas": [constants.SCHEMA_USER]}

    def deprovision(self, uid):
        _FakeUserService.last["deprovision"] = uid

    def list_users(self, *, filter_str, start_index, count):
        _FakeUserService.last["list"] = (filter_str, start_index, count)
        return {
            "schemas": [constants.SCHEMA_LIST_RESPONSE],
            "totalResults": 0,
            "startIndex": start_index,
            "itemsPerPage": 0,
            "Resources": [],
        }


class _FakeGroupService(_FakeUserService):
    def create(self, r):
        return {"id": "g1", "displayName": r.display_name, "schemas": [constants.SCHEMA_GROUP]}

    def get(self, gid, *, excluded_attributes=None):
        _FakeGroupService.last["get"] = (gid, excluded_attributes)
        return {"id": gid, "schemas": [constants.SCHEMA_GROUP]}

    def list_groups(self, *, filter_str, start_index, count, excluded_attributes=None):
        _FakeGroupService.last["glist"] = (filter_str, start_index, count, excluded_attributes)
        return {
            "schemas": [constants.SCHEMA_LIST_RESPONSE],
            "totalResults": 0,
            "startIndex": start_index,
            "itemsPerPage": 0,
            "Resources": [],
        }

    def delete(self, gid):
        _FakeGroupService.last["delete"] = gid


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(scim_router)
    return application


def test_protected_routes_require_token(app: FastAPI) -> None:
    client = TestClient(app)
    assert client.get("/scim/v2/Users").status_code == 401
    assert client.get("/scim/v2/Groups").status_code == 401
    body = client.get("/scim/v2/Users").json()
    assert body["schemas"] == [constants.SCHEMA_ERROR]


def test_all_provisioning_routes_use_verify_scim_token() -> None:
    guarded = 0
    for route in scim_router.routes:
        path = getattr(route, "path", "")
        if "/Users" in path or "/Groups" in path:
            deps = [d.cache_key[0] for d in route.dependant.dependencies]
            assert verify_scim_token in deps, path
            guarded += 1
    # Every /Users and /Groups route must be guarded; the exact count is
    # incidental (6 + 6 today) — assert coverage, not a hard-coded number.
    assert guarded >= 12


@pytest.fixture
def authed_client(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(users_api, "ScimUserService", _FakeUserService)
    monkeypatch.setattr(groups_api, "ScimGroupService", _FakeGroupService)
    app.dependency_overrides[verify_scim_token] = lambda: ScimContext(
        db=None, tenant_id="public", token_id=1, actor_user_id="actor-1"
    )
    return TestClient(app)


def test_create_user_201_parses_body_and_coerces_active(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/scim/v2/Users",
        json={"schemas": [constants.SCHEMA_USER], "userName": "a@b.com", "active": "False"},
    )
    assert resp.status_code == 201
    assert resp.headers["content-type"].startswith(constants.SCIM_CONTENT_TYPE)
    assert _FakeUserService.last["create"].user_name == "a@b.com"
    assert _FakeUserService.last["create"].active is False
    assert _FakeUserService.last["actor"] == "actor-1"


def test_list_users_passes_filter_and_pagination(authed_client: TestClient) -> None:
    resp = authed_client.get('/scim/v2/Users?filter=userName eq "a@b.com"&startIndex=3&count=25')
    assert resp.status_code == 200
    assert _FakeUserService.last["list"] == ('userName eq "a@b.com"', 3, 25)


def test_patch_user_normalises_op_and_returns_200(authed_client: TestClient) -> None:
    resp = authed_client.patch(
        "/scim/v2/Users/u1",
        json={
            "schemas": [constants.SCHEMA_PATCH_OP],
            "Operations": [{"op": "Replace", "value": {"active": False}}],
        },
    )
    assert resp.status_code == 200
    assert _FakeUserService.last["patch_ops"][0].op == "replace"


def test_delete_user_returns_204(authed_client: TestClient) -> None:
    assert authed_client.delete("/scim/v2/Users/u1").status_code == 204


def test_group_patch_returns_204_and_delete_204(authed_client: TestClient) -> None:
    assert authed_client.post("/scim/v2/Groups", json={"displayName": "Eng"}).status_code == 201
    patch_resp = authed_client.patch(
        "/scim/v2/Groups/g1",
        json={
            "schemas": [constants.SCHEMA_PATCH_OP],
            "Operations": [{"op": "add", "path": "members", "value": [{"value": "u1"}]}],
        },
    )
    assert patch_resp.status_code == 204
    assert authed_client.delete("/scim/v2/Groups/g1").status_code == 204


def test_group_list_and_get_pass_excluded_attributes(authed_client: TestClient) -> None:
    authed_client.get("/scim/v2/Groups?excludedAttributes=members&startIndex=1&count=50")
    assert _FakeGroupService.last["glist"] == (None, 1, 50, "members")
    authed_client.get("/scim/v2/Groups/g9?excludedAttributes=members")
    assert _FakeGroupService.last["get"] == ("g9", "members")


def test_malformed_body_returns_400_invalid_syntax(authed_client: TestClient) -> None:
    resp = authed_client.post(
        "/scim/v2/Users",
        content="not json",
        headers={"Content-Type": constants.SCIM_CONTENT_TYPE},
    )
    assert resp.status_code == 400
    assert resp.json()["scimType"] == "invalidSyntax"


def test_user_serialization_mapping() -> None:
    svc = ScimUserService.__new__(ScimUserService)
    svc.base_url = "https://h/scim/v2"
    user = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        email="a@b.com",
        is_active=True,
        personal_name="Alice A",
    )
    d = svc._to_scim(user, "ext-1")
    assert d["userName"] == "a@b.com"
    assert d["active"] is True
    assert d["displayName"] == "Alice A"
    assert d["externalId"] == "ext-1"
    assert d["emails"][0]["value"] == "a@b.com"
    assert d["meta"]["location"].endswith("/Users/11111111-1111-1111-1111-111111111111")
