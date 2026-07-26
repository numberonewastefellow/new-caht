# Community 404

> 37 nodes · cohesion 0.11

## Key Concepts

- **fetch_existing_llm_provider()** (23 connections) — `backend/om/db/llm.py`
- **LLMProviderRecommendation** (15 connections) — `backend/om/llm/well_known_providers/auto_update_models.py`
- **_cleanup_provider()** (11 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **.test_switching_default_between_auto_mode_providers()** (11 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **.test_sync_auto_mode_creates_flow_rows()** (10 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **.test_auto_mode_syncs_models_from_github_config()** (10 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **Session** (9 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **TestAutoModeSyncFeature** (9 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **.test_auto_mode_provider_not_in_config()** (9 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **.test_auto_mode_with_multiple_providers_in_config()** (9 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **test_llm_provider_auto_mode.py** (8 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **_create_mock_admin()** (8 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **.test_existing_provider_transition_to_auto_mode()** (8 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **_create_mock_llm_recommendations()** (7 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **LLMRecommendations** (6 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **TestAutoModeMissingFlows** (5 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **auto_update_models.py** (3 connections) — `backend/om/llm/well_known_providers/auto_update_models.py`
- **.normalize_default_model()** (3 connections) — `backend/om/llm/well_known_providers/auto_update_models.py`
- **provider_name()** (2 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **Any** (1 connections) — `backend/om/llm/well_known_providers/auto_update_models.py`
- **Tests for the LLM Provider Auto Mode feature.  This tests the automatic model sy** (1 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **# NOTE: We need to provide a default_model_name for the initial upsert,** (1 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **Test that auto mode only syncs models for the matching provider type,         ig** (1 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **Test that when an existing provider with visible models transitions to auto mode** (1 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- **Create a mock admin user for testing.** (1 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`
- *... and 12 more nodes in this community*

## Relationships

- [[Community 107]] (20 shared connections)
- [[Community 299]] (10 shared connections)
- [[Community 504]] (3 shared connections)
- [[Community 145]] (1 shared connections)
- [[Community 429]] (1 shared connections)
- [[Community 65]] (1 shared connections)
- [[Community 85]] (1 shared connections)
- [[Analytics & Usage Models (WS-H)]] (1 shared connections)

## Source Files

- `backend/om/db/llm.py`
- `backend/om/llm/well_known_providers/auto_update_models.py`
- `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py`

## Audit Trail

- EXTRACTED: 125 (68%)
- INFERRED: 59 (32%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*