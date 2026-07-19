# `om.tenancy` — Multi-tenant data isolation (WS-M)

Self-hosted, **schema-per-tenant** data isolation for Postgres, fully **decoupled from
billing / Stripe / any external control plane**. This package is a clean-room
reimplementation of the Onyx-EE isolation core: the isolation *mechanism* is kept, the
cloud-business coupling is stripped, and a self-hosted tenant-admin experience is added.

> **Contract 3** (see `rewrite-plans/CONTRACTS.md`) is owned here. Every other workstream
> imports tenant primitives from `om.tenancy.context` — never from Onyx's originals.

---

## 1. Isolation model

Each tenant owns a dedicated **Postgres schema**. The same table set (the Alembic
baseline) is created inside every tenant schema, and a request only ever reads/writes
inside its own schema. There is no `tenant_id` column on feature tables — isolation is at
the *schema* level, which is stronger (a missing `WHERE tenant_id = …` cannot leak data).

Schema binding uses SQLAlchemy's **`schema_translate_map`** (`{None: "<tenant_id>"}`) on
the connection, **not** a mutated session `search_path`. `schema_translate_map` is scoped
to the connection/execution and cannot "stick" and silently point later work at the wrong
schema — the well-known footgun of `SET search_path` (see references below).

```
request ─▶ TenantTrackingMiddleware ─▶ CURRENT_TENANT_ID_CONTEXTVAR = "<tenant>"
                                              │
        get_current_tenant_session() ────────┘
                                              │
                       engine.connect().execution_options(
                           schema_translate_map={None: "<tenant>"})
                                              │
                                     all queries run in "<tenant>" schema
```

A tenant id **doubles as a schema name**, so it can never be a bound parameter and is
always validated against a strict allow-list (`om.tenancy.schema`) before being
interpolated. Two levels:

- `is_safe_schema_name` — loose `[A-Za-z0-9_-]+` injection guard (used for any value
  reaching `schema_translate_map`, including `public`).
- `is_tenant_id` / `assert_tenant_id` — strict shape (`tenant_<uuid>` / `tenant_i-<hex>`),
  required before `CREATE`/`DROP SCHEMA` so provisioning can **never** resolve to `public`.

## 2. Request → tenant resolution

`TenantTrackingMiddleware` (`middleware.py`) is a **pure ASGI middleware** (not
`BaseHTTPMiddleware`): it sets the contextvar in the *same* asyncio task that runs the
endpoint, so propagation to the route handler is guaranteed, and the token is reset in a
`finally` block so it never leaks into a pooled worker. Precedence (first match wins):

1. **API key / PAT** — tenant is parsed from the bearer token (`<prefix><tenant>.<rand>`).
2. **Session auth token** — the login token in Redis carries `tenant_id`.
3. **Anonymous-user cookie** — *only* when `ALLOW_ANONYMOUS_TENANT_ACCESS=true`.
4. **Explicit tenant cookie** (`onyx_tid`) — front-end workaround for token-less flows.
5. **Default schema** — nothing identified a tenant; holds no per-tenant data, so
   tenant-scoped endpoints reject the request downstream (`get_session` 401s in MT mode).

A malformed identifier at any step is rejected with **HTTP 400** (never routed anywhere).

## 3. How other features must use Contract 3

Import from **`om.tenancy.context`** — one place, stable names:

```python
from om.tenancy.context import get_current_tenant_id          # str, from the contextvar
from om.tenancy.context import get_current_tenant_session     # @contextmanager, request tenant
from om.tenancy.context import get_tenant_session             # explicit tenant (bg jobs)
from om.tenancy.context import get_shared_schema_session      # public schema (global tables ONLY)
from om.tenancy.context import get_tenant_session_dependency  # FastAPI dep (401s unauth in MT)
```

