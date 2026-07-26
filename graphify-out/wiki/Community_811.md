# Community 811

> 17 nodes · cohesion 0.12

## Key Concepts

- **reset_opensearch_kg_index()** (7 connections) — `backend/om/kg/resets/reset_opensearch.py`
- **reset_full_kg_index__commit()** (6 connections) — `backend/om/kg/resets/reset_index.py`
- **_reset_opensearch_for_doc()** (6 connections) — `backend/om/kg/resets/reset_opensearch.py`
- **reset_source_kg_index()** (6 connections) — `backend/om/kg/resets/reset_source.py`
- **extend_lock()** (5 connections) — `backend/om/kg/utils/lock_utils.py`
- **RedisLock** (2 connections) — `backend/om/kg/resets/reset_opensearch.py`
- **reset_opensearch.py** (2 connections) — `backend/om/kg/resets/reset_opensearch.py`
- **Session** (1 connections) — `backend/om/kg/resets/reset_index.py`
- **RedisLock** (1 connections) — `backend/om/kg/resets/reset_source.py`
- **RedisLock** (1 connections) — `backend/om/kg/utils/lock_utils.py`
- **reset_index.py** (1 connections) — `backend/om/kg/resets/reset_index.py`
- **Resets the knowledge graph index.** (1 connections) — `backend/om/kg/resets/reset_index.py`
- **Clears the KG fields (kg_entities, kg_relationships, kg_terms) for every     chu** (1 connections) — `backend/om/kg/resets/reset_opensearch.py`
- **Reset the kg info in OpenSearch for all documents of a given source name,     or** (1 connections) — `backend/om/kg/resets/reset_opensearch.py`
- **reset_source.py** (1 connections) — `backend/om/kg/resets/reset_source.py`
- **Resets the knowledge graph index and the document index for a source.** (1 connections) — `backend/om/kg/resets/reset_source.py`
- **lock_utils.py** (1 connections) — `backend/om/kg/utils/lock_utils.py`

## Relationships

- [[Backend Agent/API Test Fixtures]] (3 shared connections)
- [[Community 83]] (2 shared connections)
- [[Document Access & Indexing]] (1 shared connections)
- [[Community 266]] (1 shared connections)
- [[Community 148]] (1 shared connections)
- [[Community 330]] (1 shared connections)
- [[Community 178]] (1 shared connections)

## Source Files

- `backend/om/kg/resets/reset_index.py`
- `backend/om/kg/resets/reset_opensearch.py`
- `backend/om/kg/resets/reset_source.py`
- `backend/om/kg/utils/lock_utils.py`

## Audit Trail

- EXTRACTED: 28 (64%)
- INFERRED: 16 (36%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*