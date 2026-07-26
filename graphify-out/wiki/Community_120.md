# Community 120

> 102 nodes · cohesion 0.04

## Key Concepts

- **RedisConnectorDelete** (33 connections) — `backend/om/redis/redis_connector_delete.py`
- **connector_credential_pair.py** (31 connections) — `backend/om/db/connector_credential_pair.py`
- **get_connector_credential_pair_from_id()** (26 connections) — `backend/om/db/connector_credential_pair.py`
- **Session** (25 connections) — `backend/om/db/connector_credential_pair.py`
- **check_for_indexing()** (23 connections) — `backend/om/background/celery/tasks/docprocessing/tasks.py`
- **monitor_connector_deletion_taskset()** (18 connections) — `backend/om/background/celery/tasks/connector_deletion/tasks.py`
- **ConnectorCredentialPair** (15 connections) — `backend/om/db/connector_credential_pair.py`
- **add_credential_to_connector()** (14 connections) — `backend/om/db/connector_credential_pair.py`
- **try_generate_document_cc_pair_cleanup_tasks()** (13 connections) — `backend/om/background/celery/tasks/connector_deletion/tasks.py`
- **get_connector_credential_pairs_for_user()** (12 connections) — `backend/om/db/connector_credential_pair.py`
- **RedisConnectorDeletePayload** (12 connections) — `backend/om/redis/redis_connector_delete.py`
- **_unsafe_deletion()** (12 connections) — `backend/scripts/force_delete_connector_by_id.py`
- **tasks.py** (11 connections) — `backend/om/background/celery/tasks/connector_deletion/tasks.py`
- **check_for_connector_deletion_task()** (11 connections) — `backend/om/background/celery/tasks/connector_deletion/tasks.py`
- **update_connector_credential_pair_from_id()** (10 connections) — `backend/om/db/connector_credential_pair.py`
- **create_deletion_attempt_for_connector_id()** (10 connections) — `backend/om/server/manage/administrative.py`
- **_add_user_filters()** (9 connections) — `backend/om/db/connector_credential_pair.py`
- **get_connector_credential_pair()** (9 connections) — `backend/om/db/connector_credential_pair.py`
- **get_connector_credential_pairs()** (9 connections) — `backend/om/db/connector_credential_pair.py`
- **_delete_connector()** (9 connections) — `backend/scripts/force_delete_connector_by_id.py`
- **RedisConnector** (8 connections) — `backend/om/background/celery/tasks/connector_deletion/tasks.py`
- **User** (8 connections) — `backend/om/db/connector_credential_pair.py`
- **get_cc_pairs_by_source()** (8 connections) — `backend/om/db/connector_credential_pair.py`
- **remove_credential_from_connector()** (8 connections) — `backend/om/db/connector_credential_pair.py`
- **.generate_tasks()** (8 connections) — `backend/om/redis/redis_connector_delete.py`
- *... and 77 more nodes in this community*

## Relationships

- [[Document Indexing Adapter]] (19 shared connections)
- [[Community 59]] (12 shared connections)
- [[Community 161]] (11 shared connections)
- [[Community 99]] (10 shared connections)
- [[Community 85]] (10 shared connections)
- [[Community 61]] (9 shared connections)
- [[Community 111]] (8 shared connections)
- [[Backend Agent/API Test Fixtures]] (6 shared connections)
- [[Community 83]] (6 shared connections)
- [[Community 144]] (6 shared connections)
- [[Community 373]] (4 shared connections)
- [[Community 218]] (4 shared connections)

## Source Files

- `backend/om/background/celery/tasks/connector_deletion/tasks.py`
- `backend/om/background/celery/tasks/docprocessing/tasks.py`
- `backend/om/db/connector_credential_pair.py`
- `backend/om/redis/redis_connector_delete.py`
- `backend/om/redis/redis_utils.py`
- `backend/om/server/manage/administrative.py`
- `backend/scripts/force_delete_connector_by_id.py`

## Audit Trail

- EXTRACTED: 401 (69%)
- INFERRED: 181 (31%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*