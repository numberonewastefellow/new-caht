# WS-D — Standard answers (clean-room)

## ▶ AGENT INSTRUCTIONS — START HERE (read this whole block first)

**You were pointed at this file to IMPLEMENT workstream WS-D. Do exactly this:**

0. **DUPLICATE CHECK — before anything.** If `.claude/worktrees/ws-d` already exists OR
   `rewrite-plans/status/WS-D.md` already has status lines from another agent, another agent owns WS-D:
   **STOP, report "WS-D already in progress — standing down", make NO changes.** Otherwise self-isolate:
   `git worktree add .claude/worktrees/ws-d -b rewrite/ws-d rename_onyx_to_om`
   Working root = `d:\llm\danswer20022026\.claude\worktrees\ws-d`; do ALL edits there, never the main tree.
1. **Read** `rewrite-plans/CONTRACTS.md` (contracts + ownership rules + 12 standards) and the rest of
   THIS file. Use the Access API (Contract 2) for the query endpoint; tenant-safe (Contract 3).
2. **Legal — clean-room.** Behavior spec only. NEVER open/copy/paraphrase Onyx EE source at
   `D:\llm\danswer07022026_original\onyx\backend\ee\...`.
3. **Orient with graphify** before reading source.
4. **Phases + review gates.** TodoWrite; self-review after each phase.
5. **Research first** (canned-response/keyword-match patterns); cite in README.
6. **Standards:** multi-tenant-safe; dedicated config table + admin "Standard Answers" UI; VertualAI
   design system; add a menu entry; structured OpenSearch logs on CRUD/match in try/except; safe regex
   (no catastrophic backtracking); OOP + strict typing.
7. **Delete old handler/db/manage files only in the FINAL phase**, after verify.
8. **Write** a module README.
9. **Progress:** append to `d:\llm\danswer20022026\rewrite-plans\status\WS-D.md` at each phase.
10. **Do NOT commit/push. Do NOT run `alembic upgrade` by hand.** Summarize at the end.

**Wave:** 1. **Emphasis:** standard answers clean-room (Slack canned/keyword answers + categories).

---

> Read `CONTRACTS.md` first. Depends on **Contract 2 (Access API)** (query endpoint) + Contract 3
> (tenant). Follow all Engineering standards. Work in your own worktree.

## Goal
Clean-room reimplementation of the Slack-bot "standard answers" (keyword/regex canned answers with
categories), replacing the Onyx-EE feature.

## Research first (Standard 2)
Web-research canned-response / keyword-matching UX patterns (regex vs token match, category tagging).

## Behavior spec (WHAT — own HOW; do not open Onyx files)
Replaces: `onyxbot/slack/handlers/handle_standard_answers.py`, `db/standard_answer.py`,
`server/manage/standard_answer.py`, and the `/query/standard-answer` endpoint on `query_backend.py`.

- On incoming Slack message: match against active standard answers for the channel's categories
  (regex OR keyword all/any); skip answers already used in the thread; post matched answer(s) as Slack
  blocks with a "Generate Full Answer" button; record a synthetic chat session/messages; react.
- `oneoff_standard_answers`: stateless variant powering the query endpoint.
- Admin CRUD for answers + categories.

## New tables (own names)
- `standard_answer` (keyword, answer, active, match_regex, match_any_keywords) + partial-unique on
  (keyword, active); `standard_answer_category` (name unique); assoc tables answer↔category,
  slack-channel-config↔category, chat-message↔answer.

## Config + UI
- Admin **Standard Answers** screen (VertualAI design system): CRUD answers + categories, assign
  categories to Slack channels. Feature toggle in a **dedicated config table**.
- Update MENU: "Standard Answers" under admin (curator/admin-gated).

## Shared-file snippets (integrator)
- `models.py`: standard-answer model block. `main.py`: standard-answer admin router + `/query/standard-answer`.
- `auth_check.py`: any public entries. Alembic: revisions for the tables.
- Slack listener: hook `handle_standard_answers` into the message path (own wrapper).

## Phases (with review gates)
- **Phase 1 — Tables + matching engine + CRUD service.** **Review:** regex/keyword matching correct +
  safe (no catastrophic regex); tenant-scoped.
- **Phase 2 — Slack handler + query endpoint.** **Review:** thread de-dup; block rendering; synthetic
  chat records.
- **Phase 3 — Admin UI + menu.** **Review:** design-system; role-gating.
- **Phase 4 — Delete old + verify.** Remove old handler/db/manage files. **Review:** end-to-end match →
  post works (mock Slack ok); structured logs present.

## Structured logs (Standard 9)
`event=standard_answer.created|updated|deleted|matched`, `entity=standard_answer|category`, `entity_id`,
`tenant_id`, `actor_user_id`, `action`, `status`, `duration_ms`, `error`.

## Verification
- CRUD works; a Slack message matching a keyword/regex posts the answer; already-used answers skipped.
- Query endpoint returns matches. Tenant-scoped.

## README
`backend/om/.../standard_answers/README.md`: matching model, tables, config/UI, log events, extension.
