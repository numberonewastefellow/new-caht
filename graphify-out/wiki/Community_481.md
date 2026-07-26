# Community 481

> 31 nodes · cohesion 0.10

## Key Concepts

- **admin_search()** (9 connections) — `backend/om/search/admin/service.py`
- **tag.py** (8 connections) — `backend/om/db/tag.py`
- **build_index_filters()** (8 connections) — `backend/om/search/filters.py`
- **Session** (7 connections) — `backend/om/db/tag.py`
- **upsert_document_tags()** (7 connections) — `backend/om/db/tag.py`
- **get_valid_tags()** (6 connections) — `backend/om/search/admin/service.py`
- **create_or_add_document_tag()** (6 connections) — `backend/om/db/tag.py`
- **create_or_add_document_tag_list()** (6 connections) — `backend/om/db/tag.py`
- **delete_orphan_tags__no_commit()** (5 connections) — `backend/om/db/tag.py`
- **find_tags()** (5 connections) — `backend/om/db/tag.py`
- **get_structured_tags_for_document()** (5 connections) — `backend/om/db/tag.py`
- **DocumentSource** (4 connections) — `backend/om/db/tag.py`
- **Tag** (4 connections) — `backend/om/db/tag.py`
- **check_tag_validity()** (4 connections) — `backend/om/db/tag.py`
- **service.py** (3 connections) — `backend/om/search/admin/service.py`
- **delete_document_tags_for_documents__no_commit()** (3 connections) — `backend/om/db/tag.py`
- **Session** (2 connections) — `backend/om/search/admin/service.py`
- **filters.py** (2 connections) — `backend/om/search/filters.py`
- **Admin/curator search + tag lookup (clean-room).  - ``admin_search`` runs a dir** (1 connections) — `backend/om/search/admin/service.py`
- **BaseFilters** (1 connections) — `backend/om/search/admin/service.py`
- **DocumentSource** (1 connections) — `backend/om/search/admin/service.py`
- **SearchDoc** (1 connections) — `backend/om/search/admin/service.py`
- **User** (1 connections) — `backend/om/search/admin/service.py`
- **BaseFilters** (1 connections) — `backend/om/search/filters.py`
- **IndexFilters** (1 connections) — `backend/om/search/filters.py`
- *... and 6 more nodes in this community*

## Relationships

- [[Community 85]] (3 shared connections)
- [[Community 880]] (2 shared connections)
- [[Community 120]] (2 shared connections)
- [[Community 83]] (1 shared connections)
- [[Community 59]] (1 shared connections)
- [[Backend Agent/API Test Fixtures]] (1 shared connections)
- [[Community 232]] (1 shared connections)
- [[Community 102]] (1 shared connections)
- [[Community 716]] (1 shared connections)

## Source Files

- `backend/om/db/tag.py`
- `backend/om/search/admin/service.py`
- `backend/om/search/filters.py`

## Audit Trail

- EXTRACTED: 90 (84%)
- INFERRED: 17 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*