# SCIM 2.0 Provisioning (WS-G)

Clean-room reimplementation of SCIM 2.0 user/group provisioning, replacing the
Onyx-EE SCIM feature. Identity providers (Okta, Microsoft Entra ID, …) use it to
automatically provision/deprovision users and sync groups to **Teams**
(Contract 1). Written from the RFCs + vendor docs — never from the EE source.

## Standards implemented

- **RFC 7643** — SCIM Core Schema (User, Group, common `meta`, discovery schemas).
  <https://datatracker.ietf.org/doc/html/rfc7643>
- **RFC 7644** — SCIM Protocol (CRUD, list/filter, PATCH §3.5.2, errors §3.12,
  discovery §4). <https://datatracker.ietf.org/doc/html/rfc7644>
- Okta SCIM client guidance (create-dedup via `userName eq`, deactivate via PATCH
  `active:false`, group push via PATCH members).
  <https://developer.okta.com/docs/concepts/scim/>
- Microsoft Entra ID SCIM guidance (capitalised `op`, path-less `replace`, both
  group-member remove shapes, `204` on group PATCH, string `"False"` for `active`).
  <https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups>
  and <https://learn.microsoft.com/en-us/entra/identity/app-provisioning/application-provisioning-config-problem-scim-compatibility>

These vendor quirks are handled explicitly: `op` is normalised to lowercase;
`active` accepts `"True"`/`"False"` strings; group-member `remove` accepts both
`members[value eq "x"]` and `members` + `value:[{value:x}]`; empty filtered lists
return `200` + `totalResults:0` (never `404`); group `PATCH` returns `204`.

## Architecture

```
server/scim/
  api.py           scim_router: mounts discovery routes + /Users + /Groups
  users_api.py     /Users endpoints  (verify_scim_token)
  groups_api.py    /Groups endpoints (verify_scim_token)  → Teams
  admin_api.py     scim_admin_router: /admin/scim token mgmt + status (current_admin_user)
  discovery.py     /ServiceProviderConfig, /ResourceTypes, /Schemas payloads
  auth.py          token gen/hash/display/tenant-parse + verify_scim_token dep + ScimContext
  service.py       ScimUserService / ScimGroupService (business logic, serialization)
  resources.py     Pydantic SCIM wire models (User, Group, ListResponse, PatchOp, Error)
  filters.py       RFC 7644 §3.4.2.2 filter parser + evaluator
  patch_ops.py     RFC 7644 §3.5.2 PATCH applier
  errors.py        ScimError + ScimRoute (renders application/scim+json errors)
  responses.py     response builders + body parsing
  scim_logging.py  Standard-9 structured event logging
  constants.py     URNs, prefixes, content type
db/scim.py         ScimRepository — data access for the 3 SCIM tables only
```

Layering (Standard 10): **routers → services → repository → models**. The
repository touches only the SCIM-owned tables; `User`/`Team` access lives in the
services. Strict typing throughout.

## Endpoints

