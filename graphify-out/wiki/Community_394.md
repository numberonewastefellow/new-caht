# Community 394

> 38 nodes · cohesion 0.12

## Key Concepts

- **hierarchy.py** (19 connections) — `backend/om/db/hierarchy.py`
- **Session** (16 connections) — `backend/om/db/hierarchy.py`
- **upsert_hierarchy_nodes_batch()** (14 connections) — `backend/om/db/hierarchy.py`
- **DocumentSource** (12 connections) — `backend/om/db/hierarchy.py`
- **upsert_hierarchy_node()** (12 connections) — `backend/om/db/hierarchy.py`
- **HierarchyNode** (10 connections) — `backend/om/db/hierarchy.py`
- **get_hierarchy_node_by_raw_id()** (10 connections) — `backend/om/db/hierarchy.py`
- **get_all_hierarchy_nodes_for_source()** (8 connections) — `backend/om/db/hierarchy.py`
- **get_source_hierarchy_node()** (8 connections) — `backend/om/db/hierarchy.py`
- **get_root_hierarchy_nodes_for_source()** (7 connections) — `backend/om/db/hierarchy.py`
- **resolve_parent_hierarchy_node_id()** (7 connections) — `backend/om/db/hierarchy.py`
- **upsert_parents()** (7 connections) — `backend/om/db/hierarchy.py`
- **ensure_source_node_exists()** (6 connections) — `backend/om/db/hierarchy.py`
- **update_hierarchy_node_permissions()** (6 connections) — `backend/om/db/hierarchy.py`
- **_flush_or_commit()** (5 connections) — `backend/om/db/hierarchy.py`
- **get_hierarchy_node_children()** (5 connections) — `backend/om/db/hierarchy.py`
- **link_hierarchy_nodes_to_documents()** (5 connections) — `backend/om/db/hierarchy.py`
- **PydanticHierarchyNode** (4 connections) — `backend/om/db/hierarchy.py`
- **_extract_node_permissions()** (4 connections) — `backend/om/db/hierarchy.py`
- **get_hierarchy_node_by_id()** (4 connections) — `backend/om/db/hierarchy.py`
- **get_document_parent_hierarchy_node_ids()** (3 connections) — `backend/om/db/hierarchy.py`
- **Persistence helpers for :class:`HierarchyNode` rows.  A hierarchy node capture** (1 connections) — `backend/om/db/hierarchy.py`
- **Return the SOURCE root for ``source``, creating it on first use.      The SOUR** (1 connections) — `backend/om/db/hierarchy.py`
- **Map a source-level parent identifier onto a database ``parent_id``.      A con** (1 connections) — `backend/om/db/hierarchy.py`
- **Compute the ``(is_public, external_user_emails, external_team_ids)`` triple** (1 connections) — `backend/om/db/hierarchy.py`
- *... and 13 more nodes in this community*

## Relationships

- [[Community 360]] (8 shared connections)
- [[Community 684]] (5 shared connections)
- [[Community 351]] (1 shared connections)
- [[Community 102]] (1 shared connections)
- [[Community 59]] (1 shared connections)
- [[Community 144]] (1 shared connections)

## Source Files

- `backend/om/db/hierarchy.py`

## Audit Trail

- EXTRACTED: 177 (94%)
- INFERRED: 12 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*