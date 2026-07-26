# Community 661

> 22 nodes · cohesion 0.11

## Key Concepts

- **NoOpPromptCacheProvider** (15 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **process_with_prompt_cache()** (13 connections) — `backend/om/llm/prompt_cache/processor.py`
- **.prepare_messages_for_caching()** (5 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **processor.py** (4 connections) — `backend/om/llm/prompt_cache/processor.py`
- **CacheMetadata** (3 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **.extract_cache_metadata()** (3 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **CacheMetadata** (2 connections) — `backend/om/llm/prompt_cache/processor.py`
- **LanguageModelInput** (2 connections) — `backend/om/llm/prompt_cache/processor.py`
- **LLMConfig** (2 connections) — `backend/om/llm/prompt_cache/processor.py`
- **LanguageModelInput** (2 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **noop.py** (2 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **.get_cache_ttl_seconds()** (2 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **.supports_caching()** (2 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **Main processor for prompt caching.** (1 connections) — `backend/om/llm/prompt_cache/processor.py`
- **# TODO: test with a history containing images** (1 connections) — `backend/om/llm/prompt_cache/processor.py`
- **Process prompt with caching support.      This function takes a cacheable prefix** (1 connections) — `backend/om/llm/prompt_cache/processor.py`
- **No-op provider adapter for providers without caching support.** (1 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **No-op adapter for providers that don't support prompt caching.** (1 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **No-op providers don't support caching.** (1 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **Return messages unchanged (no caching support).          Args:             cache** (1 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **No cache metadata to extract.** (1 connections) — `backend/om/llm/prompt_cache/providers/noop.py`
- **Return default TTL (not used for no-op).** (1 connections) — `backend/om/llm/prompt_cache/providers/noop.py`

## Relationships

- [[Community 430]] (8 shared connections)
- [[Community 525]] (3 shared connections)
- [[Community 161]] (2 shared connections)
- [[Community 213]] (1 shared connections)
- [[Community 536]] (1 shared connections)
- [[Community 1128]] (1 shared connections)

## Source Files

- `backend/om/llm/prompt_cache/processor.py`
- `backend/om/llm/prompt_cache/providers/noop.py`

## Audit Trail

- EXTRACTED: 45 (68%)
- INFERRED: 21 (32%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*