Mounted at **`/scim/v2`** WITHOUT the global API prefix (IdPs expect the base URL
to end in `/scim/v2`). Content type: `application/scim+json`.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/scim/v2/ServiceProviderConfig` | public | capabilities |
| GET | `/scim/v2/ResourceTypes[/{id}]` | public | User, Group |
| GET | `/scim/v2/Schemas[/{id}]` | public | User, Group schemas |
| POST/GET/PUT/PATCH/DELETE | `/scim/v2/Users[/{id}]` | bearer | → `User` |
| POST/GET/PUT/PATCH/DELETE | `/scim/v2/Groups[/{id}]` | bearer | → `Team` |

Discovery is public per RFC 7644 §4 (IdPs probe before a token exists). All
provisioning routes require the SCIM bearer token (`verify_scim_token`).

Admin (session/admin auth, global-prefixed):

| Method | Path | Notes |
|---|---|---|
| GET | `/admin/scim/status` | base URL, MT flag, active-token/user/team counts |
| GET | `/admin/scim/tokens` | list token metadata |
| POST | `/admin/scim/tokens` | mint token (raw returned **once**) |
| DELETE | `/admin/scim/tokens/{id}` | soft-revoke |

## Token model

- Opaque, high-entropy (`secrets.token_urlsafe(48)`), prefixed `scim_`.
- Only the **SHA-256 hash** is stored (`scim_token.hashed_token`, unique). The raw
  token is shown to the admin **once**, at creation. `token_display` keeps a
  masked `scim_****abcd` form for the UI.
- Presented tokens are compared with `hmac.compare_digest` (constant-time), in
  addition to the indexed hash lookup.
- Revocation is a soft-disable (`is_active=false`) to preserve the audit trail.
- **Multi-tenant routing:** in MT mode the tenant id is URL-encoded into the token
  (`scim_<tenant>.<random>`), the same self-routing technique the API-key
  subsystem uses. `verify_scim_token` parses the tenant, binds the request to that
  tenant's Postgres schema (`CURRENT_TENANT_ID_CONTEXTVAR` + tenant session), then
  verifies the hash against the per-tenant `scim_token` table. This makes SCIM
  self-routing without depending on the tenant middleware for `/scim/v2`.

## Data model (per-tenant — Contract 3)

- `scim_token` (`hashed_token` unique, `token_display`, `created_by → user.id`,
  `is_active`, `created_at`, `last_used_at`).
- `scim_user_mapping` (`external_id` unique, `user_id → user.id` unique).
- `scim_team_mapping` (`external_id` unique, `team_id → team.id` BIGINT unique) —
  replaces EE `scim_group_mapping`; SCIM Groups map to **Teams** (Contract 1).

All three live inside the per-tenant schema. No `{"schema": "public"}`.

## Attribute mapping

| SCIM (User) | Internal |
|---|---|
| `id` | `User.id` (UUID, string) |
| `userName` | `User.email` (unique key) |
| `active` | `User.is_active` |
| `displayName` / `name.formatted` | `User.personal_name` |
| `emails` | derived `[{value: email, type: work, primary: true}]` |
| `externalId` | `scim_user_mapping.external_id` |

| SCIM (Group) | Internal |
|---|---|
| `id` | `Team.id` (BIGINT, string) |
| `displayName` | `Team.name` |
| `members[].value` | `User.id` via `user__team` rows |
| `externalId` | `scim_team_mapping.external_id` |

**DELETE /Users/{id}** performs a *soft deprovision* — deactivate (`is_active=false`)
and remove the SCIM mapping — rather than a destructive row delete, so the user's
owned data is retained. This matches how Okta actually deprovisions (PATCH
`active:false`). **Re-provisioning is idempotent:** a later `POST /Users` with the
same `userName` finds the deactivated, unmapped row and reactivates it in place
(restoring `is_active`, display name and the SCIM mapping) instead of returning a
`409`. A `userName` that collides with an *active* or still-mapped user is a genuine
`409 uniqueness`. **DELETE /Groups/{id}** removes the Team, its `user__team` rows and
the mapping.

`PUT`/`PATCH` on a `User` or `Group` that would collide with another resource's
unique key (a `userName`→email rename, or a `displayName`→Team-name rename) return
`409 uniqueness` (the DB constraint violation is translated), not a `500`.

Provisioned users get an unusable random password hash (they authenticate via
SSO, never a password) and `is_verified=true`, `role=basic`.

## Multi-tenant readiness

Imports the Contract-3 facade `om.tenancy.context` only. `verify_scim_token`
binds the tenant per request; all queries run in the tenant schema; every log
line carries `tenant_id`. No cross-tenant lookups (`id`/`externalId` are scoped
to the request's tenant schema).

## Config + Admin UI

- Dedicated typed config table set (the 3 tables above) — no `key_value_store`.
- Admin screen `web/src/app/admin/scim/` (VertualAI design system): SCIM base URL
  for IdP setup (copyable), status stat cards (`--virtualai-accent`), token table,
  one-time raw-token modal, generate/revoke.
- Menu: **"SCIM Provisioning"** under **Admin → User Management** (admin-gated),
  `web/src/sections/sidebar/AdminSidebar.tsx`.

## Structured log events (Standard 9)

Emitted (JSON, OpenSearch-friendly) via `scim_logging` with fields `event`,
`entity`, `entity_id`, `tenant_id`, `actor_user_id`, `action`, `status`,
`duration_ms`, `error` — all wrapped in try/except:

`scim.user_provisioned`, `scim.user_updated`, `scim.user_deprovisioned`,
`scim.group_synced`, `scim.group_deprovisioned`, `scim.token_created`,
`scim.token_revoked` (entities `scim_user`, `scim_team`, `scim_token`).

## Verification (simulated IdP requests)

```bash
BASE=https://host/scim/v2
TOK=scim_...           # from POST /admin/scim/tokens

