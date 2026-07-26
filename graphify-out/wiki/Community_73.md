# Community 73

> 144 nodes · cohesion 0.02

## Key Concepts

- **get_session_with_tenant()** (28 connections) — `backend/om/db/engine/sql_engine.py`
- **sql_engine.py** (17 connections) — `backend/om/db/engine/sql_engine.py`
- **build_connection_string()** (14 connections) — `backend/om/db/engine/sql_engine.py`
- **get_all_tenant_ids()** (13 connections) — `backend/om/db/engine/tenant_utils.py`
- **SlackbotHandler** (13 connections) — `backend/om/onyxbot/slack/listener.py`
- **get_sqlalchemy_engine()** (12 connections) — `backend/om/db/engine/sql_engine.py`
- **env.py** (11 connections) — `backend/alembic/env.py`
- **.acquire_tenants()** (10 connections) — `backend/om/onyxbot/slack/listener.py`
- **run_multitenant_migrations.py** (9 connections) — `backend/alembic/run_multitenant_migrations.py`
- **._manage_clients_per_tenant()** (9 connections) — `backend/om/onyxbot/slack/listener.py`
- **get_session()** (8 connections) — `backend/om/db/engine/sql_engine.py`
- **get_session_with_shared_schema()** (8 connections) — `backend/om/db/engine/sql_engine.py`
- **is_valid_schema_name()** (8 connections) — `backend/om/db/engine/sql_engine.py`
- **mark_all_connectors_for_deletion()** (8 connections) — `backend/scripts/tenant_cleanup/on_pod_scripts/execute_connector_deletion.py`
- **get_async_session()** (7 connections) — `backend/om/db/engine/async_sql_engine.py`
- **get_db_readonly_user_session_with_current_tenant()** (7 connections) — `backend/om/db/engine/sql_engine.py`
- **run_async_migrations()** (6 connections) — `backend/alembic/env.py`
- **run_migrations_offline()** (6 connections) — `backend/alembic/env.py`
- **main()** (6 connections) — `backend/alembic/run_multitenant_migrations.py`
- **env.py** (6 connections) — `backend/alembic_tenants/env.py`
- **Session** (6 connections) — `backend/om/db/engine/sql_engine.py`
- **cloud_beat_task_generator()** (6 connections) — `backend/om/background/celery/tasks/cloud/tasks.py`
- **async_sql_engine.py** (6 connections) — `backend/om/db/engine/async_sql_engine.py`
- **get_sqlalchemy_async_engine()** (6 connections) — `backend/om/db/engine/async_sql_engine.py`
- **cloud_check_alembic()** (6 connections) — `backend/om/background/celery/tasks/monitoring/tasks.py`
- *... and 119 more nodes in this community*

## Relationships

- [[Community 119]] (21 shared connections)
- [[Community 148]] (9 shared connections)
- [[Community 106]] (7 shared connections)
- [[Community 161]] (6 shared connections)
- [[Community 85]] (6 shared connections)
- [[Backend Agent/API Test Fixtures]] (5 shared connections)
- [[Community 127]] (5 shared connections)
- [[Document Indexing Adapter]] (4 shared connections)
- [[Community 69]] (4 shared connections)
- [[Community 103]] (4 shared connections)
- [[Community 70]] (3 shared connections)
- [[Community 121]] (3 shared connections)

## Source Files

- `backend/alembic/env.py`
- `backend/alembic/run_multitenant_migrations.py`
- `backend/alembic_tenants/env.py`
- `backend/om/background/celery/tasks/cloud/tasks.py`
- `backend/om/background/celery/tasks/monitoring/tasks.py`
- `backend/om/db/engine/async_sql_engine.py`
- `backend/om/db/engine/connection_warmup.py`
- `backend/om/db/engine/iam_auth.py`
- `backend/om/db/engine/sql_engine.py`
- `backend/om/db/engine/tenant_utils.py`
- `backend/om/onyxbot/slack/listener.py`
- `backend/scripts/debugging/onyx_db.py`
- `backend/scripts/debugging/onyx_list_tenants.py`
- `backend/scripts/tenant_cleanup/on_pod_scripts/check_documents_deleted.py`
- `backend/scripts/tenant_cleanup/on_pod_scripts/cleanup_tenant_schema.py`
- `backend/scripts/tenant_cleanup/on_pod_scripts/execute_connector_deletion.py`
- `backend/scripts/tenant_cleanup/on_pod_scripts/get_tenant_connectors.py`
- `backend/scripts/tenant_cleanup/on_pod_scripts/get_tenant_index_name.py`
- `backend/scripts/tenant_cleanup/on_pod_scripts/get_tenant_users.py`

## Audit Trail

- EXTRACTED: 382 (74%)
- INFERRED: 134 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*