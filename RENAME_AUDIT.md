# RENAME AUDIT — remaining `onyx` / `danswer` references

> Companion to [`DO_NOT_RENAME.md`](DO_NOT_RENAME.md). That file is the authoritative **frozen**
> list; this file is the full **inventory** — what still needs renaming, what must stay, and why.

We are mid-way through a staged rename of the fork. Two distinct targets:

- **Runtime / code / infra / env keys → `om`** (package is already `backend/om/`, images `om/om-*`).
- **User-facing brand PROSE → `VertualAI`** (the web Dockerfile LABELs already read `com.vertualai.*`,
  the Tauri `productName`, chrome manifest name, widget titles, and the `--virtualai-*` design system
  are all `VertualAI`). Do **not** rebrand prose to "Om".

Scope of the sweep: `backend/`, `web/`, `extensions/`, `desktop/`, `widget/`, `deployment/`,
`.github/`, `tools/`, `docs/`, root. ~4,700 raw case-insensitive matches across ~780 files
(excluding the generated `graphify-out/`).

## ⚠️ Read first — the `danswer` false positive

~95% of raw `danswer` hits are **not** brand references. The `standard-answer` feature
(`StandardAnswer`, `standardAnswer…`, `standard_answer_categories`) matches "…stan**dAnswer**"
case-insensitively. **Never** include `standard-answer` / `StandardAnswer*` in a `danswer` rename.
Genuine frontend `Danswer` tokens are rare — after excluding `standardAnswer*`, the remainder is:
the env key `NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED` (Bucket B, keep value),
`extensions/chrome/LICENSE` copyright (Bucket A, legal), and stray UI prose such as
`web/src/app/admin/bots/SlackBotTable.tsx:114` ("…chatting with **Danswer**!" → **VertualAI**,
Bucket C). Grep with `rg -io '\bdanswer\w*'` and eyeball each — do not bulk-replace.

## How to read the buckets

- **A — FROZEN**: do not change. External / on-disk / on-wire contracts. Renaming compiles fine and
  breaks at runtime. Also recorded in `DO_NOT_RENAME.md`.
- **B — RENAME-BUT-KEEP-VALUE**: rename the identifier, but the string **value** it holds is frozen.
- **C — RENAME (safe)**: internal → `om`; brand prose → `VertualAI`.
- **D — STALE / BROKEN**: rename that also fixes real breakage (dead paths, tag drift).

## Completed on this branch

- Embedding chunk-index prefix `danswer_chunk_*` → **`chunk_*`** (greenfield; shared by Vespa +
  OpenSearch via `SearchSettings.index_name`). Lockstep sites: `backend/om/configs/embedding_configs.py`,
  alembic seed `dbaa756c2ccf:53,68`, `provisioning.py:476`, `document_index_utils.py:45`
  (`DEFAULT_INDEX_NAME`), commented formula `search_settings.py:87`, OpenSearch Dashboards pattern
  (`build_ndjson.py:15` + `files_and_chunks.ndjson`), README examples. Requires a fresh DB.
- Alt/secondary index suffix `__danswer_alt_index` → **`__alt_index`** (`ALT_INDEX_SUFFIX` in
  `shared_configs/configs.py:45` + the two literals in `scripts/debugging/onyx_vespa_schemas.py`;
  migration `d9ec13955951` keeps the old literal to clean legacy data). The Vespa schema *template*
  `danswer_chunk.sd.jinja` was left as-is (Vespa-removal scope).

---

## Bucket A — FROZEN (do NOT rename)

