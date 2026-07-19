# DO NOT RENAME — external contracts

> **Read this before any `onyx` → `om` (or any other) mass rename / find-and-replace.**

Most `onyx` strings in this repo are safe to rename. **The strings on this page are NOT.**
They are *external contracts*: they point at artifacts owned by someone else (HuggingFace Hub,
Docker Hub, the browser, Redis, the OS), or at on-disk/on-wire names that outlive the code. If
you rename them, nothing fails at build time, mypy stays green, the app starts fine — and then
it **breaks at runtime** the first time that path executes (a model download 404s, a session
cookie is dropped, a Redis key misses, a log dir is wrong).

This is exactly how the last few migration bugs happened: a string literal is invisible to the
compiler and the type checker. Treat everything below as **frozen** until the "How to actually
own these" section is done.

---

## 1. HuggingFace model repo IDs — trained models, NOW re-hosted under `bommina`

These are downloaded at runtime via `snapshot_download` / `from_pretrained`. The repo id **is
the download URL**. All three trained models were pulled from the original Onyx/Danswer repos and
re-pushed under our own HF namespace `bommina/om-*` (see §3 — that TODO is **done**). They resolve
from our account now, so the ids below are ours and no longer frozen. The mirrored connector tag
`1.0.0` was re-created on the new repo.

| String (now ours) | Location | What it is |
|---|---|---|
| `bommina/om-hybrid-intent-token-classifier` | `backend/shared_configs/configs.py:38` (`INTENT_MODEL_VERSION`) | **ACTIVE** intent / keyword-vs-semantic token classifier (re-host of `onyx-dot-app/hybrid-intent-token-classifier`) |
| `bommina/om-filter-extraction-model` | `backend/shared_configs/configs.py:36` (`CONNECTOR_CLASSIFIER_MODEL_REPO`, tag `1.0.0`) | **ACTIVE** connector classifier (re-host of `Danswer/filter-extraction-model`) |
| `bommina/om-information-content-model` | `backend/model_server/legacy/custom_models.py:36` | information-content SetFit classifier (currently commented-out legacy; re-host of `onyx-dot-app/information-content-model`) |

### Third-party public models (also do NOT rename — not ours to rename)
`nomic-ai/nomic-embed-text-v1`, `thenlper/gte-small`, `intfloat/e5-base-v2`,
`intfloat/e5-small-v2`, `intfloat/multilingual-e5-base`, `intfloat/multilingual-e5-small`,
`mixedbread-ai/mxbai-rerank-xsmall-v1` (comment), `distilbert-base-uncased` (commented).
Found in `backend/om/configs/model_configs.py`, `backend/om/configs/embedding_configs.py`,
`backend/Dockerfile`, `backend/Dockerfile.model_server`.

---

## 2. Other frozen external contracts (from the Stage-1 `onyx`→`om` rename)

| String / name | Where | Why frozen |
|---|---|---|
| `onyx_tid`, `onyx_anonymous_user` | auth / session cookies | live browsers hold these; renaming logs everyone out / drops anon sessions |
| `onyx:` key prefix | Redis namespace | renaming misses every existing key (locks, caches, taskset ids) |
| `github.com/onyx-dot-app/…`, `raw.githubusercontent.com/onyx-dot-app/…` | upstream repo + asset URLs | real upstream URLs (release notes, Slack icons); renaming 404s the asset |
| `founders@onyx.app`, `onyx.app` | Dockerfile `LABEL` maintainer value / docs | real email + domain — the LABEL **keys** (`com.danswer.*`→`com.om.*`) and brand **prose** were renamed to `om`, but this email/domain **value** stays as-is |
| `hub.docker.com/r/onyx/onyx-model-server` | `Dockerfile.model_server` `LABEL` description | Docker Hub URL — no `om/…` image is published there yet; renaming points the label at a 404 |

### Already renamed to `om` (no longer frozen — kept here so nobody "restores" them)