# discovery (public)
curl $BASE/ServiceProviderConfig
# create user
curl -X POST $BASE/Users -H "Authorization: Bearer $TOK" \
  -H "Content-Type: application/scim+json" \
  -d '{"schemas":["urn:ietf:params:scim:schemas:core:2.0:User"],
       "userName":"alice@acme.com","externalId":"okta-1","active":true}'
# dedup lookup (Okta)
curl "$BASE/Users?filter=userName%20eq%20%22alice@acme.com%22" -H "Authorization: Bearer $TOK"
# deactivate (Okta/Entra)
curl -X PATCH $BASE/Users/<id> -H "Authorization: Bearer $TOK" \
  -d '{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
       "Operations":[{"op":"replace","value":{"active":false}}]}'
# create group -> Team, then push a member
curl -X POST $BASE/Groups -H "Authorization: Bearer $TOK" \
  -d '{"schemas":["urn:ietf:params:scim:schemas:core:2.0:Group"],"displayName":"Engineering","externalId":"g1"}'
curl -X PATCH $BASE/Groups/<id> -H "Authorization: Bearer $TOK" \
  -d '{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
       "Operations":[{"op":"add","path":"members","value":[{"value":"<userId>"}]}]}'
```

Automated tests: `backend/tests/unit/om/server/scim/` (token auth, filters, PATCH,
discovery, HTTP layer, service mapping, structured logging). Full live-DB
end-to-end provisioning runs during integration (real Postgres + WS-B `team`).

## How to extend

- **New SCIM attribute:** add the field to the model in `resources.py`, map it in
  the relevant `Scim*Service._to_scim` + create/replace/patch, and (if it needs to
  be filterable) it is already covered by the generic filter evaluator.
- **New resource type:** add a schema/resource-type in `discovery.py`, a service +
  sub-router, and mount it in `api.py`.
- **New filter operator / PATCH shape:** extend `filters.py` / `patch_ops.py`; both
  are unit-tested in isolation.

## Integrator hand-off (shared-file snippets)

See `rewrite-plans/status/WS-G.md` for the exact snippets. Summary:

- **`db/models.py`** — WS-G banner block with `ScimToken`, `ScimUserMapping`,
  `ScimTeamMapping` (already applied under the labeled banner).
- **`main.py`** — `from om.server.scim.api import scim_router` +
  `from om.server.scim.admin_api import scim_admin_router`;
  `application.include_router(scim_router)` (no global prefix) and
  `include_router_with_global_prefix_prepended(application, scim_admin_router)`.
- **`auth_check.py`** — the 5 `/scim/v2` discovery entries are in the base
  `PUBLIC_ENDPOINT_SPECS`; provisioning routes use `verify_scim_token` (already
  recognised by `check_router_auth`).
- **Alembic** — `alembic/versions/wsg_scim_provisioning.py` (`down_revision=None`
  placeholder). Linearize **after `0003_agent_rename` AND after WS-B's team rename**
  (needs `team` for the `scim_team_mapping.team_id` FK).
- **`om/tenancy/context.py`** — thin integration shim in this worktree; drop in
  favour of WS-M's canonical module.
```
