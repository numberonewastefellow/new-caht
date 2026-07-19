# WS-D — Standard answers (clean-room) — integrator hand-off

**Branch:** `rewrite/ws-d` (worktree `.claude/worktrees/ws-d`, off `rename_onyx_to_om`)
**Wave:** 1 · **Type:** clean-room feature rewrite (Slack keyword/regex canned answers + categories)

Replaces the Onyx-EE standard-answers feature. New self-contained module
`backend/om/standard_answers/` (see its `README.md`). The four shared files + menu are
handled below via section-ownership snippets for the integrator to apply.

## New files (disjoint — no merge risk)

- `backend/om/standard_answers/` — `safe_regex.py`, `matching.py`, `repository.py`, `service.py`,
  `config.py`, `events.py`, `schemas.py`, `blocks.py`, `slack_handler.py`, `api.py`, `README.md`.
- `backend/om/tenancy/context.py` + `__init__.py` — **standalone Contract-3 facade shim** (see below).
- `backend/alembic/versions/wsd_standard_answer_config.py` — new config table migration.
- `backend/tests/unit/om/standard_answers/` — unit tests (45).
- Frontend: new page dir `web/src/app/admin/standard-answers/` (see Frontend section).

## Shared-file changes for the INTEGRATOR

### 1. `backend/om/db/models.py` (WS-D owns the standard-answer model block)

The SA answer/category/association models already existed in the folded baseline; WS-D wrapped
them in `# === WS-D: standard answers … ===` banners (clean-room docstrings, **identical schema**)
and added one NEW typed table `StandardAnswerConfig` (`standard_answer_config`). No other WS touches
these classes. Nothing to merge beyond keeping the WS-D block.

### 2. `backend/om/main.py` (WS-D delivers routers; integrator wires)

Register the two new routers and **remove** the old standard-answer router import + registration.

```diff
- from om.server.manage.standard_answer import router as standard_answer_router
+ from om.standard_answers.api import admin_router as standard_answer_admin_router
+ from om.standard_answers.api import query_router as standard_answer_query_router
```
```diff
- include_router_with_global_prefix_prepended(application, standard_answer_router)
+ include_router_with_global_prefix_prepended(application, standard_answer_admin_router)
+ include_router_with_global_prefix_prepended(application, standard_answer_query_router)
```

The admin router keeps prefix `/nexus` and paths `/admin/standard-answer…` (unchanged public
contract `/api/nexus/…`). The query router keeps `GET /query/standard-answer`. Both use the standard
`current_admin_user` / `current_user` auth deps (recognised by `check_router_auth`).

**Net-new routes** (no old equivalent → not in the route-rename `before/` snapshots):
`DELETE /admin/standard-answer/category/{id}` (guarded delete) and `GET`/`PUT
/admin/standard-answer/config`. All admin-gated → no `auth_check` public entries.

### 3. `backend/om/server/query_and_chat/query_backend.py` (remove old query endpoint)

Delete the old `GET /standard-answer` route (`get_standard_answer`), the `StandardAnswerRequest` /
`StandardAnswerResponse` models, and the `from …handle_standard_answers import oneoff_standard_answers`
import — the endpoint now lives in `om/standard_answers/api.py::query_router`.

### 4. `backend/om/onyxbot/slack/handlers/handle_message.py` (repoint the handler)

