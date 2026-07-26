# Community 632

> 24 nodes · cohesion 0.22

## Key Concepts

- **TestTracer** (20 connections) — `phoenix/tests/unit/test_tracers.py`
- **DbSessionFactory** (17 connections) — `phoenix/tests/unit/test_tracers.py`
- **Tracer** (15 connections) — `phoenix/tests/unit/test_tracers.py`
- **Project** (14 connections) — `phoenix/tests/unit/test_tracers.py`
- **GenerativeModel** (7 connections) — `phoenix/tests/unit/test_tracers.py`
- **GenerativeModelStore** (5 connections) — `phoenix/tests/unit/test_tracers.py`
- **SpanCostCalculator** (5 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_calculates_costs_for_llm_spans()** (5 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_skips_costs_for_non_llm_spans()** (5 connections) — `phoenix/tests/unit/test_tracers.py`
- **.generative_model_store()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.span_cost_calculator()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_correctly_computes_cumulative_counts()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_does_not_clear_buffer()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_handles_llm_spans_without_token_counts()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_handles_missing_pricing_model()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_handles_multiple_traces()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_persists_events_and_exceptions()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_persists_nested_spans()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_save_db_traces_populates_llm_token_count_fields()** (4 connections) — `phoenix/tests/unit/test_tracers.py`
- **.gpt_4o_mini_generative_model()** (3 connections) — `phoenix/tests/unit/test_tracers.py`
- **.project()** (3 connections) — `phoenix/tests/unit/test_tracers.py`
- **.tracer()** (3 connections) — `phoenix/tests/unit/test_tracers.py`
- **test_tracers.py** (2 connections) — `phoenix/tests/unit/test_tracers.py`
- **.test_clear_removes_captured_spans()** (2 connections) — `phoenix/tests/unit/test_tracers.py`

## Relationships

- [[Community 66]] (14 shared connections)
- [[Phoenix GraphQL Schema]] (8 shared connections)

## Source Files

- `phoenix/tests/unit/test_tracers.py`

## Audit Trail

- EXTRACTED: 125 (86%)
- INFERRED: 21 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*