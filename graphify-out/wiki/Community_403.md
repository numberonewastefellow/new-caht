# Community 403

> 37 nodes · cohesion 0.11

## Key Concepts

- **_create_test_connector_credential_pair()** (15 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **create_doc_permission_sync_attempt()** (14 connections) — `backend/om/db/permission_sync_attempt.py`
- **mark_doc_permission_sync_attempt_in_progress()** (11 connections) — `backend/om/db/permission_sync_attempt.py`
- **Session** (10 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **TestDocPermissionSyncAttempt** (10 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **.test_status_enum_methods()** (9 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **get_doc_permission_sync_attempt()** (8 connections) — `backend/om/db/permission_sync_attempt.py`
- **DocPermissionSyncAttempt** (7 connections) — `backend/om/db/permission_sync_attempt.py`
- **.test_complete_doc_permission_sync_attempt_can_be_called_multiple_times()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **.test_complete_doc_permission_sync_attempt_success()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **.test_complete_doc_permission_sync_attempt_with_errors()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **.test_mark_doc_permission_sync_attempt_failed()** (7 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **get_recent_doc_permission_sync_attempts_for_cc_pair()** (6 connections) — `backend/om/db/permission_sync_attempt.py`
- **.test_create_doc_permission_sync_attempt()** (6 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **.test_get_doc_permission_sync_attempt()** (6 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **.test_get_recent_doc_permission_sync_attempts_for_cc_pair()** (6 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **.test_mark_doc_permission_sync_attempt_in_progress()** (6 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **get_latest_doc_permission_sync_attempt_for_cc_pair()** (5 connections) — `backend/om/db/permission_sync_attempt.py`
- **test_doc_permission_sync_attempt.py** (3 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **ConnectorCredentialPair** (1 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **DocumentSource** (1 connections) — `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`
- **Get recent doc permission sync attempts for a cc pair, most recent first.** (1 connections) — `backend/om/db/permission_sync_attempt.py`
- **Mark a doc permission sync attempt as IN_PROGRESS.     Locks the row during upda** (1 connections) — `backend/om/db/permission_sync_attempt.py`
- **Create a new doc permission sync attempt.      Args:         connector_credentia** (1 connections) — `backend/om/db/permission_sync_attempt.py`
- **Get a doc permission sync attempt by ID.      Args:         db_session: The data** (1 connections) — `backend/om/db/permission_sync_attempt.py`
- *... and 12 more nodes in this community*

## Relationships

- [[Community 218]] (17 shared connections)
- [[Community 199]] (2 shared connections)
- [[Community 161]] (2 shared connections)
- [[Community 70]] (1 shared connections)
- [[Salesforce Connector]] (1 shared connections)
- [[Chat Datetime & OAuth Tokens]] (1 shared connections)

## Source Files

- `backend/om/db/permission_sync_attempt.py`
- `backend/tests/external_dependency_unit/permission_sync/test_doc_permission_sync_attempt.py`

## Audit Trail

- EXTRACTED: 117 (70%)
- INFERRED: 51 (30%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*