# Rate Limits (WS-F)

Clean-room, multi-tenant, **observable** token-rate-limiting for chat/search. Replaces the
Onyx-EE `token_rate_limit` enforcement **and** the cloud `tenant_usage` control-plane meter with a
single subsystem that has real budget visibility, metrics, and structured logs.

> Written from a behavior spec, not from Onyx EE source (see `rewrite-plans/CONTRACTS.md`). Own
> module layout, own names, own control flow.

---

## 1. Why this exists / what the old code did

The previous limiter (`om/server/query_and_chat/token_limit.py`) summed
`chat_message.token_count` over a lookback window on **every** chat request and returned a bare
`429` when a `token_rate_limit` row's `token_budget * 1000` was exceeded. Scopes were
`GLOBAL / USER / USER_GROUP`. The separate cloud meter (`usage_limits.py` + `tenant_usage`) fetched
per-tenant caps from a **Stripe/control-plane** endpoint.

Gaps this redesign closes:

1. **No remaining-budget visibility** — callers/admin only learned of a limit via a 429.
2. **No metrics** — nothing emitted for allow/deny.
3. **No first-class per-tenant scope** (and the meter's tenant-awareness was control-plane-only).
4. **No structured logging** on allow/deny/config-change.
5. **O(messages) SQL sum per request** — accurate but unindexed-friendly and slow at scale.
6. **`user_group` lineage** — must move to `team` (Contract 1).

The cloud `tenant_usage` meter (trial/paid tiers, billing coupling) is **deleted** — the deployment
is self-hosted with **no billing** (`CONTRACTS.md` "Deployment target").

## 2. Research → algorithm choice

Surveyed fixed-window, sliding-window (log & counter), token-bucket, and GCRA:

- **Fixed window** allows a 2× burst straddling the window boundary — unacceptable for a budget cap.
- **GCRA** is elegant and O(1), but *"how many tokens are left is a question you cannot ask
  directly"* — and we need exactly that for the remaining-budget API + admin gauge. Rejected.
- **Token bucket** has clean burst semantics but is request-shaped; our cap is a smooth
  tokens-per-hour budget over multi-hour windows.
- **Sliding-window counter** approximates a true rolling window with **O(1) memory** (two integers +
  a weight) and, on Cloudflare's published data, a **~0.003% error rate**. It answers "remaining
  budget" directly and smooths the fixed-window boundary burst.

**Chosen: token-weighted sliding-window counter over Redis, executed atomically via a Lua script.**
Redis Lua (`EVAL`/`register_script`) makes the read-modify-write atomic on the server in one round
trip; we deliberately avoid `WATCH/MULTI/EXEC`, which retry-storms under contention.

Sources that informed the design:
- Cloudflare — *"How we built rate limiting capable of scaling to millions of domains"* (sliding
  window counter accuracy).
- Redis — *"Build 5 Rate Limiters with Redis: Fixed Window, Sliding Window, …"* (Lua atomicity).
- brandur.org — *"Rate Limiting, Cells, and GCRA"* (why GCRA can't report remaining budget).
- Zuplo / Portkey / Azure APIM `llm-token-limit` — **token-** and **cost-based** limiting for LLM
  traffic and multi-tier (org → team → user) budget hierarchies ("must pass all tiers").
- IETF `draft-ietf-httpapi-ratelimit-headers` + Envoy rate-limit observability — `RateLimit-Remaining`
  / `RateLimit-Reset` conventions and `allowed` / `over_limit` Prometheus counters.

## 3. Scopes

`RateLimitScope` = `GLOBAL | TENANT | TEAM | USER` (`om/configs/constants.py`).

- **USER** → keyed on `user_id`.
- **TEAM** → keyed on `team_id` (FK `team.id`, Contract 1). A user in several teams is checked
  against **each** team's policy.
- **TENANT / GLOBAL** → the whole tenant schema (no subject). Because every table already lives in
  the tenant's Postgres schema (Contract 3), both are org-wide; **TENANT** is the recommended,
  explicitly tenant-aware label and **GLOBAL** is kept for parity (usable as a second independent
  org-wide policy).

**Enforcement semantics (intentional change):** a request must pass **all** applicable policies
(the standard org→team→user tier model). The old limiter used "most-lenient group wins" for groups;
we use **"any exceeded → 429"** across user + every team + tenant/global — simpler and predictable.

## 4. Data model (per-tenant schema — Contract 3)

Both tables live **inside the tenant schema** (no `{"schema": "public"}`).

### `rate_limit_policy` — typed config (Standard 5: dedicated config table, UI-editable)
| column | type | notes |
|---|---|---|
| `id` | BIGINT PK | |
| `scope` | varchar enum | `RateLimitScope` |
| `user_id` | UUID FK `user.id` null | set for USER scope |
| `team_id` | BIGINT FK `team.id` null | set for TEAM scope (Contract 1) |
| `token_budget` | BIGINT | **raw tokens** (not thousands) |
| `period_hours` | INT | window length |
| `algorithm` | varchar enum | `RateLimitAlgorithm`, default `sliding_window` |
| `enabled` | BOOL | |
| `created_at` / `updated_at` | timestamptz | |

Unique `(scope, user_id, team_id)` — one policy per subject.

### `rate_limit_usage` — durable hourly roll-up (history + Redis reconciliation)
`(scope, subject_key, bucket_start)` unique; `tokens_used`, `allowed_count`, `throttled_count`
incremented via `INSERT … ON CONFLICT DO UPDATE` (race-free). `subject_key` is always populated
(the scope name for tenant-wide scopes) so the UPSERT groups correctly.

## 5. Runtime architecture

```
   chat send + search send request
               │
      enforce_rate_limits (FastAPI dependency)        ← on chat_backend AND search_backend
               │  short-circuits when no policy exists (per-tenant TTL cache)
   ┌───────────┴─────────────┐
   │  RateLimitService.check │  resolves user → teams → policies
   └───────────┬─────────────┘
               │  per policy: engine.estimate_used()
        RateLimiterEngine (Redis, Lua)  ── sliding-window counter, tenant-prefixed keys
               │
   over budget?├── yes → 429  { scope, remaining=0, reset_seconds }  + metric + structured log
               └── no  → allow                                       + metric + structured log

  recording (best-effort, own session):
   • user prompt  → create_new_chat_message → record_chat_message_tokens()
   • LLM response → save_chat_turn (direct ORM finalize) → record_chat_message_tokens()
               │  engine.record_usage() (Redis INCRBY, atomic)
               └  repository.increment_usage() (Postgres roll-up, UPSERT)
```

**Two recording chokepoints** are required because the user prompt and the assistant response are
persisted by different paths: the prompt goes through `create_new_chat_message`, while the response's
final `token_count` is set by direct ORM mutation in `om/chat/save_chat.py::save_chat_turn`. Hooking
only the former would silently under-count every budget by the (larger) response tokens.

- **`engine.py`** — `RateLimiterEngine`: the sliding-window counter. Two Lua scripts (`peek`,
  `record`); keys are `"{tenant_id}:om:ratelimit:v1:{subject}:{window_index}"`. `TenantRedis` does
  **not** auto-prefix `eval`/`evalsha`, so the engine prepends the tenant id itself (same scheme as
  `TenantRedis._prefixed`, which is idempotent) → counters isolated per tenant. `WindowMath` holds
  the pure arithmetic (unit-testable).
- **`repository.py`** — `RateLimitRepository`: policy CRUD + roll-up UPSERT/query, over a
  tenant-bound `Session`.
- **`service.py`** (Phase 2) — orchestration: resolve subjects, check all policies, build the 429
  payload, record usage, emit metrics + logs, and the remaining-budget view.
- **`_tenancy.py`** — Contract 3 bridge (prefers `om.tenancy.context`, falls back pre-integration).

**Failure mode:** Redis errors **fail open** (allow) with a warning log + `errors` metric — a chat
product should not hard-fail because the limiter's cache is unreachable. The durable roll-up plus
cold-start reconciliation (`engine.seed_current_window`) restore budgets after a Redis flush without
resetting everyone to zero.

## 6. Observability (FULL — the point of this workstream)

- **Remaining-budget API** (`GET /admin/rate-limits/budget`) → per active policy: `budget`, `used`,
  `remaining`, `reset_seconds`, plus a live view surfaced as a gauge in the admin UI.
- **Prometheus** (`prometheus_client`, already wired at `/metrics`) — see `metrics.py`:
  - `om_ratelimit_checks_total{scope,decision}` — counter
  - `om_ratelimit_throttled_total{scope}` — counter
  - `om_ratelimit_tokens_recorded_total{scope}` — counter
  - `om_ratelimit_remaining_budget{scope}` — gauge, set to the tightest remaining per scope (labelled
    by scope only to avoid per-user cardinality; per-subject values are in the `/budget` API)
  - `om_ratelimit_engine_errors_total{operation}` — counter (Redis fail-open)
- **Structured logs (Standard 9, OpenSearch-friendly, all in try/except)** — one JSON-friendly line per
  event with `event, entity, entity_id, tenant_id, actor_user_id, action, status, duration_ms,
  remaining_budget, error`:
  - `ratelimit.allowed`, `ratelimit.throttled`
  - `ratelimit.policy_created`, `ratelimit.policy_updated`, `ratelimit.policy_deleted`

## 7. Config + UI (Phase 3) — configuring rate limits from the admin UI

Everything is configured from the **admin screen** at `web/src/app/admin/rate-limits/` (VertualAI
design system). It is registered in `web/src/components/admin/adminNavItems.ts` +
`web/src/sections/sidebar/AdminSidebar.tsx` and is **admin-gated** (all `/admin/rate-limits/*`
endpoints require `current_admin_user`).

**Navigation:** Admin → **Governance** → **Rate Limits** (`/admin/rate-limits`).

### Scopes — pick when creating a policy

| Scope | Applies to | Subject | Typical use |
|---|---|---|---|
| **Tenant** | every request in the workspace | none | the primary org-wide cap (recommended) |
| **Global** | every request in the workspace | none | a second, independent org-wide cap |
| **Per-User** | each user, against their own usage | none (`user_id` null = default) | a fair per-person allowance |
| **Team** | everyone on one team (shared pool) | `team_id` | a shared budget for a group |

A subject can have **several** policies with different windows (e.g. an hourly *and* a daily cap);
each is enforced independently and a request must pass **all** applicable policies.

### Actions (each maps to an admin endpoint)

| Do this in the UI | Result | Endpoint |
|---|---|---|
| **Create a Rate Limit Policy** → scope, Team (if Team scope), Time Window (hours), Token Budget | new policy (enabled) | `POST /admin/rate-limits/policies` |
| Toggle the **Enabled** checkbox in the table | enable / disable | `PUT /admin/rate-limits/policies/{id}` |
| **Delete** button in the table | remove the policy | `DELETE /admin/rate-limits/policies/{id}` |
| **Live Remaining Budget** panel (auto-refresh 5 s) | current usage/remaining per policy | `GET /admin/rate-limits/budget` |
| **Usage & Throttle History** chart (Tenant/Global tabs) | tokens used + 429s per hour | `GET /admin/rate-limits/history` |

**Reading the panels:** the budget gauge bar is accent-colored when healthy, **amber past 75%**, and
**red once the budget is spent**; the history chart overlays tokens-used (area) with throttled-429
counts (bars) per hour over the last 48 h.

### What a throttled end user sees
A request over budget gets **HTTP 429** with a structured `detail`
(`{message, scope, budget, used, remaining, reset_seconds, period_hours}`) plus `Retry-After`,
`RateLimit-Remaining`, and `RateLimit-Reset` headers — so the client knows exactly how long to wait.

### Known limitations (today)
- **No in-place edit** of a policy's budget/window in the UI — the table only toggles `enabled` /
  deletes. Change a budget by deleting and recreating. (The `PUT` endpoint *does* accept
  `token_budget`/`period_hours`; only the UI form is not wired.)
- **Per-user override** for one specific person (USER scope with a concrete `user_id`) and
  **per-Team / per-User history** are **API-only** — the create modal makes only the per-user
  *default*, and the history chart exposes only Tenant/Global.
- **Algorithm** is fixed to `sliding_window` (the API accepts the field, but only one strategy
  exists, so it is not surfaced in the UI).

## 8. Multi-tenant readiness

Every DB query runs in the tenant schema (Contract 3 session); every Redis key is tenant-prefixed;
every metric and log line carries `tenant_id`. No cross-tenant read path exists — a policy, its
counters, and its roll-up are all inside one tenant's schema/keyspace.

## 9. Extending

- **New algorithm** — add a value to `RateLimitAlgorithm` and a branch in the engine (the `peek`/
  `record` contract is `subject_key + period_hours → estimate`); no schema change needed.
- **New scope** — add to `RateLimitScope`, extend `subject_key()` and
  `RateLimitRepository.list_enabled_for_subjects()`.
- **Cost weighting** (per-model $ budgets) — record a weighted token count instead of raw tokens;
  the engine already treats the increment as an opaque cost.

## 10. Integration notes (Wave 1)

- Depends on **WS-B** (`team` table, `team.id`) and **WS-M** (`om.tenancy.context` facade). Neither
  is on this base branch yet; `_tenancy.py` bridges the tenant import and the `team_id` FK resolves
  once WS-B merges. The integrator linearizes the Alembic revisions (`wsf_rate_limits`, then the
  legacy-drop `wsf_drop_legacy_rate_limit`) off the shared head, after WS-B.
- `models.py` block is under the `# === WS-F: rate-limit models ===` banner.
- `main.py` router wiring + `auth_check.py` spec are delivered as snippets in `rewrite-plans/status/WS-F.md`.
