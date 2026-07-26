# Community 217

> 60 nodes · cohesion 0.06

## Key Concepts

- **get_acl_for_user()** (12 connections) — `backend/om/access/access.py`
- **_resolve_access_for_documents()** (11 connections) — `backend/om/access/access.py`
- **prefix_user_email()** (11 connections) — `backend/om/access/utils.py`
- **access.py** (10 connections) — `backend/om/access/access.py`
- **get_access_for_knowledge_files()** (10 connections) — `backend/om/access/access.py`
- **test_knowledge_file_access.py** (9 connections) — `backend/tests/unit/om/access/test_knowledge_file_access.py`
- **get_access_for_documents()** (8 connections) — `backend/om/access/access.py`
- **_FakeSession** (8 connections) — `backend/tests/unit/om/access/test_knowledge_file_access.py`
- **get_access_for_document()** (7 connections) — `backend/om/access/access.py`
- **_mit_access_for_documents()** (7 connections) — `backend/om/access/access.py`
- **test_read_side_get_acl_for_user_emits_team_prefixes()** (7 connections) — `backend/tests/unit/om/access/test_acl_parity.py`
- **_FakeQuery** (7 connections) — `backend/tests/unit/om/access/test_knowledge_file_access.py`
- **_kf()** (7 connections) — `backend/tests/unit/om/access/test_knowledge_file_access.py`
- **prefix_external_team()** (7 connections) — `backend/om/access/utils.py`
- **DocumentAccess** (7 connections) — `backend/om/access/access.py`
- **Session** (7 connections) — `backend/om/access/access.py`
- **test_acl_parity.py** (6 connections) — `backend/tests/unit/om/access/test_acl_parity.py`
- **test_visibility_intersection_owner_vs_other_user()** (6 connections) — `backend/tests/unit/om/access/test_knowledge_file_access.py`
- **prefix_team()** (6 connections) — `backend/om/access/utils.py`
- **_acl_for_user_without_teams()** (5 connections) — `backend/om/access/access.py`
- **get_null_document_access()** (5 connections) — `backend/om/access/access.py`
- **.to_acl()** (5 connections) — `backend/om/access/models.py`
- **test_allow_deny_matrix()** (5 connections) — `backend/tests/unit/om/access/test_acl_parity.py`
- **_visible()** (5 connections) — `backend/tests/unit/om/access/test_acl_parity.py`
- **test_mixed_batch_maps_each_file_independently()** (5 connections) — `backend/tests/unit/om/access/test_knowledge_file_access.py`
- *... and 35 more nodes in this community*

## Relationships

- [[Document Access & Indexing]] (6 shared connections)
- [[Community 83]] (4 shared connections)
- [[Community 362]] (4 shared connections)
- [[Community 69]] (2 shared connections)
- [[Community 601]] (2 shared connections)
- [[Community 210]] (2 shared connections)
- [[Community 61]] (1 shared connections)
- [[Community 85]] (1 shared connections)
- [[Document External Access]] (1 shared connections)
- [[Community 533]] (1 shared connections)
- [[Community 136]] (1 shared connections)

## Source Files

- `backend/om/access/access.py`
- `backend/om/access/models.py`
- `backend/om/access/utils.py`
- `backend/tests/unit/om/access/test_acl_parity.py`
- `backend/tests/unit/om/access/test_knowledge_file_access.py`

## Audit Trail

- EXTRACTED: 172 (72%)
- INFERRED: 67 (28%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*