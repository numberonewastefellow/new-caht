# WS-D — Standard answers (clean-room) — status log

Worktree: `.claude/worktrees/ws-d` (branch `rewrite/ws-d` off `rename_onyx_to_om`).
Replaces the Onyx-EE Slack "standard answers" feature (keyword/regex canned answers + categories):
`onyxbot/slack/handlers/handle_standard_answers.py`, `db/standard_answer.py`,
`server/manage/standard_answer.py`, the `StandardAnswer`/`StandardAnswerCategory` models + assoc
tables, and the `/query/standard-answer` endpoint on `query_backend.py`.

Phase plan:
- P0 Setup + research: worktree, read CONTRACTS.md + WS-D, graphify orient, map integration surface,
  research canned-response / keyword-match / ReDoS-safety patterns.
- P1 Tables + matching engine + CRUD service (clean-room `om/standard_answers/`). Review: regex/keyword
  matching correct + safe (no catastrophic backtracking); tenant-scoped.
- P2 Slack handler + query endpoint. Review: thread de-dup; block rendering; synthetic chat records.
- P3 Admin UI + "Standard Answers" menu entry. Review: VertualAI design system; role-gating.
- P4 Delete old handler/db/manage files + verify; structured logs present.

---

- [P0] Started: read `CONTRACTS.md` + `WS-D-standard-answers.md` in full. Worktree created
  (`.claude/worktrees/ws-d`, branch `rewrite/ws-d` off `rename_onyx_to_om`). All edits happen inside
  the worktree; centralized status appended here in the main tree.
- [P0] graphify orient (`query`/`explain StandardAnswer`) located the EE-origin surface:
  `backend/om/db/standard_answer.py`, `backend/om/server/manage/standard_answer.py`,
  `backend/om/onyxbot/slack/handlers/handle_standard_answers.py` (`oneoff_standard_answers` L48),
  models `StandardAnswer`/`StandardAnswerCategory` in `backend/om/db/models.py` (~L3922) + Pydantic
  DTOs in `backend/om/server/manage/models.py` (~L443-490), seeding hook
  `create_initial_default_standard_answer_category` in `backend/om/server/seeding.py`.
- [P0] Clean-room discipline: current merged `backend/om/**` files are read ONLY for the public
  integration surface (what to delete + who imports + table/column names to drop + frontend API
  contract); the original Onyx EE checkout at `D:\llm\danswer07022026_original` is NOT opened. All new
  matching logic / control flow / module layout is authored from the WS-D behavior spec.
- [P0] Research (Standard 2) — recorded in module README:
  - **ReDoS / catastrophic backtracking**: backtracking NFA engines (Python `re`) explode to O(2^n)
    on "evil" shapes — nested/overlapping quantifiers `(a+)+`, `(a|a)*`, quantified optional groups.
    A single crafted admin regex against unbounded input can hang a worker. Mitigations adopted:
    (1) **validate at CRUD** — compile for syntax + a static evil-shape heuristic (reject nested
    quantifiers); (2) **cap input length** before matching; (3) prefer **linear-time RE2**
    (`google-re2`) when importable, else stdlib `re` on the already-validated + length-capped pattern,
    always in try/except. Sources: Snyk ReDoS guide, regular-expressions.info/redos, google/re2,
    pyre2/google-re2.
  - **Matching UX** (One-Match / All-Match categories research; chatbot.com keyword system): default to
    **token/keyword matching** (safer than regex); support **match-any** (any keyword present) vs
    **match-all** (every keyword present) modes, plus an explicit **regex** opt-in per answer.
    Category tagging scopes which answers a given Slack channel considers.
- [P0] Dispatched an Explore agent to produce the full integration-surface map (models/DTOs/endpoints/
  DB service signatures/Slack call site/query endpoint/tenancy Contract-3 exports/config-table
  pattern/structured-logger/admin-menu registry/existing FE page/seeding). Awaiting map before P1.

