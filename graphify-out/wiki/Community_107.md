# Community 107

> 112 nodes · cohesion 0.04

## Key Concepts

- **llm.py** (39 connections) — `backend/om/db/llm.py`
- **Session** (36 connections) — `backend/om/db/llm.py`
- **LLMRecommendations** (33 connections) — `backend/om/llm/well_known_providers/auto_update_models.py`
- **upsert_llm_provider()** (26 connections) — `backend/om/db/llm.py`
- **update_default_provider()** (14 connections) — `backend/om/db/llm.py`
- **fetch_existing_llm_providers()** (13 connections) — `backend/om/db/llm.py`
- **sync_model_configurations()** (13 connections) — `backend/om/db/llm.py`
- **Session** (11 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider.py`
- **list_llm_providers_for_agent()** (11 connections) — `backend/om/server/manage/llm/api.py`
- **_create_mock_admin()** (11 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider.py`
- **remove_llm_provider()** (10 connections) — `backend/om/db/llm.py`
- **update_default_contextual_model()** (10 connections) — `backend/om/db/llm.py`
- **_cleanup_provider()** (10 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider.py`
- **test_answer_with_only_anthropic_provider()** (9 connections) — `backend/tests/external_dependency_unit/answer/test_answer_without_openai.py`
- **LLMModelFlowType** (9 connections) — `backend/om/db/llm.py`
- **can_user_access_llm_provider()** (9 connections) — `backend/om/db/llm.py`
- **fetch_team_ids()** (9 connections) — `backend/om/db/llm.py`
- **sync_auto_mode_models()** (9 connections) — `backend/om/db/llm.py`
- **get_valid_model_names_for_agent()** (9 connections) — `backend/om/server/manage/llm/api.py`
- **fetch_default_llm_model()** (8 connections) — `backend/om/db/llm.py`
- **fetch_default_model()** (8 connections) — `backend/om/db/llm.py`
- **TestLLMConfigurationEndpoint** (8 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider.py`
- **LLMProviderModel** (7 connections) — `backend/om/db/llm.py`
- **create_new_flow_mapping__no_commit()** (7 connections) — `backend/om/db/llm.py`
- **fetch_default_contextual_rag_model()** (7 connections) — `backend/om/db/llm.py`
- *... and 87 more nodes in this community*

## Relationships

- [[Community 404]] (20 shared connections)
- [[Community 145]] (20 shared connections)
- [[Community 85]] (8 shared connections)
- [[Community 429]] (5 shared connections)
- [[Community 740]] (5 shared connections)
- [[Community 102]] (5 shared connections)
- [[Community 299]] (5 shared connections)
- [[Community 931]] (5 shared connections)
- [[Community 504]] (4 shared connections)
- [[Chat Datetime & OAuth Tokens]] (3 shared connections)
- [[Community 662]] (3 shared connections)
- [[Community 65]] (3 shared connections)

## Source Files

- `backend/om/db/llm.py`
- `backend/om/llm/well_known_providers/auto_update_models.py`
- `backend/om/server/manage/llm/api.py`
- `backend/tests/external_dependency_unit/answer/test_answer_without_openai.py`
- `backend/tests/external_dependency_unit/llm/test_llm_provider.py`

## Audit Trail

- EXTRACTED: 434 (73%)
- INFERRED: 163 (27%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*