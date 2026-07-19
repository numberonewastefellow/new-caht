# Standard Answers (WS-D) — module reference

Clean-room reimplementation of the Slack-bot **standard answers** feature: keyword/
regex canned answers tagged with categories, plus a stateless query endpoint and an
admin UI. Replaces the Onyx-EE originals (`onyxbot/slack/handlers/handle_standard_answers.py`,
`db/standard_answer.py`, `server/manage/standard_answer.py`, and the `/query/standard-answer`
endpoint on `query_backend.py`). Written from the WS-D behavior spec — no Onyx EE source
was opened; module layout, names, and control flow are our own.

## What it does

On an inbound Slack message the bot checks, **before** running a full LLM answer, whether
any active standard answer matches. Answers are scoped by **category**: a Slack channel is
assigned one or more categories, and only answers in those categories are considered. A
match posts the canned answer(s) as Slack blocks with a **"Generate Full Answer"** button
(to escalate to a real LLM answer), records a synthetic chat session/messages for the
thread, and clears the processing reaction. Answers already posted in the same thread are
skipped (de-duplication). The same matching, without side effects, powers the stateless
`GET /query/standard-answer` endpoint.

## Architecture (clean OOP — models / repository / service)

```
om/standard_answers/
├── safe_regex.py    ReDoS-resistant pattern validation + bounded matching
├── matching.py      pure keyword/regex engine over AnswerRule value objects
├── repository.py    StandardAnswer{,Category}Repository — atomic tenant-scoped DB ops
├── service.py       StandardAnswerService — CRUD + validation + matching + config + logging
├── config.py        per-tenant feature-config accessors (dedicated typed table)
├── events.py        structured OpenSearch event logging (emit_event / logged_operation)
├── schemas.py       Pydantic DTOs (frozen frontend/API contract)
├── blocks.py        Slack Block Kit rendering for matched answers
├── slack_handler.py handle_standard_answers (message path) + oneoff_standard_answers (query)
└── api.py           FastAPI admin_router (/nexus) + query_router (/query)
```

Layering: `api` / `slack_handler` → `service` → `repository` → ORM. Matching (`matching`,
`safe_regex`) is pure and dependency-free; `events` and `config` are cross-cutting. The
session is passed down from the transport layer; nothing reaches for a global session.

## Matching model

A `standard_answer` row has a `keyword` trigger plus two mode flags:

| `match_regex` | `match_any_keywords` | Behaviour |
|---|---|---|
| `false` | `true`  | **Any** of the whitespace/comma-separated tokens present (One-Match) |
| `false` | `false` | **All** tokens present (All-Match) |
| `true`  | — | `keyword` is a **regex**, matched case-insensitively |

Keyword tokens match case-insensitively on word boundaries (lookarounds, so `api` does not
fire inside `capitalize`). Empty/whitespace triggers never match (fail-closed).

### ReDoS safety (safe_regex.py)

Admin-authored regexes are only semi-trusted and run on every inbound message, so:

1. **Write-time validation** (`validate_pattern`, called on create/update): syntax check +
   length bound + a heuristic that rejects catastrophic-backtracking shapes (nested
   quantifiers `(a+)+`, overlapping alternation `(a|a)*`). Surfaces a 400 to the admin.
2. **Input length cap** (`MAX_MATCH_INPUT_CHARS = 8000`, mirrored by the per-tenant
   `match_input_char_limit`) before matching — bounds worst-case work regardless of pattern.
3. **Linear-time engine preferred**: uses Google **RE2** (`google-re2`) when importable
   (immune to backtracking), else stdlib `re` on the validated + capped input.
4. **Fail-closed at match time**: any engine error → "no match", never a raise/hang.

## Tables (per-tenant schema — Contract 3)

Pre-existing in the folded baseline `0001_baseline_schema` (WS-D owns the model block; see
the `# === WS-D … ===` banners in `db/models.py`):

- `standard_answer` (`keyword`, `answer`, `active`, `match_regex`, `match_any_keywords`) +
  partial-unique index `unique_keyword_active` on `(keyword, active) WHERE active`.
- `standard_answer_category` (`name` unique).
- `standard_answer__standard_answer_category` (answer ↔ category).
- `slack_channel_config__standard_answer_category` (channel ↔ category — scopes matching).
- `chat_message__standard_answer` (message ↔ answer — thread de-dup source).

