# Community 155

> 82 nodes · cohesion 0.03

## Key Concepts

- **utils.py** (25 connections) — `backend/om/llm/utils.py`
- **get_bedrock_token_limit()** (21 connections) — `backend/om/llm/utils.py`
- **TestGetBedrockTokenLimit** (19 connections) — `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- **get_model_map()** (13 connections) — `backend/om/llm/utils.py`
- **find_model_obj()** (10 connections) — `backend/om/llm/utils.py`
- **.from_model()** (7 connections) — `backend/om/server/manage/llm/models.py`
- **litellm_exception_to_error_msg()** (7 connections) — `backend/om/llm/utils.py`
- **model_is_reasoning_model()** (7 connections) — `backend/om/llm/utils.py`
- **build_litellm_passthrough_kwargs()** (6 connections) — `backend/om/llm/utils.py`
- **litellm_thinks_model_supports_image_input()** (6 connections) — `backend/om/llm/utils.py`
- **model_supports_image_input()** (6 connections) — `backend/om/llm/utils.py`
- **test_no_overwrite_in_model_map()** (4 connections) — `backend/tests/unit/om/llm/test_model_map.py`
- **test_partial_match_in_model_map()** (4 connections) — `backend/tests/unit/om/llm/test_model_map.py`
- **llm_max_input_tokens()** (4 connections) — `backend/om/llm/utils.py`
- **_unwrap_nested_exception()** (4 connections) — `backend/om/llm/utils.py`
- **explicit_tool_calling_supported()** (4 connections) — `backend/om/tools/utils.py`
- **Exception** (3 connections) — `backend/om/llm/utils.py`
- **.test_case_insensitive_matching()** (3 connections) — `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- **.test_cross_region_model_id()** (3 connections) — `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- **.test_default_fallback_unknown_model()** (3 connections) — `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- **.test_hardcoded_mapping_claude_3_5()** (3 connections) — `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- **.test_hardcoded_mapping_llama3_3()** (3 connections) — `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- **.test_hardcoded_mapping_llama3_70b()** (3 connections) — `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- **.test_hardcoded_mapping_mistral_large()** (3 connections) — `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- **.test_hardcoded_mapping_nova_pro()** (3 connections) — `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- *... and 57 more nodes in this community*

## Relationships

- [[Community 181]] (7 shared connections)
- [[Community 344]] (6 shared connections)
- [[Community 145]] (4 shared connections)
- [[Community 65]] (3 shared connections)
- [[Community 194]] (2 shared connections)
- [[Community 232]] (1 shared connections)
- [[Community 1235]] (1 shared connections)
- [[Community 148]] (1 shared connections)
- [[Community 516]] (1 shared connections)
- [[Community 321]] (1 shared connections)
- [[Chat Datetime & OAuth Tokens]] (1 shared connections)
- [[Agent Chat Packets & Citations]] (1 shared connections)

## Source Files

- `backend/om/llm/utils.py`
- `backend/om/server/manage/llm/models.py`
- `backend/om/tools/utils.py`
- `backend/tests/unit/om/llm/test_bedrock_token_limit.py`
- `backend/tests/unit/om/llm/test_model_is_reasoning.py`
- `backend/tests/unit/om/llm/test_model_map.py`
- `backend/tests/unit/om/tools/test_tool_utils.py`

## Audit Trail

- EXTRACTED: 189 (71%)
- INFERRED: 77 (29%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*