# Rename decision log (Phase 0 output)

Status: **DRAFT — fill the "Probe result" column after running `live_data_probes.sql` / `.sh`, then confirm each decision.**
Inventory: `SUMMARY.md` (counts), `inventory.csv` (every hit, classified), `path_renames.txt` (125 paths whose *name* contains the brand).
Baseline before any change: `tests/unit/migration_safety` = **28 passed** (run from `backend/`).

Strategies: **RENAME** = plain rename, gate with tsc/mypy/tests · **DUAL** = accept old and new for a window, then drop old · **MIGRATE** = data/schema migration then rename · **RUNBOOK** = manual infra cutover tested on the scratch stack · **REPLACE** = swap an external reference for our own.

| # | Item | Class | Proposed strategy | Phase | Probe result | Decision |
|---|---|---|---|---|---|---|
| 1 | Frontend names, icons, tailwind tokens, `@onyx/opal`, `onyx.ico` | S | RENAME | 1 | n/a | |
| 2 | Docs, comments ("Onyx-EE"), root `pyproject` name/include, requirements regen | S | RENAME | 1 | n/a | |
| 3 | `om/onyxbot`, `server/onyx_api`, `onyx_*.py`, identifiers | S | RENAME (`git mv`, fix dotted strings) | 2 | n/a | |
| 4 | `chat_session.onyxbot_flow` | P | MIGRATE (`0008`, reversible) | 3 | bot_sessions count | |
| 5 | `DANSWER_*` / `ONYX_*` env names | P | DUAL (read old if new unset) | 4 | grep deployed `.env` | |
| 6 | PAT prefix `onyx_pat_` | P | DUAL (accept both; mint new prefix) | 5 | pats_active | |
| 7 | API-key emails `@onyxapikey.ai` | P | MIGRATE (UPDATE `user.email`) or DUAL match | 5 | api_key_users_onyx_domain | |
| 8 | `.onyx_metadata.json` / `ONYX_METADATA` | P | DUAL (accept both filenames) | 5 | ask users / search file store | |
| 9 | Cookies `onyx_tid`, `onyx_anonymous_user` | P | RENAME backend+web together (one-time re-login) | 5 | n/a | |
| 10 | Redis prefixes, beat heartbeat key, `da_function_lock` | P | RENAME (ephemeral; flush once) | 5 | redis scan counts | |
| 11 | S3 prefix `onyx-files`, bucket default | P | RUNBOOK (copy objects, then flip) | 5 | files_under_onyx_prefix | |
| 12 | Prometheus `onyx_*` metrics | P | RENAME + update Grafana/alerts | 5 | dashboards using them | |
| 13 | Sandbox namespace `onyx-sandboxes`, `managed-by: onyx` | P | RUNBOOK | 5 | kubectl probe | |
| 14 | Compose volumes `onyx-stack_*`, project `name: onyx` | P | RUNBOOK (**highest risk**; volume copy) | 6 | docker volume probe | |
| 15 | Helm chart dir/resource names, ECS, terraform | P | RUNBOOK | 6 | n/a | |
| 16 | `onyx-dot-app` URLs, `onyx.app` domains/emails, `hub.docker.com/r/onyx`, helm dep repos | X | REPLACE with ours or delete | 7 | n/a | |
| 17 | `ONYX_GITHUB_*` CI secrets | X | RENAME in repo settings + workflows together | 7 | n/a | |
| 18 | Widget / extension / desktop identity | P | RENAME + notify embedders; DUAL storage-key read | 7 | n/a | |
| 19 | Vendored `phoenix/`, `Perplexica/`, LICENSE/NOTICE attribution text | X | KEEP (not ours / legally required) | — | n/a | |

## Gate checklist (per phase)
1. `python -I rename-audit/build_inventory.py` — class counts for the touched category go to zero.
2. `cd backend && pytest tests/unit/migration_safety` (baseline 28 passed) + `tests/route_rename` snapshot compare.
3. `mypy`, `pytest tests/unit`, `npx tsc --noEmit`, lint, `docker compose config`, `helm template`.
4. Scratch stack (`docker compose -p om-scratch`, fresh volumes + restored copy of live data): login, PAT/API key call, file upload/read, bot import, one seeded workflow run.
5. User reviews the uncommitted diff and rebuilds Docker before the next phase.
