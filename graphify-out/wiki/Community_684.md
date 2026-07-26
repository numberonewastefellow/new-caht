# Community 684

> 21 nodes · cohesion 0.16

## Key Concepts

- **_get_accessible_hierarchy_nodes_for_source()** (11 connections) — `backend/om/db/hierarchy.py`
- **test_hierarchy_access_filter.py** (7 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **HierarchyNode** (6 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **Session** (5 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **seeded_nodes()** (5 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **test_combined_email_and_group()** (5 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **test_email_filter()** (5 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **test_group_overlap_filter()** (5 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **test_no_credentials_returns_only_public()** (5 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **_visibility_predicate()** (4 connections) — `backend/om/db/hierarchy.py`
- **_make_node()** (3 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **ColumnElement** (1 connections) — `backend/om/db/hierarchy.py`
- **Build the WHERE clause governing whether a caller may see a node.      A node** (1 connections) — `backend/om/db/hierarchy.py`
- **Query the nodes of ``source`` visible to the caller, ordered by name.      Kep** (1 connections) — `backend/om/db/hierarchy.py`
- **Return the nodes of ``source`` the caller is allowed to browse.      Visibilit** (1 connections) — `backend/om/db/hierarchy.py`
- **Tests for hierarchy node access filtering.  Validates that the overlap operato** (1 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **User email matching should return the email-permissioned node.** (1 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **With no email and no groups, only public nodes should be returned.** (1 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **Both email and group filters should apply together via OR.** (1 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **Seed hierarchy nodes with various permission configurations.** (1 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`
- **The overlap (&&) operator must work on the VARCHAR[] column.      This is the** (1 connections) — `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`

## Relationships

- [[Community 394]] (5 shared connections)

## Source Files

- `backend/om/db/hierarchy.py`
- `backend/tests/external_dependency_unit/hierarchy/test_hierarchy_access_filter.py`

## Audit Trail

- EXTRACTED: 63 (89%)
- INFERRED: 8 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*