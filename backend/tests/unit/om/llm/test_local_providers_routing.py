"""LiteLLM call arguments per provider.

Two jobs:
1. Regression guard: for every provider that existed before local-provider
   support was added, the kwargs we pass to `litellm.completion` must be
   identical to the golden capture in
   `fixtures/local_providers/golden_existing_provider_kwargs.json`
   (taken before the local-provider routing change).
2. Routing for the new local providers (`lm_studio`, `openai_compatible`).

`capture_completion_kwargs` is also used to (re)generate the golden file;
only regenerate it when a kwargs change is intended.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from om.llm.factory import get_llm
from om.llm.models import UserMessage

GOLDEN_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "local_providers"
    / "golden_existing_provider_kwargs.json"
)

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": "Look something up",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
            },
        },
    }
]

# Providers that existed before local-provider support. Keys are stable ids
# used in the golden file.
EXISTING_PROVIDER_CASES: dict[str, dict[str, Any]] = {
    "openai_gpt4o": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "sk-test",
    },
    "openai_custom_base": {
        "provider": "openai",
        "model": "llama-3.1-8b",
        "api_key": "local-key",
        "api_base": "http://h:8000/v1",
    },
    "azure_gpt4o": {
        "provider": "azure",
        "model": "gpt-4o",
        "api_key": "az-key",
        "api_base": "https://res.openai.azure.com",
        "api_version": "2024-02-15-preview",
        "deployment_name": "gpt4o-deploy",
    },
    "anthropic_sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "api_key": "ant-key",
    },
    "bedrock_claude": {
        "provider": "bedrock",
        "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "custom_config": {"AWS_REGION_NAME": "us-east-1"},
    },
    "vertex_gemini": {
        "provider": "vertex_ai",
        "model": "gemini-2.5-flash",
        "custom_config": {"vertex_location": "us-central1"},
    },
    "openrouter_llama": {
        "provider": "openrouter",
        "model": "meta-llama/llama-3.1-8b-instruct",
        "api_key": "or-key",
        "api_base": "https://openrouter.ai/api/v1",
    },
    "ollama_with_key": {
        "provider": "ollama_chat",
        "model": "llama3.1:8b",
        "api_base": "http://host.docker.internal:11434",
        "custom_config": {"OLLAMA_API_KEY": "olk"},
        "model_kwargs": {"num_ctx": 8192},
    },
    "ollama_no_key": {
        "provider": "ollama_chat",
        "model": "qwen2.5:7b",
        "api_base": "http://127.0.0.1:11434",
    },
    "mistral_large": {
        "provider": "mistral",
        "model": "mistral-large-latest",
        "api_key": "mi-key",
    },
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # e.g. the isolated HTTPHandler client: record only its type
    return f"<{type(value).__name__}>"


def capture_completion_kwargs(case: dict[str, Any]) -> dict[str, Any]:
    """Build the LLM through `get_llm` and capture `litellm.completion` kwargs
    for a streamed call without tools and with tools."""
    llm = get_llm(
        provider=case["provider"],
        model=case["model"],
        max_input_tokens=case.get("max_input_tokens", 32000),
        deployment_name=case.get("deployment_name"),
        api_key=case.get("api_key"),
        api_base=case.get("api_base"),
        api_version=case.get("api_version"),
        custom_config=case.get("custom_config"),
        temperature=0.5,
        timeout=30,
        model_kwargs=dict(case.get("model_kwargs") or {}),
    )
    captured: dict[str, Any] = {}
    for label, tools in (("plain", None), ("tools", _TOOLS)):
        with patch("litellm.completion") as mock_completion:
            mock_completion.return_value = []
            list(llm.stream([UserMessage(content="Hi")], tools=tools))
            assert mock_completion.call_count == 1
            captured[label] = _jsonable(dict(mock_completion.call_args.kwargs))
    return captured


def capture_all_existing() -> dict[str, Any]:
    return {
        case_id: capture_completion_kwargs(case)
        for case_id, case in EXISTING_PROVIDER_CASES.items()
    }


@pytest.mark.parametrize("case_id", sorted(EXISTING_PROVIDER_CASES))
def test_existing_provider_kwargs_unchanged(case_id: str) -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert case_id in golden, f"golden capture missing case {case_id}"
    actual = capture_completion_kwargs(EXISTING_PROVIDER_CASES[case_id])
    assert actual == golden[case_id]


def test_golden_covers_all_cases() -> None:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert set(golden) == set(EXISTING_PROVIDER_CASES)


# ---------------------------------------------------------------------------
# New local providers
# ---------------------------------------------------------------------------


def _local_kwargs(**case: Any) -> dict[str, Any]:
    return capture_completion_kwargs(case)["plain"]


def test_lm_studio_routing_without_key() -> None:
    kwargs = _local_kwargs(
        provider="lm_studio",
        model="qwen2.5-7b-instruct",
        api_base="http://host.docker.internal:1234",
    )
    assert kwargs["model"] == "lm_studio/qwen2.5-7b-instruct"
    assert kwargs["base_url"] == "http://host.docker.internal:1234/v1"
    assert kwargs["custom_llm_provider"] is None
    assert kwargs["api_key"] == ""
    assert kwargs["client"] is None


def test_lm_studio_routing_with_custom_config_key() -> None:
    kwargs = _local_kwargs(
        provider="lm_studio",
        model="qwen2.5-7b-instruct",
        api_base="http://host.docker.internal:1234/v1/",
        custom_config={"LM_STUDIO_API_KEY": "lms-secret"},
    )
    assert kwargs["model"] == "lm_studio/qwen2.5-7b-instruct"
    assert kwargs["base_url"] == "http://host.docker.internal:1234/v1"
    assert kwargs["api_key"] == "lms-secret"


def test_openai_compatible_routing_without_key() -> None:
    kwargs = _local_kwargs(
        provider="openai_compatible",
        model="llama-3.1-8b",
        api_base="http://host.docker.internal:8000",
    )
    assert kwargs["model"] == "openai/llama-3.1-8b"
    assert "responses" not in kwargs["model"]
    assert kwargs["custom_llm_provider"] == "openai"
    assert kwargs["base_url"] == "http://host.docker.internal:8000/v1"
    assert kwargs["api_key"] == "not-needed"
    assert kwargs["client"] is None


def test_openai_compatible_routing_with_key_and_openai_like_model_name() -> None:
    # Even a model that shares a name with a real OpenAI model must stay on
    # chat-completions (no Responses API bridge) for an OpenAI-compatible server.
    kwargs = _local_kwargs(
        provider="openai_compatible",
        model="gpt-4o",
        api_key="srv-key",
        api_base="http://h:8000/v1",
    )
    assert kwargs["model"] == "openai/gpt-4o"
    assert kwargs["api_key"] == "srv-key"
    assert kwargs["base_url"] == "http://h:8000/v1"
    assert kwargs["client"] is None
    assert "reasoning" not in kwargs


@pytest.mark.parametrize(
    "provider,api_base,custom_config,expected_model",
    [
        (
            "lm_studio",
            "http://host.docker.internal:1234",
            {"LM_STUDIO_API_KEY": "k"},
            "lm_studio/qwen3-8b",
        ),
        ("openai_compatible", "http://host.docker.internal:8000/v1", None, None),
    ],
)
def test_admin_test_endpoint_builds_local_llm(
    provider: str,
    api_base: str,
    custom_config: dict[str, str] | None,
    expected_model: str | None,
) -> None:
    """`POST /admin/llm/test` for a new (not yet saved) local provider."""
    from om.server.manage.llm.api import test_llm_configuration
    from om.server.manage.llm.models import TestLLMRequest

    captured: dict[str, Any] = {}

    def _fake_test_llm(llm: Any) -> None:
        captured["llm"] = llm
        return None

    with (
        patch(
            "om.server.manage.llm.api.fetch_existing_llm_provider", return_value=None
        ),
        patch("om.server.manage.llm.api.test_llm", side_effect=_fake_test_llm),
    ):
        test_llm_configuration(
            TestLLMRequest(
                name="new-local",
                provider=provider,
                api_base=api_base,
                custom_config=custom_config,
                default_model_name="qwen3-8b",
                model_configurations=[],
                api_key_changed=True,
                custom_config_changed=True,
            ),
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
        )
    llm = captured["llm"]
    assert llm.config.model_provider == provider
    assert llm.config.api_base.endswith("/v1")
    if expected_model:
        assert llm._litellm_model_prefix + "/qwen3-8b" == expected_model


def test_local_provider_config_reports_original_provider() -> None:
    llm = get_llm(
        provider="openai_compatible",
        model="llama-3.1-8b",
        max_input_tokens=8192,
        deployment_name=None,
        api_base="http://h:8000",
    )
    # Stored provider string is kept for display / DB lookups.
    assert llm.config.model_provider == "openai_compatible"
    assert llm.config.api_base == "http://h:8000/v1"
