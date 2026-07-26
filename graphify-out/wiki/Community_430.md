# Community 430

> 35 nodes · cohesion 0.08

## Key Concepts

- **PromptCacheProvider** (23 connections) — `backend/om/llm/prompt_cache/providers/base.py`
- **AnthropicPromptCacheProvider** (11 connections) — `backend/om/llm/prompt_cache/providers/anthropic.py`
- **OpenAIPromptCacheProvider** (11 connections) — `backend/om/llm/prompt_cache/providers/openai.py`
- **VertexAIPromptCacheProvider** (11 connections) — `backend/om/llm/prompt_cache/providers/vertex.py`
- **get_provider_adapter()** (9 connections) — `backend/om/llm/prompt_cache/providers/factory.py`
- **LLMConfig** (6 connections) — `backend/om/llm/prompt_cache/providers/factory.py`
- **PromptCacheProvider** (6 connections) — `backend/om/llm/prompt_cache/providers/factory.py`
- **PromptCacheProvider** (4 connections)
- **base.py** (3 connections) — `backend/om/llm/prompt_cache/providers/base.py`
- **.get_cache_ttl_seconds()** (2 connections) — `backend/om/llm/prompt_cache/providers/anthropic.py`
- **.supports_caching()** (2 connections) — `backend/om/llm/prompt_cache/providers/anthropic.py`
- **.get_cache_ttl_seconds()** (2 connections) — `backend/om/llm/prompt_cache/providers/base.py`
- **.supports_caching()** (2 connections) — `backend/om/llm/prompt_cache/providers/base.py`
- **factory.py** (2 connections) — `backend/om/llm/prompt_cache/providers/factory.py`
- **openai.py** (2 connections) — `backend/om/llm/prompt_cache/providers/openai.py`
- **.get_cache_ttl_seconds()** (2 connections) — `backend/om/llm/prompt_cache/providers/openai.py`
- **.supports_caching()** (2 connections) — `backend/om/llm/prompt_cache/providers/openai.py`
- **.get_cache_ttl_seconds()** (2 connections) — `backend/om/llm/prompt_cache/providers/vertex.py`
- **.supports_caching()** (2 connections) — `backend/om/llm/prompt_cache/providers/vertex.py`
- **Anthropic adapter for prompt caching (explicit caching with cache_control).** (1 connections) — `backend/om/llm/prompt_cache/providers/anthropic.py`
- **Anthropic supports explicit prompt caching.** (1 connections) — `backend/om/llm/prompt_cache/providers/anthropic.py`
- **Get cache TTL for Anthropic (5 minutes default).** (1 connections) — `backend/om/llm/prompt_cache/providers/anthropic.py`
- **Base interface for provider-specific prompt caching adapters.** (1 connections) — `backend/om/llm/prompt_cache/providers/base.py`
- **Abstract base class for provider-specific prompt caching logic.** (1 connections) — `backend/om/llm/prompt_cache/providers/base.py`
- **Whether this provider supports prompt caching.          Returns:             Tru** (1 connections) — `backend/om/llm/prompt_cache/providers/base.py`
- *... and 10 more nodes in this community*

## Relationships

- [[Community 661]] (8 shared connections)
- [[Community 1433]] (4 shared connections)
- [[Community 1436]] (4 shared connections)
- [[Community 1437]] (4 shared connections)
- [[Community 1434]] (2 shared connections)
- [[Agent Tracing Processor]] (2 shared connections)
- [[Community 1438]] (2 shared connections)
- [[Community 1435]] (2 shared connections)

## Source Files

- `backend/om/llm/prompt_cache/providers/anthropic.py`
- `backend/om/llm/prompt_cache/providers/base.py`
- `backend/om/llm/prompt_cache/providers/factory.py`
- `backend/om/llm/prompt_cache/providers/openai.py`
- `backend/om/llm/prompt_cache/providers/vertex.py`

## Audit Trail

- EXTRACTED: 77 (64%)
- INFERRED: 43 (36%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*