| Cluster | Representative location(s) | Why frozen |
|---|---|---|
| HF model repo ids | `backend/shared_configs/configs.py:36,38`; `backend/model_server/legacy/custom_models.py:36` | download URLs; no `om/…` on HF Hub |
| Session/tenant cookies `onyx_tid`, `onyx_anonymous_user` | `web/src/lib/constants.ts:29`; `web/src/proxy.ts:7`; backend `om/auth` consts | live browsers hold them |
| Redis `onyx:` prefix | `backend/om/configs/constants.py` (`OM_CELERY_BEAT_HEARTBEAT_KEY="onyx:celery:beat:heartbeat"`); `backend/supervisord.conf:160` | misses every existing key |
| Vespa schema template `danswer_chunk.sd.jinja` (template input, not a physical index) | `backend/om/document_index/vespa/vespa_document_index.py:95`; `vespa_constants.py:20,25` | Vespa-removal scope (the `__danswer_alt_index` suffix was renamed to `__alt_index` — see Completed) |
| Upstream URLs `github.com/onyx-dot-app/…`, `raw.githubusercontent.com/onyx-dot-app/…` | both Dockerfiles; `backend/om/onyxbot/slack/icons.py` (~27 asset URLs); helm `Chart.yaml`/`Chart.lock`; `ct.yaml`; CF nginx template; `deployment/docker_compose/install.sh` | real upstream artifacts → 404 |
| Real domain/email `onyx.app`, `founders@onyx.app`, `telemetry.onyx.app`, `cloud.onyx.app`, `docs.onyx.app`, `api.onyx.app` | LABELs; `backend/om/utils/telemetry.py:24`; helm `values.yaml`; `env.template`; `desktop/src-tauri/src/main.rs`; widget/chrome HTML; `tools/ods` | real contacts/endpoints |
| Docker Hub URL `hub.docker.com/r/onyx/…` | `backend/Dockerfile.model_server:31` (LABEL description) | real Docker Hub URL in a label; not an image we build. (`onyxdotapp/code-interpreter` + `python-executor-sci` were RENAMED to `om/*` local — see §done) |
| Token prefixes `onyx_pat_`, `onyx_scim_` | `backend/om/auth/constants.py:9` (`PAT_PREFIX`); `backend/om/server/scim/auth.py:31` (`SCIM_TOKEN_PREFIX`) | live tokens carry them |
| KV / lock / store prefixes `onyx_kv_store:`, `da_function_lock:`, `onyx-files` (S3), `onyx-sandboxes` (k8s ns) | `backend/om/key_value_store/store.py:18`; `backend/om/configs/constants.py:164`; `backend/om/configs/app_configs.py:1129` (`S3_FILE_STORE_PREFIX`); sandbox config | prefixes on existing keys/objects/namespaces |
| API-key pseudo-user `onyxapikey.ai`, `API_KEY__` | `backend/om/configs/constants.py:98,99`; matched by `.endswith()`/parse in `om/auth/users.py`, `om/db/api_key.py` | stamped on existing DB rows |
| `ONYX_METADATA` file marker `<!-- ONYX_METADATA={…} -->`, `#ONYX_METADATA=`, `.onyx_metadata.json` | `backend/om/file_processing/extract_file_text.py:122-127`; `backend/om/connectors/file/utils.py:163` | user-authored file format contract |
| Tauri app identity `app.onyx.desktop` (bundle id + on-disk config dir), `tabbingIdentifier:"onyx"` | `desktop/src-tauri/tauri.conf.json:5,30`; `desktop/src-tauri/src/main.rs:199`; `desktop/README.md:118-143` | OS treats a changed id as a new app; orphans installs + saved config |
| Chrome persisted `chrome.storage.local` keys `onyxExtension*` (7) | `extensions/chrome/src/utils/constants.js:22-29` | existing installs hold them |
| Cross-boundary wire type `ONYX_APP_LOADED` (web ↔ extension postMessage) | `web/src/lib/extension/constants.ts:15` **and** `extensions/chrome/src/utils/constants.js:34` (+ `panel.js:79`, `onyx_home.js:216`) | must match on both sides |
| Widget public API `<onyx-chat-widget>` element, `onyx-widget.js` bundle | `widget/src/widget.ts:20,604`; `widget/src/index.ts:11,13`; `widget/vite.config.ts:20`; `widget/package.json` | third-party embeds depend on tag/filename |
| Browser storage keys `onyxTheme`, `onyx:hideMoveCustomAgentModal`, `onyx-widget-session` | `web/src/lib/extension/constants.ts:27`; `web/src/sections/sidebar/constants.ts:8`; `widget/src/utils/storage.ts:7` | persisted client state |
| `danswer.ai` test-fixture emails (`hagen@`, `chris@`) | `backend/tests/external_dependency_unit/connectors/**`; `backend/tests/daily/connectors/**` | baked into recorded connector fixtures |
| Alembic revision ids (filenames + `down_revision`) | `backend/alembic/versions/*onyx*.py` | migration-chain identity — never change ids (bodies/comments only) |
| Prometheus metric names `onyx_*` | `docs/METRICS.md` + backend emit sites | Grafana dashboards / alerts depend |
| GitHub Actions secret names `ONYX_GITHUB_*` | `.github/workflows/pr-integration-tests.yml:40-44` | must match repo secret settings |

