# Community 740

> 19 nodes · cohesion 0.13

## Key Concepts

- **sync_llm_models_from_github()** (9 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **auto_update_service.py** (7 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **fetch_llm_recommendations_from_github()** (7 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **check_for_auto_llm_updates()** (5 connections) — `backend/om/background/celery/tasks/llm_model_update/tasks.py`
- **_get_cached_last_updated_at()** (5 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **_set_cached_last_updated_at()** (5 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **datetime** (4 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **reset_cache()** (3 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **LLMRecommendations** (2 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **Session** (2 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **Task** (1 connections) — `backend/om/background/celery/tasks/llm_model_update/tasks.py`
- **tasks.py** (1 connections) — `backend/om/background/celery/tasks/llm_model_update/tasks.py`
- **Periodic task to fetch LLM model updates from GitHub     and sync them to provid** (1 connections) — `backend/om/background/celery/tasks/llm_model_update/tasks.py`
- **Service for fetching and syncing LLM model configurations from GitHub.  This ser** (1 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **Reset the cache timestamp in Redis. Useful for testing.** (1 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **Get the cached last_updated_at timestamp from Redis.** (1 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **Set the cached last_updated_at timestamp in Redis.** (1 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **Fetch LLM configuration from GitHub.      Returns:         GitHubLLMConfig if su** (1 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`
- **Sync models from GitHub config to database for all Auto mode providers.      In** (1 connections) — `backend/om/llm/well_known_providers/auto_update_service.py`

## Relationships

- [[Community 107]] (5 shared connections)
- [[Community 69]] (3 shared connections)
- [[Backend Agent/API Test Fixtures]] (1 shared connections)
- [[Community 145]] (1 shared connections)
- [[Community 299]] (1 shared connections)
- [[Community 504]] (1 shared connections)

## Source Files

- `backend/om/background/celery/tasks/llm_model_update/tasks.py`
- `backend/om/llm/well_known_providers/auto_update_service.py`

## Audit Trail

- EXTRACTED: 44 (76%)
- INFERRED: 14 (24%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*