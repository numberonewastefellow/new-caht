# Community 536

> 28 nodes · cohesion 0.10

## Key Concepts

- **PgRedisKVStore** (11 connections) — `backend/om/key_value_store/store.py`
- **CacheManager** (8 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **cache_manager.py** (6 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **._build_cache_key()** (6 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **.store()** (5 connections) — `backend/om/key_value_store/store.py`
- **.retrieve_cache_metadata()** (5 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **.store_cache_metadata()** (5 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **generate_cache_key_hash()** (5 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **CacheMetadata** (3 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **.delete()** (3 connections) — `backend/om/key_value_store/store.py`
- **.load()** (3 connections) — `backend/om/key_value_store/store.py`
- **.delete_cache_metadata()** (3 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **.__init__()** (3 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **_make_json_serializable()** (3 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **JSON_ro** (2 connections) — `backend/om/key_value_store/store.py`
- **LanguageModelInput** (2 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **store.py** (2 connections) — `backend/om/key_value_store/store.py`
- **PgRedisKVStore** (2 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **KeyValueStore** (1 connections)
- **Cache manager for storing and retrieving prompt cache metadata.** (1 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **Retrieve cache metadata.          Args:             provider: LLM provider name** (1 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **Delete cache metadata.          Args:             provider: LLM provider name** (1 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **Recursively convert objects to JSON-serializable types.      Handles Pydantic mo** (1 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **Generate a deterministic cache key hash from cacheable prefix.      Args:** (1 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- **Manages storage and retrieval of prompt cache metadata.** (1 connections) — `backend/om/llm/prompt_cache/cache_manager.py`
- *... and 3 more nodes in this community*

## Relationships

- [[Backend Agent/API Test Fixtures]] (3 shared connections)
- [[Community 106]] (2 shared connections)
- [[Community 161]] (2 shared connections)
- [[Community 303]] (1 shared connections)
- [[Community 69]] (1 shared connections)
- [[User Roles & Agent Config]] (1 shared connections)
- [[Community 661]] (1 shared connections)

## Source Files

- `backend/om/key_value_store/store.py`
- `backend/om/llm/prompt_cache/cache_manager.py`

## Audit Trail

- EXTRACTED: 73 (84%)
- INFERRED: 14 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*