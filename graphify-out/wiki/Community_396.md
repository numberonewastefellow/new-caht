# Community 396

> 38 nodes · cohesion 0.08

## Key Concepts

- **apply_monkey_patches()** (10 connections) — `backend/om/llm/litellm_singleton/monkey_patches.py`
- **monkey_patches.py** (9 connections) — `backend/om/llm/litellm_singleton/monkey_patches.py`
- **config.py** (7 connections) — `backend/om/llm/litellm_singleton/config.py`
- **initialize_litellm()** (7 connections) — `backend/om/llm/litellm_singleton/config.py`
- **_create_iterator()** (7 connections) — `backend/tests/unit/om/llm/test_litellm_monkey_patches.py`
- **test_litellm_monkey_patches.py** (6 connections) — `backend/tests/unit/om/llm/test_litellm_monkey_patches.py`
- **_build_chunk()** (6 connections) — `backend/tests/unit/om/llm/test_litellm_monkey_patches.py`
- **__init__.py** (5 connections) — `backend/om/llm/litellm_singleton/__init__.py`
- **load_model_metadata_enrichments()** (4 connections) — `backend/om/llm/litellm_singleton/config.py`
- **_patch_azure_responses_should_fake_stream()** (3 connections) — `backend/om/llm/litellm_singleton/monkey_patches.py`
- **_patch_logging_assembled_streaming_response()** (3 connections) — `backend/om/llm/litellm_singleton/monkey_patches.py`
- **_patch_ollama_chunk_parser()** (3 connections) — `backend/om/llm/litellm_singleton/monkey_patches.py`
- **_patch_openai_responses_parallel_tool_calls()** (3 connections) — `backend/om/llm/litellm_singleton/monkey_patches.py`
- **_patch_openai_responses_transform_response()** (3 connections) — `backend/om/llm/litellm_singleton/monkey_patches.py`
- **_patch_responses_api_usage_format()** (3 connections) — `backend/om/llm/litellm_singleton/monkey_patches.py`
- **load_enrichments()** (3 connections) — `backend/tests/unit/om/llm/conftest.py`
- **test_ollama_chunk_parser_handles_think_tag_after_native_thinking()** (3 connections) — `backend/tests/unit/om/llm/test_litellm_monkey_patches.py`
- **test_ollama_chunk_parser_keeps_tagged_thinking_until_close_tag()** (3 connections) — `backend/tests/unit/om/llm/test_litellm_monkey_patches.py`
- **test_ollama_chunk_parser_preserves_content_when_thinking_and_content_coexist()** (3 connections) — `backend/tests/unit/om/llm/test_litellm_monkey_patches.py`
- **test_ollama_chunk_parser_transitions_from_native_thinking_to_content()** (3 connections) — `backend/tests/unit/om/llm/test_litellm_monkey_patches.py`
- **configure_litellm_settings()** (2 connections) — `backend/om/llm/litellm_singleton/config.py`
- **register_ollama_models()** (2 connections) — `backend/om/llm/litellm_singleton/config.py`
- **conftest.py** (2 connections) — `backend/tests/unit/om/llm/conftest.py`
- **Any** (1 connections) — `backend/tests/unit/om/llm/test_litellm_monkey_patches.py`
- **Load model metadata enrichments from JSON file and merge into litellm.model_cost** (1 connections) — `backend/om/llm/litellm_singleton/config.py`
- *... and 13 more nodes in this community*

## Relationships

- [[Agent Chat Packets & Citations]] (2 shared connections)
- [[Community 106]] (1 shared connections)

## Source Files

- `backend/om/llm/litellm_singleton/__init__.py`
- `backend/om/llm/litellm_singleton/config.py`
- `backend/om/llm/litellm_singleton/monkey_patches.py`
- `backend/tests/unit/om/llm/conftest.py`
- `backend/tests/unit/om/llm/test_litellm_monkey_patches.py`

## Audit Trail

- EXTRACTED: 109 (95%)
- INFERRED: 6 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*