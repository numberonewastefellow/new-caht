"""Cross-verification of the local-provider port against a hand-written case
table (fixtures/local_providers/*.json). Feeds the fixtures to OUR functions;
httpx and litellm.completion are mocked, no network."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from om.llm.local_providers import normalize_openai_v1_base
from om.llm.local_providers import strip_openai_v1_suffix
from om.server.manage.llm.api import get_lm_studio_available_models
from om.server.manage.llm.api import get_ollama_available_models
from om.server.manage.llm.api import get_openai_compatible_available_models
from om.server.manage.llm.models import LMStudioModelsRequest
from om.server.manage.llm.models import OllamaModelsRequest
from om.server.manage.llm.models import OpenAICompatibleModelsRequest

FIXTURES = Path(__file__).parent / "fixtures" / "local_providers"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _response(payload: Any, status_error: Exception | None = None) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status = MagicMock(side_effect=status_error)
    return response


URL_CASES = _load("url_cases.json")


# --- C2: URL normalisation --------------------------------------------------


@pytest.mark.parametrize("raw,expected", URL_CASES["normalize_openai_v1_base"])
def test_c2_normalize_openai_v1_base(raw: str, expected: str) -> None:
    assert normalize_openai_v1_base(raw) == expected


@pytest.mark.parametrize("raw,expected", URL_CASES["strip_openai_v1_suffix"])
def test_c2_strip_openai_v1_suffix(raw: str, expected: str) -> None:
    assert strip_openai_v1_suffix(raw) == expected


def test_c2_lm_studio_empty_base_is_400() -> None:
    with pytest.raises(HTTPException) as exc:
        get_lm_studio_available_models(
            LMStudioModelsRequest(api_base="   "), MagicMock(), MagicMock()
        )
    assert exc.value.status_code == 400
    assert URL_CASES["lm_studio_empty_base_error"] in exc.value.detail


@pytest.mark.parametrize("base,expected_url", URL_CASES["openai_compatible_list_url"])
def test_c2_openai_compatible_list_url(base: str, expected_url: str) -> None:
    with patch("om.server.manage.llm.api.httpx.get") as mock_get:
        mock_get.return_value = _response(_load("openai_models.json"))
        get_openai_compatible_available_models(
            OpenAICompatibleModelsRequest(api_base=base), MagicMock(), MagicMock()
        )
    assert mock_get.call_args.args[0] == expected_url


@pytest.mark.parametrize("base,expected_url", URL_CASES["lm_studio_list_url"])
def test_c2_lm_studio_list_url(base: str, expected_url: str) -> None:
    with patch("om.server.manage.llm.api.httpx.get") as mock_get:
        mock_get.return_value = _response(_load("lm_studio_models.json"))
        get_lm_studio_available_models(
            LMStudioModelsRequest(api_base=base), MagicMock(), MagicMock()
        )
    assert mock_get.call_args.args[0] == expected_url


# --- C3: Ollama /api/tags + /api/show ---------------------------------------


def _ollama_show_router(
    failing_model: str | None = None,
) -> Any:
    shows = {
        "llama3.1:8b": _load("ollama_show_chat.json"),
        "llava:7b": _load("ollama_show_vision.json"),
        "nomic-embed-text:latest": _load("ollama_show_embedding.json"),
    }

    def _post(url: str, json: dict, **_: Any) -> MagicMock:  # noqa: A002
        model = json["model"]
        if model == failing_model:
            return _response({}, status_error=RuntimeError("500 Server Error"))
        return _response(shows[model])

    return _post


def test_c3_ollama_tags_and_show() -> None:
    with (
        patch("om.server.manage.llm.api.httpx.get") as mock_get,
        patch("om.server.manage.llm.api.httpx.post", side_effect=_ollama_show_router()),
    ):
        mock_get.return_value = _response(_load("ollama_tags.json"))
        results = get_ollama_available_models(
            OllamaModelsRequest(api_base="http://h:11434"), MagicMock(), MagicMock()
        )
    by_name = {r.name: r for r in results}
    assert set(by_name) == {"llama3.1:8b", "llava:7b"}  # embedding skipped
    assert by_name["llava:7b"].supports_image_input is True
    assert by_name["llama3.1:8b"].supports_image_input is False
    # num_ctx (8192) wins over llama.context_length (131072)
    assert by_name["llama3.1:8b"].max_input_tokens == 8192
    # no num_ctx -> <arch>.context_length
    assert by_name["llava:7b"].max_input_tokens == 4096


def test_c3_ollama_show_failure_still_listed() -> None:
    with (
        patch("om.server.manage.llm.api.httpx.get") as mock_get,
        patch(
            "om.server.manage.llm.api.httpx.post",
            side_effect=_ollama_show_router(failing_model="llava:7b"),
        ),
    ):
        mock_get.return_value = _response(_load("ollama_tags.json"))
        results = get_ollama_available_models(
            OllamaModelsRequest(api_base="http://h:11434"), MagicMock(), MagicMock()
        )
    by_name = {r.name: r for r in results}
    assert "llava:7b" in by_name
    assert by_name["llava:7b"].max_input_tokens is None


def test_c3_ollama_empty_tags_is_400() -> None:
    with patch("om.server.manage.llm.api.httpx.get") as mock_get:
        mock_get.return_value = _response({"models": []})
        with pytest.raises(HTTPException) as exc:
            get_ollama_available_models(
                OllamaModelsRequest(api_base="http://h:11434"),
                MagicMock(),
                MagicMock(),
            )
    assert exc.value.status_code == 400


# --- C4: LM Studio /api/v1/models -------------------------------------------


def test_c4_lm_studio_parsing() -> None:
    with patch("om.server.manage.llm.api.httpx.get") as mock_get:
        mock_get.return_value = _response(_load("lm_studio_models.json"))
        results = get_lm_studio_available_models(
            LMStudioModelsRequest(api_base="http://h:1234"), MagicMock(), MagicMock()
        )
    by_name = {r.name: r for r in results}
    assert list(by_name) == sorted(by_name, key=str.lower)
    assert set(by_name) == {"gemma-3-4b", "qwen2.5-vl-7b-instruct", "qwen3-8b"}

    vl = by_name["qwen2.5-vl-7b-instruct"]
    assert vl.supports_image_input is True
    assert vl.max_input_tokens == 32768
    assert vl.display_name == "Qwen2.5 VL 7B Instruct"

    assert by_name["qwen3-8b"].supports_reasoning is True
    assert by_name["gemma-3-4b"].supports_reasoning is False  # ["off"] only
    assert by_name["gemma-3-4b"].display_name == "gemma-3-4b"  # key fallback
    assert by_name["gemma-3-4b"].max_input_tokens == 131072


# --- C5: OpenAI /v1/models + masked key -------------------------------------


def test_c5_openai_models_parsing() -> None:
    with patch("om.server.manage.llm.api.httpx.get") as mock_get:
        mock_get.return_value = _response(_load("openai_models.json"))
        results = get_openai_compatible_available_models(
            OpenAICompatibleModelsRequest(api_base="http://h:8000"),
            MagicMock(),
            MagicMock(),
        )
    assert [r.name for r in results] == ["llama-3.1-8b", "qwen2.5-vl"]
    assert results[1].max_input_tokens == 32768
    assert results[0].max_input_tokens is None


def test_c5_openai_empty_data_is_400() -> None:
    with patch("om.server.manage.llm.api.httpx.get") as mock_get:
        mock_get.return_value = _response({"data": []})
        with pytest.raises(HTTPException) as exc:
            get_openai_compatible_available_models(
                OpenAICompatibleModelsRequest(api_base="http://h:8000"),
                MagicMock(),
                MagicMock(),
            )
    assert exc.value.status_code == 400


def _stored_openai_compatible_provider(api_base: str) -> MagicMock:
    provider = MagicMock()
    provider.api_base = api_base
    provider.custom_config = None
    provider.api_key.get_value.return_value = "stored-secret"
    return provider


@pytest.mark.parametrize(
    "request_base,stored_base,expect_auth",
    [
        ("http://h:8000/v1", "http://h:8000/v1", "Bearer stored-secret"),
        # same server written without /v1 -> still the same base
        ("http://h:8000", "http://h:8000/v1", "Bearer stored-secret"),
        # changed host -> stored key must NOT be sent
        ("http://evil:8000/v1", "http://h:8000/v1", None),
    ],
)
def test_c5_masked_key_resolution(
    request_base: str, stored_base: str, expect_auth: str | None
) -> None:
    with (
        patch("om.server.manage.llm.api.httpx.get") as mock_get,
        patch(
            "om.server.manage.llm.api.fetch_existing_llm_provider",
            return_value=_stored_openai_compatible_provider(stored_base),
        ),
    ):
        mock_get.return_value = _response(_load("openai_models.json"))
        get_openai_compatible_available_models(
            OpenAICompatibleModelsRequest(
                api_base=request_base,
                api_key="stor****cret",
                api_key_changed=False,
                provider_name="my-vllm",
            ),
            MagicMock(),
            MagicMock(),
        )
    headers = mock_get.call_args.kwargs["headers"]
    assert headers.get("Authorization") == expect_auth


# --- C6: LiteLLM routing per provider ---------------------------------------


@pytest.mark.parametrize(
    "case", _load("routing_cases.json"), ids=lambda c: c["id"]  # type: ignore[no-any-return]
)
def test_c6_routing(case: dict[str, Any]) -> None:
    from tests.unit.om.llm.test_local_providers_routing import (
        capture_completion_kwargs,
    )

    kwargs = capture_completion_kwargs(case)["plain"]
    for key, expected in case["expect"].items():
        assert kwargs.get(key) == expected, key
    assert "/responses/" not in kwargs["model"]
