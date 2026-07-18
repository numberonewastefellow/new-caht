# Handoff: rename `Persona` → `Agent` (DB + backend + frontend)

> Written for the agent picking up after session compaction. The author just completed two
> analogous renames in this repo (**Project→Workspace** and **UserFile→KnowledgeFile**) — this
> is the same playbook applied to the much larger `Persona` entity. Read "Proven methodology"
> and "Gotchas" before touching code.

## 0. Current repo state (what's already done — don't redo)
- Branch: **`rename_onyx_to_om`** (working directly here, no worktree).
- **Project→Workspace** and **UserFile→KnowledgeFile** renames are COMPLETE + verified: mappers configure, `compileall` clean, frontend `tsc` clean, fresh-DB SQL runs clean.
- Alembic is a **single folded baseline** `0001_baseline_schema` (`revision="0001_baseline_schema"`, `down_revision=None`). The rename was folded directly into `0001_baseline_schema.sql`; there is **no `0002`**. The running dev DB is stamped at `0001_baseline_schema`.
- **`persona__user_file` was already renamed to `persona__knowledge_file`** by the prior work. So in the schema today the persona junction to files is `persona__knowledge_file` (its FK column is `knowledge_file_id`). The persona rename below turns it into `<target>__knowledge_file`.
- User rule: **never commit unless asked**; implement + verify only, user reviews & rebuilds Docker.

## 1. ⚠️ DECISION #1 — the target name (persona → ?)
The codebase is **mid-migration across three terms** — confirm with the user before starting:
- **DB model/table:** `Persona` / `persona` (+ 9 related tables).
- **Some DB tables already say "assistant":** `assistant__user_specific_config` (its FK column is `assistant_id` → `persona(id)`).
- **Frontend already says "Agent":** `AgentEditorPage`, `AgentViewerModal`, `useAgents`, `QuickCreateAgentModal`, and `admin/assistants/`.

Most likely target is **`Agent`** (frontend-driven) or **`Assistant`**. **Ask the user.** Everything below uses `Agent` / `agent` as the placeholder — substitute the confirmed name.

Also confirm (as with the Project rename): do any **AI fields** get workspace-style renames? Persona's AI columns are `system_prompt`, `task_prompt`, `description`, `num_chunks`, `chunks_above/below`, `llm_relevance_filter`, `llm_filter_extraction`, `llm_model_version_override`, `llm_model_provider_override`, `recency_bias`, `max_output_tokens`, `default_model_configuration_id`, `replace_base_system_prompt`. Likely **keep these as-is**; confirm.

## 2. Footprint (grounded — this is LARGE and central)
- Backend: **~230** `Persona` refs, **~235** `persona_id`, across **66 files**.
- Frontend: **~1084** `persona`/`Persona` refs.
- **Recommend running a full multi-agent inventory first** (the prior work used the `Workflow` tool to fan out finders across DB/API/chat/frontend/tests — see the completed plan `~/.claude/plans/we-have-renamed-project-groovy-forest.md` for the exact workflow shape). Persona touches chat, tools, document sets, users/groups, slack/discord bots, workflows, LLM providers, starter messages, labels.

### 2a. Persona tables (10) — from `0001_baseline_schema.sql`
`persona`, `persona__document`, `persona__document_set`, `persona__hierarchy_node`,
`persona__knowledge_file` (already renamed from persona__user_file), `persona__persona_label`,
`persona__tool`, `persona__user`, `persona__user_group`, `llm_provider__persona`, plus `persona_label`.

### 2b. External FK-holders — **NOTE the inconsistent column names**
| Table | FK column → persona(id) |
|---|---|
| `chat_session` | `persona_id` (constraint `fk_chat_session_persona_id`) |
| `agent_workflow_step` | `persona_id` |
| `assistant__user_specific_config` | **`assistant_id`** (already "assistant"-named) |
| `discord_channel_config` | **`persona_override_id`** |
| `discord_guild_config` | **`default_persona_id`** |
| `slack_channel_config` | `persona_id` |
| `llm_provider__persona` | `persona_id` |
| each `persona__*` junction | `persona_id` |

### 2c. `persona`-named columns on the persona table itself (must rename)
`builtin_persona`, `is_default_persona` (both contain "persona").

## 3. ⚠️ SUBSTRING HAZARDS — do NOT rename (a naive sed corrupts these)
`persona` is a prefix of these unrelated identifiers — **exclude them**:
- **`personal_access_token`** (table + ~36 code refs) — "**persona**l_access_token".
- **`personalization`** / `personalization_user_info` — "**persona**lization".
- Any English "personal"/"personalized" in prose/prompts.
- PascalCase hazard too: **`PersonalizationUserInfo`** etc. contain "Persona" as a prefix — a boundary-less `Persona`→`Agent` sed would corrupt them.
- Exclude the vendored `phoenix/` subtree entirely.

## 4. Proven methodology (worked twice — apply exactly)
Work in layers, verifying after each. Use `sed -i` for the bulk, hand-edit the nuanced spots.