- [P1] DONE + reviewed. Clean-room module `backend/om/standard_answers/`:
  - `safe_regex.py` — ReDoS defence: write-time `validate_pattern` (syntax + evil-shape
    heuristic rejecting nested/overlapping quantifiers + length bound), `SafeRegex` bounded/
    fail-closed matcher, linear-time RE2 (`google-re2`) preferred when importable else stdlib `re`
    on length-capped input (`MAX_MATCH_INPUT_CHARS=8000`).
  - `matching.py` — pure engine on `AnswerRule` value objects: regex mode (SafeRegex) + keyword
    mode (tokenized, case-insensitive, lookaround word-boundary, all/any). Fail-closed on empty/
    unsafe. No ORM/tenancy coupling.
  - `events.py` — structured OpenSearch event logger (net-new; repo had none): `emit_event` +
    `logged_operation` ctx-mgr emit `event/entity/entity_id/tenant_id/actor_user_id/action/status/
    duration_ms/error` as one JSON line prefixed `standard_answer_event `; always try/except so
    instrumentation can't break the op; tenant_id auto from Contract-3 contextvar.
  - `repository.py` — `StandardAnswerRepository` + `StandardAnswerCategoryRepository` (pure DB,
    tenant-scoping inherited from the session; never commit).
  - `service.py` — `StandardAnswerService`: CRUD + validation (non-empty keyword/answer, regex
    safety, category existence, name length) + soft delete + matching (`match_by_category_ids/names`,
    emits `matched`) + per-tenant config get/update. Owns the transaction; structured events on every
    mutation.
  - `config.py` — accessors for the singleton per-tenant `standard_answer_config` (typed table).
  - `schemas.py` — Pydantic DTOs preserving the frozen frontend contract (StandardAnswer,
    StandardAnswerCreationRequest{≥1 category}, StandardAnswerCategory, config + query DTOs).
  - Models: `db/models.py` SA block wrapped in `# === WS-D … ===` banners (clean-room docstrings,
    identical schema — tables pre-exist in `0001_baseline_schema`) + NEW typed `StandardAnswerConfig`
    table. Migration `alembic/versions/wsd_standard_answer_config.py` (rev `wsd_standard_answer_config`,
    down_revision `0003_agent_rename` placeholder) creates only the new config table.
  - Contract-3: added standalone facade shim `om/tenancy/context.py` re-exporting the real primitives
    (`sql_engine.get_session` → `get_tenant_session_dependency`, `get_current_tenant_id`, …). INTEGRATOR:
    delete in favour of WS-M's canonical facade on merge (identical exports).
  - **Verification:** 41 unit tests pass (`tests/unit/om/standard_answers/`): safe_regex (evil-shape
    rejection, length cap, case), matching (all/any, boundary, regex, fail-closed), and service+repository
    CRUD/matching/config end-to-end on in-memory SQLite. `om.db.models` + full service stack import clean
    (DB deps present in this env). **Review gate PASS:** matching correct + ReDoS-safe; every query runs on
    the tenant-bound session; structured events on all mutations + match.
  - Deferred to API layer (P2): map IntegrityError from the `unique_keyword_active` partial index
    (duplicate active keyword on create/update) → 400/409.

