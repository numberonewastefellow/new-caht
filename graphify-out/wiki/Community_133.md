# Community 133

> 95 nodes · cohesion 0.04

## Key Concepts

- **Choice** (52 connections) — `backend/om/llm/model_response.py`
- **OpenAIModel** (17 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/legacy/models/test_openai.py`
- **TestRecordLlmResponse** (16 connections) — `backend/tests/external_dependency_unit/tracing/test_llm_span_recording.py`
- **send_spans.py** (13 connections) — `phoenix/scripts/testing/send_spans.py`
- **generate_traces.py** (11 connections) — `phoenix/scripts/data/generate_traces.py`
- **ChatCompletionMessageToolCall** (10 connections) — `backend/om/llm/model_response.py`
- **test_openai.py** (10 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/legacy/models/test_openai.py`
- **TestParseOutput** (10 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/legacy/models/test_openai.py`
- **generate_spans_with_event_attributes.py** (7 connections) — `phoenix/scripts/generate_spans_with_event_attributes.py`
- **main()** (7 connections) — `phoenix/scripts/generate_spans_with_event_attributes.py`
- **_gen_attributes()** (6 connections) — `phoenix/scripts/data/generate_traces.py`
- **_gen_attributes()** (6 connections) — `phoenix/scripts/testing/send_spans.py`
- **.model()** (5 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/legacy/models/test_openai.py`
- **AttributeValue** (5 connections) — `phoenix/scripts/data/generate_traces.py`
- **AttributeValue** (5 connections) — `phoenix/scripts/testing/send_spans.py`
- **create_llm_span_with_events()** (5 connections) — `phoenix/scripts/generate_spans_with_event_attributes.py`
- **.test_records_all_fields_together()** (5 connections) — `backend/tests/external_dependency_unit/tracing/test_llm_span_recording.py`
- **.test_records_tool_calls_from_response()** (5 connections) — `backend/tests/external_dependency_unit/tracing/test_llm_span_recording.py`
- **_gen_llm()** (4 connections) — `phoenix/scripts/data/generate_traces.py`
- **_gen_messages()** (4 connections) — `phoenix/scripts/data/generate_traces.py`
- **_gen_spans()** (4 connections) — `phoenix/scripts/data/generate_traces.py`
- **_get_tracers()** (4 connections) — `phoenix/scripts/data/generate_traces.py`
- **test_selfhosted()** (4 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/legacy/models/test_openai.py`
- **.test_parse_output_chat_completion_with_empty_tool_arguments()** (4 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/legacy/models/test_openai.py`
- **.test_parse_output_chat_completion_with_multiple_tool_calls()** (4 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/legacy/models/test_openai.py`
- *... and 70 more nodes in this community*

## Relationships

- [[Phoenix Annotation Tests]] (14 shared connections)
- [[Community 65]] (11 shared connections)
- [[Community 220]] (7 shared connections)
- [[Community 102]] (3 shared connections)
- [[Community 106]] (2 shared connections)
- [[Community 497]] (2 shared connections)
- [[Analytics & Usage Models (WS-H)]] (2 shared connections)
- [[Community 75]] (2 shared connections)
- [[Community 688]] (2 shared connections)
- [[Phoenix Playground LLM Clients]] (1 shared connections)
- [[Community 90]] (1 shared connections)
- [[Community 560]] (1 shared connections)

## Source Files

- `backend/om/llm/model_response.py`
- `backend/tests/external_dependency_unit/tracing/test_llm_span_recording.py`
- `phoenix/packages/phoenix-evals/tests/phoenix/evals/legacy/models/test_openai.py`
- `phoenix/scripts/data/generate_traces.py`
- `phoenix/scripts/generate_spans_with_event_attributes.py`
- `phoenix/scripts/test_axis_label_clipping.py`
- `phoenix/scripts/testing/send_spans.py`

## Audit Trail

- EXTRACTED: 276 (73%)
- INFERRED: 102 (27%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*