New in this rewrite (migration `alembic/versions/wsd_standard_answer_config.py`):

- **`standard_answer_config`** — dedicated typed feature-config table (Engineering Standard 5),
  singleton row `id=1`: `enabled`, `max_matches_per_message`, `match_input_char_limit`,
  timestamps. Read/written via `config.py`; the Slack handler gates on `enabled`.

Deactivation is a **soft delete** (`active=False`); the partial-unique index allows at most
one active answer per keyword while preserving historical inactive rows.

## Config + UI

- Admin **Standard Answers** screen (VertualAI design system): CRUD answers + categories,
  assign categories to Slack channels (via the Slack channel config screen), and the
  feature toggle + matching bounds. Endpoints `GET/PUT /nexus/admin/standard-answer/config`.
- Menu: a **"Standard Answers"** entry under admin (curator/admin-gated) — see the frontend
  section of `rewrite-plans/notes/WS-D-README.md` for the exact `adminNavItems.ts` snippet.

## API

Admin (admin-gated, prefix `/nexus`, public path `/api/nexus/…`):

| Method | Path | Purpose |
|---|---|---|
| POST | `/admin/standard-answer` | create answer |
| GET | `/admin/standard-answer` | list active answers |
| PATCH | `/admin/standard-answer/{id}` | update answer |
| DELETE | `/admin/standard-answer/{id}` | soft-delete answer |
| POST | `/admin/standard-answer/category` | create category |
| GET | `/admin/standard-answer/category` | list categories |
| PATCH | `/admin/standard-answer/category/{id}` | rename category |
| DELETE | `/admin/standard-answer/category/{id}` | delete category (blocked if in use or default) |
| GET | `/admin/standard-answer/config` | read feature config |
| PUT | `/admin/standard-answer/config` | update feature config |

Query (user-gated, prefix `/query`): `GET /query/standard-answer` → matches for a message
scoped to the given category names.

## Structured log events (Standard 9)

`events.py` emits one JSON line per event, prefixed `standard_answer_event `, with fields
`event`, `entity`, `entity_id`, `tenant_id`, `actor_user_id`, `action`, `status`,
`duration_ms`, `error`. Emission is always wrapped in try/except so it can never break the
operation. `tenant_id` is resolved from the Contract-3 contextvar.

Events: `standard_answer.created|updated|deleted|matched`,
`standard_answer.category.created|updated|deleted`, `standard_answer.config.updated`.

## Multi-tenant readiness (Contract 3)

Every DB operation runs on the tenant-bound session injected by the transport layer
(`om.tenancy.context.get_tenant_session_dependency` / the Slack listener's session). No
table sets `{"schema": "public"}`; the config singleton lives in the tenant schema. Every
log line carries `tenant_id`. No cross-tenant reads exist — matching only ever sees rows in
the caller's schema.

## How to extend

- **New match mode** (e.g. semantic/embedding match): add a mode flag + a branch in
  `StandardAnswerMatcher.matches`; keep it pure and add a fail-closed path.
- **New channel scoping** (beyond categories): the handler resolves candidates via
  `service.match_by_category_ids`; add an alternate resolver and a matching repository query.
- **New config knob**: add a typed column to `StandardAnswerConfig` + a migration, expose it
  in `schemas.StandardAnswerConfigUpdateRequest` and the config endpoint.
- **New event**: add a member to `events.SAEvent` and call `emit_event` / `logged_operation`.

## Research that informed the design

- **ReDoS / catastrophic backtracking**: Snyk ReDoS guide; regular-expressions.info/redos;
  google/re2 + `google-re2`/pyre2 (linear-time DFA). → validate-at-write + cap-input +
  prefer-RE2 + fail-closed.
- **Keyword-matching UX**: "One-Match and All-Match Categories for Keywords Matching in
  Chatbot"; chatbot.com keyword system. → default to token matching, offer any/all modes +
  an explicit regex opt-in, and use category tags to scope per channel.

## Tests

`backend/tests/unit/om/standard_answers/`: `test_safe_regex.py` (evil-shape rejection, input
cap, case), `test_matching.py` (any/all, word boundary, regex, fail-closed, ordering),
`test_service.py` (CRUD + validation + matching + config on SQLite), `test_slack_handler.py`
(post/record/react happy path, no-match, disabled config, thread de-dup). Full multi-tenant
Postgres + live-Slack integration is the integrator's Docker gate.
