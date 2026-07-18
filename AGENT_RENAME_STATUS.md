# Persona → Agent rename — STATUS & HANDOFF

> **Code done + verified. DB migration written + VERIFIED (forward + downgrade, exit 0). Only the
> Docker rebuild (user does this) + post-deploy steps remain.** Branch: `rename_onyx_to_om`.
> Target name **Agent** confirmed by user (chose Agent over Assistant, even after seeing the overload data).
> Full plan: `~/.claude/plans/we-have-renamed-project-groovy-forest.md`. Prior context: `PERSONA_RENAME_HANDOFF.md`.

> **⚠️ MIGRATION RENUMBERED `0002_agent_rename` → `0003_agent_rename`.** A second agent added
> `0002_workspace_soft_delete.py` (adds a `deleted` bool to `workspace`; no persona overlap), which also
> chained off `0001_baseline_schema` → **two alembic heads**. Fixed by linearizing:
> `0001_baseline_schema → 0002_workspace_soft_delete → 0003_agent_rename` (single head verified). The
> agent-rename file is now `backend/alembic/versions/0003_agent_rename.py`, `down_revision="0002_workspace_soft_delete"`.
> DB is still stamped at `0001_baseline_schema`, so the next rebuild applies BOTH 0002 and 0003.

## ✅ DONE + verified this session
- **Backend** (`backend/om`, `backend/tests`, `backend/scripts`): renamed Persona→Agent via a hazard-protected sed
  (protects `personal`/`Personal`/`PERSONAL`, `personalization`, `impersonat`). Did mixed-case, lowercase, AND
  ALL-CAPS (`PERSONA`→`AGENT`) passes. **`compileall` clean, `configure_mappers()` = MAPPERS OK, 0 residual persona** (excl hazards).
  - `git mv` done: `db/persona.py`→`db/agent.py`, `server/features/persona/`→`server/features/agent/`,
    `server/features/build/sandbox/util/persona_mapping.py`→`agent_mapping.py`, test manager `managers/persona.py`→`agent.py`,
    `tests/integration/tests/personas/`→`agents/` (+ test files `test_persona_*`→`test_agent_*`), `test_persona_display_priority.py`, etc.
- **Frontend** (`web/src`): same hazard-protected sed (mixed+lower+CAPS). `git mv`: `PersonaTable.tsx`→`AgentTable.tsx`,
  `PersonaMessagesChart.tsx`→`AgentMessagesChart.tsx`, `hooks/useAdminPersonas.ts`→`useAdminAgents.ts`.
  Fixed one collision: `lib/constants.ts` had a dead duplicate `MAX_CHARACTERS_PERSONA_DESCRIPTION=5000000` that
  collided with the real `MAX_CHARACTERS_AGENT_DESCRIPTION=500` — removed the dead 5000000 line.
  **`npx tsc --noEmit` clean** (only the pre-existing `dotenv`/playwright error remains).
- **Migration GENERATED + VERIFIED**: `backend/alembic/versions/0003_agent_rename.py` — **79 rename pairs**
  (74 persona→agent from the live catalog + 5 for the `assistant__user_specific_config`→`agent__user_specific_config`
  table/column/constraints), `down_revision="0002_workspace_soft_delete"`,
  revision id `0003_agent_rename` (17 chars ≤32). Generated from the LIVE catalog by
  `<scratchpad>/gen_agent_migration.py` (queries pg catalog, excludes `personal*`, transforms `persona`→`agent`,
  renames columns/constraints/indexes/sequences BEFORE tables so FKs auto-repoint).
  **VERIFIED against the real DB (2026-07-19):** all 79 forward stmts ran in a `BEGIN…ROLLBACK` txn = exit 0;
  a forward+downgrade round-trip restored the original schema exactly (`persona` table + `chat_session.persona_id`
  back, `agent` table gone); alembic chain has a single linear head.

## Decisions baked in
- **`assistant__user_specific_config` → `agent__user_specific_config` NOW RENAMED (bounded)** (2026-07-19, user chose
  "rename it"). Table + column `assistant_id`→`agent_id` + 3 constraints renamed in migration `0003` (5 extra pairs,
  now **79** total); ORM class `Assistant__UserSpecificConfig`→`Agent__UserSpecificConfig`, attribute `.agent_id`
  (`models.py`, `db/user_preferences.py`, and the `server/manage/users.py` consumer that read `config.assistant_id`).
  The **broad API wire field `assistant_id` is intentionally KEPT** (chat/preferences endpoints still send/accept it) —
  the ~543 "assistant" product-term refs remain a separate follow-up. Mappers OK; forward+downgrade round-trip verified.
