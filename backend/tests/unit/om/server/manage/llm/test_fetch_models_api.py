"""Tests for LLM model fetch endpoints.

These tests verify the full request/response flow for fetching models
from dynamic providers (Ollama, OpenRouter, LM Studio, OpenAI-compatible),
including the
sync-to-DB behavior when provider_name is specified.
"""

from unittest.mock import MagicMock
from unittest.mock import patch

import litellm  # noqa: F401  # load before tests patch httpx.get (litellm fetches its model map on import)
import pytest

from om.server.manage.llm.models import LMStudioModelsRequest
from om.server.manage.llm.models import OllamaFinalModelResponse
from om.server.manage.llm.models import OllamaModelsRequest
from om.server.manage.llm.models import OpenAICompatibleModelsRequest
from om.server.manage.llm.models import OpenRouterFinalModelResponse
from om.server.manage.llm.models import OpenRouterModelsRequest


class TestGetOllamaAvailableModels:
    """Tests for the Ollama model fetch endpoint."""

    @pytest.fixture
    def mock_ollama_tags_response(self) -> dict:
        """Mock response from Ollama /api/tags endpoint."""
        return {
            "models": [
                {"name": "llama3:latest"},
                {"name": "mistral:7b"},
                {"name": "qwen2.5:14b"},
            ]
        }

    @pytest.fixture
    def mock_ollama_show_response(self) -> dict:
        """Mock response from Ollama /api/show endpoint."""
        return {
            "details": {"family": "llama", "families": ["llama"]},
            "model_info": {
                "general.architecture": "llama",
                "llama.context_length": 8192,
            },
            "capabilities": [
                "completion"
            ],  # Required to pass supports_completion() check
        }

    def test_returns_model_list(
        self, mock_ollama_tags_response: dict, mock_ollama_show_response: dict
    ) -> None:
        """Test that endpoint returns properly formatted model list."""
        from om.server.manage.llm.api import get_ollama_available_models

        mock_session = MagicMock()

        with patch("om.server.manage.llm.api.httpx") as mock_httpx:
            # Mock GET for /api/tags
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = mock_ollama_tags_response
            mock_get_response.raise_for_status = MagicMock()
            mock_httpx.get.return_value = mock_get_response

            # Mock POST for /api/show (called for each model)
            mock_post_response = MagicMock()
            mock_post_response.json.return_value = mock_ollama_show_response
            mock_post_response.raise_for_status = MagicMock()
            mock_httpx.post.return_value = mock_post_response

            request = OllamaModelsRequest(api_base="http://localhost:11434")
            results = get_ollama_available_models(request, MagicMock(), mock_session)

            assert len(results) == 3
            assert all(isinstance(r, OllamaFinalModelResponse) for r in results)
            # Check display names are generated
            assert any("Llama" in r.display_name for r in results)
            assert any("Mistral" in r.display_name for r in results)
            # Results should be alphabetically sorted by model name
            assert [r.name for r in results] == sorted(
                [r.name for r in results], key=str.lower
            )

    def test_syncs_to_db_when_provider_name_specified(
        self, mock_ollama_tags_response: dict, mock_ollama_show_response: dict
    ) -> None:
        """Test that models are synced to DB when provider_name is given."""
        from om.server.manage.llm.api import get_ollama_available_models

        mock_session = MagicMock()
        mock_provider = MagicMock()
        mock_provider.id = 1
        mock_provider.model_configurations = []

        with (
            patch("om.server.manage.llm.api.httpx") as mock_httpx,
            patch("om.db.llm.fetch_existing_llm_provider", return_value=mock_provider),
        ):
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = mock_ollama_tags_response
            mock_get_response.raise_for_status = MagicMock()
            mock_httpx.get.return_value = mock_get_response

            mock_post_response = MagicMock()
            mock_post_response.json.return_value = mock_ollama_show_response
            mock_post_response.raise_for_status = MagicMock()
            mock_httpx.post.return_value = mock_post_response

            request = OllamaModelsRequest(
                api_base="http://localhost:11434",
                provider_name="my-ollama",
            )
            get_ollama_available_models(request, MagicMock(), mock_session)

            # Verify DB operations were called
            assert mock_session.execute.call_count == 6
            mock_session.commit.assert_called_once()

    def test_no_sync_when_provider_name_not_specified(
        self, mock_ollama_tags_response: dict, mock_ollama_show_response: dict
    ) -> None:
        """Test that models are NOT synced when provider_name is None."""
        from om.server.manage.llm.api import get_ollama_available_models

        mock_session = MagicMock()

        with patch("om.server.manage.llm.api.httpx") as mock_httpx:
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = mock_ollama_tags_response
            mock_get_response.raise_for_status = MagicMock()
            mock_httpx.get.return_value = mock_get_response

            mock_post_response = MagicMock()
            mock_post_response.json.return_value = mock_ollama_show_response
            mock_post_response.raise_for_status = MagicMock()
            mock_httpx.post.return_value = mock_post_response

            request = OllamaModelsRequest(api_base="http://localhost:11434")
            get_ollama_available_models(request, MagicMock(), mock_session)

            # No DB operations should happen
            mock_session.execute.assert_not_called()
            mock_session.commit.assert_not_called()