The Docker-runtime layer was fully renamed in lockstep and is done:

- Docker image tags `onyxdotapp/onyx-{backend,web-server,model-server}` → **`om/om-*`** (compose,
  CF templates, helm `values.yaml`, sandbox k8s manifests, `get_state.py`).
- Unix user/group `onyx` (uid/gid 1001) → **`om`**; log dir `/var/log/onyx` → **`/var/log/om`**
  (both Dockerfiles + `logger.py` / `memory_monitoring.py` / `packet_logger.py` + compose volume
  mounts, all changed together).
- Env-var keys `ONYX_{BACKEND,WEB_SERVER,MODEL_SERVER}_IMAGE` → **`OM_*_IMAGE`**.
- Dockerfile `LABEL` keys `com.danswer.maintainer` / `com.danswer.description` → **`com.om.*`**, and
  the brand **prose** `Onyx` / `DanswerAI` → **`Om`** in both Dockerfiles' descriptions. The stale
  Community/Enterprise-Edition licensing sentence was removed (EE was dissolved). The embedded
  `founders@onyx.app`, `github.com/onyx-dot-app/onyx`, and `hub.docker.com/r/onyx/…` values stay
  frozen (see the table above).
- Runtime version env key `ONYX_VERSION` → **`OM_VERSION`** (`backend/Dockerfile`,
  `Dockerfile.model_server`, `web/Dockerfile`, the 10 `--build-arg` lines in
  `.github/workflows/deployment.yml`, and the consumers `backend/om/__init__.py` +
  `web/src/lib/version.ts`), and `DANSWER_RUNNING_IN_DOCKER` → **`OM_RUNNING_IN_DOCKER`** (both
  Dockerfile `ENV`s + the `OM_DOCKER_ENV_STR` constant in `backend/om/utils/logger.py`), all changed
  in lockstep.
- **Fork-internal env-var KEYS `ONYX_*` → `OM_*` (hard switch, no fallback)** — the whole B2 family:
  `ENABLE_OPENSEARCH_{INDEXING,RETRIEVAL}_FOR_OM`, `OM_DISABLE_VESPA`, `OM_QUERY_HISTORY_TYPE`,
  `LOG_OM_MODEL_INTERACTIONS`, `OM_BOT_*`, `OM_API_KEY`, `OM_EVAL_API_KEY`,
  `CONFLUENCE_USE_OM_USERS_FOR_GROUP_SYNC`, nginx `OM_{BACKEND_API,WEB_SERVER,MCP_SERVER}_HOST`,
  CI `OM_{BACKEND,WEB_SERVER,MODEL_SERVER}_IMAGE`, web `OM_CRAFT_CALENDAR_URL`. Code reads ONLY the
  `OM_*` name now, so a live `.env`/helm override on the old `ONYX_*` key silently reverts to default
  — update deployments in tandem. Full old→new list in [`RENAME_AUDIT.md`](RENAME_AUDIT.md) §B2.
  These are NOT frozen; kept here only so nobody "restores" the `ONYX_*` spellings.
- Embedding chunk-index prefix `danswer_chunk_*` → **`chunk_*`** (greenfield, no data to preserve;
  shared by both Vespa and OpenSearch since both read `SearchSettings.index_name`). Changed in
  lockstep: the 21 literals in `backend/om/configs/embedding_configs.py`, the seed formula in
  `backend/alembic/versions/dbaa756c2ccf_embedding_models.py:53,68`, the Cohere hardcode in
  `backend/om/server/tenants/provisioning.py:476`, `DEFAULT_INDEX_NAME` in
  `backend/om/document_index/document_index_utils.py:45`, the commented formula in
  `backend/om/server/manage/search_settings.py:87`, the OpenSearch Dashboards index-pattern
  (`deployment/docker_compose/opensearch_dashboards/build_ndjson.py:15` + `files_and_chunks.ndjson`),
  and README examples. **Requires a fresh DB** for the new name to reach `SearchSettings.index_name`.
