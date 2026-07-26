# Community 725

> 20 nodes · cohesion 0.15

## Key Concepts

- **TracerProvider** (33 connections) — `phoenix/packages/phoenix-otel/src/phoenix/otel/otel.py`
- **TestTracerProvider** (14 connections) — `phoenix/packages/phoenix-otel/tests/test_otel.py`
- **TestTracedEvaluator** (7 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/test_evaluators.py`
- **.test_async_trace_id_in_score_metadata_with_tracing_enabled()** (6 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/test_evaluators.py`
- **.test_trace_id_in_score_metadata_with_tracing_enabled()** (6 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/test_evaluators.py`
- **.__init__()** (5 connections) — `phoenix/src/phoenix/tracers.py`
- **.test_trace_id_not_present_without_tracing()** (4 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/test_evaluators.py`
- **.__init__()** (4 connections) — `backend/om/tracing/phoenix_tracing_processor.py`
- **.test_tracer_provider_verbose()** (3 connections) — `phoenix/packages/phoenix-otel/tests/test_otel.py`
- **.test_tracer_provider_with_grpc_endpoint()** (3 connections) — `phoenix/packages/phoenix-otel/tests/test_otel.py`
- **.test_tracer_provider_with_http_endpoint()** (3 connections) — `phoenix/packages/phoenix-otel/tests/test_otel.py`
- **.test_add_span_processor_replaces_default()** (2 connections) — `phoenix/packages/phoenix-otel/tests/test_otel.py`
- **.test_add_span_processor_without_replace()** (2 connections) — `phoenix/packages/phoenix-otel/tests/test_otel.py`
- **.test_tracer_provider_creation()** (2 connections) — `phoenix/packages/phoenix-otel/tests/test_otel.py`
- **.test_tracer_provider_with_resource()** (2 connections) — `phoenix/packages/phoenix-otel/tests/test_otel.py`
- **Test evaluator tracing and trace_id injection.** (1 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/test_evaluators.py`
- **Test that trace_id is added to Score metadata when tracing is enabled.** (1 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/test_evaluators.py`
- **Test that evaluation works without trace_id when tracing is not configured.** (1 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/test_evaluators.py`
- **Test that trace_id is added to Score metadata in async evaluation.** (1 connections) — `phoenix/packages/phoenix-evals/tests/phoenix/evals/test_evaluators.py`
- **An extension of `opentelemetry.sdk.trace.TracerProvider` with Phoenix-aware defa** (1 connections) — `phoenix/packages/phoenix-otel/src/phoenix/otel/otel.py`

## Relationships

- [[Community 497]] (16 shared connections)
- [[Community 316]] (7 shared connections)
- [[Community 554]] (4 shared connections)
- [[Phoenix Playground LLM Clients]] (4 shared connections)
- [[Community 545]] (4 shared connections)
- [[Community 225]] (2 shared connections)
- [[Phoenix LDAP Auth Tests]] (2 shared connections)
- [[Phoenix GraphQL Schema]] (2 shared connections)
- [[Community 1305]] (1 shared connections)
- [[Community 86]] (1 shared connections)

## Source Files

- `backend/om/tracing/phoenix_tracing_processor.py`
- `phoenix/packages/phoenix-evals/tests/phoenix/evals/test_evaluators.py`
- `phoenix/packages/phoenix-otel/src/phoenix/otel/otel.py`
- `phoenix/packages/phoenix-otel/tests/test_otel.py`
- `phoenix/src/phoenix/tracers.py`

## Audit Trail

- EXTRACTED: 50 (50%)
- INFERRED: 50 (50%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*