# Community 415

> 36 nodes · cohesion 0.20

## Key Concepts

- **QueryExpansionsPacket** (28 connections) — `backend/om/search/orchestration/packets.py`
- **SearchOrchestrator** (27 connections) — `backend/om/search/orchestration/orchestrator.py`
- **LLMSelectedDocsPacket** (27 connections) — `backend/om/search/orchestration/packets.py`
- **SearchDocsPacket** (27 connections) — `backend/om/search/orchestration/packets.py`
- **SearchErrorPacket** (27 connections) — `backend/om/search/orchestration/packets.py`
- **send_search_message()** (10 connections) — `backend/om/search/api/router.py`
- **Session** (10 connections) — `backend/om/search/api/router.py`
- **User** (10 connections) — `backend/om/search/api/router.py`
- **BaseFilters** (9 connections) — `backend/om/search/orchestration/orchestrator.py`
- **HistoryTurn** (9 connections) — `backend/om/search/orchestration/orchestrator.py`
- **User** (9 connections) — `backend/om/search/orchestration/orchestrator.py`
- **SearchStreamPacket** (9 connections) — `backend/om/search/orchestration/orchestrator.py`
- **router.py** (8 connections) — `backend/om/search/api/router.py`
- **SendSearchQueryRequest** (8 connections) — `backend/om/search/api/router.py`
- **write_expansion_settings()** (7 connections) — `backend/om/search/api/router.py`
- **ExpansionSettingsResponse** (7 connections) — `backend/om/search/api/router.py`
- **SearchFullResponse** (7 connections) — `backend/om/search/api/router.py`
- **SearchOrchestrator** (7 connections) — `backend/om/search/api/router.py`
- **_collect_full_response()** (6 connections) — `backend/om/search/api/router.py`
- **_effective_config()** (6 connections) — `backend/om/search/api/router.py`
- **SearchFlowConfig** (6 connections) — `backend/om/search/api/router.py`
- **StreamingResponse** (6 connections) — `backend/om/search/api/router.py`
- **ExpansionSettingsUpdateRequest** (6 connections) — `backend/om/search/api/router.py`
- **packets.py** (6 connections) — `backend/om/search/orchestration/packets.py`
- **SearchFlowClassificationRequest** (6 connections) — `backend/om/search/api/router.py`
- *... and 11 more nodes in this community*

## Relationships

- [[Community 716]] (36 shared connections)
- [[Community 658]] (10 shared connections)
- [[Community 1515]] (7 shared connections)
- [[Document Access & Indexing]] (5 shared connections)
- [[Community 642]] (5 shared connections)
- [[Analytics & Usage Models (WS-H)]] (4 shared connections)
- [[Community 715]] (2 shared connections)
- [[Community 1258]] (2 shared connections)
- [[Community 880]] (2 shared connections)

## Source Files

- `backend/om/search/api/router.py`
- `backend/om/search/orchestration/orchestrator.py`
- `backend/om/search/orchestration/packets.py`

## Audit Trail

- EXTRACTED: 103 (32%)
- INFERRED: 218 (68%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*