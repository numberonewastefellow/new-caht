# Rename connectors to datasource: tracker

No business changes. Groundwork for the Dify-style chunker and RAG wizard, which get their own plan afterwards.

## Where this work lives
- **Branch:** `refactor/connectors-to-datasource`, rebuilt on `bedd3686b` with the tools below.
- **Re-run on a newer main:** `python -I D:/tmp/datasource/stage1_rename.py <repo>`, then re-sort imports with `reorder-python-imports-black==3.14.0` and regenerate the golden snapshot.
- **Scratch stack (outside the repo):** `D:/tmp/datasource/live/compose.yml`.
  - New DB `ds_rename3` (earlier runs `ds_rename`, `ds_rename2`), a clone of the real DB with its 3 cc-pairs paused. Redis DBs 9/10/11. API on `127.0.0.1:8095`.
  - Start only the API with `docker compose up -d`. Add workers with `docker compose --profile workers up -d`.
  - **OpenSearch and MinIO are shared with the main stack.** Live tests create and delete only their own new data source. Never delete a cloned connector here, because that would remove real chunks.
- **Baselines and logs:** `D:/tmp/datasource/stage0/` and `stage1/`.

## What stays unchanged
REST URLs, JSON fields, frontend, class and file names inside the package (`SlackConnector`, `slack/connector.py`), `om/federated_connectors/`, `om/db/connector.py`, `om/redis/redis_connector*.py`, `server/documents/connector.py`, local `cc_pair` variables, Celery queue and task names, Redis keys, env vars, stored enum values.

## Stage 1: namespace

**Moved with `git mv`:**
| Old | New |
|---|---|
| `backend/om/connectors/` | `backend/om/datasource/` |
| `backend/tests/unit/om/connectors/` | `backend/tests/unit/om/datasource/` |
| `backend/tests/daily/connectors/` | `backend/tests/daily/datasource/` |
| `backend/tests/external_dependency_unit/connectors/` | `backend/tests/external_dependency_unit/datasource/` |

**Docker and compose:** `backend/Dockerfile`, compose files, `supervisord.conf` and helm have no reference to the old package path, so they didn't change. They mention only queue names, env vars and `force_delete_connector_by_id.py`, which stay. `test_no_old_connectors_namespace.py` enforces this.

**Misses found by review, handled by exact rules in the script:** `tests/external_dependency_unit/conftest.py` (`Path(...) / "connectors"`, which would have silently stopped the account-skip logic), `test_importlib_factories.py`, `rename-audit/build_inventory.py`, `rename-audit/gen_accounts_doc.py`.

**Before and after (old code is a clean export of `9e997db4c`):**
| Check | Before | After |
|---|---|---|
| Unit suite | 2637 passed, 15 failed, 3 errors, 109 skipped | Same counts; failure list identical apart from the path |
| Migration-safety suite | 33 passed, 1 failed (stale snapshot), 1 skipped | 36 passed, 1 skipped (snapshot regenerated, 2 new guard tests) |
| Golden snapshot content | | Identical after swapping the name |
| Tests collected, all folders | 3753, 11 errors | 3755 (2 new guard tests), same 11 errors |
| `mypy om` | 213 errors | 213, same errors |
| `compileall` | | Clean |
| OpenAPI | 423 routes, 557 schemas | Same routes and schema content |
| Python diff | | Old and new lines match exactly after the name swap, apart from moved imports and 4 blank lines |

**OpenAPI is not byte-identical, and that isn't caused by the rename.** Two pairs of models share a name (`ChatSessionSummary`, `UploadResponse`), and which one gets the short name varies between runs on the same code. The comparison normalises those names.

**Live on the scratch stack:** API and all workers boot on renamed code; 52 sources in the registry; old package not importable. A new file data source went through upload, create, associate, index (11 s), search index check and delete (26 s), with no import errors in any log. The real DB's connector count didn't change.

**Existing problems found:**
1. Fixed 2026-11-02 (patch `D:/tmp/datasource/mediawiki_fix.patch`, for its own commit): `backend/om/datasource/mediawiki/family.py:15` imports `pywikibot.scripts.generate_knowledge_files`. The package only has `generate_user_files`, so an earlier rename changed a third-party name by mistake. The MediaWiki and Wikipedia connectors can't load, confirmed inside the built image, on old code too. 
2. `tests/unit/om/tools/tool_implementations/mcp/test_mcp_result_errors.py` can't be collected (`No module named 'mcp.test_mcp_result_errors'`); the `mcp` test folder probably shadows the `mcp` package. Not investigated further.
3. `tests/unit/migration_safety/snapshots/baseline.json` was 27 lines out of date, so the golden test was already failing on main. Regenerated here.

## Stage 2: database and models
Tested on scratch DBs first. The migration follows `0006_webhook_notify_on_success`.

