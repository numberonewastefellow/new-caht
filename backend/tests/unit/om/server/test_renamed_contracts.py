"""S2: headers, route, metrics and analytics names are om-named (no aliases)."""

import importlib

import pytest
from fastapi import Request
from starlette.datastructures import Headers

from om.auth import constants as auth_constants
from om.configs import constants


def test_alternative_auth_header_is_om_named() -> None:
    assert auth_constants.API_KEY_HEADER_ALTERNATIVE_NAME == "X-Om-Authorization"


def test_bearer_token_is_read_from_the_om_header_only() -> None:
    from om.auth.utils import get_hashed_bearer_token_from_request

    def req(headers: dict[str, str]) -> Request:
        return Request({"type": "http", "headers": Headers(headers).raw})

    token = "on_secret"
    assert get_hashed_bearer_token_from_request(
        req({"X-Om-Authorization": f"Bearer {token}"}), ["on_"], lambda t: f"h:{t}"
    ) == f"h:{token}"
    # the old header name is no longer honoured
    assert get_hashed_bearer_token_from_request(
        req({"X-Onyx-Authorization": f"Bearer {token}"}), ["on_"], lambda t: f"h:{t}"
    ) is None


def test_ingestion_router_prefix_is_om_api() -> None:
    from om.server.om_api.ingestion import router

    assert router.prefix == "/om-api"
    assert all(r.path.startswith("/om-api") for r in router.routes)  # type: ignore[attr-defined]


@pytest.mark.parametrize("module", ["om.server.metrics.postgres_connection_pool", "om.server.metrics.opensearch_search", "om.server.metrics.slow_requests"])
def test_metric_names_are_om_prefixed(module: str) -> None:
    import inspect

    source = inspect.getsource(importlib.import_module(module))
    assert "onyx_" not in source
    assert "om_" in source


def test_analytics_names_are_om_named() -> None:
    assert constants.OM_UTM_SOURCE == "om_app"
    assert constants.MilestoneRecordType.CREATED_OM_BOT.value == "created_om_bot"


def test_craft_flag_name_defaults_to_om_and_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    import om.server.features.build.utils as utils

    assert utils.OM_CRAFT_ENABLED_FLAG == "om-craft-enabled"
    monkeypatch.setenv("OM_CRAFT_ENABLED_FLAG", "my-flag")
    assert importlib.reload(utils).OM_CRAFT_ENABLED_FLAG == "my-flag"
    monkeypatch.delenv("OM_CRAFT_ENABLED_FLAG")
    importlib.reload(utils)
