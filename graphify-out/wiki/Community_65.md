# Community 65

> 159 nodes · cohesion 0.03

## Key Concepts

- **ModelResponse** (65 connections) — `backend/om/llm/model_response.py`
- **Delta** (51 connections) — `backend/om/llm/model_response.py`
- **ModelResponseStream** (49 connections) — `backend/om/llm/model_response.py`
- **FunctionCall** (31 connections) — `backend/om/llm/model_response.py`
- **ChatCompletionDeltaToolCall** (29 connections) — `backend/om/llm/model_response.py`
- **LLMResponse** (23 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **MockLLM** (23 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **StreamingChoice** (23 connections) — `backend/om/llm/model_response.py`
- **LLMAnswerResponse** (20 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **MockLLMController** (20 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **LLMToolCallResponse** (19 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **model_response.py** (18 connections) — `backend/om/llm/model_response.py`
- **TestRecordLlmSpanOutput** (17 connections) — `backend/tests/external_dependency_unit/tracing/test_llm_span_recording.py`
- **test_model_response.py** (16 connections) — `backend/tests/unit/om/llm/test_model_response.py`
- **mock_llm.py** (15 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **test_user_sends_message_to_private_provider()** (15 connections) — `backend/tests/external_dependency_unit/llm/test_llm_provider_called.py`
- **SyncStreamController** (14 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **from_litellm_model_response_stream()** (13 connections) — `backend/om/llm/model_response.py`
- **LLMReasoningResponse** (12 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **StreamItem** (12 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **from_litellm_model_response()** (11 connections) — `backend/om/llm/model_response.py`
- **T** (10 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **LLMResponseType** (10 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **StreamTimeoutError** (10 connections) — `backend/tests/external_dependency_unit/mock_llm.py`
- **Usage** (9 connections) — `backend/om/llm/model_response.py`
- *... and 134 more nodes in this community*

## Relationships

- [[Agent Chat Packets & Citations]] (34 shared connections)
- [[Community 115]] (25 shared connections)
- [[Community 181]] (15 shared connections)
- [[Analytics & Usage Models (WS-H)]] (13 shared connections)
- [[Community 344]] (12 shared connections)
- [[Community 220]] (12 shared connections)
- [[Community 133]] (11 shared connections)
- [[Community 102]] (8 shared connections)
- [[Community 429]] (6 shared connections)
- [[Community 577]] (6 shared connections)
- [[User Roles & Agent Config]] (4 shared connections)
- [[Community 525]] (4 shared connections)

## Source Files

- `backend/om/deep_research/utils.py`
- `backend/om/llm/interfaces.py`
- `backend/om/llm/model_response.py`
- `backend/om/llm/multi_llm.py`
- `backend/tests/external_dependency_unit/llm/test_llm_provider_called.py`
- `backend/tests/external_dependency_unit/mock_llm.py`
- `backend/tests/external_dependency_unit/tracing/test_llm_span_recording.py`
- `backend/tests/unit/om/llm/test_model_response.py`
- `backend/tests/unit/om/llm/test_multi_llm.py`

## Audit Trail

- EXTRACTED: 493 (50%)
- INFERRED: 499 (50%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*