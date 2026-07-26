# Community 218

> 60 nodes · cohesion 0.08

## Key Concepts

- **create_external_group_sync_attempt()** (18 connections) — `backend/om/db/permission_sync_attempt.py`
- **_create_test_connector_credential_pair()** (18 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **Session** (16 connections) — `backend/om/db/permission_sync_attempt.py`
- **permission_sync_attempt.py** (16 connections) — `backend/om/db/permission_sync_attempt.py`
- **Session** (15 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **TestExternalGroupPermissionSyncAttempt** (14 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **mark_external_group_sync_attempt_in_progress()** (11 connections) — `backend/om/db/permission_sync_attempt.py`
- **complete_doc_permission_sync_attempt()** (10 connections) — `backend/om/db/permission_sync_attempt.py`
- **complete_external_group_sync_attempt()** (10 connections) — `backend/om/db/permission_sync_attempt.py`
- **get_external_group_sync_attempt()** (10 connections) — `backend/om/db/permission_sync_attempt.py`
- **mark_external_group_sync_attempt_failed()** (9 connections) — `backend/om/db/permission_sync_attempt.py`
- **.test_status_enum_methods()** (9 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **mark_doc_permission_sync_attempt_failed()** (8 connections) — `backend/om/db/permission_sync_attempt.py`
- **get_recent_external_group_sync_attempts_for_cc_pair()** (7 connections) — `backend/om/db/permission_sync_attempt.py`
- **.test_complete_external_group_sync_attempt_can_be_called_multiple_times()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **.test_complete_external_group_sync_attempt_success()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **.test_complete_external_group_sync_attempt_with_errors()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **.test_external_group_sync_attempt_not_stuck_on_early_failure()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **.test_get_recent_global_external_group_sync_attempts()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **.test_global_vs_connector_specific_attempts()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **.test_mark_external_group_sync_attempt_failed()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **ExternalGroupPermissionSyncAttempt** (6 connections) — `backend/om/db/permission_sync_attempt.py`
- **.test_create_external_group_sync_attempt_with_cc_pair()** (6 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **.test_get_external_group_sync_attempt()** (6 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- **.test_get_recent_external_group_sync_attempts_for_cc_pair()** (6 connections) — `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`
- *... and 35 more nodes in this community*

## Relationships

- [[Community 403]] (17 shared connections)
- [[Community 601]] (5 shared connections)
- [[Community 99]] (4 shared connections)
- [[Community 120]] (4 shared connections)
- [[Community 199]] (3 shared connections)
- [[Community 70]] (2 shared connections)
- [[Salesforce Connector]] (1 shared connections)
- [[Chat Datetime & OAuth Tokens]] (1 shared connections)

## Source Files

- `backend/om/db/permission_sync_attempt.py`
- `backend/tests/external_dependency_unit/permission_sync/test_external_group_permission_sync_attempt.py`

## Audit Trail

- EXTRACTED: 209 (69%)
- INFERRED: 94 (31%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*