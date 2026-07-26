# Community 502

> 30 nodes · cohesion 0.08

## Key Concepts

- **DAL** (15 connections) — `backend/om/db/dal.py`
- **TestDALFromTenant** (8 connections) — `backend/tests/unit/om/db/test_dal.py`
- **TestDALSessionDelegation** (8 connections) — `backend/tests/unit/om/db/test_dal.py`
- **.from_tenant()** (3 connections) — `backend/om/db/dal.py`
- **.session()** (3 connections) — `backend/om/db/dal.py`
- **.test_commit_propagates_exception()** (3 connections) — `backend/tests/unit/om/db/test_dal.py`
- **Session** (2 connections) — `backend/om/db/dal.py`
- **dal.py** (2 connections) — `backend/om/db/dal.py`
- **.__init__()** (2 connections) — `backend/om/db/dal.py`
- **test_dal.py** (2 connections) — `backend/tests/unit/om/db/test_dal.py`
- **.test_subclass_from_tenant_returns_subclass_instance()** (2 connections) — `backend/tests/unit/om/db/test_dal.py`
- **.test_uncommitted_changes_not_auto_committed()** (2 connections) — `backend/tests/unit/om/db/test_dal.py`
- **.test_commit()** (2 connections) — `backend/tests/unit/om/db/test_dal.py`
- **.test_flush()** (2 connections) — `backend/tests/unit/om/db/test_dal.py`
- **.test_rollback()** (2 connections) — `backend/tests/unit/om/db/test_dal.py`
- **.test_session_property_exposes_underlying_session()** (2 connections) — `backend/tests/unit/om/db/test_dal.py`
- **.commit()** (1 connections) — `backend/om/db/dal.py`
- **.flush()** (1 connections) — `backend/om/db/dal.py`
- **.rollback()** (1 connections) — `backend/om/db/dal.py`
- **Base Data Access Layer (DAL) for database operations.  The DAL pattern groups** (1 connections) — `backend/om/db/dal.py`
- **Base Data Access Layer.      Holds a SQLAlchemy session and provides transacti** (1 connections) — `backend/om/db/dal.py`
- **Direct access to the underlying session for advanced use cases.** (1 connections) — `backend/om/db/dal.py`
- **Create a DAL with a self-managed session for the given tenant.          The se** (1 connections) — `backend/om/db/dal.py`
- **Verify that DAL methods delegate correctly to the underlying session.** (1 connections) — `backend/tests/unit/om/db/test_dal.py`
- **Exiting the context manager should NOT auto-commit.** (1 connections) — `backend/tests/unit/om/db/test_dal.py`
- *... and 5 more nodes in this community*

## Relationships

- [[Community 73]] (1 shared connections)
- [[Salesforce Connector]] (1 shared connections)

## Source Files

- `backend/om/db/dal.py`
- `backend/tests/unit/om/db/test_dal.py`

## Audit Trail

- EXTRACTED: 58 (78%)
- INFERRED: 16 (22%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*