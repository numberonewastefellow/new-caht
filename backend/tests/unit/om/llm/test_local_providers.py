"""Unit tests for om/llm/local_providers.py and the LLM-layer paths the new
local providers (LM Studio, OpenAI-compatible) go through."""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from om.db.enums import LLMModelFlowType
from om.llm.constants import AGGREGATOR_PROVIDERS
from om.llm.constants import LlmProviderNames
from om.llm.constants import PROVIDER_DISPLAY_NAMES
from om.llm.constants import WELL_KNOWN_PROVIDER_NAMES
from om.llm.cost import calculate_llm_cost_cents
from om.llm.local_providers import is_local_provider
from om.llm.local_providers import is_non_chat_model_id
from om.llm.local_providers import litellm_lookup_provider
from om.llm.local_providers import LOCAL_PROVIDER_NAMES
from om.llm.local_providers import normalize_openai_v1_base
from om.llm.local_providers import OPENAI_COMPATIBLE_PLACEHOLDER_API_KEY
from om.llm.local_providers import resolve_local_provider_routing
from om.llm.local_providers import strip_openai_v1_suffix
from om.llm.utils import get_max_input_tokens_from_llm_provider
from om.llm.utils import is_true_openai_model
from om.llm.utils import model_is_reasoning_model
from om.llm.utils import model_supports_image_input
from om.llm.well_known_providers.llm_provider_options import (
    get_provider_display_name,
)


