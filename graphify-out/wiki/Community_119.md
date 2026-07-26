# Community 119

> 103 nodes · cohesion 0.03

## Key Concepts

- **SqlEngine** (129 connections) — `backend/om/db/engine/sql_engine.py`
- **background.py** (9 connections) — `backend/om/background/celery/apps/background.py`
- **docprocessing.py** (9 connections) — `backend/om/background/celery/apps/docprocessing.py`
- **user_file_processing.py** (9 connections) — `backend/om/background/celery/apps/user_file_processing.py`
- **Any** (9 connections) — `backend/om/background/celery/apps/background.py`
- **Any** (9 connections) — `backend/om/background/celery/apps/docprocessing.py`
- **Any** (9 connections) — `backend/om/background/celery/apps/user_file_processing.py`
- **docfetching.py** (8 connections) — `backend/om/background/celery/apps/docfetching.py`
- **heavy.py** (8 connections) — `backend/om/background/celery/apps/heavy.py`
- **light.py** (8 connections) — `backend/om/background/celery/apps/light.py`
- **Any** (8 connections) — `backend/om/background/celery/apps/docfetching.py`
- **Any** (8 connections) — `backend/om/background/celery/apps/heavy.py`
- **Any** (8 connections) — `backend/om/background/celery/apps/light.py`
- **conftest.py** (6 connections) — `backend/tests/external_dependency_unit/craft/conftest.py`
- **.init_engine()** (6 connections) — `backend/om/db/engine/sql_engine.py`
- **conftest.py** (6 connections) — `backend/tests/external_dependency_unit/conftest.py`
- **build_session()** (5 connections) — `backend/tests/external_dependency_unit/craft/conftest.py`
- **.init_readonly_engine()** (5 connections) — `backend/om/db/engine/sql_engine.py`
- **.scoped_engine()** (5 connections) — `backend/om/db/engine/sql_engine.py`
- **Session** (4 connections) — `backend/tests/external_dependency_unit/craft/conftest.py`
- **db_session()** (4 connections) — `backend/tests/external_dependency_unit/craft/conftest.py`
- **test_user()** (4 connections) — `backend/tests/external_dependency_unit/craft/conftest.py`
- **db_session()** (4 connections) — `backend/tests/external_dependency_unit/conftest.py`
- **on_task_postrun()** (3 connections) — `backend/om/background/celery/apps/background.py`
- **on_task_prerun()** (3 connections) — `backend/om/background/celery/apps/background.py`
- *... and 78 more nodes in this community*

## Relationships

- [[Community 73]] (21 shared connections)
- [[Agent Chat Packets & Citations]] (13 shared connections)
- [[Community 148]] (10 shared connections)
- [[Backend Agent/API Test Fixtures]] (7 shared connections)
- [[Community 82]] (7 shared connections)
- [[Community 99]] (6 shared connections)
- [[Community 349]] (6 shared connections)
- [[Community 235]] (6 shared connections)
- [[Community 70]] (5 shared connections)
- [[Community 127]] (4 shared connections)
- [[Chat Datetime & OAuth Tokens]] (3 shared connections)
- [[Community 59]] (3 shared connections)

## Source Files

- `backend/om/background/celery/apps/background.py`
- `backend/om/background/celery/apps/docfetching.py`
- `backend/om/background/celery/apps/docprocessing.py`
- `backend/om/background/celery/apps/heavy.py`
- `backend/om/background/celery/apps/light.py`
- `backend/om/background/celery/apps/user_file_processing.py`
- `backend/om/db/engine/sql_engine.py`
- `backend/tests/external_dependency_unit/conftest.py`
- `backend/tests/external_dependency_unit/craft/conftest.py`

## Audit Trail

- EXTRACTED: 307 (67%)
- INFERRED: 148 (33%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*