# Community 117

> 105 nodes · cohesion 0.05

## Key Concepts

- **insert_on_conflict()** (26 connections) — `phoenix/src/phoenix/db/insertion/helpers.py`
- **InsertEvaluationError** (24 connections) — `phoenix/src/phoenix/db/insertion/evaluation.py`
- **DocumentAnnotationQueueInserter** (23 connections) — `phoenix/src/phoenix/db/insertion/document_annotation.py`
- **SessionAnnotationQueueInserter** (23 connections) — `phoenix/src/phoenix/db/insertion/session_annotation.py`
- **SpanAnnotationQueueInserter** (23 connections) — `phoenix/src/phoenix/db/insertion/span_annotation.py`
- **TraceAnnotationQueueInserter** (23 connections) — `phoenix/src/phoenix/db/insertion/trace_annotation.py`
- **_QueueInserters** (21 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **SpanInsertionEvent** (21 connections) — `phoenix/src/phoenix/db/insertion/span.py`
- **ProjectSessionAnnotationDmlEvent** (18 connections) — `phoenix/src/phoenix/server/dml_event.py`
- **Any** (13 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **Evaluation** (12 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **Span** (12 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **.__init__()** (11 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **as_kv()** (11 connections) — `phoenix/src/phoenix/db/insertion/helpers.py`
- **DataManipulation** (11 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **DbSessionFactory** (11 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **DmlEvent** (11 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **TransactionResult** (10 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **evaluation.py** (10 connections) — `phoenix/src/phoenix/db/insertion/evaluation.py`
- **._partition()** (10 connections) — `phoenix/src/phoenix/db/insertion/session_annotation.py`
- **CanPutItem** (10 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **DataManipulationEvent** (10 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **DocumentAnnotation** (10 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **ProjectName** (10 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- **SessionAnnotation** (10 connections) — `phoenix/src/phoenix/db/bulk_inserter.py`
- *... and 80 more nodes in this community*

## Relationships

- [[Community 66]] (76 shared connections)
- [[Community 97]] (20 shared connections)
- [[Phoenix GraphQL Schema]] (19 shared connections)
- [[Phoenix Dataset Events]] (9 shared connections)
- [[Phoenix LDAP Auth Tests]] (6 shared connections)
- [[Phoenix Annotation Mutations]] (3 shared connections)
- [[Phoenix GraphQL DataLoaders]] (2 shared connections)
- [[Community 72]] (2 shared connections)
- [[Agent Tracing Processor]] (2 shared connections)
- [[Community 765]] (2 shared connections)
- [[Phoenix Annotation Config & Evaluators]] (2 shared connections)
- [[Community 146]] (1 shared connections)

## Source Files

- `phoenix/src/phoenix/db/bulk_inserter.py`
- `phoenix/src/phoenix/db/helpers.py`
- `phoenix/src/phoenix/db/insertion/document_annotation.py`
- `phoenix/src/phoenix/db/insertion/evaluation.py`
- `phoenix/src/phoenix/db/insertion/helpers.py`
- `phoenix/src/phoenix/db/insertion/session_annotation.py`
- `phoenix/src/phoenix/db/insertion/span.py`
- `phoenix/src/phoenix/db/insertion/span_annotation.py`
- `phoenix/src/phoenix/db/insertion/trace_annotation.py`
- `phoenix/src/phoenix/db/insertion/types.py`
- `phoenix/src/phoenix/server/api/input_types/ProjectSessionSort.py`
- `phoenix/src/phoenix/server/api/input_types/SpanSort.py`
- `phoenix/src/phoenix/server/dml_event.py`
- `phoenix/tests/unit/db/insertion/test_helpers.py`

## Audit Trail

- EXTRACTED: 319 (47%)
- INFERRED: 363 (53%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*