> Guard test: `backend/tests/unit/migration_safety/test_no_stray_package_paths.py` deliberately
> allowlists several of the above (`onyx:celery`, `onyx-sandboxes`, cookie prefixes, `onyx-dot-app/`).
> Update it **in tandem** — never blindly strip it.

---

## Bucket B — RENAME-BUT-KEEP-VALUE (rename the name → `om_*`; FREEZE the value)

Backend constants whose **name** is renameable but whose **string value** is a live contract (each
value is in Bucket A):

| Constant | File:line | Frozen value |
|---|---|---|
| `DANSWER_API_KEY_DUMMY_EMAIL_DOMAIN` | `backend/om/configs/constants.py:99` | `onyxapikey.ai` |
| `DANSWER_API_KEY_PREFIX` | `backend/om/configs/constants.py:98` | `API_KEY__` |
| `DANSWER_REDIS_FUNCTION_LOCK_PREFIX` | `backend/om/configs/constants.py:164` | `da_function_lock:` |
| `PAT_PREFIX` | `backend/om/auth/constants.py:9` | `onyx_pat_` |
| `SCIM_TOKEN_PREFIX` | `backend/om/server/scim/auth.py:31` | `onyx_scim_` |
| `REDIS_KEY_PREFIX` (KV store only) | `backend/om/key_value_store/store.py:18` | `onyx_kv_store:` |
| `S3_FILE_STORE_PREFIX` | `backend/om/configs/app_configs.py:1129` | `onyx-files` |
| `SANDBOX_NAMESPACE` | craft/sandbox config | `onyx-sandboxes` |
| `_DANSWER_TELEMETRY_ENDPOINT` | `backend/om/utils/telemetry.py:24` | `https://telemetry.onyx.app/…` |
| `DANSWER_TOOL_NAME` / `DANSWER_TOOL_DESCRIPTION` | `backend/om/prompts/chat_tools.py:4-5` | LLM-facing tool label prose |

Frontend values that arrive over the wire from the backend — rename **only in lockstep** with the
backend enum/settings:

- `onyx_web_crawler` — ~15 refs (`web/src/app/admin/configuration/web-search/**`, `contentProviderUtils.ts`, e2e specs). Must match the backend web-content-provider id.
- `onyx_craft_enabled` — 6 refs (`web/src/sections/sidebar/AppSidebar.tsx:236`, `web/src/app/admin/settings/SettingsForm.tsx:474,481`). A backend settings field.

### B2 — env-key LOCKSTEP families — ✅ RENAMED `ONYX_*` → `OM_*` (hard switch)

**DONE.** All fork-internal `ONYX_*` env-var KEYS were renamed to `OM_*` in lockstep across the
backend `os.environ` reads, the compose/helm/template setters, `env.template`, `README.md`, the
switch scripts, and tests. **Hard switch** — code reads only the `OM_*` name (no `ONYX_*`
fallback), so any live `.env` / helm override MUST use the new key or the value reverts to default.