- Alt/secondary index suffix `ALT_INDEX_SUFFIX = "__danswer_alt_index"` → **`"__alt_index"`**
  (`backend/shared_configs/configs.py:45`, propagated via the constant to `setup.py:317`; the two
  hardcoded literals in `backend/scripts/debugging/onyx_vespa_schemas.py:63,133` updated to match).
  Greenfield; Vespa-setup-only. The migration `d9ec13955951` keeps the old literal on purpose (it
  strips the legacy suffix from old `model_name` data).
- Still left as-is: the Vespa schema *template* `danswer_chunk.sd.jinja` (template input, not a
  physical index name) — belongs to the future Vespa-removal effort.

### Frozen items found in the full audit (Stage-2 sweep)

The repo-wide sweep surfaced more frozen contracts than the original list. These are **frozen** for
the same reason as §1–§2: renaming compiles clean but breaks at runtime / orphans stored state. The
full renameable inventory lives in [`RENAME_AUDIT.md`](RENAME_AUDIT.md); this is only the *new frozen*
set.

| String / name | Where | Why frozen |
|---|---|---|
| `onyx_pat_`, `onyx_scim_` | `backend/om/auth/constants.py:9` (`PAT_PREFIX`), `backend/om/server/scim/auth.py:31` (`SCIM_TOKEN_PREFIX`) | prefix on live personal-access / SCIM tokens |
| `onyx_kv_store:` | `backend/om/key_value_store/store.py:18` (`REDIS_KEY_PREFIX`) | prefix on every KV-store Redis key |
| `da_function_lock:` | `backend/om/configs/constants.py:164` | live Redis lock keys |
| `onyxapikey.ai`, `API_KEY__` | `backend/om/configs/constants.py:98,99` | stamped on existing API-key pseudo-user rows (matched by `.endswith()`) |
| `onyx-files` (S3), `onyx-sandboxes` (k8s ns) | `backend/om/configs/app_configs.py:1129` (`S3_FILE_STORE_PREFIX`), sandbox config | prefixes on existing objects / live namespace |
| `ONYX_METADATA` file marker (`<!-- ONYX_METADATA={…} -->`, `#ONYX_METADATA=`, `.onyx_metadata.json`) | `backend/om/file_processing/extract_file_text.py:122-127`, `backend/om/connectors/file/utils.py:163` | user-authored file format |
| `telemetry.onyx.app`, `cloud.onyx.app`, `docs.onyx.app`, `api.onyx.app` | `backend/om/utils/telemetry.py:24`; `desktop/**`; `widget/**`; helm/env templates | real hosted endpoints |
| `app.onyx.desktop` (Tauri bundle id + on-disk config dir), `tabbingIdentifier:"onyx"` | `desktop/src-tauri/tauri.conf.json:5,30`, `src/main.rs:199` | OS app identity; orphans installs + saved config |
| `onyxExtension*` (7 keys) | `extensions/chrome/src/utils/constants.js:22-29` | persisted `chrome.storage.local` keys on existing installs |
| `ONYX_APP_LOADED` | `web/src/lib/extension/constants.ts:15` + `extensions/chrome/src/utils/constants.js:34` | web↔extension postMessage type — must match both sides |
| `<onyx-chat-widget>`, `onyx-widget.js` | `widget/src/widget.ts:20`, `widget/src/index.ts:11,13`, `widget/vite.config.ts:20` | public custom-element tag + bundle name embedders depend on |
| `onyxTheme`, `onyx:hideMoveCustomAgentModal`, `onyx-widget-session` | `web/src/lib/extension/constants.ts:27`, `web/src/sections/sidebar/constants.ts:8`, `widget/src/utils/storage.ts:7` | persisted browser storage keys |
| `@danswer.ai` / `@onyx.app` fixture emails | `backend/tests/external_dependency_unit/connectors/**`, `backend/tests/daily/connectors/**` | baked into recorded connector test data |
| Alembic revision ids | `backend/alembic/versions/*onyx*.py` (filenames + `down_revision`) | migration-chain identity — rename bodies/comments only, never ids |
| Prometheus metric names `onyx_*` | `docs/METRICS.md` + backend emit sites | Grafana dashboards / alerts depend |
| `ONYX_GITHUB_*` secret names | `.github/workflows/pr-integration-tests.yml:40-44` | must match repo secret settings |
| ~~`onyxdotapp/code-interpreter` / `onyxdotapp/python-executor-sci`~~ **→ RENAMED to `om/code-interpreter` + `om/python-executor-sci` (local)** | dev compose, helm values, executor defaults (`app_configs.py`, `Dockerfile` ENV) all updated | **No longer frozen.** Remaining TODO: publish to a registry you own + republish the external helm subchart. |