class TestNormalizeOpenAIV1Base:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("http://h:8000", "http://h:8000/v1"),
            ("http://h:8000/", "http://h:8000/v1"),
            ("http://h:8000/v1", "http://h:8000/v1"),
            ("http://h:8000/v1/", "http://h:8000/v1"),
            ("  http://h:1234  ", "http://h:1234/v1"),
            ("http://h/proxy/v1", "http://h/proxy/v1"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_cases(self, raw: str | None, expected: str) -> None:
        assert normalize_openai_v1_base(raw) == expected


class TestStripOpenAIV1Suffix:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("http://h:1234/v1", "http://h:1234"),
            ("http://h:1234/v1/", "http://h:1234"),
            ("http://h:1234/", "http://h:1234"),
            ("http://h:1234", "http://h:1234"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_cases(self, raw: str | None, expected: str) -> None:
        assert strip_openai_v1_suffix(raw) == expected

    def test_is_inverse_of_normalize(self) -> None:
        for base in ("http://h:1234", "http://host.docker.internal:8000"):
            assert strip_openai_v1_suffix(normalize_openai_v1_base(base)) == base


class TestResolveLocalProviderRouting:
    def test_lm_studio_without_key(self) -> None:
        assert resolve_local_provider_routing(
            "lm_studio", "http://host.docker.internal:1234", None
        ) == ("lm_studio", None, "http://host.docker.internal:1234/v1", "")

    def test_lm_studio_with_key(self) -> None:
        assert resolve_local_provider_routing(
            "lm_studio", "http://h:1234/v1", " k "
        ) == (
            "lm_studio",
            None,
            "http://h:1234/v1",
            "k",
        )

    def test_openai_compatible_without_key(self) -> None:
        assert resolve_local_provider_routing(
            "openai_compatible", "http://h:8000", None
        ) == (
            "openai",
            "openai",
            "http://h:8000/v1",
            OPENAI_COMPATIBLE_PLACEHOLDER_API_KEY,
        )

    def test_openai_compatible_with_key(self) -> None:
        _, _, _, key = resolve_local_provider_routing(
            "openai_compatible", "http://h:8000/v1", "secret"
        )
        assert key == "secret"

    def test_empty_base_becomes_none(self) -> None:
        _, _, base, _ = resolve_local_provider_routing("openai_compatible", "", None)
        assert base is None

    @pytest.mark.parametrize(
        "provider",
        ["openai", "azure", "anthropic", "bedrock", "vertex_ai", "ollama_chat"],
    )
    def test_rejects_non_local_providers(self, provider: str) -> None:
        assert not is_local_provider(provider)
        with pytest.raises(ValueError):
            resolve_local_provider_routing(provider, "http://h", None)


class TestIsNonChatModelId:
    @pytest.mark.parametrize(
        "model_id",
        [
            "text-embedding-3-small",
            "nomic-embed-text-v1.5",
            "BAAI/bge-reranker-v2-m3",
            "bge-m3",
            "e5-large-v2",
            "whisper-1",
            "tts-1",
            "dall-e-3",
            "all-MiniLM-L6-v2",
            "",
        ],
    )
    def test_non_chat(self, model_id: str) -> None:
        assert is_non_chat_model_id(model_id)

    @pytest.mark.parametrize(
        "model_id",
        [
            "llama-3.1-8b",
            "qwen2.5-vl",
            "Qwen/Qwen2.5-7B-Instruct",
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistral-7b-instruct-v0.3",
            "gpt-oss-20b",
            "deepseek-r1-distill-qwen-7b",
            "phi-3.5-mini-instruct",
        ],
    )
    def test_chat(self, model_id: str) -> None:
        assert not is_non_chat_model_id(model_id)


class TestConstantsAndDisplayNames:
    def test_enum_values(self) -> None:
        assert LlmProviderNames.LM_STUDIO.value == "lm_studio"
        assert LlmProviderNames.OPENAI_COMPATIBLE.value == "openai_compatible"
        assert LOCAL_PROVIDER_NAMES == {"lm_studio", "openai_compatible"}

    def test_aggregator_membership(self) -> None:
        assert LlmProviderNames.LM_STUDIO in AGGREGATOR_PROVIDERS
        assert LlmProviderNames.OPENAI_COMPATIBLE in AGGREGATOR_PROVIDERS

    def test_not_in_onboarding_list(self) -> None:
        # Decided 2026-10-30: admin page only, not first-run onboarding.
        assert LlmProviderNames.LM_STUDIO not in WELL_KNOWN_PROVIDER_NAMES
        assert LlmProviderNames.OPENAI_COMPATIBLE not in WELL_KNOWN_PROVIDER_NAMES

    def test_display_names(self) -> None:
        assert get_provider_display_name("lm_studio") == "LM Studio"
        assert get_provider_display_name("openai_compatible") == "OpenAI-Compatible"
        assert PROVIDER_DISPLAY_NAMES["lm_studio"] == "LM Studio"
        # Existing names untouched
        assert get_provider_display_name("ollama_chat") == "Ollama"
        assert get_provider_display_name("openai") == "ChatGPT (OpenAI)"

    def test_lookup_provider(self) -> None:
        assert litellm_lookup_provider("openai_compatible") == "openai"
        for provider in ("lm_studio", "openai", "azure", "ollama_chat", "bedrock"):
            assert litellm_lookup_provider(provider) == provider


class TestLLMLayerPathsForLocalProviders:
    def test_openai_compatible_never_uses_responses_api(self) -> None:
        assert is_true_openai_model("openai_compatible", "gpt-4o") is False
        assert is_true_openai_model("lm_studio", "gpt-4o") is False

    @pytest.mark.parametrize("provider", ["lm_studio", "openai_compatible"])
    def test_unknown_model_is_not_reasoning_and_does_not_raise(
        self, provider: str
    ) -> None:
        assert model_is_reasoning_model("qwen2.5-7b-instruct", provider) is False

    def test_cost_is_zero_for_unknown_local_model(self) -> None:
        assert calculate_llm_cost_cents("lm_studio/qwen2.5-7b-instruct", 10, 10) == 0
        assert calculate_llm_cost_cents("openai/my-local-llama", 10, 10) == 0

    def test_max_input_tokens_come_from_model_configuration(self) -> None:
        provider_view = SimpleNamespace(
            name="my-lm-studio",
            model_configurations=[
                SimpleNamespace(name="qwen2.5-7b-instruct", max_input_tokens=32768)
            ],
        )
        with patch("om.llm.utils.get_max_input_tokens") as fallback:
            assert (
                get_max_input_tokens_from_llm_provider(
                    provider_view, "qwen2.5-7b-instruct"  # type: ignore[arg-type]
                )
                == 32768
            )
            fallback.assert_not_called()

    def test_image_input_from_db_vision_flow(self) -> None:
        model_config = SimpleNamespace(
            llm_model_flow_types=[LLMModelFlowType.CHAT, LLMModelFlowType.VISION]
        )
        session = MagicMock()
        session.scalar.return_value = model_config

        @contextmanager
        def _session():  # type: ignore[no-untyped-def]
            yield session

        with patch("om.llm.utils.get_session_with_current_tenant", _session):
            assert model_supports_image_input("qwen2.5-vl", "openai_compatible")

    def test_image_input_falls_back_to_false_without_crash(self) -> None:
        session = MagicMock()
        session.scalar.return_value = None

        @contextmanager
        def _session():  # type: ignore[no-untyped-def]
            yield session

        with patch("om.llm.utils.get_session_with_current_tenant", _session):
            assert not model_supports_image_input("my-local-model", "lm_studio")
