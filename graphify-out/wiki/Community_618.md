# Community 618

> 24 nodes · cohesion 0.17

## Key Concepts

- **TeamRepository** (30 connections) — `backend/om/access/rbac/repository.py`
- **Session** (15 connections) — `backend/om/access/rbac/repository.py`
- **UUID** (7 connections) — `backend/om/access/rbac/repository.py`
- **Team** (5 connections) — `backend/om/access/rbac/repository.py`
- **.teams_for_user()** (5 connections) — `backend/om/access/rbac/repository.py`
- **.curated_team_ids()** (4 connections) — `backend/om/access/rbac/repository.py`
- **repository.py** (3 connections) — `backend/om/access/rbac/repository.py`
- **.get()** (3 connections) — `backend/om/access/rbac/repository.py`
- **.get_by_name()** (3 connections) — `backend/om/access/rbac/repository.py`
- **.is_curator()** (3 connections) — `backend/om/access/rbac/repository.py`
- **.is_member()** (3 connections) — `backend/om/access/rbac/repository.py`
- **.list_all()** (3 connections) — `backend/om/access/rbac/repository.py`
- **.list_by_ids()** (3 connections) — `backend/om/access/rbac/repository.py`
- **.member_ids()** (3 connections) — `backend/om/access/rbac/repository.py`
- **.member_team_ids()** (3 connections) — `backend/om/access/rbac/repository.py`
- **.teams_for_agent()** (2 connections) — `backend/om/access/rbac/repository.py`
- **.teams_for_cc_pair()** (2 connections) — `backend/om/access/rbac/repository.py`
- **.teams_for_credential()** (2 connections) — `backend/om/access/rbac/repository.py`
- **.teams_for_document_set()** (2 connections) — `backend/om/access/rbac/repository.py`
- **.teams_for_llm_provider()** (2 connections) — `backend/om/access/rbac/repository.py`
- **Data-access layer for teams and team-scoped grants.  Every method takes a call** (1 connections) — `backend/om/access/rbac/repository.py`
- **Read queries for teams, memberships, and resource -> team grant edges.** (1 connections) — `backend/om/access/rbac/repository.py`
- **All teams the user belongs to (member or curator).** (1 connections) — `backend/om/access/rbac/repository.py`
- **Teams for which the user has the team-scoped curator flag set.** (1 connections) — `backend/om/access/rbac/repository.py`

## Relationships

- [[Community 154]] (8 shared connections)
- [[Community 210]] (3 shared connections)
- [[Community 61]] (1 shared connections)
- [[Connector Indexing Types]] (1 shared connections)

## Source Files

- `backend/om/access/rbac/repository.py`

## Audit Trail

- EXTRACTED: 94 (88%)
- INFERRED: 13 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*