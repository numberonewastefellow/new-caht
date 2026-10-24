# Phase 2 log: backend code names (one step at a time)

Rules: rename code names only. Any string VALUE that is persisted (DB, Redis, S3, cookies, browser storage),
sent to external systems (HTTP headers, metrics, analytics, URLs) or part of a client contract is left for its
own later phase and listed under "Deferred". Every step has a gate; results are recorded here.

Baselines taken before Phase 2:
- `tests/unit/migration_safety`: 28 passed.
- `tests/unit` (ignoring the 2 uncollectable mediawiki/snippet modules): 19 failed, 1556 passed. The 19 failures
  are pre-existing (websearch utils, censoring, chat utils, llm reasoning, connector factory, ...). Failure set saved and
  compared after every step.

## Step 2.1 Modules, packages and the string paths that point at them

| Old | New |
|---|---|
| package `om.onyxbot` (slack, discord) | `om.ombot` |
| tests dir `tests/unit/om/onyxbot` | `tests/unit/om/ombot` |
| package `om.server.onyx_api` | `om.server.om_api` |
| `om.configs.onyxbot_configs` | `om.configs.ombot_configs` |
| `connectors.confluence.onyx_confluence` | `om_confluence` |
| `connectors.salesforce.onyx_salesforce` | `om_salesforce` |
| `connectors.slack.onyx_retry_handler`, `onyx_slack_web_client` | `om_retry_handler`, `om_slack_web_client` |
| `server.runtime.onyx_runtime` | `om_runtime` |
| `tools.tool_implementations.open_url.onyx_web_crawler` (module only) | `om_web_crawler` |
| scripts: `onyx_openapi_schema`, `debugging/onyx_{db,list_tenants,redis}` | `om_*` |
| tests: `test_onyx_confluence`, `test_onyx_web_crawler` | `test_om_*` |

String references to these paths (invisible to the type checker) were checked and updated:
`backend/supervisord.conf` (slack listener + discord client commands), helm `slackbot.yaml` / `discordbot.yaml`
container commands, `backend/tests/integration/Dockerfile` (schema script), `.vscode/launch.json` and
`tasks.template.jsonc` (these also had a stale dead package root: `onyx.main:app`, `onyx.background...`,
`backend/onyx/...` pointed at a package that no longer exists; now `om.*`), mock.patch target strings in tests,
docstring paths.

Verification:
- `git mv` used for all moves (history kept). 16 moves, 72 files with content edits.
- Golden snapshot test failed as expected on `modules` only. Proved the diff is a pure 1:1 rename: after applying the
  mapping the old and new inventories are identical (1001 modules; 50 celery tasks and 20 beat tasks unchanged;
  0 dynamic fetch targets). Baseline re-captured.
- Full `tests/unit`: 19 failed / 1556 passed, failure set identical to baseline.

Deferred from 2.1 (string values, not module paths):
- `onyx_web_crawler` as the web content provider type VALUE (DB/settings + web UI) -> Phase 5.
- generated client package `onyx_openapi_client` and the `/onyx-api` route prefix -> step 2.4 / Phase 5.

## Step 2.2 Code identifiers (exact-token map, word-boundary, 335 replacements in 77 files)

Only identifiers whose string value is NOT persisted or external. Checked first: no `Onyx*` class is still defined
(they were already `Om*`; the leftovers were docstrings/log text), no target name collides with an existing definition,
no pydantic/DB field is in the list, and no dict-key string depends on any of them.

Renamed (examples): `setup_onyx`, `setup_multitenant_onyx`, `onyx_request_id` family
(`make_randomized_onyx_request_id`, `make_structured_onyx_request_id`, `_make_onyx_request_id`,
`add_onyx_request_id_middleware`, `add_onyx_tenant_id_middleware`), `process_onyx_metadata`,
`_extract_onyx_metadata`, `ignore_onyx_metadata`, `handle_onyx_date_awareness`, `create_onyx_oauth_router`,
`is_onyx_craft_enabled`, `require_onyx_craft_enabled`, `onyx_craft_enabled_for_user`, `get_onyx_bot_auth_ids`,
`remove_onyx_bot_tag`, `is_onyx_bot_msg/response`, `include_onyxbot_flows` (function parameter only),
`_convert_onyx_chunk_to_opensearch_document`, `_ONYX_PROVIDER_DISPLAY_NAMES`, `CREATED_ONYX_BOT` (enum MEMBER only,
value `created_onyx_bot` kept because it is stored in the milestone table), local variables (`onyx_user`, `onyx_file`,
`onyx_document`, ...), the dev script flag `--onyx-url` -> `--om-url`.