- **OpenSearch field renamed in code**: `PERSONAS_FIELD_NAME`→`AGENTS_FIELD_NAME`, value `"personas"`→`"agents"`
  (`backend/om/document_index/opensearch/schema.py:51`, +search.py/opensearch_document_index.py). **Needs a reindex**
  (existing docs carry the old `personas` field) — dev: fine to drop/reindex, same as the workspace `user_workspaces` case.
- A few persisted string VALUES also changed by the blanket sed (dev: fine to wipe): `PERSONA_SHARED="agent_shared"`
  (was `persona_shared`), `SLACK_BOT_PERSONA_PREFIX="__slack_bot_agent__"` (was `__slack_bot_persona__`).
- DB state right now: dev DB `postgres` is at `0001_baseline_schema` with the **persona** schema still in place
  (this session changed only code + the migration FILE, NOT the DB). Workspace/KnowledgeFile already applied in DB + baseline (prior sessions).
- Container/creds for local checks: `virtualai-relational_db-1`, user `postgres` / pw `password` / db `postgres`.

## ⏳ PENDING — do these next, in order

### 1. ✅ DONE — migration verified (forward + downgrade, exit 0)
Ran all 79 forward statements + a forward→downgrade round-trip against the real DB inside `BEGIN…ROLLBACK`
(`ON_ERROR_STOP=1`) — exit 0, schema restored exactly, single linear alembic head. Nothing more to do here.
Re-run recipe if needed (note the **0003** filename):
```bash
cd /d/llm/danswer20022026
python -c "import ast; t=open('backend/alembic/versions/0003_agent_rename.py').read(); s=t.index('_RENAMES = ['); lit=t[t.index('[',s):t.index('\n]',s)+2]; p=ast.literal_eval(lit); print('BEGIN;'); [print(f+';') for f,_ in p]; print('ROLLBACK;')" > /tmp/agent_mig_test.sql
docker exec -i -e PGPASSWORD=password virtualai-relational_db-1 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f - < /tmp/agent_mig_test.sql 2>&1 | tail -20
```

### 2. ✅ DONE — residual sweeps clean (backend om/tests/scripts = 0 persona tokens, excl hazards). Re-run:
```bash
grep -rnE "\bPersona\b|\bpersona\b|\bPERSONA\b" backend/om --include=*.py | grep -vE "impersonat|personal|Personal|PERSONAL"   # expect 0
cd web && npx tsc --noEmit 2>&1 | grep -vE "playwright|dotenv"   # expect empty
```

### 3. Rebuild + apply  ← FIRST REMAINING STEP (user does this)
`docker compose up -d --build` — the api runs `alembic upgrade head` on startup. DB is at `0001_baseline_schema`,
so it applies BOTH pending migrations in order: `0002_workspace_soft_delete` (adds `workspace.deleted`) then
`0003_agent_rename` (renames persona→agent IN PLACE, data preserved). Rebuild web + workers too (same image).
Watch logs for `Running upgrade 0001_baseline_schema -> 0002_workspace_soft_delete ... done` and
`Running upgrade 0002_workspace_soft_delete -> 0003_agent_rename ... done`.

### 4. Post-deploy
- **OpenSearch reindex** for the `personas`→`agents` field (dev: or just re-upload/drop). Only matters for persona-scoped doc filtering.
- **Regenerate app-derived snapshots** (in Docker/CI): `backend/tests/route_rename/snapshots/after/*` (persona→agent operation ids/paths)
  and `backend/tests/unit/migration_safety/snapshots/baseline.json` (module paths `db/agent`, `features/agent`, celery task names) via `MIGRATION_SNAPSHOT_CAPTURE=1`.
- Per user rule: implement + verify only; **user reviews & rebuilds Docker; no commit unless asked.**

## Gotchas already handled (don't re-hit)
- `alembic_version.version_num` is `varchar(32)` → keep revision id short (done: `0003_agent_rename`, 17 chars).
- **Two heads** (this migration + the other agent's `0002_workspace_soft_delete`, both off `0001_baseline_schema`) →
  linearized by renumbering ours to `0003` with `down_revision="0002_workspace_soft_delete"`. Verified single head.
  If a THIRD sibling migration appears later off `0001`/`0002`, re-linearize the same way (or `alembic merge`).
- Word-boundary sed skips compound constraint names → the migration was generated from the CATALOG (real names), not sed, so it's complete.
- Hazards `personal_access_token` / `personalization_user_info` / `impersonate` are protected everywhere.
- No name collisions: `agent`, `agent_label`, `agent_category*`, `agent_pkey`, `agent_workflow_id_fkey`, `agent_id_seq` were all free (verified).
