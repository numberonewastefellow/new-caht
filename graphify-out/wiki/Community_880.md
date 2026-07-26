# Community 880

> 15 nodes · cohesion 0.18

## Key Concepts

- **emit_search_event()** (12 connections) — `backend/om/search/log_events.py`
- **timed_search_event()** (7 connections) — `backend/om/search/log_events.py`
- **classify_search_flow()** (6 connections) — `backend/om/search/classification.py`
- **log_events.py** (6 connections) — `backend/om/search/log_events.py`
- **UUID** (3 connections) — `backend/om/search/log_events.py`
- **_safe_tenant_id()** (3 connections) — `backend/om/search/log_events.py`
- **Any** (2 connections) — `backend/om/search/log_events.py`
- **classification.py** (2 connections) — `backend/om/search/classification.py`
- **LLM** (1 connections) — `backend/om/search/classification.py`
- **Lightweight LLM classification: is a query a document-search or a chat turn.** (1 connections) — `backend/om/search/classification.py`
- **Return True if the query should go to the search flow.** (1 connections) — `backend/om/search/classification.py`
- **Structured, OpenSearch-friendly logging for the clean-room search stack.  Engi** (1 connections) — `backend/om/search/log_events.py`
- **Read the current tenant id without ever raising into the caller.** (1 connections) — `backend/om/search/log_events.py`
- **Emit one structured JSON log line. Never raises.** (1 connections) — `backend/om/search/log_events.py`
- **Time a block and emit a success/error structured event on exit.      Yields a** (1 connections) — `backend/om/search/log_events.py`

## Relationships

- [[Community 415]] (2 shared connections)
- [[Community 481]] (2 shared connections)
- [[Community 715]] (2 shared connections)
- [[Chat Datetime & OAuth Tokens]] (1 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 642]] (1 shared connections)
- [[Community 716]] (1 shared connections)

## Source Files

- `backend/om/search/classification.py`
- `backend/om/search/log_events.py`

## Audit Trail

- EXTRACTED: 37 (77%)
- INFERRED: 11 (23%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*