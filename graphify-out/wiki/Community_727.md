# Community 727

> 20 nodes · cohesion 0.12

## Key Concepts

- **models.py** (8 connections) — `backend/om/search/expansion/models.py`
- **QueryExpansionResult** (6 connections) — `backend/om/search/expansion/models.py`
- **ExpandedQuery** (4 connections) — `backend/om/search/expansion/models.py`
- **ExpansionTrace** (4 connections) — `backend/om/search/expansion/models.py`
- **.retrieval_variants()** (4 connections) — `backend/om/search/expansion/models.py`
- **StrategyTrace** (4 connections) — `backend/om/search/expansion/models.py`
- **ExpansionStrategy** (3 connections) — `backend/om/search/expansion/models.py`
- **.add()** (3 connections) — `backend/om/search/expansion/models.py`
- **HistoryTurn** (3 connections) — `backend/om/search/expansion/models.py`
- **.effective_query()** (2 connections) — `backend/om/search/expansion/models.py`
- **.expansion_texts()** (2 connections) — `backend/om/search/expansion/models.py`
- **Domain models for LLM-backed query expansion.  Three complementary transforms** (1 connections) — `backend/om/search/expansion/models.py`
- **Ordered, de-duplicated expansion variants to run in addition to the         ori** (1 connections) — `backend/om/search/expansion/models.py`
- **One prior conversation turn used for history-aware expansion.** (1 connections) — `backend/om/search/expansion/models.py`
- **A single expanded/rephrased query variant to run against the index.** (1 connections) — `backend/om/search/expansion/models.py`
- **Per-strategy LLM tracing for explainability + cost accounting.** (1 connections) — `backend/om/search/expansion/models.py`
- **Aggregate trace across every expansion strategy that ran.** (1 connections) — `backend/om/search/expansion/models.py`
- **Outcome of expanding a single query.** (1 connections) — `backend/om/search/expansion/models.py`
- **Best single query for display / history: the standalone rephrase when         a** (1 connections) — `backend/om/search/expansion/models.py`
- **Flat list of the produced expansion strings (no original).** (1 connections) — `backend/om/search/expansion/models.py`

## Relationships

- [[Analytics & Usage Models (WS-H)]] (5 shared connections)
- [[Community 72]] (3 shared connections)

## Source Files

- `backend/om/search/expansion/models.py`

## Audit Trail

- EXTRACTED: 52 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*