Renamed families (old → new):
- `ENABLE_OPENSEARCH_{INDEXING,RETRIEVAL}_FOR_ONYX` → `…_FOR_OM` (const + key; `app_configs.py:286-294`)
- `ONYX_DISABLE_VESPA` → `OM_DISABLE_VESPA`, `ONYX_QUERY_HISTORY_TYPE` → `OM_QUERY_HISTORY_TYPE`
- `LOG_ONYX_MODEL_INTERACTIONS` → `LOG_OM_MODEL_INTERACTIONS` (const + key)
- `ONYX_BOT_*` → `OM_BOT_*` (all keys; consts were already `OM_BOT_*`; also the private
  `_ONYX_BOT_*` counters in `onyxbot/slack/utils.py` → `_OM_BOT_*`)
- `ONYX_API_KEY` → `OM_API_KEY`, `ONYX_EVAL_API_KEY` → `OM_EVAL_API_KEY`
- `CONFLUENCE_USE_ONYX_USERS_FOR_GROUP_SYNC` → `CONFLUENCE_USE_OM_USERS_FOR_GROUP_SYNC`
- nginx host vars `ONYX_{BACKEND_API,WEB_SERVER,MCP_SERVER}_HOST` → `OM_*_HOST`
  (`run-nginx.sh` exports + envsubst allowlist + all `*.template` + CF template, all in lockstep)
- CI image build-args `ONYX_{BACKEND,WEB_SERVER,MODEL_SERVER}_IMAGE` → `OM_*_IMAGE` (were
  silently ignored — compose already read `OM_*_IMAGE`; fixed the mismatch)
- web const `ONYX_CRAFT_CALENDAR_URL` → `OM_CRAFT_CALENDAR_URL`

Verified: 0 dangling old identifiers in code/config/tests (only `graphify-out/` cache lags, regen
with `graphify update .`). `NEXT_PUBLIC_ONYX_BACKEND_URL` does not exist in this tree.

Out of scope / still `ONYX` (NOT env keys — internal code constants, leave unless a later pass
targets code identifiers): `ONYX_CLOUD_CELERY_TASK_PREFIX` (`beat_schedule.py`),
`_ONYX_PROVIDER_DISPLAY_NAMES` (`llm_provider_options.py`), `_ONYX_MANAGED_API_KEYS`
(`usage_limits.py`), and `YOUR_ONYX_{DOMAIN,TOKEN_HERE}` doc placeholders. `DANSWER_*` keys belong
to the separate `danswer` rename, untouched here.

### B3 — infra resource names (renameable, but orphan LIVE state if already deployed)

Safe on a fresh deploy; on a running cluster either migrate the state or leave as-is:

- Docker volumes `onyx-stack_*` (15, `docker-compose.yml:663-696`), network `onyx_default`, container `onyx-api_server-1` (CI).
- Buckets `onyx-file-store-bucket` (`docker-compose.yml:558`, `values.yaml:943`), `onyx-playwright-artifacts`.
- Helm resource/secret names in `values.yaml`: `onyx-postgresql`, `onyx-redis`, `onyx-opensearch*`, `onyx-objectstorage`, `onyx-oauth`, `onyx-smtp`, `onyx-nginx-conf`, `host: onyx.local`, KEDA `scope: onyx-*`.
- Terraform module dir `deployment/terraform/modules/aws/onyx/` + `name="onyx"`.
- CloudFormation stack/service logical names `deployment/aws_ecs_fargate/cloudformation/**`.

---

## Bucket C — RENAME (safe): internal → `om`, brand prose → `VertualAI`

- **`onyxbot/` package** — largest cluster (~415 refs / 64 files): `backend/om/onyxbot/{slack,discord}`
  plus mirror `backend/tests/unit/om/onyxbot/`. Heavy files `slack/listener.py`, `slack/utils.py`,
  `handlers/*`. ⚠️ URLs inside `slack/icons.py` are frozen (Bucket A) — line-level care, not file sed.