- **Request-scoped code** → `get_current_tenant_session()` or the FastAPI dependency.
- **Background jobs / cross-tenant loops** → `get_tenant_session(tenant_id=…)`. Contextvars
  do **not** auto-propagate into `asyncio.create_task`/threads, so background work must
  bind the tenant explicitly (that's exactly what this helper is for).
- **Never** hardcode a schema or set `{"schema": "public"}` on a new model.

### Adding a tenant-scoped table

Just define the model normally (no `schema=` argument) and add its DDL to the migration
chain. Because the baseline + migrations run **inside each tenant schema**, the table is
automatically created per-tenant and isolated. Nothing else to do.

### Adding a *global* (public) table — rare

Only for genuinely cross-tenant data (e.g. email→tenant routing). Set
`__table_args__ = ({"schema": "public"},)`, add it to `PUBLIC_SCHEMA_TABLES` in
`context.py`, and create it with a **`public`-qualified, idempotent** Alembic revision
(the per-tenant baseline cannot create a public-only table — see
`alembic/versions/wsm_user_tenant_mapping.py`). Keep this set tiny.

**Public-schema tables (the whole set):**

| table                 | purpose                                   | owner |
|-----------------------|-------------------------------------------|-------|
| `user_tenant_mapping` | email → tenant login routing              | WS-M  |
| `alembic_version`     | migration bookkeeping for public baseline | infra |

## 4. Provisioning (billing-free, on demand)

`provisioning.py` creates a tenant **synchronously against the local Postgres only**:

1. `create_tenant_schema` — the isolated schema (strict-id validated).
2. `run_migrations_for_schema` — the full Alembic chain (baseline also seeds built-in
   tools / default assistant / search settings).
3. `setup_onyx` — per-tenant runtime setup (document index).
4. `TenantMappingRepository.assign` — record the email→tenant route (public).

Failure at any step drops the half-built schema (`drop_tenant_schema`) so a retry starts
clean. `get_or_provision_tenant(email=…)` is the **registration** entry point: it routes
existing (or invited) users to their tenant and only provisions for a genuinely new email,
serialized by a Postgres advisory lock so two concurrent first-logins can't double-provision.
The blocking DDL/migration work runs in a worker thread so the event loop is never stalled.

`get_login_tenant_id(email) -> str | None` is the **read-only** counterpart used by the
authentication path (`UserManager.authenticate` / `get_by_email` / the OAuth callback): it
resolves the tenant an email should log into — the default schema when self-hosted, the
active/invited mapping in multi-tenant mode — and **never provisions**, returning `None`
for an unknown email so a login attempt can never create a tenant as a side effect. This is
the clean-room replacement for the EE `get_tenant_id_for_email`; the auth layer no longer
imports anything from `om.server.tenants.*`.

### Removed billing coupling (kept here for history)

The Onyx-EE flow reached an external control plane; **all of it is gone**:
`notify_control_plane`, `submit_to_hubspot`, Stripe, data-plane token exchange, the
`available_tenant` pre-provision **pool** (replaced by on-demand), and control-plane
seat/subscription gating. `get_or_provision_tenant` still accepts `referral_source` /
`request` for call-site compatibility but **ignores** them (they fed marketing/HubSpot).

## 5. Tenant-admin surface

- **Backend:** `om/server/tenancy/api.py` — superuser-gated CRUD under `/admin/tenants`
  (`GET` list, `POST` create, `POST /{id}/users` assign/move, `POST /{id}/deactivate`,
  `DELETE /{id}`). Gating = instance ADMIN (`current_admin_user`) **plus** the optional
  `TENANT_ADMIN_EMAILS` allow-list, enforced in-handler (`_enforce_platform_admin`).

  > The routes depend directly on `current_admin_user` (not a custom wrapper dependency)
  > because `check_router_auth` only recognises a fixed set of auth deps at the route's
  > top level and does not recurse — a custom wrapper dep would fail the startup auth
  > check. The allow-list is a plain in-handler check.

- **Frontend:** `web/src/app/admin/tenants/**` — list + stat cards + provision/assign
  modals, built on the VertualAI design system (accent via `--virtualai-accent`; no
  hardcoded colors).

- **Menu:** a **Tenants** entry in the admin **Governance** group
  (`web/src/components/admin/adminNavItems.ts`), admin-only (non-curator), orange group
  color, route-label + breadcrumb-color registered alongside.

## 6. Config (Standard 5)

Small, dedicated env-driven surface (`config.py`) — no external control plane:

| env var                         | meaning                                              | default |
|---------------------------------|------------------------------------------------------|---------|
| `MULTI_TENANT`                  | enable multi-tenant mode                             | `false` |
| `TENANT_ADMIN_EMAILS`           | CSV allow-list of platform operators (empty = any admin) | empty |
| `ALLOW_ANONYMOUS_TENANT_ACCESS` | honour the anonymous-user cookie in resolution       | `false` |

## 7. Structured logging (Standard 9)

`events.py` emits one JSON-friendly line per create/update/delete/assignment via
`emit_tenant_event` / the `tenant_operation` timing context manager. Fields:
`event`, `entity` (`tenant`), `entity_id`, `tenant_id`, `actor_user_id`, `action`,
`status`, `duration_ms`, `error`. Events:
`tenant.created` · `tenant.updated` · `tenant.deleted` · `tenant.deactivated` ·
`tenant.user_assigned` · `tenant.user_removed` · `tenant.user_moved`. Emission is wrapped
so logging never breaks the operation it describes.

## 8. Verification

`backend/tests/unit/om/tenancy/test_tenant_isolation.py`:
- **Schema safety** (runs anywhere): loose/strict validation, `assert_tenant_id` blocks
  `public`, `new_tenant_id` round-trips.
- **Resolution precedence** (runs in-container; `importorskip` otherwise): API-key ▶
  session ▶ cookie ▶ default, Redis-failure degrades to default (no 500), malformed id
  raises `InvalidTenantError`.

Cross-tenant smoke (integrator, needs live Postgres): create tenants A + B, write under A,
confirm it is invisible under B across a representative query; confirm migrations apply to
all schemas.

## 9. EE-remnant deletion manifest (integrator / coordinated)

Fresh DB → dropped tables need **no** migration. Already deleted here (fully replaced,
zero importers): `om/server/middleware/tenant_tracking.py`. The following are EE
cloud-pool / anonymous remnants that still have cross-cutting importers spanning **other
workstreams** (celery, user-management, WS-A billing) and must be dropped in a coordinated
pass so the build stays green:

- **Cloud pool:** `AvailableTenant` model + `available_tenant` table; celery
  `background/celery/tasks/tenant_provisioning/` (`pre_provision_tenant`) + its beat
  registration in `apps/background.py` / `apps/monitoring.py`; the
  `CHECK_AVAILABLE_TENANTS_LOCK` + cloud task-name constants.
- **Billing provisioning:** `om/server/tenants/provisioning.py` functions
  `notify_control_plane`, `submit_to_hubspot`, `get_available_tenant`,
  `delete_user_from_control_plane`, `get_tenant_by_domain_from_control_plane` (the login
  path already routes to `om.tenancy.provisioning`).
- **Anonymous path (only if anonymous access is not wanted):** `TenantAnonymousUserPath`
  model + `tenant_anonymous_user_path` table + `om/server/tenants/anonymous_user_path.py`
  + `anonymous_users_api.py`.

## References (Standard 2)

Design informed by:
- MergeBoard, *Multitenancy with FastAPI, SQLAlchemy and PostgreSQL* — `schema_translate_map`.
- PlanetScale, *Approaches to tenancy in Postgres* — schema-per-tenant trade-offs.
- Python docs + FastAPI/Starlette discussions on `contextvars` request-scoping and why raw
  ASGI middleware (not `BaseHTTPMiddleware`) gives correct contextvar propagation.
