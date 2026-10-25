# Fresh-install fix, folded renames, build hardening (log)

Date: 2026-10-25. Triggered by a finding during Phase 3: a brand-new environment could not be installed.

## 1. Root cause
`0001_baseline_schema` sent its 6,945-line, ~770-statement SQL file to Postgres in one call. Alembic runs through
asyncpg (prepared statements: one command per call), so an empty database failed with "cannot insert multiple commands
into a prepared statement". Existing databases never hit it because they were already past 0001. Reproduced on the
Phase 2 image, so it predates the rename work.

## 2. Fix A1: run the baseline one statement at a time
`0001_baseline_schema.py` carries its own splitter (`_split_statements`: single quotes, double quotes, `--` and
`/* */` comments, `$$`/`$tag$` bodies). Deliberately **inside the migration**: a migration must not import application code,
because moving that code would silently change old migrations. Tests: `tests/unit/migration_safety/test_baseline_sql_split.py`
(6 tests, loads the migration by file path, lossless round trip of the real baseline).

## 3. Fix A2: renames folded into the baseline
`0001_baseline_schema.sql` is regenerated **from a database** (never by text substitution: `0004_team_rename` also widens
team ids to BIGINT). Reproducible with `rename-audit/gen_baseline_sql.py`:
old baseline -> real `0003_agent_rename` + `0004_team_rename` + `0008` SQL on a scratch Postgres 15.2 -> `pg_dump` -> generator.
The committed file is byte-identical to the generator output. A fresh install now creates `agent`, `team`, `ombot_flow`
directly. Revisions `0003`, `0004_team_rename`, `0008` check the catalog and skip themselves when the final names already
exist (inline 3-line checks). Revision ids/order unchanged, so every existing database upgrades normally.

Two bugs found by the test matrix and fixed in the generator before the file was committed:
- the dump carried `alembic_version` (it existed only because of `alembic stamp` in the scratch DB);
- `public.gin_trgm_ops` / `public.show_trgm` must stay schema-qualified: tenant schemas have only themselves on the
  search_path and cannot resolve pg_trgm objects otherwise. Only the second-schema test caught this.

## 4. Migration matrix (`rename-audit/migration_matrix.sh`, throwaway containers, working-tree migrations mounted over the image)
| Route | Result |
|---|---|
| A. empty DB -> head (new baseline) | 17 upgrades, 0 errors, re-run is a no-op |
| D. legacy DB (old baseline, stamped 0001) -> head | 16 upgrades, renames still apply |
| E. mid-history (0001 -> 0003 genuinely run, then head) | 14 upgrades |
| F. copy of the live DB at 0008 -> head | 0 upgrades, 368 chat sessions intact |
| G. second schema (`-x schemas=tenant_test`) | 17 upgrades, `ombot_flow`, 1 agent, 11 tools |
Schema (`pg_dump -s`) of A, D, E identical to the old-baseline reference: 0 differing lines. Seed data identical (0 differing lines).
Against the live dev DB: identical except one `COMMENT ON SCHEMA public` line that exists only there.
`user_tenant_mapping` is intentionally public-only (121 tables in a tenant schema vs 122 in public).

## 5. Full first-install stack (`docker compose -p om-fresh`, empty volumes, ports 3100/8180, torn down afterwards)
Base compose pins fixed volume names (`onyx-stack_*`), so the override renames every volume; otherwise the "fresh" stack would
silently reuse old data. Result: all 17 revisions ran on first start, 122 tables, API healthy (OpenSearch setup succeeded on
attempt 2 of its built-in retry), **15/15 API checks**: first registered user is admin, agent created (id 1), chat session
created and listed (exercises `ombot_flow`), query-history, admin pages, workflow list. Done twice (second time from `down -v`).
Observations, not bugs: a fresh install has no LLM provider, so `GET /converse/max-selected-document-tokens` returns 400
"No default LLM model found" until one is configured; nginx requires the `phoenix` service to be running (its generated
upstream config fails otherwise), fine for the normal full `up`.

## 6. Browser smoke (headless Chromium, light + dark, 12 pages each, real login form)
All pages load, title "VertualAI", **0 occurrences of "Onyx" in page text**, no 5xx/404 responses. Console: only the site's own
CSP blocking the Google Fonts stylesheet (pre-existing; `next.config.js` change was only the package rename). Screenshots in
`D:\tmp\p1\screens\` (outside the repo).

## 7. Build hardening
- `web/Dockerfile`: npm fetch retries/timeouts + `RUN --mount=type=cache,target=/root/.npm npm ci`.
- `backend/Dockerfile`: uv cache mount + `UV_HTTP_TIMEOUT=180`, `UV_LINK_MODE=copy`. First attempt failed all 3 retries for a
  **non-network** reason of my own making: the cleanup step ran `rm -rf ~/.cache/uv`, which is now a mount ("Device or resource
  busy"). Removed from the cleanup. Lesson: the retry wrapper cannot help with deterministic failures, and 3 identical failures
  are the signal to read the log.
- `deployment/docker_compose/build_retry.sh` / `.bat`: retry per service, `BUILD_ATTEMPTS` / `BUILD_RETRY_DELAY`.
- **Measured, honestly:** the cache mount does NOT make `npm ci` faster here. A forced `--no-cache` rebuild with a warm mount took
  about 5 minutes (first cold run about 3); the time is dominated by unpacking 1,236 packages on this machine, not by downloading.
  The benefit is resilience (retries/timeouts, and a retried build resumes from cached tarballs), not speed. Web builds succeeded
  3 times in a row with the new Dockerfile; the earlier failures (EIDLETIMEOUT, "Exit handler never called") did not recur,
  but 3 runs cannot prove the network flakiness is fixed.

## 8. Live dev stack
New backend image deployed; no migrations ran (already at head); revision `0008_ombot_flow_rename`; 368 sessions;
api healthy; background 7 supervisor programs RUNNING; `/api/versions` and login page 200.

## 9. Unit tests
19 failed / 1563 passed; failure set identical to the pre-change baseline. `migration_safety` 28 passed (+6 new split tests).