**Tools, re-runnable on a newer main (`D:/tmp/datasource/stage2/`):**
- `gen_migration.py` builds the migration from the live catalog. Re-generate it if another branch adds connector objects.
- `stage2_rename.py` with `models`, `classes`, `kwargs`, then `mypy <report>` in a loop until no old-attribute errors remain (`mypy_round.sh`).
- `stage2_exact.py` holds the fixes mypy can't see.
- `residual.py` lists every remaining old attribute for review.

**Renamed:** 8 tables, 15 columns, 31 constraints, 11 standalone indexes, 5 sequences, 8 ORM classes, plus attributes on 12 more models. Full lists are in `alembic/versions/0007_datasource_rename.py`.

**Not renamed:** REST URLs, JSON fields, API (Pydantic) models, `ConnectorCredentialPairStatus`, `FederatedConnectorSource`, the separate `FederatedConnector` interface class in `om/federated_connectors/interfaces.py`, error message text.

**Before moving to main:**
- Stop all workers, take a `pg_dump`, then restart so the backend applies it. Old and new code can't share a schema.

**Fixes mypy could not find, found by review:**
- `getattr(document_set, "federated_connectors", [])` in `document_index/tasks.py` would have silently returned `[]`, so federated-only document sets would be deleted.
- `attempt.connector_credential_pair...` on an untyped value in `server/documents/connector.py`.
- `.c.connector_credential_pair_id` on two subqueries in `db/index_attempt.py`.

**Results on `bedd3686b` (2026-11-02):**
| Check | Before | After |
|---|---|---|
| Unit suite | 2715 passed, 15 failed, 3 errors | 2717 passed, 14 failed, 1 error; no new failures, 3 fixed by the MediaWiki patch |
| Migration-safety suite | | 42 passed, 1 skipped |
| Tests collected | 3849, 11 errors | 3881, 9 errors (the MediaWiki 2 fixed) |
| `compileall` | | Clean |
| `mypy om` | 279 errors | 279, same errors |
| OpenAPI | 424 routes, 558 schemas | Same content |
| Docker image `om/om-backend:ds-rename-final` | | Builds; 52 of 52 sources load |
| Golden snapshot | | Same, plus the 3 MediaWiki and Wikipedia modules that now import |
| 122 API GET routes, real responses | | 120 same; 2 differ by noise (live speed value, `is_up_to_date` after sync) |
| Row counts, ID maxima, FK, index, sequence totals | 127 tables | Identical; only the revision changed |
| Old names left in the DB | | 0 |
| Fresh install from baseline | | Works through 0001 to 0007; schema equals the migrated clone apart from one empty comment on schema `public` |
| Alembic ORM vs DB differences | 161 | 161, same after renaming (existing drift, not fixed here) |
| Migration down and up on real rows | | Catalog identical, 3 of 3 pass |
| Tenant schema | | Renames only inside that schema; down and up work |
| DB-backed tests (including Pulse) | | 113 passed; 3 Slack tests need a real `OPENAI_API_KEY` |

**Warning about `tests/external_dependency_unit/slack_bot/test_slack_bot_federated_search.py`:** its setup (line 417) deletes every LLM provider, then the test fails if there's no API key, leaving the DB with no default model. It emptied scratch DBs here. Never point it at a DB you care about.

**Live on the migrated schema:** upload, create, index, re-index (`success`), pause, resume, rename, config edit, prune, document set edit, federated source (including a federated-only document set surviving the sync task), team grant add and remove, chat search finding the indexed document, delete with chunks gone from the search index. No attribute or schema errors in API or worker logs.

**Webhooks:** a real call to `/hooks/{token}` was accepted (202), the workflow ran to its human-input step (`needs_input`), and a wrong secret got 401.

**Trace:** traces saved before the migration load; new `sequential` and `llm_decision` runs save traces, read by session and by message; Phoenix received all 37 spans from the runs.

**Not run:**
- The integration suite, because its fixtures reset the DB and search index, and OpenSearch is shared with the main stack.
- Daily connector tests, which need real accounts.
- The frontend wasn't changed, so no browser test. The API contract checks above cover it.

## Tracker
- [x] 2026-11-01 Stage 0 baselines recorded on a clean worktree
- [x] 2026-11-01 Stage 1 rename script run; guard tests added; golden snapshot regenerated
- [x] 2026-11-01 Stage 1 unit, safety, mypy, OpenAPI and collection comparison
- [x] 2026-11-01 Scratch stack `ds_rename`; live lifecycle test
- [x] 2026-11-01 Stage 1 Docker image `om/om-backend:ds-rename-stage1` builds; 50 of 52 sources load inside it (the other 2 are problem 1 below the table)
- [x] 2026-11-02 User approved moving to `main_multi_agent_stable`
- [x] 2026-11-02 Stage 2 implemented and verified on `ds_rename`; awaiting user review
- [x] 2026-11-02 Applied to the real DB (workers stopped, `pg_dump` verified by restoring it, API restart ran the migration); row counts and IDs identical; about 6 minutes of downtime
- [x] 2026-11-02 Rebuilt on `bedd3686b`, branch `refactor/connectors-to-datasource`; all checks re-run
