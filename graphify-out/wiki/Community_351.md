# Community 351

> 42 nodes · cohesion 0.11

## Key Concepts

- **redis_hierarchy.py** (20 connections) — `backend/om/redis/redis_hierarchy.py`
- **DocumentSource** (15 connections) — `backend/om/redis/redis_hierarchy.py`
- **Redis** (12 connections) — `backend/om/redis/redis_hierarchy.py`
- **cache_hierarchy_nodes_batch()** (12 connections) — `backend/om/redis/redis_hierarchy.py`
- **refresh_hierarchy_cache_from_db()** (12 connections) — `backend/om/redis/redis_hierarchy.py`
- **cache_hierarchy_node()** (10 connections) — `backend/om/redis/redis_hierarchy.py`
- **get_ancestors_from_raw_id()** (10 connections) — `backend/om/redis/redis_hierarchy.py`
- **get_source_node_id_from_cache()** (9 connections) — `backend/om/redis/redis_hierarchy.py`
- **_cache_key()** (8 connections) — `backend/om/redis/redis_hierarchy.py`
- **ensure_source_node_exists()** (8 connections) — `backend/om/redis/redis_hierarchy.py`
- **_source_node_key()** (8 connections) — `backend/om/redis/redis_hierarchy.py`
- **_walk_ancestor_chain()** (8 connections) — `backend/om/redis/redis_hierarchy.py`
- **clear_hierarchy_cache()** (7 connections) — `backend/om/redis/redis_hierarchy.py`
- **get_node_id_from_raw_id()** (7 connections) — `backend/om/redis/redis_hierarchy.py`
- **get_parent_id_from_cache()** (7 connections) — `backend/om/redis/redis_hierarchy.py`
- **_raw_id_cache_key()** (7 connections) — `backend/om/redis/redis_hierarchy.py`
- **Session** (5 connections) — `backend/om/redis/redis_hierarchy.py`
- **_construct_parent_value()** (5 connections) — `backend/om/redis/redis_hierarchy.py`
- **is_cache_populated()** (5 connections) — `backend/om/redis/redis_hierarchy.py`
- **.from_db_model()** (4 connections) — `backend/om/redis/redis_hierarchy.py`
- **_loading_lock_key()** (4 connections) — `backend/om/redis/redis_hierarchy.py`
- **_unpack_parent_value()** (4 connections) — `backend/om/redis/redis_hierarchy.py`
- **HierarchyNodeType** (2 connections) — `backend/om/redis/redis_hierarchy.py`
- **Redis cache operations for hierarchy node ancestor resolution.  This module prov** (1 connections) — `backend/om/redis/redis_hierarchy.py`
- **Unpack a cached value string back into (parent_id, node_type).      Returns None** (1 connections) — `backend/om/redis/redis_hierarchy.py`
- *... and 17 more nodes in this community*

## Relationships

- [[Community 144]] (7 shared connections)
- [[Community 59]] (1 shared connections)
- [[Community 69]] (1 shared connections)
- [[Community 394]] (1 shared connections)

## Source Files

- `backend/om/redis/redis_hierarchy.py`

## Audit Trail

- EXTRACTED: 202 (97%)
- INFERRED: 6 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*