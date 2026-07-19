# WS-F — Rate limits (redesign + full observability) — progress log

Worktree: `.claude/worktrees/ws-f` (branch `rewrite/ws-f`, based on `rename_onyx_to_om`).
Owner agent: WS-F. Depends on **Contract 1 (Team FK → `team.id`)** + **Contract 3 (tenant context)**.

---

## Step 0 — Current implementation summary (behavior only; clean-room, no code copied)

Read the existing EE-origin rate limiter + cloud usage meter. Findings:

### Token rate limiter (the feature we redesign)
- **Enforcement point:** `check_token_rate_limits` FastAPI dependency in
  `om/server/query_and_chat/token_limit.py`, wired onto `POST` chat send in
  `chat_backend.py:532` (`_rate_limit_check: None = Depends(check_token_rate_limits)`) and mirrored
  by `features/build/api/messages_api.py`.
- **Scopes (enum `TokenRateLimitScope`):** `GLOBAL`, `USER`, `USER_GROUP`. No tenant scope.
- **Window/budget:** each `token_rate_limit` row has `period_hours` (int) + `token_budget` (int, in
  units of 1,000 tokens via `TOKEN_BUDGET_UNIT`) + `enabled` + `scope` + `created_at`.
- **Algorithm = fixed lookback sum (sliding total, no buckets):** on each request it sums
  `chat_message.token_count` over `time_sent >= now - period_hours` (grouped by minute) and compares to
  `token_budget * 1000`. Group usage joins `chat_session → user__user_group`. Global sums all messages.
- **Short-circuit:** `any_rate_limit_exists()` is `@lru_cache`'d so the hot path skips the DB when no
  limits are configured. Cache cleared on create.
- **Enforcement semantics:** user + all groups + global checked in parallel
  (`run_functions_tuples_in_parallel`); ANY exceeded → **HTTP 429** with a plain-text `detail`. Group
  rule = "most lenient wins" (blocked only if EVERY group is over). Anonymous/API-key users → global only.
- **Admin routes:** `om/server/token_rate_limits/api.py`, prefix `/admin/token-rate-limits`
  (`/global`, `/users`, `/user-group/{id}`, `/user-groups`, `PUT|DELETE /rate-limit/{id}`),
  `current_admin_user` gated. CRUD lives in `om/db/token_limit.py`.
- **Tables:** `token_rate_limit`, `token_rate_limit__user_group` (FK `user_group.id`).

### Cloud usage meter (EE control-plane; to be dropped)
- `om/server/usage_limits.py` + `tenant_usage_limits.py` + `om/db/usage.py` + table `tenant_usage`:
  weekly fixed-window counters (`llm_cost_cents`, `chunks_indexed`, `api_calls`,
  `non_streaming_api_calls`) with per-tenant overrides fetched from a **Stripe/control-plane** endpoint
  (`fetch_billing_information`, `generate_data_plane_token`, `CONTROL_PLANE_API_BASE_URL`). Trial/paid
  tiers. This is exactly the control-plane coupling the rewrite removes (self-hosted, no billing).

### Gaps identified (drive the redesign)
1. **No remaining-budget visibility** — a caller only learns of the limit via a 429; no "how much left".
2. **No metrics** — nothing emitted to Prometheus/logs on allow/deny.
3. **No per-tenant awareness** — GLOBAL is org-wide, but there is no tenant-scoped policy and the meter's
   tenant-awareness is control-plane-only.
4. **No per-key structured logging** on allow/deny/config-change.
5. **DB-sum on every request** — accurate but O(messages) per check; no counter/roll-up.
6. **Team rename** — `user_group` lineage → `team` (Contract 1); FK must move to `team.id`.

### Environment facts (for the new design)
- Tenant primitives today: `shared_configs.contextvars.get_current_tenant_id()` + `CURRENT_TENANT_ID_CONTEXTVAR`;
  `om.db.engine.sql_engine.get_session_with_current_tenant()`. Contract 3 requires importing from the
  **`om.tenancy.context`** facade (WS-M) — not yet present on this base branch → bridged via a local
  compat shim that prefers the facade and falls back to the primitives.
- Redis: `om.redis.redis_pool.get_redis_client()` returns a **tenant-key-prefixed** `Redis` (isolation
  built in).
