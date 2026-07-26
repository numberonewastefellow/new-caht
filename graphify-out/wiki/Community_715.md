# Community 715

> 20 nodes · cohesion 0.13

## Key Concepts

- **list_search_history()** (8 connections) — `backend/om/search/history/service.py`
- **SearchQueryRepository** (6 connections) — `backend/om/search/history/repository.py`
- **service.py** (4 connections) — `backend/om/search/history/service.py`
- **SearchHistoryService** (4 connections) — `backend/om/search/history/service.py`
- **.record()** (4 connections) — `backend/om/search/history/service.py`
- **UUID** (3 connections) — `backend/om/search/history/repository.py`
- **UUID** (3 connections) — `backend/om/search/history/service.py`
- **repository.py** (3 connections) — `backend/om/search/history/repository.py`
- **.create()** (3 connections) — `backend/om/search/history/repository.py`
- **.list_for_user()** (3 connections) — `backend/om/search/history/repository.py`
- **SearchQuery** (2 connections) — `backend/om/search/history/repository.py`
- **.__init__()** (2 connections) — `backend/om/search/history/repository.py`
- **.__init__()** (2 connections) — `backend/om/search/history/service.py`
- **Session** (1 connections) — `backend/om/search/history/repository.py`
- **SearchQuery** (1 connections) — `backend/om/search/history/service.py`
- **Session** (1 connections) — `backend/om/search/history/service.py`
- **Repository for per-user search history (the ``search_query`` table).  The sess** (1 connections) — `backend/om/search/history/repository.py`
- **Search-history service.  ``SearchHistoryService`` doubles as the orchestrator'** (1 connections) — `backend/om/search/history/service.py`
- **Persist one search. Opens its own tenant session; never raises.** (1 connections) — `backend/om/search/history/service.py`
- **Read a user's search history (tenant-scoped via the bound session).** (1 connections) — `backend/om/search/history/service.py`

## Relationships

- [[Community 415]] (2 shared connections)
- [[Community 880]] (2 shared connections)

## Source Files

- `backend/om/search/history/repository.py`
- `backend/om/search/history/service.py`

## Audit Trail

- EXTRACTED: 46 (85%)
- INFERRED: 8 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*