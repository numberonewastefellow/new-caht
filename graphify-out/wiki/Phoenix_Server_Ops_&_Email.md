# Phoenix Server Ops & Email

> 205 nodes · cohesion 0.02

## Key Concepts

- **config.py** (168 connections) — `phoenix/src/phoenix/config.py`
- **getenv()** (50 connections) — `phoenix/src/phoenix/config.py`
- **main()** (42 connections) — `phoenix/src/phoenix/server/main.py`
- **_bool_val()** (25 connections) — `phoenix/src/phoenix/config.py`
- **verify_server_environment_variables()** (13 connections) — `phoenix/src/phoenix/config.py`
- **get_env_auth_settings()** (12 connections) — `phoenix/src/phoenix/config.py`
- **get_env_postgres_connection_str()** (12 connections) — `phoenix/src/phoenix/config.py`
- **get_env_root_url()** (12 connections) — `phoenix/src/phoenix/config.py`
- **get_env_tls_config()** (12 connections) — `phoenix/src/phoenix/config.py`
- **get_env_host()** (11 connections) — `phoenix/src/phoenix/config.py`
- **get_env_phoenix_admin_secret()** (11 connections) — `phoenix/src/phoenix/config.py`
- **get_env_port()** (11 connections) — `phoenix/src/phoenix/config.py`
- **SimpleEmailSender** (10 connections) — `phoenix/src/phoenix/server/email/sender.py`
- **get_base_url()** (10 connections) — `phoenix/src/phoenix/config.py`
- **.from_env()** (10 connections) — `phoenix/src/phoenix/config.py`
- **initialize_settings()** (10 connections) — `phoenix/src/phoenix/server/main.py`
- **_float_val()** (9 connections) — `phoenix/src/phoenix/config.py`
- **_int_val()** (9 connections) — `phoenix/src/phoenix/config.py`
- **Path** (9 connections) — `phoenix/src/phoenix/config.py`
- **main.py** (9 connections) — `phoenix/src/phoenix/server/main.py`
- **.__init__()** (9 connections) — `phoenix/src/phoenix/trace/exporter.py`
- **get_env_collector_endpoint()** (8 connections) — `phoenix/src/phoenix/config.py`
- **get_env_database_connection_str()** (8 connections) — `phoenix/src/phoenix/config.py`
- **get_env_tls_enabled_for_http()** (8 connections) — `phoenix/src/phoenix/config.py`
- **get_env_client_headers()** (7 connections) — `phoenix/src/phoenix/config.py`
- *... and 180 more nodes in this community*

## Relationships

- [[Community 66]] (25 shared connections)
- [[Community 74]] (20 shared connections)
- [[Community 270]] (9 shared connections)
- [[Community 149]] (9 shared connections)
- [[Community 589]] (8 shared connections)
- [[Community 302]] (7 shared connections)
- [[Community 839]] (6 shared connections)
- [[Community 287]] (6 shared connections)
- [[Community 170]] (6 shared connections)
- [[Community 93]] (5 shared connections)
- [[Community 180]] (5 shared connections)
- [[Community 674]] (5 shared connections)

## Source Files

- `phoenix/src/phoenix/config.py`
- `phoenix/src/phoenix/server/api/exceptions.py`
- `phoenix/src/phoenix/server/api/queries.py`
- `phoenix/src/phoenix/server/daemons/db_disk_usage_monitor.py`
- `phoenix/src/phoenix/server/email/sender.py`
- `phoenix/src/phoenix/server/main.py`
- `phoenix/src/phoenix/session/session.py`
- `phoenix/src/phoenix/tests/test_config.py`
- `phoenix/src/phoenix/trace/exporter.py`
- `phoenix/src/phoenix/utilities/logging.py`
- `phoenix/src/phoenix/version.py`
- `phoenix/tests/unit/server/test_main.py`
- `phoenix/tests/unit/test_config.py`

## Audit Trail

- EXTRACTED: 959 (97%)
- INFERRED: 31 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*