- [P2] DONE + reviewed. Slack handler + query/admin API (clean-room):
  - `blocks.py` — `build_answer_blocks(answers)` → per-answer `SectionBlock`(markdown) +
    `ActionsBlock`["Generate Full Answer" `ButtonElement` action_id=`GENERATE_ANSWER_BUTTON_ACTION_ID`],
    dividers between. Button carries no value (existing button router reads thread context), so it
    stays compatible with the un-rewritten `handle_buttons.py`.
  - `slack_handler.py` — `handle_standard_answers(message_info, receiver_ids, slack_channel_config,
    logger, client, db_session) -> bool` (SAME signature as the old handler → 1-line import repoint at
    the `handle_message.py` call site). Flow: config feature-gate → extract text → channel categories
    (`slack_channel_config.standard_answer_categories`) → match (input truncated to config limit) →
    **thread de-dup** (`_already_used_answer_ids` scans all chat sessions for the slack thread and their
    `chat_message.standard_answers` links) → cap to `max_matches_per_message` → post blocks
    (`respond_in_thread_or_channel`) → **record synthetic chat** (reuse/create onyxbot chat session,
    root+user+assistant messages, link posted answers via `assistant.standard_answers`) → clear the
    "eyes" processing react (`OM_BOT_REACT_EMOJI`, skip for slash cmds). Post failure → False (no
    double answer); record/react best-effort after a successful post. `oneoff_standard_answers(message,
    slack_bot_categories, db_session)` = stateless variant (DTOs) behind the query endpoint.
  - `api.py` — `admin_router` (prefix `/nexus`, `current_admin_user`): POST/GET `/admin/standard-answer`,
    PATCH/DELETE `/admin/standard-answer/{id}`, POST/GET `/admin/standard-answer/category`, PATCH
    `/admin/standard-answer/category/{id}`, GET/PUT `/admin/standard-answer/config` (new feature-toggle).
    `query_router` (prefix `/query`, `current_user`): GET `/standard-answer`. Paths preserve the existing
    frontend contract (`/api/nexus/admin/standard-answer…`). Domain errors mapped: Invalid→400,
    NotFound→404, IntegrityError(dup active keyword / dup category name)→400. Uses the standard
    `current_admin_user`/`current_user` auth deps (avoids WS-M's check_router_auth custom-dep pitfall)
    and the Contract-3 session dep.
  - **Verification:** 45 unit tests pass (added handler tests: happy-path post+record+react, no-match,
    disabled-config short-circuit, thread-dedup skip; + `build_answer_blocks` structure). All Phase-2
    files `py_compile` clean; slack_sdk block symbols + `MessageType`/`OM_BOT_REACT_EMOJI`/
    `GENERATE_ANSWER_BUTTON_ACTION_ID` + all `om.db.chat` helper signatures verified against real source.
    Full router import needs backend optional deps (braintrust/posthog) absent in the partial local
    Python → integrator Docker gate (matches sibling WS-A/WS-C precedent). **Review gate PASS:** thread
    de-dup correct; block rendering correct; synthetic chat records written + answers linked.

- [P3] DONE + reviewed. Admin UI + menu (VertualAI design system). New clean-room page dir
  `web/src/app/admin/standard-answers/` (plural — own dir):
  - `page.tsx` — polished list: search, category-filter pills, pagination, delete-confirm, mode badges
    (Regex / Match any / Match all) using accent CSS vars; **role-gated** via `useUser()` (admin OR
    curator) with a restricted fallback.
  - `ConfigPanel.tsx` — the feature toggle: `Switch` (enabled) + max-matches / char-limit inputs + Save,
    backed by `GET/PUT /nexus/admin/standard-answer/config`.
  - `StandardAnswerForm.tsx` — create/edit (Formik + `@/components/Field` + `MultiSelectDropdown`,
    regex-vs-keyword + any/all UX). `new/page.tsx` + `[id]/page.tsx` server pages (fetchSS list+cats).
  - `lib.ts` / `hooks.ts` — API client + SWR; paths unchanged (`/api/nexus/admin/standard-answer…`).
  - Menu: `adminNavItems.ts` entry relabeled **"Standard Answers"** → `/admin/standard-answers` (+ label
    & route-color maps); visible to admin+curator. Design rules honoured: VertualAI components +
    `--virtualai-accent`/`--theme-primary-05`, no hardcoded accent colors; `react-markdown` v9 → `prose`
    via wrapper `div` (no `className` on `<ReactMarkdown>`).
  - **Review gate PASS:** design-system + accent vars; role-gating (page + menu). All imports/prop-shapes
    verified against real component sources (Switch, Modal, refresh Button extends ButtonHTMLAttributes,
    useUser→isAdmin/isCurator, AdminPageTitle.description, Field exports, MultiSelectDropdown controlled).
    `tsc`/`next build` = integrator gate (fresh worktree has no node_modules).

- [P4] DONE + reviewed. Deleted old + verified.
  - **Deleted** (3 backend + 1 FE route dir): `onyxbot/slack/handlers/handle_standard_answers.py`,
    `db/standard_answer.py`, `server/manage/standard_answer.py`, and `web/src/app/admin/standard-answer/`.
  - **Repointed importers (applied in-worktree, WS-A precedent; documented for integrator):**
    `handle_message.py` (→ `om.standard_answers.slack_handler`), `seeding.py` (→
    `StandardAnswerService.ensure_default_category`), `db/slack_channel_config.py` (2 lazy imports →
    `om.standard_answers.repository.fetch_standard_answer_categories_by_ids` compat helper),
    `main.py` (old `standard_answer_router` → `admin_router` + `query_router`), `query_backend.py`
    (removed old `GET /standard-answer` + `StandardAnswerRequest/Response` + now-orphaned
    `HTTPException`/`BaseModel`/`Field` imports).
  - **Kept intentionally:** `server/manage/models.py` SA DTOs (`StandardAnswerCategory` still used by the
    SlackBot/SlackChannelConfig DTOs at L329/L350; the other 3 are now dead → flagged prunable for the
    integrator). `web/src/components/standardAnswers/` (used by Slack bot channel-config screens).
    `web/src/sections/sidebar/AdminSidebar.tsx` (dead legacy sidebar with a stale `/admin/standard-answer`
    link — **WS-A deletes this file**, so left untouched to avoid a merge conflict). `proxy.ts` comment
    mentioning the old route (cosmetic).
  - **Verification:** grep confirms ZERO dangling refs to deleted backend modules or the deleted FE dir;
    all 9 modified/new backend files `py_compile` clean; no orphaned imports; **48 unit tests pass**
    (added `test_events.py`: structured events carry all mandated fields, success/error emit + re-raise,
    emit never raises). **Review gate PASS:** end-to-end match→post verified via mock-Slack handler test;
    structured logs present + correct. Full multi-tenant Postgres boot + live-Slack = integrator Docker gate.

**WS-D COMPLETE.** No commit/push performed (per instructions). Integrator hand-off:
`rewrite-plans/notes/WS-D-README.md`. Module reference: `backend/om/standard_answers/README.md`.

- [REVIEW] Rigorous self-review vs CONTRACTS.md + WS-D plan + the 12 standards. Re-read both in full.
  **Phase checklist:** P0 orient/research ✓ · P1 tables+matching+CRUD ✓ · P2 handler+blocks+query+API ✓ ·
  P3 admin UI+menu ✓ · P4 delete-old+verify ✓ — all DONE (no missed/partial phases). Contracts: C3
  tenant-scoped throughout (every query on the injected tenant session; per-tenant config; tenant_id in
  every log) ✓; C2 Access API correctly NOT used (canned-answer matching is not document-ACL-filtered;
  no RBAC/Access internals imported) ✓; C1 N/A to WS-D ✓.
  **Gaps found + fixed (7):**
  1. **Category delete missing** — plan says "CRUD ... categories" but categories only had C/R/U (and
     `SAEvent.CATEGORY_DELETED` was an unused enum). Added a **reference-guarded** `delete_category`
     (blocks the default id=0 and any category in use by answers/channels via `reference_counts`
     COUNT-on-assoc), `DELETE /admin/standard-answer/category/{id}` (404/400/IntegrityError mapped), a
     FE "Categories" management card (guarded delete, default hidden), and 4 unit tests.
  2. **N+1 queries** — `from_model`/`_to_rule` lazy-loaded `.categories` per row; added
     `selectinload(StandardAnswer.categories)` to `list_active` + `list_active_in_categories`.
  3. **RE2 branch bug** — google-re2 `compile(pattern, flags, options)` takes `options` 3rd, so the old
     positional `compile(pattern, options)` bound it to `flags`. Switched to the documented drop-in flags
     API (`re2.IGNORECASE`); the untested branch is now correct.
  4. **Singleton-config insert race** — two first-time `update_config` calls could both INSERT id=1;
     `get_or_create_config` now inserts inside a SAVEPOINT (`begin_nested`) and re-fetches on
     IntegrityError, leaving the caller's transaction intact.
  5. **Empty-post guard** — a misconfigured `max_matches_per_message<=0` (bypassing the API's `ge=1`)
     could post an empty Slack message; added a post-slice `if not new_answers: return False`.
  6. **mypy-strict hygiene** — made the `_CompiledMatcher.search` param positional-only (`/`) so
     `re.Pattern` structurally conforms; loaded optional `re2` as `Any` to drop the `# type: ignore`
     churn (avoids `warn_unused_ignores`); removed the write-only `_uses_re2` dead field.
  7. **Category delete efficiency/correctness** — delete via Core `DELETE` (not `session.delete`) so it
     doesn't load m2m collections; DB FK is the race backstop.
  **Bug/edge review (no change needed):** all new endpoints auth-gated (admin/user); no missing None/empty
  handling (matcher fail-closed, empty message/keyword guarded); IntegrityError→400 on all mutating admin
  routes; migration single linear head (`wsd_standard_answer_config`←`0003_agent_rename`); zero hardcoded
  accent hex in FE (CSS vars only); structured events on every create/update/delete/match/config in
  try/except; all functions annotated (`disallow_untyped_defs`); no unused imports/args (dummy `_`
  ARG-exempt); grep confirms zero leftover refs to deleted EE modules.
  **Verification:** `py_compile` clean on all 10 changed backend files; **52 unit tests pass** (was 48;
  +4 category-delete); `om.db.models` + full service stack import clean. mypy/ruff not installed locally
  (integrator CI gate) — held code to `disallow_untyped_defs`/ARG/F manually. `tsc` = integrator gate
  (no node_modules); FE additions use only verified components/props. No commit; no `alembic upgrade`.

- [REVIEW-FOLLOWUP] Pruned dead code in `server/manage/models.py`: removed the 3 now-unused SA DTOs
  (`StandardAnswer`, `StandardAnswerCreationRequest`, `StandardAnswerCategoryCreationRequest`) + their
  orphaned imports (`import re`, `from typing import Any`, `StandardAnswer as StandardAnswerModel`). KEPT
  `StandardAnswerCategory` DTO (used by SlackBot/SlackChannelConfig DTOs L329/L350) + `field_validator`/
  `model_validator`/`StandardAnswerCategoryModel` (used elsewhere). Verified: `py_compile` clean; grep =
  zero refs to the removed classes across `backend/` + zero residual `re`/`Any`/`StandardAnswerModel` in
  the file; **standard_answers suite still 52 passed**. Full import of `manage.models` fails only on a
  pre-existing missing dep (`aioboto3` via the untouched `SavedSearchSettings` import) → integrator gate,
  not a NameError for any removed symbol. `test_slack_gating.py` errors are ALSO pre-existing env issues
  (missing `mistune`/`aioboto3` block `om.onyxbot.slack.blocks`/`handle_message` import → `@patch` targets
  unresolvable), NOT caused by this change — proven: my `om.standard_answers.slack_handler` imports clean,
  and `handle_message` breaks at line 12 (blocks→formatting→`mistune`), code I never touched. No commit.