- **`onyx_`-prefixed source filenames** → `om_*`: `configs/onyxbot_configs.py`,
  `connectors/**/onyx_*.py`, `server/runtime/onyx_runtime.py`, `model_server/legacy/onyx_torch_model.py`,
  `scripts/onyx_*.py`, `scripts/debugging/onyx_*.py`, and their tests.
- **Internal code identifiers** → `om`: `onyx_metadata` (marker VALUE frozen, symbol free),
  `onyx_request_id` (`om/utils/middleware.py`), `_ONYX_PROVIDER_DISPLAY_NAMES`, `_ONYX_MANAGED_API_KEYS`;
  frontend `MinimalOnyxDocument` (57), `SvgOnyxOctagon`, `SvgOnyxLogo`, `useOnyxBotAnalytics`,
  `isOnyxCraftEnabled`; CSS vars `--onyx-*` (`web/src/app/css/colors.css`, widget shadow-DOM styles);
  desktop Rust `TRAY_ID="onyx-tray"`, window labels.
- **Helm chart internals** — directory `deployment/helm/charts/onyx/` + `_helpers.tpl` identifiers
  `onyx.name`/`onyx.fullname`/… (~28 defs) + every `include "onyx.*"` across ~60 templates. Lockstep.
- **Tool package** `tools/ods` `name="onyx-devtools"` (+ `uv.lock`, CI `uv run --with onyx-devtools`)
  → coordinated rename. Leave `onyx.app`/`onyx-dot-app` values (Bucket A). `go.mod` module path
  `github.com/onyx-dot-app/onyx/tools/ods` → leave until the fork's real remote slug is finalized.
- **Brand PROSE → `VertualAI`**: `README.md`, root `*_PLAN.md` / design docs, `docs/**`, compose/CI
  comments + job names, chrome omnibox keyword pair (`manifest.json:55` + options help text), E2E
  test-message fixtures. Exclude `standard-answer` / `StandardAnswer*` entirely.

---

## Bucket D — STALE / BROKEN (rename that also fixes real breakage)

1. **Broken doc paths `backend/onyx/…`** (package is now `backend/om/`): `docs/folder-connector.md`
   (~50 refs), `docs/METRICS.md`, root plan docs, `backend/om/connectors/README.md:1` (its own
   `ONYX_METADATA` link still points at `…/backend/onyx/…`). Update to `backend/om/…`.
2. **Image-tag drift** (missed by the "already done" `om/om-*` pass): `docker-bake.hcl:6-18` still
   `onyxdotapp/onyx-{backend,web-server,model-server,integration}` → `om/om-*` (decide on
   `-integration`). Note: `onyxdotapp/code-interpreter` + `python-executor-sci` are now RENAMED to
   `om/*` (local-only): dev compose, helm values, and the executor defaults
   (`code-interpreter/.../app_configs.py`, `Dockerfile` ENV) — publishing to a registry is TODO.
3. **Stale Go test fixtures**: `tools/ods/internal/lazyimports/lazyimports_test.go` reference
   `onyx.llm…` / `onyx/main.py`; verify against the real tree (now `om/…`) before renaming.
4. **Dead Linear URLs** `linear.app/onyx-app/issue/ENG-1/…` across `.github/workflows/pr-*.yml` —
   disabled-for-fork prose; drop or ignore.

---

## Suggested batch order (each is independently reviewable)

1. Bucket D fixes (correctness: dead paths + tag drift) — low risk, high value.
2. Bucket C internal identifiers, per subsystem — start with the `onyxbot/` package.
3. Bucket C brand prose → `VertualAI` (docs/UI), excluding `standard-answer`.
4. Bucket B / B2 env-key lockstep families — one family at a time, backend + deployment together.
5. Bucket B3 infra names — only alongside a fresh deploy or a state migration.
6. Never: Bucket A.
