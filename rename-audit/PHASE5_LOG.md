# Phase 5 log: external references, stored values, tests and prose

Status: implemented and tested locally; NOT committed, NOT deployed to the live stack (see "Why not live yet").
Plan: approved in the planning session of 2026-10-27 (Step 0, Group A, Group B, Group C).

## Step 0: regression from Phase 2, fixed
`OM_METADATA_FILENAME` had silently become `.om_metadata.json` in Phase 2 (my identifier rename matched `onyx_metadata`
inside the string). Zips with the legacy `.onyx_metadata.json` lost their metadata. Now:
`OM_METADATA_FILENAME = ".om_metadata.json"`, `LEGACY_METADATA_FILENAMES = (".onyx_metadata.json",)`, `METADATA_FILENAMES` (both).
Readers (`file_processing/extract_file_text.py`, `server/documents/connector.py`) accept both names and both inline markers
(`OM_METADATA=` / legacy `ONYX_METADATA=`); only the om name is ever written. Fixture `with_meta.zip` regenerated.
Audit of Phases 2-4: the metadata file name was the only stored/external VALUE changed by accident. A second Phase 2 miss was
found and fixed: `tests/api/test_api.py` still indexed `['onyx']` inside two f-strings.
Tests: `tests/unit/om/file_processing/test_metadata_names.py` (11).

