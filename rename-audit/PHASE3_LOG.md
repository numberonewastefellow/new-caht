# Phase 3 log: database column `chat_session.onyxbot_flow` -> `ombot_flow`

## What changed
- New revision `backend/alembic/versions/0008_ombot_flow_rename.py` (down_revision `0007_team_enrichment`):
  `ALTER TABLE chat_session RENAME COLUMN onyxbot_flow TO ombot_flow`; downgrade is the reverse. Metadata-only, no data movement.
- ORM attribute and every Python user renamed in the same release: `db/models.py`, `db/chat.py`, `db/chat_search.py`,
  `evals/eval.py`, `standard_answers/slack_handler.py`, `server/query_history/service.py`.
- `0001_baseline_schema.sql` deliberately NOT edited (it creates the original name; 0008 renames it afterwards).
- `rename-audit/live_data_probes.sql` updated to the new name.

## Pre-checks (read-only)
- Live DB has only the `public` schema; one matching column; NOT NULL, no default, no index/constraint/view on it.
- The name appears in no API model, raw SQL or JSON.

## Test evidence
| Check | Result |
|---|---|
| `tests/unit` | 19 failed / 1556 passed; failure set identical to the pre-Phase-2 baseline |
| Alembic scripts (read-only) | single head `0008_ombot_flow_rename`, chain of 17 |
| Scratch DB = restore of the live dump (isolated network, throwaway Postgres) | revision 0007 -> 0008; column `ombot_flow` NOT NULL; 368 rows, 0 bot sessions, unchanged |
| ORM on migrated scratch DB | `ChatSession.ombot_flow` filters work; query_history and chat modules import |
| Downgrade then upgrade (scratch) | old name returns at 0007, new name at 0008 |
| Baseline-created schema (psql load of 0001 sql, stamp, upgrade) | 0002..0008 all apply, ends with `ombot_flow` |
| Live deploy | fresh dump first (`postgres_pre_phase3_20261024.dump`), api_server recreated, migration ran on start, api healthy; background started after; slack and discord bots RUNNING; celery tasks executing; `/api/versions` 200; live ORM read of the new column OK (368 sessions) |

Rollback available: image tag `om/om-backend:phase2-rollback` (previous image) plus the pre-migration dump, or `alembic downgrade -1`
through a container start.

## Findings (not caused by this phase)
1. **A brand-new empty database cannot be built by `alembic upgrade head`.** Revision `0001_baseline_schema` fails with asyncpg
   "cannot insert multiple commands into a prepared statement" (it runs a multi-statement SQL file through one prepared statement).
   Reproduced with the Phase 2 image, so it predates this work. Existing databases are unaffected (they are already past 0001),
   but a fresh install would fail. Not fixed here (out of scope); worth a separate fix, e.g. execute the SQL file with
   `exec_driver_sql` / split statements. Workaround used for testing: load the baseline SQL with psql, `alembic stamp`, upgrade.
2. Background container logs a one-time celery-beat `gdbm ... Resource temporarily unavailable` traceback for the local schedule file
   during restart; beat then runs normally. Not related to the database.