1. **`models.py` first (the foundation).** Hand-edit `class Persona` → `class Agent`, all junction classes (`Persona__Tool` → `Agent__Tool`, etc.), `__tablename__`s, the `persona_id`/`assistant_id`/`persona_override_id`/`default_persona_id` FK columns + `ForeignKey("persona.id")` targets, `builtin_persona`/`is_default_persona` columns, and **every `relationship()` + `back_populates` pair in lockstep** (there are many: `Persona.tools`↔`Tool.personas`, `Persona.document_sets`, `Persona.users`, `Persona.groups`, `Persona.labels`, `Persona.knowledge_files`, `ChatSession.persona`↔`Persona.chat_sessions`, `User.personas`, etc.). Mapper config fails at import if any pair is mismatched.
2. **Global PascalCase sed** for `Persona`→`Agent` across `backend/om backend/tests backend/scripts` and `web/src` — **but exclude the `Personal*` hazards** (either anchor patterns or exclude the files/lines). Verify `Personalization`/`PersonalAccessToken` untouched.
3. **snake_case, scoped/excluded:** `persona_id`→`agent_id`, `persona__`→`agent__`, table `persona`→`agent` — **exclude `personal_access_token`, `personalization`**. Handle the odd FK columns individually (`assistant_id`, `persona_override_id`, `default_persona_id`).
4. **Module/dir renames** (`git mv` + update import paths): e.g. `db/persona.py`→`db/agent.py`, `server/features/persona/`→`server/features/agent/`, frontend `admin/assistants/` and `Persona*` components/files. Rename the FILE whenever its basename is a renamed symbol used in an import path (the prior work hit this: `UserFilesModal.tsx` import path broke until the file was renamed).
5. **Keep operational/wire string VALUES** unless the user wants them rotated (celery task/queue names, redis locks, any persisted enum string values, slack/discord config keys). Rename identifiers only.

## 5. Migration approach — RECOMMEND a new `0002` (not another baseline fold)
The baseline was just folded and re-stamped; keep it stable. Add **`0002_persona_rename.py`**, `down_revision="0001_baseline_schema"`, pure `ALTER … RENAME` (table/column/constraint/index/sequence) exactly like the prior `0002` did. Extract the **exact current object names from `0001_baseline_schema.sql`** (grep `persona`) — includes constraint names like `fk_chat_session_persona_id`, `persona__tool_persona_id_fkey`, `agent_workflow_step_persona_id_fkey`, `assistant__user_specific_config_assistant_id_fkey`, plus the `persona_pkey`/sequence. Provide a symmetric `downgrade()`.

**Migration gotchas (learned the hard way):**
- **`alembic_version.version_num` is `varchar(32)`** — keep the revision id short (e.g. `0002_agent_rename`, ≤32 chars). A long id fails at the final version-bump step (whole migration rolls back under transactional DDL).
- **Word-boundary `\bpersona_id\b` sed SKIPS compound constraint names** (`fk_chat_session_persona_id`, `..._persona_id_fkey`). Do a **boundary-less** pass for constraint/index NAMES, *with* the substring-hazard exclusions.
- Rename tables **before** their columns/constraints in the `ALTER` list so later statements resolve.

If instead the user wants to fold into the baseline (fresh-install cleanliness): edit `0001_baseline_schema.sql` with the ordered sed (compound junctions → bare `persona` → `persona_id` → odd FK columns), **excluding `personal`/`personalization`**, then re-stamp the dev DB (`UPDATE alembic_version SET version_num='0001_baseline_schema'`) or wipe. The prior work did exactly this for the workspace fold — see that plan for the verification pattern.

## 6. Verification (exact commands the prior work used — all must pass)
```bash
# 1. ORM mapper config (catches back_populates mismatches immediately)
cd backend && python -c "import om.db.models; from sqlalchemy.orm import configure_mappers; configure_mappers(); print('MAPPERS OK')"
# 2. backend compiles
python -m compileall -q backend/om
# 3. no stray OLD names (excl hazards/keep)
grep -rnE "\bPersona\b|\bpersona_id\b" backend/om --include=*.py | grep -vE "personal_|personalization|phoenix/"
# 4. frontend typecheck (expect only the pre-existing dotenv/playwright error)
cd web && npx tsc --noEmit
# 5. fresh-DB proof (if folding into baseline) — run the SQL on a throwaway db, expect exit 0
docker exec -i virtualai-relational_db-1 psql -U postgres -d fold_test -v ON_ERROR_STOP=1 -q < backend/alembic/versions/0001_baseline_schema.sql
# 6. snapshots regenerate in Docker/CI (route_rename after/, migration_safety baseline.json) — noted, can't do locally
```
Then rebuild: `docker compose up -d --build` (api applies the migration on startup via `alembic upgrade head`, then uvicorn). DB creds for local verify: container `virtualai-relational_db-1`, user `postgres`, password `password`, db `postgres`.

## 7. Sequence for the next agent
1. Confirm target name (Agent vs Assistant) + whether to reconcile the existing `assistant__user_specific_config` naming.
2. (Recommended) run the multi-agent inventory `Workflow` to get the exact per-file list.
3. Do `models.py` → global seds (with hazard exclusions) → module/file renames → frontend.
4. Author `0002_agent_rename.py` (short revision id) from the exact `0001_baseline_schema.sql` object names.
5. Run the full verification block; rebuild Docker.