- Prometheus: `prometheus_client` + `prometheus-fastapi-instrumentator` already wired
  (`om/server/metrics/prometheus_setup.py`, `/metrics` exposed). Custom `Counter`/`Gauge` supported.
- Recharts `^2.13.1` present (`web/src/components/ui/areaChart.tsx`). Admin menu registry:
  `web/src/components/admin/adminNavItems.ts` (current entry: "Usage Limits" → `/admin/token-rate-limits`).
- **Integration dependencies (Wave-1):** `Team`/`team` table (WS-B) + `om.tenancy.context` facade (WS-M)
  are NOT yet merged on this base branch. WS-F codes against the contracts; integrator merges WS-B/WS-M first.

---

## Research (Standard 2) — algorithm decision

Web-researched fixed-window vs sliding-window (log/counter) vs token-bucket vs GCRA, Redis Lua
atomicity, LLM token/cost-based limiting, and rate-limit observability (RateLimit-Remaining/Reset +
Prometheus). **Chosen: token-weighted sliding-window counter over Redis via atomic Lua** — O(1)
memory, ~0.003% error (Cloudflare), directly answers "remaining budget" (GCRA can't), smooths the
fixed-window boundary burst. Fail-open on Redis errors. Sources cited in the module README §2.

## Phase 1 — DONE (tables + core engine + design doc)

New files under `backend/om/server/rate_limits/`: `__init__.py`, `constants.py` (re-exports the
`RateLimitScope`/`RateLimitAlgorithm` enums added to `om/configs/constants.py` + `subject_key()`),
`_tenancy.py` (Contract 3 bridge), `engine.py` (`RateLimiterEngine` + `WindowMath`, sliding-window
Lua), `repository.py` (`RateLimitRepository`: policy CRUD + roll-up UPSERT/query), `README.md`.
Models `RateLimitPolicy` + `RateLimitUsage` appended to `om/db/models.py` under `# === WS-F: ... ===`.
Migration `alembic/versions/wsf_rate_limits.py` (`down_revision=None` placeholder).

**Phase 1 self-review — findings fixed:**
1. **Bug (correctness):** the original supports *multiple* limits per scope (different windows), but
   my first cut (a) could collide two policies' Redis counters when their window indices coincided and
   (b) had a unique constraint `(scope,user_id,team_id)` that forbade multiple windows per subject.
   **Fixed:** Redis key now encodes `period_hours` (`…:{subject}:{period}h:{window_index}`); unique
   constraint is now `(scope,user_id,team_id,period_hours)`.
2. **Bug (roll-up):** `rate_limit_usage.subject_key` made NOT NULL (always the `subject_key()` value,
   scope-name for tenant-wide) so the UPSERT groups tenant-wide rows (Postgres NULLs are distinct).
3. **Concurrency:** enforcement counter is a single atomic Lua script (INCRBY+PEXPIRE+weighted read);
   roll-up uses atomic `ON CONFLICT DO UPDATE`. Check-then-record overshoot is bounded + documented
   (acceptable for a token budget; the record is never lost). Redis errors fail open + metric.
4. **Tenant + team scoping:** Redis keys tenant-prefixed (idempotent w/ `TenantRedis._prefixed`);
   all DB in tenant schema; `list_enabled_for_subjects` returns tenant-wide + user + each team policy.
5. Typing tightened (`UUID`), all modules import + `py_compile` clean.

**Deferred to Phase 2 (noted):** validate `period_hours > 0` + `token_budget >= 0` at the API;
guard duplicate tenant-wide policies at the service layer (constraint can't, due to NULL semantics).

## Phase 2 — DONE (enforcement + observability API + metrics + logs)

New files: `metrics.py` (Prometheus counters/gauge + `log_ratelimit_event`), `api_models.py`
(validated Pydantic), `service.py` (`RateLimitService` + `RateLimitExceededError` +
`record_chat_message_tokens`), `cache.py` (per-tenant existence cache), `dependencies.py`
(`enforce_rate_limits`), `api.py` (`/admin/rate-limits` CRUD + `/budget` + `/history`).

Wiring:
- `chat_backend.py`: `Depends(check_token_rate_limits)` → `Depends(enforce_rate_limits)` (import swapped).
- `db/chat.py` `create_new_chat_message`: best-effort `record_chat_message_tokens(...)` after persist.
- `main.py`: imported + registered `rate_limit_admin_router` next to the legacy router (legacy removed
  in Phase 4 — no double-registration).

**Metrics emitted:** `om_ratelimit_checks_total{scope,decision}`, `om_ratelimit_throttled_total{scope}`,
`om_ratelimit_tokens_recorded_total{scope}`, `om_ratelimit_remaining_budget{scope}` (gauge),
`om_ratelimit_engine_errors_total{operation}`.
**Structured logs:** `ratelimit.allowed|throttled|policy_created|policy_updated|policy_deleted` with the
Standard-9 field set, all in try/except.

**Phase 2 self-review — findings fixed:**
1. **Observability bug (cardinality):** the remaining-budget gauge was labelled by `subject` (a per-user
   UUID) → Prometheus cardinality explosion. **Fixed:** gauge is now `{scope}` only, set to the tightest
   (min) remaining per scope; per-subject detail is in the `/budget` API instead.
2. **Transaction safety:** the record hook's roll-up UPSERT calls `commit()`; running it on the caller's
   session would prematurely commit the chat transaction (which may pass `commit=False`). **Fixed:** the
   hook reads identity on the caller's session but performs roll-up WRITES on an independent tenant
   session; Redis is separate. Never raises.
3. **Multi-tenant bug (carried from old code):** the old `any_rate_limit_exists()` used a process-global
   `@lru_cache` that would leak one tenant's "no limits" to others. **Fixed:** per-tenant TTL cache with
   explicit invalidation on config change.
4. **429 correctness:** structured `detail` (scope/budget/used/remaining/reset/period) + `Retry-After` /
   `RateLimit-Remaining` / `RateLimit-Reset` headers; rejects on the most-restrictive breached policy.
5. **Validation:** `period_hours>0`, `token_budget>=0`, scope↔subject agreement enforced in Pydantic
   (`RateLimitPolicyArgs`); duplicate tenant-wide policies guarded in the API (constraint can't due to NULLs).
6. Fail-open on Redis errors (allow + metric + log). All modules import + `py_compile` clean.

Note: admin routes are `current_admin_user`-gated (not public) → no `auth_check` public-spec entry needed.

## Phase 3 — DONE (admin UI + menu)

New page `web/src/app/admin/rate-limits/`: `types.ts`, `lib.ts`, `CreatePolicyModal.tsx` (scope +
team picker, validated), `PolicyTable.tsx` (list/toggle/delete), `RemainingBudgetPanel.tsx` (live
auto-refreshing gauge bars), `ThrottleHistoryChart.tsx` (recharts ComposedChart: tokens area +
throttle bars, Tenant/Global tabs), `page.tsx`. VertualAI design system throughout; healthy gauge
fill uses `var(--virtualai-accent)` (theme-aware), warning/critical use semantic status colors; no
hardcoded accent colors. Menu: `adminNavItems.ts` + `AdminSidebar.tsx` entry "Rate Limits" →
`/admin/rate-limits`, admin-gated (non-curator governance group).

**Phase 3 self-review — findings fixed:**
1. **Bug:** the PUT/update endpoint reused the create-shaped `RateLimitPolicyArgs`, whose validator
   requires `team_id` for TEAM scope — so a simple enable/disable toggle (which doesn't resend the
   subject) would 422 for team policies. **Fixed:** added `RateLimitPolicyUpdateArgs` (mutable fields
   only; scope/subject are immutable).
2. **Fidelity:** made USER scope support `user_id=None` = per-user **default** (matches the original's
   "per-user" semantics — applied to each user against their own usage) plus specific-user overrides.
   Threaded the effective subject through the service; extended repo + validators + duplicate guard.
3. Design-system + role-gating verified; frontend `tsc --noEmit` in the worktree = **0 errors**.

## Phase 4 — DONE (delete old + verify)

Removed the token-rate-limit subsystem WS-F replaced:
- Backend files deleted: `om/server/query_and_chat/token_limit.py`, `om/db/token_limit.py`,
  `om/server/token_rate_limits/` (dir).
- Models `TokenRateLimit` + `TokenRateLimit__UserGroup` and enum `TokenRateLimitScope` removed;
  `om/db/user_group.py` cleanup fn + caller + import removed; `om/main.py` legacy router removed.
- Frontend removed: `web/src/app/admin/token-rate-limits/`, `groups/[groupId]/AddTokenRateLimitForm.tsx`,
  and the per-group rate-limit section in `GroupDisplay.tsx` (WS-B-owned page — minimal edit, flagged).
- Teardown migration `alembic/versions/wsf_drop_legacy_rate_limit.py` drops the 2 legacy tables.
- Unit tests: `tests/unit/om/server/rate_limits/test_rate_limit_engine.py` — **12 passed** (WindowMath,
  sliding-window weighting reference, subject keying, hour bucket, API-model validation).

**Verification:** backend `py_compile` + import of new modules/models OK (old symbols gone); frontend
worktree `tsc --noEmit` 0 errors; unit tests pass. (Full runtime enforcement/DB/Redis integration test
needs a booted stack — done by the integrator per CONTRACTS §Integration.)

### ⚠️ NOT deleted — `tenant_usage` cloud meter (documented hand-off)
The cloud usage meter (`om/server/usage_limits.py`, `om/server/tenant_usage_limits.py`, `om/db/usage.py`,
table `tenant_usage`) was **intentionally left in place**. It is billing/control-plane coupled and woven
through **8+ call sites** across indexing, LLM (`multi_llm`), api-key usage, reporting, and chat/search
backends — and per CONTRACTS **WS-A owns billing/license removal**. WS-F's new subsystem replaced only
the token-rate-limit portion, so ripping out the broader meter here would break the build and overstep
WS-A. **Recommendation for integrator/WS-A:** remove `usage_limits`/`tenant_usage_limits`/`db.usage` +
`tenant_usage` alongside the billing/control-plane removal; the WS-F self-hosted `rate_limit_usage`
table supersedes its token-limiting role.

### ⚠️ Process note — main-tree recovery
Two frontend `rm`/`grep`/`tsc` Bash commands mid-session accidentally targeted the MAIN tree
(`d:\llm\danswer20022026\web`) instead of the worktree, deleting the *old* token-rate-limits page +
`AddTokenRateLimitForm.tsx` from the main tree. **Restored** via `git restore` (verified present +
clean). All Write/Edit operations correctly targeted the worktree throughout; all deletions were
then re-applied in the worktree. No main-tree changes remain from this session.

---

## Integrator snippets (shared files)

**`backend/om/main.py`** — import + register (already applied in worktree; legacy router removed):
```python
from om.server.rate_limits.api import router as rate_limit_admin_router
# ... in get_application(), alongside the other include_router calls:
include_router_with_global_prefix_prepended(application, rate_limit_admin_router)
```

**`backend/om/db/models.py`** — models under `# === WS-F: rate-limit models ===` (RateLimitPolicy,
RateLimitUsage). Enums `RateLimitScope`/`RateLimitAlgorithm` added to `om/configs/constants.py`.

**Alembic** — linearize (both `down_revision=None` placeholders), after WS-B's `team` rename:
`… → wsf_rate_limits → wsf_drop_legacy_rate_limit`.

**`auth_check.py`** — no entry needed; all `/admin/rate-limits/*` routes are `current_admin_user`-gated.

**Wave-1 dependencies:** WS-B `team` table (FK `rate_limit_policy.team_id → team.id`) + WS-M
`om.tenancy.context` facade (bridged by `_tenancy.py`; team membership bridged by `_teams.py`).

_WS-F complete. Not committed/pushed; no `alembic upgrade` run by hand (per instructions)._

---

## [REVIEW] Rigorous self-review pass — gaps found + fixed

Re-read CONTRACTS.md + WS-F plan in full; checked all 12 standards; hunted bugs; re-verified.

**Phase checklist (all DONE):** Phase 1 (read impl + README design doc + tables + engine); Phase 2
(enforcement dep + budget API + metrics + structured logs); Phase 3 (admin UI + gauge + recharts +
menu); Phase 4 (delete old token-rate-limit + verify + unit tests). Each had its self-review gate.

**Gaps found & fixed this pass:**
1. **CRITICAL — response tokens were never recorded.** The assistant response's `token_count` is
   finalized by direct ORM mutation in `om/chat/save_chat.py::save_chat_turn`, NOT via
   `create_new_chat_message` — so my single hook only counted user-prompt tokens and every budget
   silently under-counted by the (larger) response tokens. **Fixed:** added the second recording
   chokepoint in `save_chat_turn`.
2. **CRASH — `/budget` on a per-user default policy.** `remaining_budget()` called
   `subject_key(USER, None, None)` → `ValueError` (500) whenever a per-user-default policy existed.
   **Fixed:** default-user policies render as a "user:(per-user default)" template (budget only).
3. **CRASH — `/history?scope=user` without `user_id`** raised `ValueError` (500). **Fixed:** validated
   → clean 400 (and a 400 on malformed UUID).
4. **Plan conformance — enforcement on search.** Plan says "chat/search"; only chat was gated.
   **Fixed:** added `enforce_rate_limits` to `search_backend.send-search-message` (verified the nested
   `current_chat_accessible_user` never loosens the endpoint's `current_user` gate).
5. **Metric over-count.** `om_ratelimit_tokens_recorded_total` was incremented per policy; now once per
   distinct (scope, subject) so multiple windows on one subject don't multiply the token total.
6. **Standard 9 completeness.** Config-change logs now also emitted on FAILED create (409) / update &
   delete (404), with `status`/`error`, not only on success.
7. **Doc accuracy.** Corrected the `RateLimitAlgorithm` comment (engine implements SLIDING_WINDOW only;
   the column is a reserved forward-compat field, not yet dispatched on); README §5 documents the two
   recording chokepoints + chat/search enforcement.
8. **Integration conflict flagged.** WS-B renames `token_rate_limit__user_group`→`token_rate_limit__team`
   while WS-F drops it — noted in the teardown migration + here for the integrator (drop wins).

**Leftover-reference sweep:** no code references to deleted symbols remain (backend: only doc comments;
web: none). Old EE token-rate-limit code/tables/routes/UI all removed; `tenant_usage` cloud meter left
as the documented WS-A/billing hand-off.

**Verification:** `py_compile` all changed Python — OK; imports of new modules/models — OK (old symbols
gone); unit tests `tests/unit/om/server/rate_limits/` — **12 passed**; worktree `tsc --noEmit` — **0
errors** (no web files changed this pass; prior result stands). `mypy` not installed in this env
(config present in `pyproject.toml`, strict); types were written to strict by hand. Not committed; no
`alembic upgrade` run.

---

## [UI REVIEW + DOCS] Admin-UI review + configuration documentation (docs-only pass)

User asked: is the feature configurable from the UI, how, did we miss anything, and is it documented.

**UI review — configurable? Yes.** From Admin → Governance → **Rate Limits** (`/admin/rate-limits`,
admin-gated) the admin can: **create** a policy (scope / Team / window-hours / token-budget),
**enable-disable** (checkbox toggle), **delete**, watch the **live budget gauge**, and view the
**usage/throttle history** chart. Maps to `POST/PUT/DELETE /policies`, `GET /budget`, `GET /history`.

**Gaps found (documented as current limitations — NOT built this pass, per user's "docs-only" choice):**
- No in-place **edit** of a policy's budget/window in the UI (only toggle + delete; change = delete &
  recreate). Backend `PUT` supports it; only the UI form is unwired.
- Per-user **override** (specific `user_id`) + per-Team/per-User **history** are API-only.
- `algorithm` is API-settable but fixed to `sliding_window` (not surfaced).

**Docs written (channel chosen with user: in-app help + README; repo has no docs-site framework):**
- `web/src/app/admin/rate-limits/page.tsx` — added an `AdminPageTitle description` and expanded the
  on-page help: how enforcement works (429 w/ remaining+reset, all applicable policies must pass), the
  four scopes, a numbered "Setting up a policy" guide, how to read the gauge (amber ≥75%, red when
  spent) + history, and an honest limitations note.
- `backend/om/server/rate_limits/README.md` §7 — rewrote "Config + UI" into a step-by-step guide
  (navigation, scopes table, action→endpoint table, panel-reading, the 429 `detail`/headers an end
  user sees, known limitations). Also corrected a stale §6 metric line (`om_ratelimit_remaining_budget`
  is `{scope}` only after the cardinality fix).

**Verify:** worktree `tsc --noEmit` = **0 errors** (only `page.tsx` copy changed); `AdminPageTitle`
confirmed to accept `description`; README valid GFM (blank lines added before tables). No
behavioral/API/schema changes — copy only. Not committed.

**Deferred (offered as follow-up):** wire the **Edit policy** modal (backend `PUT` already supports it)
to make the UI fully match the API.
