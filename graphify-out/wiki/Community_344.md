# Community 344

> 43 nodes · cohesion 0.12

## Key Concepts

- **test_multi_llm.py** (24 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **LitellmLLM** (23 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **get_max_input_tokens()** (21 connections) — `backend/om/llm/utils.py`
- **ModelResponse** (18 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **_create_delta()** (17 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_multithreaded_custom_config_isolation()** (7 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **MonkeyPatch** (6 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **ChatCompletionDeltaToolCall** (6 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_multiple_tool_calls()** (6 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_multiple_tool_calls_streaming()** (6 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_multithreaded_invoke_without_custom_config_skips_env_lock()** (6 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_temporary_env_cleanup()** (6 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **AssistantMessage** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **_accumulate_stream_to_assistant_message()** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **_model_response_to_assistant_message()** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_anthropic_model_passes_no_client()** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_azure_openai_model_uses_httphandler_client()** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_bedrock_model_passes_no_client()** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_existing_metadata_pass_through_when_identity_disabled()** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_openai_chat_omits_reasoning_params()** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_openai_model_invoke_uses_httphandler_client()** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_temporary_env_cleanup_on_exception()** (5 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **get_max_input_tokens_from_llm_provider()** (5 connections) — `backend/om/llm/utils.py`
- **test_user_identity_metadata_disabled_omits_identity()** (4 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- **test_user_identity_metadata_enabled()** (4 connections) — `backend/tests/unit/om/llm/test_multi_llm.py`
- *... and 18 more nodes in this community*

## Relationships

- [[Community 65]] (12 shared connections)
- [[Community 429]] (6 shared connections)
- [[Community 155]] (6 shared connections)
- [[Community 267]] (2 shared connections)
- [[Community 107]] (1 shared connections)
- [[Community 102]] (1 shared connections)
- [[Community 504]] (1 shared connections)
- [[Community 145]] (1 shared connections)

## Source Files

- `backend/om/llm/utils.py`
- `backend/tests/unit/om/llm/test_multi_llm.py`

## Audit Trail

- EXTRACTED: 197 (82%)
- INFERRED: 43 (18%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*