## Group A: external references (outbound links to the upstream company)
| Item | Change |
|---|---|
| Telemetry | Hard-coded `https://telemetry.onyx.app/...` removed. Opt-in through `OM_TELEMETRY_ENDPOINT`; unset = nothing is sent. The old code sent customer uuid, user ids and the admin email domain by default unless `DISABLE_TELEMETRY=true`. Slack usage report follows the same rule. |
| Connector-request email | Recipient `OM_CONNECTOR_REQUEST_EMAIL`; unset = no email (was `hello@onyx.app`, with the requester's address and tenant id). |
| `CLOUD_DATA_PLANE_URL` (`cloud.onyx.app`) | Removed (no other reader). `SCHEDULED_EVAL_PERMISSIONS_EMAIL` default (a named person) is now empty. |
| MCP template | `cloud.onyx.app/mcp` -> placeholder host. |
| Slack icons | 27 GitHub raw URLs replaced; images served from our web app (`{WEB_DOMAIN}/<file>`), `web/public/slackbot/` added, placeholder `Bookstack.png` created (no real image existed); `Productboard.webp` was already available as `.png`. Function renamed `source_to_img_link`. |
| Docs links / URLs | `OM_DOCS_URL` setting (unset = no link) for the Google Drive scope message; sample URLs, eval default and comments no longer point at the upstream docs site. Backend Dockerfile labels and `install.sh` contact now use the project's own contact. |
| Analytics label | `Non-Onyx-Or-No-Auth-User` -> `Non-Om-Or-No-Auth-User`. |
Tests: `tests/unit/om/utils/test_optional_outbound.py` (5: no thread/HTTP/email without config, uses configured value only),
`tests/unit/om/ombot/test_slack_icons.py` (3: every icon is a real file served by our domain, no third-party host).

## Group B: stored values
| Step | Change | Data handling | Evidence |
|---|---|---|---|
| B1 | API-key synthetic domain `onyxapikey.ai` -> `omapikey.ai`; anonymous and no-auth placeholder users `@onyx.app` -> `@omapikey.ai` | migration `0012_om_stored_values` (user + user_tenant_mapping) | scratch copy of live data: 4 API-key users + seeded placeholders rewritten, downgrade restores exactly, re-upgrade OK |
| B2 | PAT prefix `onyx_pat_` -> `om_pat_`, legacy prefix still accepted, masked display adapts to the prefix | none (0 tokens exist) | 7 unit tests |
| B3 | KV key `onyx_settings` -> `om_settings`; first read copies a legacy row, leaves the legacy row in place; dead `onyx_enterprise_settings` constant removed | code-level, one-time | 4 unit tests |
| B4 | Settings field `onyx_craft_enabled` -> `om_craft_enabled` (API + 4 web files + script); old stored JSON still validates | none (computed per request) | pydantic check, `tsc` clean |
| B5 | Web content provider value `onyx_web_crawler` -> `om_web_crawler` (enum + web) | migration updates `internet_content_provider` (the app raises on unknown stored values, so this is required) | seeded row rewritten and restored |
| B6 | Confluence all-users group id `...found_by_onyx` -> `...found_by_om` | migration rewrites `document` / `hierarchy_node` ACL arrays and the external-team tables; OpenSearch ACLs catch up on the next group sync | seeded rows rewritten and restored |
| B7 | Cookies `onyx_tid` / `onyx_anonymous_user` -> `om_tid` / `om_anonymous_user`; legacy names still read, legacy anonymous cookie cleared on login | none | 6 unit tests, `tsc` |
| B8 | Redis: heartbeat `om:celery:beat:heartbeat` (supervisord.conf matches, pinned by a test), `om_kv_store:`, `om_function_lock:` | ephemeral | 2 unit tests |
| B9 | File-store defaults `om-files` / `om-file-store-bucket` (code, 6 compose files, env templates, helm values); reads use each row's stored bucket/key so old files keep working | `scripts/migrate_file_store_names.py` (dry-run default, copy + size/ETag verify, batch transactions, idempotent, old objects kept until `--delete-old`) | real data: 1,774 rows and objects copied from a copy of live MinIO, 0 failures, re-run no-op, 150 random files read through the application file store before and after deleting old copies, 4 unit tests |
| B10 | Inline marker | accepted under both names (Step 0) | covered |

Deviation from the plan: the synthetic domain is `omapikey.ai`, not `omapikey.invalid`. Verified that pydantic's email validation
rejects `.invalid` / `.local` (users are serialized through it), which would have broken user lists.

Observation: after copying and deleting, the scratch copy of the old bucket still held ~4,400 objects that no `file_record` row
references (orphans from files deleted earlier). The script leaves them alone; they can be removed by deleting the old bucket once you are satisfied.

## Group C: tests and prose
Generic test fixtures changed (emails `@onyx.app` / `onyx-test.com` -> `@om-test.com`, API-key domain, project names, README text,
search terms, `with_meta.zip` regenerated from the updated fixture). Left on purpose (they name real external accounts or are infra):
`tests/daily/**`, `external_dependency_unit/connectors`, `integration/connector_job_tests` (upstream's Google/Slack/GitHub/S3 test
accounts), metric-name tests, `/onyx-api` route tests, mock-service compose network, sandbox tests.
Old tracking documents `RENAME_AUDIT.md`, `ONYX_RENAME_REMAINING.md`, `API_RENAME_PLAN.md` moved to `rename-audit/history/`
(`DO_NOT_RENAME.md` stays: CI comments and `AGENTS.md` point at it and it still governs the remaining frozen items).

## Why not live yet
1. The live database is already at `0010_pulse_input_modes` because another developer's Pulse work (uncommitted, still changing) was deployed there.
   My migration `0012_om_stored_values` is chained after their uncommitted `0011_pulse_updated_by`; if they renumber or reorder, mine must be re-chained
   (one line) before commit. Never commit mine without theirs.
2. Building a live image from this working tree would ship their in-progress code and run their uncommitted migrations on live data.
3. Everything here was tested on throwaway stacks (see results below); deploying needs your go-ahead, a fresh backup, and the file-store script run as a separate, supervised step.

## Remaining (needs your decision, later group 3)
Sandbox/k8s names, `X-Onyx-*` headers, Prometheus `onyx_*` metric names, PostHog property/flag names (`onyx_cloud_user_id`, `onyx-craft-enabled`),
`/onyx-api` route, Slack `/onyx` command text, helm/ECS/terraform names, `ONYX_GITHUB_*` CI secrets, widget/extension identities, upstream URLs in the helm chart.
