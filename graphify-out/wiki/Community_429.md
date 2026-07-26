# Community 429

> 35 nodes · cohesion 0.11

## Key Concepts

- **LitellmLLM** (28 connections) — `backend/om/llm/multi_llm.py`
- **get_llm_for_agent()** (17 connections) — `backend/om/llm/factory.py`
- **llm_from_provider()** (14 connections) — `backend/om/llm/factory.py`
- **factory.py** (12 connections) — `backend/om/llm/factory.py`
- **LLM** (11 connections) — `backend/om/llm/factory.py`
- **get_llm()** (10 connections) — `backend/om/llm/factory.py`
- **get_llm_token_counter()** (9 connections) — `backend/om/llm/factory.py`
- **test_factory.py** (9 connections) — `backend/tests/unit/om/llm/test_factory.py`
- **get_default_llm_with_vision()** (8 connections) — `backend/om/llm/factory.py`
- **get_llm_for_contextual_rag()** (6 connections) — `backend/om/llm/factory.py`
- **get_llm_tokenizer_encode_func()** (6 connections) — `backend/om/llm/factory.py`
- **Any** (5 connections) — `backend/om/llm/factory.py`
- **LLMProviderView** (5 connections) — `backend/om/llm/factory.py`
- **_build_provider_extra_headers()** (5 connections) — `backend/om/llm/factory.py`
- **_build_provider_view()** (5 connections) — `backend/tests/unit/om/llm/test_factory.py`
- **Agent** (4 connections) — `backend/om/llm/factory.py`
- **LLMOverride** (4 connections) — `backend/om/llm/factory.py`
- **User** (4 connections) — `backend/om/llm/factory.py`
- **_build_model_kwargs()** (3 connections) — `backend/om/llm/factory.py`
- **_get_model_configured_max_input_tokens()** (3 connections) — `backend/om/llm/factory.py`
- **test_llm_from_provider_never_sets_ollama_num_ctx_for_non_ollama_provider()** (3 connections) — `backend/tests/unit/om/llm/test_factory.py`
- **test_llm_from_provider_omits_ollama_num_ctx_when_model_context_unknown()** (3 connections) — `backend/tests/unit/om/llm/test_factory.py`
- **test_llm_from_provider_passes_configured_ollama_num_ctx()** (3 connections) — `backend/tests/unit/om/llm/test_factory.py`
- **.config()** (2 connections) — `backend/om/llm/multi_llm.py`
- **.__init__()** (2 connections) — `backend/om/llm/multi_llm.py`
- *... and 10 more nodes in this community*

## Relationships

- [[User Roles & Agent Config]] (12 shared connections)
- [[Chat Datetime & OAuth Tokens]] (8 shared connections)
- [[Community 344]] (6 shared connections)
- [[Community 65]] (6 shared connections)
- [[Community 107]] (5 shared connections)
- [[Agent Chat Packets & Citations]] (5 shared connections)
- [[Community 181]] (4 shared connections)
- [[Community 525]] (4 shared connections)
- [[Backend Agent/API Test Fixtures]] (3 shared connections)
- [[Community 62]] (3 shared connections)
- [[Community 102]] (2 shared connections)
- [[Community 145]] (2 shared connections)

## Source Files

- `backend/om/llm/factory.py`
- `backend/om/llm/multi_llm.py`
- `backend/tests/unit/om/llm/test_factory.py`

## Audit Trail

- EXTRACTED: 112 (57%)
- INFERRED: 84 (43%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*