> **`standard-answer` is NOT a `danswer` reference.** `StandardAnswer` / `standardAnswer…` match
> "…stan**dAnswer**" case-insensitively and account for ~95% of raw `danswer` hits. Never bulk-replace;
> genuine `Danswer` prose (e.g. `web/src/app/admin/bots/SlackBotTable.tsx:114`) is rare and goes to
> **VertualAI** — see [`RENAME_AUDIT.md`](RENAME_AUDIT.md).

> **Guard test:** `backend/tests/unit/migration_safety/test_no_stray_package_paths.py` intentionally
> allowlists some of the above (`onyx:celery`, `onyx-sandboxes`, cookie prefixes, `onyx-dot-app/`).
> Update it in tandem with any rename — do not blindly strip it.

---

## 3. How we OWN the trained models (DONE — kept as historical record)

**Status: complete.** All three trained models were pulled from the original Onyx/Danswer repos
and re-pushed under our own HF namespace `bommina/om-*`, and the config in §1 now points at them.
The fork no longer depends on Onyx's/Danswer's HuggingFace repos. The connector's mirrored tag
`1.0.0` was re-created on the new repo so `CONNECTOR_CLASSIFIER_MODEL_TAG` still resolves.

The re-host mapping that was applied:

| Original (source) | Re-hosted (now used) |
|---|---|
| `onyx-dot-app/hybrid-intent-token-classifier` | `bommina/om-hybrid-intent-token-classifier` |
| `Danswer/filter-extraction-model` (tag `1.0.0`) | `bommina/om-filter-extraction-model` (tag `1.0.0`) |
| `onyx-dot-app/information-content-model` | `bommina/om-information-content-model` |

The recipe used (kept so anyone can re-run / re-mirror if needed):

```bash
# requires: pip install -U "huggingface_hub[cli]"; huggingface-cli login
for repo in \
  "onyx-dot-app/hybrid-intent-token-classifier" \
  "Danswer/filter-extraction-model" \
  "onyx-dot-app/information-content-model"; do
    name="${repo##*/}"
    huggingface-cli download "$repo" --local-dir "./hf_export/$name"
    huggingface-cli upload "bommina/om-$name" "./hf_export/$name" .
done
# then, for the connector, re-create its tag on the new repo:
#   HfApi().create_tag("bommina/om-filter-extraction-model", tag="1.0.0")
```

Config re-pointed in `backend/shared_configs/configs.py` (done):
- `CONNECTOR_CLASSIFIER_MODEL_REPO = "bommina/om-filter-extraction-model"`
- `INTENT_MODEL_VERSION = "bommina/om-hybrid-intent-token-classifier"`
- (and the commented-out information-content id in `backend/model_server/legacy/custom_models.py:36`)

Remaining verification for whoever rebuilds: rebuild the `model_server` image and confirm the
models load at startup (watch `*_model_server-1` logs for download + warm-up from `bommina/om-*`,
no 404).
