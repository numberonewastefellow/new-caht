"""Clean-room tests for SCIM discovery payloads + public discovery endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from om.server.scim import constants, discovery
from om.server.scim.api import scim_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(scim_router)
    return TestClient(app)


def test_service_provider_config_capabilities() -> None:
    spc = discovery.service_provider_config("https://h/scim/v2")
    assert spc["schemas"] == [constants.SCHEMA_SERVICE_PROVIDER_CONFIG]
    assert spc["patch"]["supported"] is True
    assert spc["filter"]["supported"] is True
    assert spc["bulk"]["supported"] is False
    assert spc["authenticationSchemes"][0]["type"] == "oauthbearertoken"


def test_resource_types_and_schemas_present() -> None:
    assert {e["id"] for e in discovery.resource_types("https://h/scim/v2")} == {
        "User",
        "Group",
    }
    ids = {s["id"] for s in discovery.schemas()}
    assert constants.SCHEMA_USER in ids and constants.SCHEMA_GROUP in ids


def test_discovery_endpoints_are_public_and_scim_json() -> None:
    client = _client()
    for path in ("/ServiceProviderConfig", "/ResourceTypes", "/Schemas"):
        resp = client.get(f"/scim/v2{path}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(constants.SCIM_CONTENT_TYPE)


def test_resource_types_list_response_shape() -> None:
    resp = _client().get("/scim/v2/ResourceTypes")
    body = resp.json()
    assert body["schemas"] == [constants.SCHEMA_LIST_RESPONSE]
    assert body["totalResults"] == 2


def test_unknown_schema_returns_scim_404() -> None:
    resp = _client().get("/scim/v2/Schemas/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["schemas"] == [constants.SCHEMA_ERROR]