## Step 2.3 Prose and stale paths (84 files)

- `Onyx` as a standalone word in comments, docstrings and log text -> `VertualAI`; `Onyx-EE` -> `upstream EE`.
- Stale references to the dead package root fixed in comments/READMEs/gitignore (`onyx/evals/...`, `tests/unit/onyx/...`,
  `python -m onyx.server...`). `backend/.gitignore` pointed at `onyx/connectors/salesforce/data/`, which never matched;
  now `om/...`.
- Mistake caught and reverted during this step: the rule `backend/onyx/` -> `backend/om/` also rewrote the path inside the
  upstream URL in `app_configs.py` (recommended-models JSON on raw.githubusercontent.com). That URL must keep the
  upstream path; restored to the committed value (zero diff for that line).
- Pre-existing bug found by mypy and fixed (not caused by renames): `build_ext_team_name_for_om(...)` was called with
  keyword `ext_group_name=` in `external_permissions/github/utils.py`, `github/doc_sync.py` and `db/document.py`, but the
  parameter is `external_group_name`. GitHub permission sync would have raised TypeError at runtime. Fixed 11 call sites.

## Step 2.4 API response field

`ContainerVersions.onyx` -> `ContainerVersions.om` (`/versions` endpoint, `get_state.py`, `tests/api/test_api.py`).
Consumers checked: nothing in `web/src` reads it; install scripts and helm do not call it. The route_rename "before"
snapshot still has the old key by design (it is the pre-rename capture).

## Step 2.5 Generated OpenAPI client package

`onyx_openapi_client` -> `om_openapi_client` in `scripts/om_openapi_schema.py`, `tests/integration/Dockerfile`
(`--package-name`), `pytest.ini`, `common_utils/config.py` (alias `onyx_api` -> `om_api_client`), VS Code task template,
integration README. It is generated at build time and is gitignored, so nothing persisted. A locally generated
`backend/generated/onyx_openapi_client` folder (ignored by git) is now unused; regenerate to get the new name.

## Deferred out of Phase 2 (reason -> phase)

| Value | Why not now | Phase |
|---|---|---|
| `onyxbot_flow` column and the model attribute | schema; needs an Alembic revision | 3 |
| `ONYX_*` / `DANSWER_*` env var names | deployed `.env` files and secrets | 4 |
| `onyx_settings`, `onyx_enterprise_settings` KV keys; `onyx_craft_enabled` settings field | persisted rows (JSON in the key-value table) | 5 |
| `onyx_web_crawler` provider type value | stored provider rows and the web UI | 5 |
| `All_Confluence_Users_Found_By_Onyx` group name | stored external group rows | 5 |
| `.onyx_metadata.json`, `ONYX_METADATA` marker | user-authored files | 5 |
| `onyx_pat_`, `onyxapikey.ai`, cookies, `onyx:` Redis keys, `onyx-files`, `onyx-sandboxes`, `managed-by: onyx` | live tokens, rows, objects, browsers | 5 |
| `X-Onyx-Tenant-ID`, `X-Onyx-Request-ID`, `X-Onyx-Authorization` headers | client and proxy contract | 5 |
| Prometheus `onyx_*` metric names, PostHog property names (`onyx_cloud_user_id`), UTM `onyx_app`, flag `onyx-craft-enabled` | dashboards and external analytics | 5 |
| `/onyx-api` route prefix | external ingestion clients | 5 |
| `OnyxWebCrawler/1.0` style identifiers sent to third parties | external-facing | 7 |
| `@onyx.app`, `onyx-test.com`, upstream URLs, `onyx_vespa/onyx_postgres/onyx_minio` container names | external or infra | 6/7 |