class TestGetOpenRouterAvailableModels:
    """Tests for the OpenRouter model fetch endpoint."""

    @pytest.fixture
    def mock_openrouter_response(self) -> dict:
        """Mock response from OpenRouter API."""
        return {
            "data": [
                {
                    "id": "anthropic/claude-3.5-sonnet",
                    "name": "Claude 3.5 Sonnet",
                    "context_length": 200000,
                    "architecture": {"input_modalities": ["text", "image"]},
                },
                {
                    "id": "openai/gpt-4o",
                    "name": "GPT-4o",
                    "context_length": 128000,
                    "architecture": {"input_modalities": ["text", "image"]},
                },
                {
                    "id": "meta-llama/llama-3.1-70b",
                    "name": "Llama 3.1 70B",
                    "context_length": 131072,
                    "architecture": {"input_modalities": ["text"]},
                },
            ]
        }

    def test_returns_model_list(self, mock_openrouter_response: dict) -> None:
        """Test that endpoint returns properly formatted model list."""
        from om.server.manage.llm.api import get_openrouter_available_models

        mock_session = MagicMock()

        with patch("om.server.manage.llm.api.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_openrouter_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            request = OpenRouterModelsRequest(
                api_base="https://openrouter.ai/api/v1",
                api_key="test-key",
            )
            results = get_openrouter_available_models(
                request, MagicMock(), mock_session
            )

            assert len(results) == 3
            assert all(isinstance(r, OpenRouterFinalModelResponse) for r in results)
            # Check that models have correct context lengths
            claude = next(r for r in results if "claude" in r.name.lower())
            assert claude.max_input_tokens == 200000

    def test_infers_vision_support(self, mock_openrouter_response: dict) -> None:
        """Test that vision support is correctly inferred from modality."""
        from om.server.manage.llm.api import get_openrouter_available_models

        mock_session = MagicMock()

        with patch("om.server.manage.llm.api.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_openrouter_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            request = OpenRouterModelsRequest(
                api_base="https://openrouter.ai/api/v1",
                api_key="test-key",
            )
            results = get_openrouter_available_models(
                request, MagicMock(), mock_session
            )

            # Models with "image" in modality should have vision support
            claude = next(r for r in results if "claude" in r.name.lower())
            llama = next(r for r in results if "llama" in r.name.lower())

            assert claude.supports_image_input is True
            assert llama.supports_image_input is False

    def test_syncs_to_db_when_provider_name_specified(
        self, mock_openrouter_response: dict
    ) -> None:
        """Test that models are synced to DB when provider_name is given."""
        from om.server.manage.llm.api import get_openrouter_available_models

        mock_session = MagicMock()
        mock_provider = MagicMock()
        mock_provider.id = 1
        mock_provider.model_configurations = []

        with (
            patch("om.server.manage.llm.api.httpx.get") as mock_get,
            patch("om.db.llm.fetch_existing_llm_provider", return_value=mock_provider),
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = mock_openrouter_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            request = OpenRouterModelsRequest(
                api_base="https://openrouter.ai/api/v1",
                api_key="test-key",
                provider_name="my-openrouter",
            )
            get_openrouter_available_models(request, MagicMock(), mock_session)

            # Verify DB operations were called
            assert mock_session.execute.call_count == 8
            mock_session.commit.assert_called_once()

    def test_preserves_existing_models_on_sync(
        self, mock_openrouter_response: dict
    ) -> None:
        """Test that existing models are not overwritten during sync."""
        from om.server.manage.llm.api import get_openrouter_available_models

        mock_session = MagicMock()

        # Provider already has claude model
        existing_model = MagicMock()
        existing_model.name = "anthropic/claude-3.5-sonnet"

        mock_provider = MagicMock()
        mock_provider.id = 1
        mock_provider.model_configurations = [existing_model]

        with (
            patch("om.server.manage.llm.api.httpx.get") as mock_get,
            patch("om.db.llm.fetch_existing_llm_provider", return_value=mock_provider),
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = mock_openrouter_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            request = OpenRouterModelsRequest(
                api_base="https://openrouter.ai/api/v1",
                api_key="test-key",
                provider_name="my-openrouter",
            )
            get_openrouter_available_models(request, MagicMock(), mock_session)

            # Only 2 new models should be inserted (claude already exists)
            assert mock_session.execute.call_count == 5

    def test_no_sync_when_provider_name_not_specified(
        self, mock_openrouter_response: dict
    ) -> None:
        """Test that models are NOT synced when provider_name is None."""
        from om.server.manage.llm.api import get_openrouter_available_models

        mock_session = MagicMock()

        with patch("om.server.manage.llm.api.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_openrouter_response
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            request = OpenRouterModelsRequest(
                api_base="https://openrouter.ai/api/v1",
                api_key="test-key",
            )
            get_openrouter_available_models(request, MagicMock(), mock_session)

            # No DB operations should happen
            mock_session.execute.assert_not_called()
            mock_session.commit.assert_not_called()


def _json_response(payload: object) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status = MagicMock()
    return response


_LM_STUDIO_PAYLOAD = {
    "models": [
        {
            "type": "llm",
            "key": "qwen3-8b",
            "display_name": "Qwen3 8B",
            "max_context_length": 40960,
            "capabilities": {"reasoning": {"allowed_options": ["off", "on"]}},
        },
        {"type": "embedding", "key": "nomic-embed", "max_context_length": 2048},
    ]
}

_OPENAI_COMPATIBLE_PAYLOAD = {
    "data": [
        {"id": "llama-3.1-8b"},
        {"id": "text-embedding-3-small"},
        {"id": "qwen2.5-vl", "context_length": 32768},
    ]
}


class TestOllamaApiKeyAndNumCtx:
    """Ollama fetch: optional API key (Bearer) and num_ctx precedence."""

    def test_api_key_sent_as_bearer_to_tags_and_show(self) -> None:
        from om.server.manage.llm.api import get_ollama_available_models

        with patch("om.server.manage.llm.api.httpx") as mock_httpx:
            mock_httpx.get.return_value = _json_response(
                {"models": [{"name": "llama3:latest"}]}
            )
            mock_httpx.post.return_value = _json_response(
                {
                    "model_info": {"general.architecture": "llama"},
                    "capabilities": ["completion"],
                }
            )
            get_ollama_available_models(
                OllamaModelsRequest(api_base="http://h:11434", api_key="olk"),
                MagicMock(),
                MagicMock(),
            )
            assert mock_httpx.get.call_args.kwargs["headers"] == {
                "Authorization": "Bearer olk"
            }
            assert mock_httpx.post.call_args.kwargs["headers"] == {
                "Authorization": "Bearer olk"
            }

    def test_no_key_sends_no_auth_header(self) -> None:
        from om.server.manage.llm.api import get_ollama_available_models

        with patch("om.server.manage.llm.api.httpx") as mock_httpx:
            mock_httpx.get.return_value = _json_response(
                {"models": [{"name": "llama3:latest"}]}
            )
            mock_httpx.post.return_value = _json_response(
                {"model_info": {}, "capabilities": ["completion"]}
            )
            get_ollama_available_models(
                OllamaModelsRequest(api_base="http://h:11434"),
                MagicMock(),
                MagicMock(),
            )
            assert mock_httpx.get.call_args.kwargs["headers"] == {}

    def test_masked_key_uses_stored_custom_config_key(self) -> None:
        from om.server.manage.llm.api import get_ollama_available_models

        stored = MagicMock()
        stored.api_base = "http://h:11434/"
        stored.custom_config = {"OLLAMA_API_KEY": "real-key"}
        with (
            patch("om.server.manage.llm.api.httpx") as mock_httpx,
            patch(
                "om.server.manage.llm.api.fetch_existing_llm_provider",
                return_value=stored,
            ),
        ):
            mock_httpx.get.return_value = _json_response(
                {"models": [{"name": "llama3:latest"}]}
            )
            mock_httpx.post.return_value = _json_response(
                {"model_info": {}, "capabilities": ["completion"]}
            )
            get_ollama_available_models(
                OllamaModelsRequest(
                    api_base="http://h:11434",
                    api_key="real****",
                    api_key_changed=False,
                    provider_name="my-ollama",
                ),
                MagicMock(),
                MagicMock(),
            )
            assert mock_httpx.get.call_args.kwargs["headers"] == {
                "Authorization": "Bearer real-key"
            }

    def test_num_ctx_wins_over_context_length(self) -> None:
        from om.server.manage.llm.api import get_ollama_available_models

        with patch("om.server.manage.llm.api.httpx") as mock_httpx:
            mock_httpx.get.return_value = _json_response(
                {"models": [{"name": "llama3:latest"}]}
            )
            mock_httpx.post.return_value = _json_response(
                {
                    "model_info": {
                        "general.architecture": "llama",
                        "llama.context_length": 131072,
                    },
                    "capabilities": ["completion"],
                    "parameters": "num_ctx 16384\nstop <|eot_id|>",
                }
            )
            results = get_ollama_available_models(
                OllamaModelsRequest(api_base="http://h:11434"),
                MagicMock(),
                MagicMock(),
            )
            assert results[0].max_input_tokens == 16384

    @pytest.mark.parametrize(
        "parameters,expected",
        [
            (None, None),
            ("", None),
            ("num_ctx 4096", 4096),
            ('num_ctx "4096"', 4096),
            ("num_ctx 0", None),
            ("num_ctx abc", None),
            ("temperature 0.7\nnum_ctx 2048", 2048),
        ],
    )
    def test_num_ctx_parsing(
        self, parameters: str | None, expected: int | None
    ) -> None:
        from om.server.manage.llm.models import OllamaModelDetails

        details = OllamaModelDetails(model_info={}, parameters=parameters)
        assert details.num_ctx() == expected


class TestGetLMStudioAvailableModels:
    def test_returns_llm_models_only(self) -> None:
        from om.server.manage.llm.api import get_lm_studio_available_models
        from om.server.manage.llm.models import LMStudioFinalModelResponse
        from om.server.manage.llm.models import LMStudioModelsRequest

        with patch("om.server.manage.llm.api.httpx.get") as mock_get:
            mock_get.return_value = _json_response(_LM_STUDIO_PAYLOAD)
            results = get_lm_studio_available_models(
                LMStudioModelsRequest(api_base="http://h:1234/v1/"),
                MagicMock(),
                MagicMock(),
            )
        assert mock_get.call_args.args[0] == "http://h:1234/api/v1/models"
        assert mock_get.call_args.kwargs["headers"] == {}
        assert len(results) == 1
        assert isinstance(results[0], LMStudioFinalModelResponse)
        assert results[0].name == "qwen3-8b"
        assert results[0].supports_reasoning is True
        assert results[0].max_input_tokens == 40960

    def test_api_key_sent_as_bearer(self) -> None:
        from om.server.manage.llm.api import get_lm_studio_available_models
        from om.server.manage.llm.models import LMStudioModelsRequest

        with patch("om.server.manage.llm.api.httpx.get") as mock_get:
            mock_get.return_value = _json_response(_LM_STUDIO_PAYLOAD)
            get_lm_studio_available_models(
                LMStudioModelsRequest(api_base="http://h:1234", api_key="lms"),
                MagicMock(),
                MagicMock(),
            )
        assert mock_get.call_args.kwargs["headers"] == {"Authorization": "Bearer lms"}

    def test_masked_key_resolves_stored_custom_config(self) -> None:
        from om.server.manage.llm.api import get_lm_studio_available_models
        from om.server.manage.llm.models import LMStudioModelsRequest

        stored = MagicMock()
        stored.api_base = "http://h:1234/v1"  # stored with /v1, request without
        stored.custom_config = {"LM_STUDIO_API_KEY": "real-lms"}
        with (
            patch("om.server.manage.llm.api.httpx.get") as mock_get,
            patch(
                "om.server.manage.llm.api.fetch_existing_llm_provider",
                return_value=stored,
            ),
        ):
            mock_get.return_value = _json_response(_LM_STUDIO_PAYLOAD)
            get_lm_studio_available_models(
                LMStudioModelsRequest(
                    api_base="http://h:1234",
                    api_key="real****",
                    api_key_changed=False,
                    provider_name="my-lms",
                ),
                MagicMock(),
                MagicMock(),
            )
        assert mock_get.call_args.kwargs["headers"] == {
            "Authorization": "Bearer real-lms"
        }

    def test_no_models_is_400(self) -> None:
        from fastapi import HTTPException

        from om.server.manage.llm.api import get_lm_studio_available_models
        from om.server.manage.llm.models import LMStudioModelsRequest

        with patch("om.server.manage.llm.api.httpx.get") as mock_get:
            mock_get.return_value = _json_response(
                {"models": [{"type": "embedding", "key": "e"}]}
            )
            with pytest.raises(HTTPException) as exc:
                get_lm_studio_available_models(
                    LMStudioModelsRequest(api_base="http://h:1234"),
                    MagicMock(),
                    MagicMock(),
                )
        assert exc.value.status_code == 400

    def test_server_error_is_400(self) -> None:
        from fastapi import HTTPException

        from om.server.manage.llm.api import get_lm_studio_available_models
        from om.server.manage.llm.models import LMStudioModelsRequest

        with patch(
            "om.server.manage.llm.api.httpx.get",
            side_effect=RuntimeError("connection refused"),
        ):
            with pytest.raises(HTTPException) as exc:
                get_lm_studio_available_models(
                    LMStudioModelsRequest(api_base="http://h:1234"),
                    MagicMock(),
                    MagicMock(),
                )
        assert exc.value.status_code == 400
        assert "LM Studio" in exc.value.detail

    def test_syncs_to_db_when_provider_name_specified(self) -> None:
        from om.server.manage.llm.api import get_lm_studio_available_models
        from om.server.manage.llm.models import LMStudioModelsRequest

        mock_session = MagicMock()
        with (
            patch("om.server.manage.llm.api.httpx.get") as mock_get,
            patch(
                "om.server.manage.llm.api.sync_model_configurations", return_value=1
            ) as mock_sync,
        ):
            mock_get.return_value = _json_response(_LM_STUDIO_PAYLOAD)
            get_lm_studio_available_models(
                LMStudioModelsRequest(api_base="http://h:1234", provider_name="lms"),
                MagicMock(),
                mock_session,
            )
        mock_sync.assert_called_once()
        assert mock_sync.call_args.kwargs["provider_name"] == "lms"
        assert mock_sync.call_args.kwargs["models"][0]["name"] == "qwen3-8b"


class TestGetOpenAICompatibleAvailableModels:
    def test_returns_chat_models_sorted(self) -> None:
        from om.server.manage.llm.api import get_openai_compatible_available_models
        from om.server.manage.llm.models import OpenAICompatibleModelsRequest

        with patch("om.server.manage.llm.api.httpx.get") as mock_get:
            mock_get.return_value = _json_response(_OPENAI_COMPATIBLE_PAYLOAD)
            results = get_openai_compatible_available_models(
                OpenAICompatibleModelsRequest(api_base="http://h:8000"),
                MagicMock(),
                MagicMock(),
            )
        assert mock_get.call_args.args[0] == "http://h:8000/v1/models"
        assert [r.name for r in results] == ["llama-3.1-8b", "qwen2.5-vl"]
        assert results[1].max_input_tokens == 32768
        assert all(r.supports_image_input is False for r in results)

    def test_key_passthrough(self) -> None:
        from om.server.manage.llm.api import get_openai_compatible_available_models
        from om.server.manage.llm.models import OpenAICompatibleModelsRequest

        with patch("om.server.manage.llm.api.httpx.get") as mock_get:
            mock_get.return_value = _json_response(_OPENAI_COMPATIBLE_PAYLOAD)
            get_openai_compatible_available_models(
                OpenAICompatibleModelsRequest(api_base="http://h:8000/v1", api_key="k"),
                MagicMock(),
                MagicMock(),
            )
        assert mock_get.call_args.kwargs["headers"] == {"Authorization": "Bearer k"}

    def test_only_non_chat_models_is_400(self) -> None:
        from fastapi import HTTPException

        from om.server.manage.llm.api import get_openai_compatible_available_models
        from om.server.manage.llm.models import OpenAICompatibleModelsRequest

        with patch("om.server.manage.llm.api.httpx.get") as mock_get:
            mock_get.return_value = _json_response(
                {"data": [{"id": "text-embedding-3-small"}]}
            )
            with pytest.raises(HTTPException) as exc:
                get_openai_compatible_available_models(
                    OpenAICompatibleModelsRequest(api_base="http://h:8000"),
                    MagicMock(),
                    MagicMock(),
                )
        assert exc.value.status_code == 400

    def test_masked_key_without_stored_provider_sends_nothing(self) -> None:
        from om.server.manage.llm.api import get_openai_compatible_available_models
        from om.server.manage.llm.models import OpenAICompatibleModelsRequest

        with (
            patch("om.server.manage.llm.api.httpx.get") as mock_get,
            patch(
                "om.server.manage.llm.api.fetch_existing_llm_provider",
                return_value=None,
            ),
        ):
            mock_get.return_value = _json_response(_OPENAI_COMPATIBLE_PAYLOAD)
            get_openai_compatible_available_models(
                OpenAICompatibleModelsRequest(
                    api_base="http://h:8000",
                    api_key="sk-****",
                    api_key_changed=False,
                    provider_name="gone",
                ),
                MagicMock(),
                MagicMock(),
            )
        assert mock_get.call_args.kwargs["headers"] == {}

    def test_syncs_to_db_when_provider_name_specified(self) -> None:
        from om.server.manage.llm.api import get_openai_compatible_available_models
        from om.server.manage.llm.models import OpenAICompatibleModelsRequest

        with (
            patch("om.server.manage.llm.api.httpx.get") as mock_get,
            patch(
                "om.server.manage.llm.api.sync_model_configurations", return_value=2
            ) as mock_sync,
        ):
            mock_get.return_value = _json_response(_OPENAI_COMPATIBLE_PAYLOAD)
            get_openai_compatible_available_models(
                OpenAICompatibleModelsRequest(
                    api_base="http://h:8000", provider_name="vllm"
                ),
                MagicMock(),
                MagicMock(),
            )
        names = [m["name"] for m in mock_sync.call_args.kwargs["models"]]
        assert names == ["llama-3.1-8b", "qwen2.5-vl"]


class TestLocalFetchSSRFGuard:
    """Private targets are blocked only when MULTI_TENANT is on (decided 2026-10-30)."""

    @pytest.mark.parametrize(
        "endpoint,request_factory",
        [
            (
                "get_lm_studio_available_models",
                lambda base: LMStudioModelsRequest(api_base=base),
            ),
            (
                "get_openai_compatible_available_models",
                lambda base: OpenAICompatibleModelsRequest(api_base=base),
            ),
            (
                "get_ollama_available_models",
                lambda base: OllamaModelsRequest(api_base=base),
            ),
        ],
    )
    def test_private_ip_blocked_in_multi_tenant(
        self, endpoint: str, request_factory: object
    ) -> None:
        from fastapi import HTTPException

        import om.server.manage.llm.api as api

        with (
            patch.object(api, "MULTI_TENANT", True),
            patch("om.server.manage.llm.api.httpx.get") as mock_get,
        ):
            with pytest.raises(HTTPException) as exc:
                getattr(api, endpoint)(
                    request_factory("http://10.0.0.5:8000"),  # type: ignore[operator]
                    MagicMock(),
                    MagicMock(),
                )
            mock_get.assert_not_called()
        assert exc.value.status_code == 400
        assert "not allowed" in exc.value.detail

    def test_private_ip_allowed_single_tenant(self) -> None:
        import om.server.manage.llm.api as api
        from om.server.manage.llm.models import OpenAICompatibleModelsRequest

        with (
            patch.object(api, "MULTI_TENANT", False),
            patch("om.server.manage.llm.api.httpx.get") as mock_get,
        ):
            mock_get.return_value = _json_response(_OPENAI_COMPATIBLE_PAYLOAD)
            results = api.get_openai_compatible_available_models(
                OpenAICompatibleModelsRequest(api_base="http://10.0.0.5:8000"),
                MagicMock(),
                MagicMock(),
            )
        assert results

    def test_public_ip_allowed_in_multi_tenant(self) -> None:
        import om.server.manage.llm.api as api
        from om.server.manage.llm.models import OpenAICompatibleModelsRequest

        with (
            patch.object(api, "MULTI_TENANT", True),
            patch("om.server.manage.llm.api.httpx.get") as mock_get,
        ):
            mock_get.return_value = _json_response(_OPENAI_COMPATIBLE_PAYLOAD)
            results = api.get_openai_compatible_available_models(
                OpenAICompatibleModelsRequest(api_base="http://8.8.8.8:8000"),
                MagicMock(),
                MagicMock(),
            )
        assert results
