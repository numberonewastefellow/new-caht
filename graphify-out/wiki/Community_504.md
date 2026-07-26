# Community 504

> 30 nodes · cohesion 0.10

## Key Concepts

- **llm_provider_options.py** (16 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **model_configurations_for_provider()** (9 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **_get_provider_to_models_map()** (6 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **get_recommendations()** (6 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **_build_recommendations()** (5 connections) — `backend/tests/unit/om/llm/test_llm_provider_options.py`
- **is_obsolete_model()** (5 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **MonkeyPatch** (4 connections) — `backend/tests/unit/om/llm/test_llm_provider_options.py`
- **test_model_configurations_non_vertex_preserve_provider_order()** (4 connections) — `backend/tests/unit/om/llm/test_llm_provider_options.py`
- **test_model_configurations_vertex_are_sorted_by_name()** (4 connections) — `backend/tests/unit/om/llm/test_llm_provider_options.py`
- **fetch_models_for_provider()** (4 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **get_anthropic_model_names()** (4 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **get_openai_model_names()** (4 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **get_vertexai_model_names()** (4 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **LLMRecommendations** (3 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **LLMRecommendations** (3 connections) — `backend/tests/unit/om/llm/test_llm_provider_options.py`
- **test_llm_provider_options.py** (3 connections) — `backend/tests/unit/om/llm/test_llm_provider_options.py`
- **fetch_default_model_for_provider()** (3 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **fetch_model_names_for_provider_as_set()** (3 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **fetch_visible_model_names_for_provider_as_set()** (3 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **ModelConfigurationView** (2 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **Get OpenAI model names dynamically from litellm.** (1 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **# TODO: remove these lists once we have a comprehensive model configuration page** (1 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **# NOTE: We are explicitly excluding all "timestamped" models** (1 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **Get Anthropic model names dynamically from litellm.** (1 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- **Get Vertex AI model names dynamically from litellm model_cost.** (1 connections) — `backend/om/llm/well_known_providers/llm_provider_options.py`
- *... and 5 more nodes in this community*

## Relationships

- [[Community 107]] (4 shared connections)
- [[Community 404]] (3 shared connections)
- [[Community 145]] (3 shared connections)
- [[Community 321]] (2 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 85]] (1 shared connections)
- [[Community 740]] (1 shared connections)
- [[Community 344]] (1 shared connections)
- [[Community 155]] (1 shared connections)

## Source Files

- `backend/om/llm/well_known_providers/llm_provider_options.py`
- `backend/tests/unit/om/llm/test_llm_provider_options.py`

## Audit Trail

- EXTRACTED: 89 (85%)
- INFERRED: 16 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*