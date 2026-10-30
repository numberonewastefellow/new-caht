"""Shared helpers for self-hosted LLM servers (LM Studio, OpenAI-compatible).

Used by both the runtime (`om/llm/multi_llm.py`) and the admin model-fetch
endpoints (`om/server/manage/llm/api.py`) so the `/v1` URL handling and the
LiteLLM routing rules live in exactly one place.

Pure functions only: no DB, no network, no LiteLLM import.
"""

from om.llm.constants import LlmProviderNames

# Provider strings (as stored in `llm_provider.provider`) handled here.
LOCAL_PROVIDER_NAMES: frozenset[str] = frozenset(
    {
        LlmProviderNames.LM_STUDIO.value,
        LlmProviderNames.OPENAI_COMPATIBLE.value,
    }
)

# LiteLLM's OpenAI client requires *some* key; most self-hosted servers ignore it.
OPENAI_COMPATIBLE_PLACEHOLDER_API_KEY = "not-needed"

_OPENAI_V1_SUFFIX = "/v1"

# Name fragments of models that are not chat models (embeddings, rerankers,
# speech, image generation, moderation). Matched against the lowercased id.
_NON_CHAT_MODEL_ID_MARKERS: tuple[str, ...] = (
    "embed",
    "rerank",
    "whisper",
    "tts",
    "text-to-speech",
    "speech-to-text",
    "transcribe",
    "dall-e",
    "stable-diffusion",
    "sdxl",
    "flux",
    "moderation",
    "minilm",
    "colbert",
)

# Families matched only at the start of the id's last path segment, because
# the bare fragment can appear inside chat-model names.
_NON_CHAT_MODEL_ID_PREFIXES: tuple[str, ...] = ("bge-", "e5-", "gte-", "clip")


def is_local_provider(provider: str | None) -> bool:
    return bool(provider) and provider in LOCAL_PROVIDER_NAMES


def litellm_lookup_provider(provider: str) -> str:
    """Provider to use for LiteLLM model-map lookups (reasoning, vision, tokens).

    `openai_compatible` is not a LiteLLM provider; LiteLLM serves it through its
    OpenAI client, so look models up as `openai`. Every other provider
    (including `lm_studio`, which LiteLLM knows) is returned unchanged.
    """
    if provider == LlmProviderNames.OPENAI_COMPATIBLE:
        return LlmProviderNames.OPENAI.value
    return provider


def normalize_openai_v1_base(url: str | None) -> str:
    """Return the base URL trimmed, without a trailing slash, ending in `/v1`.

    A base that already ends in `/v1` is kept as-is (so a reverse-proxy path
    such as `http://h/proxy/v1` is not rewritten). Empty input returns "".
    """
    cleaned = (url or "").strip().rstrip("/")
    if not cleaned:
        return ""
    if cleaned.endswith(_OPENAI_V1_SUFFIX):
        return cleaned
    return f"{cleaned}{_OPENAI_V1_SUFFIX}"


def strip_openai_v1_suffix(url: str | None) -> str:
    """Inverse of `normalize_openai_v1_base`: trimmed, no trailing slash, no `/v1`.

    LM Studio's native metadata endpoint lives at `<root>/api/v1/models`, so a
    base copied from an OpenAI-compatible config (`.../v1`) must be stripped.
    """
    cleaned = (url or "").strip().rstrip("/")
    if cleaned.endswith(_OPENAI_V1_SUFFIX):
        cleaned = cleaned[: -len(_OPENAI_V1_SUFFIX)].rstrip("/")
    return cleaned


def resolve_local_provider_routing(
    provider: str,
    api_base: str | None,
    api_key: str | None,
) -> tuple[str, str | None, str | None, str]:
    """LiteLLM routing for a local provider.

    Returns `(model_prefix, custom_llm_provider, api_base, api_key)`:
    - `model_prefix` is what goes before `/<model>` in the LiteLLM model string.
    - `custom_llm_provider` is passed to `litellm.completion` (None = infer
      from the prefix).

    Rules:
    - `lm_studio`: LiteLLM's native `lm_studio/` prefix, base coerced to `/v1`,
      key passed explicitly ("" when unset).
    - `openai_compatible`: LiteLLM's plain OpenAI client
      (`openai/<model>`, `custom_llm_provider="openai"`), base coerced to
      `/v1`, placeholder key when unset. Never the Responses API.

    Raises ValueError for a provider that is not a local provider.
    """
    normalized_base = normalize_openai_v1_base(api_base) or None
    cleaned_key = (api_key or "").strip()

    if provider == LlmProviderNames.LM_STUDIO:
        return (LlmProviderNames.LM_STUDIO.value, None, normalized_base, cleaned_key)

    if provider == LlmProviderNames.OPENAI_COMPATIBLE:
        return (
            LlmProviderNames.OPENAI.value,
            LlmProviderNames.OPENAI.value,
            normalized_base,
            cleaned_key or OPENAI_COMPATIBLE_PLACEHOLDER_API_KEY,
        )

    raise ValueError(f"Not a local LLM provider: {provider!r}")


def is_non_chat_model_id(model_id: str) -> bool:
    """Name heuristic: should this model id stay out of chat-model listings?

    Used for servers whose `/v1/models` gives no model type (vLLM, llama.cpp,
    LocalAI...). It is a name check only, not a capability lookup.
    """
    lowered = (model_id or "").lower()
    if not lowered:
        return True
    # Match on the last path segment so "org/model" ids are handled too.
    leaf = lowered.rsplit("/", 1)[-1]
    if leaf.startswith(_NON_CHAT_MODEL_ID_PREFIXES):
        return True
    return any(marker in leaf for marker in _NON_CHAT_MODEL_ID_MARKERS)
