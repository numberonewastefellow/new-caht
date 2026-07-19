# WS-F — Rate limits (redesign + full observability)

## ▶ AGENT INSTRUCTIONS — START HERE (read this whole block first)

**You were pointed at this file to IMPLEMENT workstream WS-F. Do exactly this:**

0. **DUPLICATE CHECK — before anything.** If `.claude/worktrees/ws-f` already exists OR
   `rewrite-plans/status/WS-F.md` already has status lines from another agent, another agent owns WS-F:
   **STOP, report "WS-F already in progress — standing down", make NO changes.** Otherwise self-isolate:
   `git worktree add .claude/worktrees/ws-f -b rewrite/ws-f rename_onyx_to_om`
   Working root = `d:\llm\danswer20022026\.claude\worktrees\ws-f`; do ALL edits there, never the main tree.
1. **Read** `rewrite-plans/CONTRACTS.md` + the rest of THIS file. FK to `team.id` (Contract 1);
   tenant-safe (Contract 3).
2. **STEP 0 of the plan: READ the current rate limiter** (behavior only — do not copy) and summarize
   its scopes/window/enforcement/gaps before redesigning.
3. **Legal — clean-room.** NEVER open/copy/paraphrase Onyx EE source at
   `D:\llm\danswer07022026_original\onyx\backend\ee\...`.
4. **Orient with graphify** before reading source.
5. **Phases + review gates.** TodoWrite; self-review after each phase.
6. **Research first** (sliding-window/token-bucket/GCRA, Redis counters, observability); cite in README.
7. **Standards:** multi-tenant-safe; dedicated config tables + admin "Rate Limits" UI (recharts for
   history); VertualAI design system; menu entry; **FULL observability** (remaining-budget API + admin
   gauge + Prometheus/structured metrics); structured OpenSearch logs on allow/deny/config-change in
   try/except; OOP + strict typing. Do NOT double-register the token-rate-limit router.
8. **Delete old token_limit/usage tables+code only in the FINAL phase**, after verify.
9. **Write** a module README. **Progress:** append to `d:\llm\danswer20022026\rewrite-plans\status\WS-F.md`.
10. **Do NOT commit/push. Do NOT run `alembic upgrade` by hand.** Summarize at the end.

**Wave:** 1. **Emphasis:** read current limiter first, then redesign with FULL observability; scopes
global/tenant/team/user.

---

> Read `CONTRACTS.md` first. Depends on **Contract 1 (Team FK)** + **Contract 3 (tenant)**. Follow all
> Engineering standards. Work in your own worktree.

## Goal
**Read the current rate limiter, understand it, then upgrade it with a new design + FULL
observability.** Replace the Onyx-EE token-rate-limit + cloud usage-metering with a clean-room,
multi-tenant, observable rate-limiting subsystem with new tables and new admin pages.

## Step 0 — READ the current implementation (understand before redesigning)
Read and summarize today's behavior (behavior only — do not copy code):
- `backend/om/server/query_and_chat/token_limit.py` — the `check_token_rate_limits` FastAPI dependency
  (enforcement point).
- `backend/om/db/token_limit.py` — CRUD/fetch, scope-filtered.
- `backend/om/server/token_rate_limits/api.py` — admin routes.
- `backend/om/server/usage_limits.py`, `tenant_usage_limits.py`, `db/usage.py` — cloud usage metering.
- Tables `token_rate_limit`, `token_rate_limit__user_group`, `tenant_usage`.
Capture: scopes (global/user/group), window (`period_hours`, `token_budget`), how usage is counted
(sum of `chat_message.token_count`), and the 429 path. Note gaps: no remaining-budget visibility, no
metrics, no per-tenant awareness.

## Research first (Standard 2)
Web-research rate-limiting algorithms (fixed-window vs sliding-window vs token-bucket vs GCRA),
distributed counters (Redis), and observability patterns (per-key remaining budget, Prometheus
metrics, structured events).

## New design (WHAT to build)
- **Scopes:** global / per-tenant / per-team / per-user (Team via Contract 1). Drop cloud
  `tenant_usage` control-plane coupling; keep a self-hosted usage meter.
- **Algorithm:** researched choice (recommend sliding-window or token-bucket via Redis for accuracy).
- **Enforcement:** dependency on chat/search endpoints → 429 with a clear, structured error including
  remaining budget + reset time.
- **FULL observability:**
  - **Remaining-budget API** + surfaced in the admin UI (live gauge).
  - **Prometheus metrics** (requests, allowed, throttled, remaining budget per scope) if a metrics
    endpoint exists; otherwise structured metric logs.
  - **Structured logs** on every allow/deny + config change (Standard 9), OpenSearch-friendly.

## New tables (own names, typed)
- `rate_limit_policy` (scope enum, subject_id nullable, budget, window, algorithm, enabled, timestamps).
- Optional `rate_limit_usage` roll-up (or Redis-backed counters + periodic persistence).
- FK team scope → `team.id`.

## Config + UI
- Admin **Rate Limits** screen (VertualAI design system): CRUD policies per scope, live remaining-budget
  view, throttle history charts (can reuse recharts). **Dedicated config tables** (typed), UI-editable.
- Update MENU: "Rate Limits" under admin (admin-gated).

## Shared-file snippets (integrator)
- `models.py`: rate-limit model block. `main.py`: rate-limit admin router (note token-rate-limit router
  is already included once — replace its routes, don't double-register).
- Alembic: revisions for new tables.

## Phases (with review gates)
- **Phase 1 — Read current impl + write design doc (in README) + new tables + core limiter engine.**
  **Review:** algorithm correctness under concurrency; tenant + team scoping.
- **Phase 2 — Enforcement dependency + remaining-budget API + metrics.** **Review:** 429 correctness;
  budget math; metrics/logs emitted.
- **Phase 3 — Admin UI (policies + live budget + charts) + menu.** **Review:** design-system; role-gating.
- **Phase 4 — Delete old + verify.** Remove old token_limit/usage EE code + tables. **Review:** limits
  enforce; observability visible; structured logs present.

## Structured logs (Standard 9)
`event=ratelimit.allowed|throttled|policy_created|policy_updated|policy_deleted`,
`entity=rate_limit_policy|request`, `entity_id`, `tenant_id`, `actor_user_id`, `action`, `status`,
`duration_ms`, `remaining_budget`, `error`.

## Verification
- Exceeding a policy returns 429 with remaining/reset; remaining-budget API + UI reflect real usage;
  metrics/logs emitted; per-tenant + per-team scoping isolated.

## README
`backend/om/.../rate_limits/README.md`: algorithm choice + why (cite research), scopes, tables,
observability (metrics + log events), config/UI, extension.
