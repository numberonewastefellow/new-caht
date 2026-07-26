# Community 161

> 80 nodes · cohesion 0.05

## Key Concepts

- **contextvars.py** (80 connections) — `backend/shared_configs/contextvars.py`
- **get_current_tenant_id()** (73 connections) — `backend/shared_configs/contextvars.py`
- **Session** (20 connections) — `backend/om/server/documents/cc_pair.py`
- **User** (20 connections) — `backend/om/server/documents/cc_pair.py`
- **ValidationError** (20 connections) — `backend/om/connectors/exceptions.py`
- **cc_pair.py** (19 connections) — `backend/om/server/documents/cc_pair.py`
- **get_connector_credential_pair_from_id_for_user()** (15 connections) — `backend/om/db/connector_credential_pair.py`
- **load_settings()** (14 connections) — `backend/om/server/settings/store.py`
- **get_cc_pair_full_info()** (12 connections) — `backend/om/server/documents/cc_pair.py`
- **StatusResponse** (11 connections) — `backend/om/server/documents/cc_pair.py`
- **associate_credential_to_connector()** (10 connections) — `backend/om/server/documents/cc_pair.py`
- **prune_cc_pair()** (10 connections) — `backend/om/server/documents/cc_pair.py`
- **sync_cc_pair()** (10 connections) — `backend/om/server/documents/cc_pair.py`
- **sync_cc_pair_groups()** (10 connections) — `backend/om/server/documents/cc_pair.py`
- **update_cc_pair_status()** (10 connections) — `backend/om/server/documents/cc_pair.py`
- **get_cc_pair_index_attempts()** (9 connections) — `backend/om/server/documents/cc_pair.py`
- **datetime** (8 connections) — `backend/om/server/documents/cc_pair.py`
- **get_cc_pair_permission_sync_attempts()** (8 connections) — `backend/om/server/documents/cc_pair.py`
- **PaginatedReturn** (7 connections) — `backend/om/server/documents/cc_pair.py`
- **get_cc_pair_indexing_errors()** (7 connections) — `backend/om/server/documents/cc_pair.py`
- **update_cc_pair_property()** (7 connections) — `backend/om/server/documents/cc_pair.py`
- **opensearch_smoke_test.py** (7 connections) — `backend/scripts/opensearch_smoke_test.py`
- **run_smoke_test()** (7 connections) — `backend/scripts/opensearch_smoke_test.py`
- **store_settings()** (7 connections) — `backend/om/server/settings/store.py`
- **get_cc_pair_last_pruned()** (6 connections) — `backend/om/server/documents/cc_pair.py`
- *... and 55 more nodes in this community*

## Relationships

- [[Document Indexing Adapter]] (32 shared connections)
- [[Community 103]] (22 shared connections)
- [[Community 91]] (15 shared connections)
- [[Community 120]] (11 shared connections)
- [[Community 99]] (7 shared connections)
- [[Community 69]] (7 shared connections)
- [[Community 111]] (7 shared connections)
- [[Community 85]] (6 shared connections)
- [[Community 73]] (6 shared connections)
- [[Connector Checkpoint & Slim Docs]] (5 shared connections)
- [[Backend Agent/API Test Fixtures]] (5 shared connections)
- [[Community 127]] (5 shared connections)

## Source Files

- `backend/om/configs/llm_configs.py`
- `backend/om/connectors/exceptions.py`
- `backend/om/db/connector_credential_pair.py`
- `backend/om/db/index_attempt.py`
- `backend/om/external_permissions/confluence/doc_sync.py`
- `backend/om/onyxbot/discord/cache.py`
- `backend/om/server/documents/cc_pair.py`
- `backend/om/server/rate_limits/_tenancy.py`
- `backend/om/server/settings/store.py`
- `backend/scripts/opensearch_smoke_test.py`
- `backend/shared_configs/contextvars.py`
- `backend/tests/external_dependency_unit/connectors/confluence/test_confluence_group_sync.py`
- `backend/tests/external_dependency_unit/connectors/jira/test_jira_group_sync.py`
- `backend/tests/integration/common_utils/managers/discord_bot.py`

## Audit Trail

- EXTRACTED: 409 (73%)
- INFERRED: 152 (27%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*