```diff
- from om.onyxbot.slack.handlers.handle_standard_answers import handle_standard_answers
+ from om.standard_answers.slack_handler import handle_standard_answers
```
The call site is unchanged — WS-D's `handle_standard_answers(message_info, receiver_ids,
slack_channel_config, logger, client, db_session) -> bool` keeps the exact signature.

### 5. `backend/om/server/seeding.py` (repoint the default-category seed)

```diff
- from om.db.standard_answer import create_initial_default_standard_answer_category
+ from om.standard_answers.service import StandardAnswerService
```
Replace the `create_initial_default_standard_answer_category(db_session)` call in `seed_db()` with
`StandardAnswerService(db_session).ensure_default_category()` (idempotently seeds the id=0 "General"
category, same behaviour).

### 6. `backend/om/server/auth_check.py`

No new **public** endpoints — every WS-D route is `current_admin_user` or `current_user` gated. No
entries to add. (When the old `db/standard_answer.py` / `server/manage/standard_answer.py` are deleted,
no auth_check specs referenced them.)

### 7. Alembic

`wsd_standard_answer_config.py` (revision `wsd_standard_answer_config`, `down_revision =
"0003_agent_rename"` placeholder) creates only the NEW `standard_answer_config` table (the SA answer/
category/assoc tables already exist in `0001_baseline_schema`). **Integrator:** re-point `down_revision`
to the preceding revision in the linearized Wave-1 chain. Per-tenant schema — not `public`. Do NOT run
`alembic upgrade` by hand (backend applies on restart).

### 8. Contract-3 facade shim — `backend/om/tenancy/context.py`

WS-D added a standalone stand-in re-exporting the real primitives (`sql_engine.get_session` →
`get_tenant_session_dependency`, `get_current_tenant_id`, `get_current_tenant_session`,
`get_tenant_session`, `get_shared_schema_session`, `CURRENT_TENANT_ID_CONTEXTVAR`) so the worktree
imports/tests standalone. **On merge, DELETE this shim and keep WS-M's canonical
`om/tenancy/context.py`** — exported names are identical.

## Deleted in phase 4 (DONE in this worktree)

- `backend/om/onyxbot/slack/handlers/handle_standard_answers.py`
- `backend/om/db/standard_answer.py`
- `backend/om/server/manage/standard_answer.py`
- `web/src/app/admin/standard-answer/` (old singular route dir)

All shared-file repoints above (sections 2–5, 8) are **already applied in the `rewrite/ws-d` worktree**
so it is self-consistent and verifiable (WS-A precedent); presented as WS-D-owned edits for the
integrator to merge. `query_backend.py` also had its now-orphaned `HTTPException`/`BaseModel`/`Field`
imports removed.

### NOT deleted — deliberate

- **`backend/om/server/manage/models.py` SA DTOs:** `StandardAnswerCategory` DTO is still referenced by
  the SlackBot/SlackChannelConfig DTOs in the same file (L329/L350) → **KEPT**. The other three
  (`StandardAnswer`, `StandardAnswerCreationRequest`, `StandardAnswerCategoryCreationRequest`) plus their
  now-orphaned imports (`import re`, `from typing import Any`, `StandardAnswer as StandardAnswerModel`)
  were **PRUNED** in the review follow-up (my API uses `om/standard_answers/schemas.py`). Verified: zero
  references across `backend/`, file compiles, `re`/`Any`/`StandardAnswerModel` have no residual use.
- **`web/src/components/standardAnswers/`** — used by the Slack bot channel-config screens
  (`admin/bots/[bot-id]/channels/*`) to assign categories to channels. **Keep.**
- **`web/src/sections/sidebar/AdminSidebar.tsx`** — dead legacy sidebar carrying a stale
  `/admin/standard-answer` link. **WS-A already deletes this whole file**, so WS-D left it untouched to
  avoid a merge conflict. (`web/src/proxy.ts` has a cosmetic comment mentioning the old route — harmless.)

## Snapshots to recapture (do NOT hand-edit — integrator, full env)

- `backend/tests/route_rename/snapshots/before/*standard_answer*.json` — route metadata for the SA
  endpoints changes (router moved module; new config routes added). Regenerate after wiring.

## Frontend (menu + page)

New clean-room admin screen at **`web/src/app/admin/standard-answers/`** (plural — own page dir):
- `page.tsx` — list (search + category filter + pagination + delete-confirm), the feature-config
  panel, mode badges, role-gated via `useUser()` (admin **or** curator).
- `ConfigPanel.tsx` — enabled `Switch` + max-matches / char-limit inputs + Save, backed by
  `GET/PUT /api/nexus/admin/standard-answer/config`.
- `StandardAnswerForm.tsx` — create/edit (Formik + `@/components/Field` + `MultiSelectDropdown`).
- `new/page.tsx`, `[id]/page.tsx` — server pages (`fetchSS` list + categories; edit finds by id since
  there is no admin GET-by-id).
- `lib.ts` / `hooks.ts` — API client + SWR (paths unchanged: `/api/nexus/admin/standard-answer…`).
- Design system: VertualAI components + accent CSS vars (`--virtualai-accent`, `--theme-primary-05`)
  for the badge/dot; no hardcoded accent colors. `react-markdown` is v9 → wrap in a `div` for `prose`
  classes (no `className` on `<ReactMarkdown>`).

Menu — `web/src/components/admin/adminNavItems.ts` (WS-D-owned edit; integrator applies):
```diff
  agentItems.push({
-   name: "Curated Responses",
+   name: "Standard Answers",
    icon: ClipboardIcon,
-   link: "/admin/standard-answer",
+   link: "/admin/standard-answers",
  });
```
```diff
- "standard-answer": "Curated Responses",
+ "standard-answers": "Standard Answers",
```
```diff
- ["/admin/standard-answer", "purple"],
+ ["/admin/standard-answers", "purple"],
```
Shown to admin + curator (unconditional push inside `getAdminNavGroups`, which only runs for those
roles); the page also self-guards.

**KEEP** `web/src/components/standardAnswers/` (`getStandardAnswerCategories`,
`StandardAnswerCategoryDropdownField`, `StandardAnswerCategoryResponse`) — these are used by the Slack
bot channel-config screens (`admin/bots/[bot-id]/channels/*`) to assign categories to channels, which
is part of this feature. Only the old **route dir** `web/src/app/admin/standard-answer/` (singular) is
deleted.

**tsc gate:** the fresh worktree has no `node_modules`, so `tsc`/`next build` is the integrator's gate.
All imports/prop-shapes were verified against the real component sources (`Switch`, `Modal`, refresh
`Button` extends `ButtonHTMLAttributes`, `useUser` returns `isAdmin`/`isCurator`, `AdminPageTitle`
has `description`, `@/components/Field` exports, `MultiSelectDropdown` is controlled not Formik-bound).
