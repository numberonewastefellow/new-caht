# Onyx → Om — Remaining Rename Checklist (current-tree audit)

> Generated from a full-tree audit of branch `rename_onyx_to_om` at HEAD `2ca01e56`
> (vendored `phoenix/` + `Perplexica/` excluded). This is a **status snapshot of what's
> LEFT**, not a replacement for [`RENAME_AUDIT.md`](RENAME_AUDIT.md) (authoritative renameable
> inventory) or [`DO_NOT_RENAME.md`](DO_NOT_RENAME.md) (authoritative frozen list). Read those
> two before executing anything here.

## Mapping (do not deviate)
- `onyx` → `om` · `Onyx` → `Om` (identifiers)
- **Brand PROSE** `Onyx` / `Danswer` / `DanswerAI` → **`VertualAI`** (user-facing text only — NOT "Om")
- `DANSWER_*` / `ONYX_*` env-var **names** → `OM_*`, but **freeze the string VALUE** where it's an external contract (see DO_NOT_RENAME.md)
- ⚠️ **`StandardAnswer` / `standardAnswer…` is NOT a `danswer` reference** (matches "…stan**dAnswer**"). ~66% of raw `danswer` hits are this. Never bulk-replace `danswer`.

## Headline (residual, whole repo)
- `onyx`: **4,193 matches / 705 files** — a large fraction is **frozen** or auto-generated noise (216 `# via onyx` in `requirements/*.txt`).
- `danswer`: **889 / 110** — ~66% is `StandardAnswer` false positive; genuine brand refs are few.

---

## 0. Reconcile stale tracking docs FIRST (2 discrepancies found)
- [ ] `DO_NOT_RENAME.md` / `RENAME_AUDIT.md` list `SCIM_TOKEN_PREFIX = "onyx_scim_"` as frozen, but the live code is already `SCIM_TOKEN_PREFIX = "scim_"` in `backend/om/server/scim/constants.py:43` (0 `onyx_scim_` hits). → update the docs.
- [ ] Root `pyproject.toml` still `name = "onyx"` (L6) with `include = ["onyx*", "tests*"]` (L216) — the `onyx*` glob is **broken** (package is `om`). This is also what generates all 216 `# via onyx` annotations. → covered in Group A below.

---

## GROUP A — Quick wins (low risk, no migration, no infra coordination)
- [ ] **`pyproject.toml`** (root): `name = "onyx"` → `om`; fix `include = ["onyx*", …]` → `["om*", …]`; dep `"onyx-devtools==0.5.7"` (leave if it's a real external package name — verify). Then regenerate `backend/requirements/*.txt` (removes the 216 `# via onyx` lines automatically).
- [ ] **Frontend `MinimalOnyxDocument` family** — `web/src/lib/search/interfaces.ts` (`MinimalOnyxDocument`→`MinimalOmDocument`, and `Loaded/Search/FilteredOnyxDocument`→`…OmDocument`) + ~10 importers (SearchCard, DocumentDisplay, TextViewModal, DocumentsSidebar, ChatDocumentDisplay, ExpandableContentWrapper, CompareView, ChatUI, AppInputBar, AppPage).
- [ ] **Stale brand prose → VertualAI**: `web/src/app/admin/bots/SlackBotTable.tsx:114` ("…chatting with Danswer!"); scan other user-facing strings.
- [ ] **`docker-bake.hcl`** image-tag drift (Bucket D) — align to `om/om-*`.
- [ ] Substantive docs mentioning old brand: `docs/folder-connector.md`, `README.md`, `NOTICE.md`, `remove-vespa.md`, `SANDBOX_*.md`, etc. (prose → VertualAI; do NOT touch the rename-plan docs themselves).

## GROUP B — Backend code cluster (largest; testable)
- [ ] **`backend/om/onyxbot/` package → `om/ombot/`** (359 refs): dir rename + `OnyxBot`→`OmBot`, `get_onyxbot_analytics`, `useOnyxBotAnalytics`, all Slack/Discord handler modules + their tests under `backend/tests/unit/om/onyxbot/`.
- [ ] **`onyx_*.py` module files → `om_*.py`** (+ update every importer):
  - `backend/om/connectors/confluence/onyx_confluence.py`
  - `backend/om/connectors/salesforce/onyx_salesforce.py`
  - `backend/om/connectors/slack/onyx_retry_handler.py`, `onyx_slack_web_client.py`
  - `backend/om/server/runtime/onyx_runtime.py`
  - `backend/om/tools/tool_implementations/open_url/onyx_web_crawler.py`
  - `backend/model_server/legacy/onyx_torch_model.py`
  - `backend/om/configs/onyxbot_configs.py`
  - `backend/scripts/onyx_openapi_schema.py`, `backend/scripts/debugging/onyx_db.py`, `onyx_list_tenants.py`, `onyx_redis.py`
  - tests: `test_onyx_confluence.py`, `test_onyx_web_crawler.py`
- [ ] **`backend/om/server/onyx_api/` → `server/om_api/`** (`ingestion.py`, `models.py`).
- [ ] Identifiers: `onyx_request_id` (`om/utils/middleware.py`), `_ONYX_PROVIDER_DISPLAY_NAMES`, version wire-field `onyx=` in `om/server/manage/get_state.py:141,147,153` (⚠️ frontend reads this field — rename in lockstep with `web/`).
- [ ] ⚠️ **`onyxbot_flow` DB column → `ombot_flow`** — needs an **Alembic migration** (new revision), not a sed. Touches `0001_baseline_schema.sql` + `om/db/models.py`, `db/chat.py`, `db/chat_search.py`, `server/query_and_chat/chat_backend.py`, `server/query_history/service.py`, `evals/eval.py`, `standard_answers/slack_handler.py` (8 files). Rename migration **bodies/comments only, never revision ids**.
- [ ] Stale doc-path references `from onyx.` / `onyx/backend` in READMEs + migration-safety test comments (Bucket D — docs only, package is already `om`).

## GROUP C — Deployment / infra (highest structural risk; deploy coordination)
- [ ] **Helm chart `deployment/helm/charts/onyx/` → `charts/om/`** — chart `name`, `_helpers.tpl` (`onyx.name/fullname/chart/labels/…`, ~28), and ~20 K8s resource/secret names: `onyx-postgresql`, `onyx-opensearch`(+`-master`), `onyx-redis`, `onyx-nginx-conf`, `onyx-objectstorage`, `onyx-oauth`, `onyx-smtp`, `onyx-dbreadonly`, label `app.kubernetes.io/instance: onyx`, ingress host `onyx.local`, annotation `onyx.app/nginx-config-version`. ⚠️ live-cluster identity — renaming these changes resource names.
  - Keep upstream dep repos `onyx-dot-app.github.io/{vespa-helm-charts,code-interpreter}` (frozen — external).
- [ ] **AWS ECS Fargate** `deployment/aws_ecs_fargate/cloudformation/` — all `onyx_*`-named templates (cluster/efs/acm + 9 `services/onyx_*`), `deploy.sh`, `uninstall.sh`.
- [ ] **Terraform** `deployment/terraform/modules/aws/onyx/` (dir + `main.tf`/`outputs.tf`/`variables.tf`/`versions.tf`) + aws `README.md`.
- [ ] **Compose**: 9 non-prod files still `name: onyx` (prod, prod-cloud, prod-no-letsencrypt, multitenant-dev, no-vectordb, search-testing, mcp-*); **13 `onyx-stack_*` external volume names** + `onyx-file-store-bucket` default in the main `docker-compose.yml`. ⚠️ volume-name change orphans existing data unless migrated.
- [ ] `.github/workflows`: `ONYX_GITHUB_*` secret names are **frozen** (must match repo settings); the rest (helm chart path `charts/onyx`, workflow display names, container `onyx-api_server-1`, `onyx-playwright-artifacts` bucket) rename with the infra above.

## GROUP D — `DANSWER_*` env-key pass (separate; name→OM_*, VALUE frozen)
- [ ] Rename the **names** only, keep values frozen where they're contracts: `DANSWER_POWERED`, `DANSWER_REDIS_FUNCTION_LOCK_PREFIX`, `DANSWER_API_KEY_PREFIX`, `DANSWER_API_KEY_DUMMY_EMAIL_DOMAIN`, `DANSWER_TELEMETRY_ENDPOINT`, `DANSWER_TOOL_NAME/DESCRIPTION`, `DANSWER_POSTGRES_DATA_DIR`, `DANSWER_OPENSEARCH_DATA_DIR`, `DANSWER_*_CACHE_DIR`, `DANSWER_VESPA_DATA_DIR`. ⚠️ lockstep across code + Dockerfile + compose + helm/env templates, or overrides silently revert to defaults.

## GROUP E — Frontend assets / package / tokens
- [ ] `OnyxApiClient` (75 refs) + `web/tests/e2e/utils/onyxApiClient.ts` → `OmApiClient` / `omApiClient.ts` (imported by ~30 e2e specs).
- [ ] opal icons `web/lib/opal/src/icons/onyx-logo.tsx` + `onyx-octagon.tsx` → `om-*`; `SvgOnyxLogo/Octagon` exports; update `icons/index.ts` re-exports.
- [ ] `@onyx/opal` package name → `@om/opal` (⚠️ lockstep: `web/package.json`, `web/lib/opal/package.json`, `next.config.js` `transpilePackages`, `package-lock.json`, `@opal/*` import alias).
- [ ] Tailwind design tokens `onyx-ink-*` / `onyx-chrome-*` → `om-*` (`web/tailwind-themes/tailwind.config.js` + CSS vars `--onyx-*` in `web/src/app/css/colors.css`, `widget/src/styles/theme.ts` + `widget-styles.ts`).
- [ ] `web/public/onyx.ico` asset rename (+ every reference).

---

## 🟢 FROZEN — DO NOT rename (authoritative: `DO_NOT_RENAME.md`)
Do not touch these even though they contain `onyx`/`danswer`:
- **Redis / KV / lock prefixes**: `onyx:`, `onyx_kv_store:`, `da_function_lock:`
- **Token prefixes**: `onyx_pat_` (`om/auth/constants.py`); (`onyx_scim_` already gone → `scim_`)
- **Cookies**: `onyx_tid`, `onyx_anonymous_user`
- **Data-format contract**: `ONYX_METADATA` marker + `.onyx_metadata.json` (user-authored files)
- **S3 / k8s**: `onyx-files` (S3 prefix), `onyx-sandboxes` (namespace)
- **API-key stamps**: `onyxapikey.ai`, `API_KEY__`
- **Upstream URLs / assets**: `github.com/onyx-dot-app/…`, `raw.githubusercontent.com/onyx-dot-app/…`, `onyx-dot-app.github.io/…`, the 27 `onyx-dot-app` URLs in `om/onyxbot/slack/icons.py`
- **Domains / emails**: `onyx.app`, `telemetry.onyx.app`, `cloud/docs/api.onyx.app`, `founders@onyx.app`, `@danswer.ai`/`danswerai.*`/`docs.danswer.dev`, test-fixture emails
- **Prometheus metric names** `onyx_*` (`docs/METRICS.md` = 28 hits + emit sites) — Grafana depends
- **Desktop/extension/widget public identity**: `app.onyx.desktop`, `tabbingIdentifier:"onyx"`, `onyxExtension*` storage keys, `ONYX_APP_LOADED`, `<onyx-chat-widget>` + `onyx-widget.js`, `onyxTheme`, `onyx-widget-session`, `onyx_tid`
- **Alembic revision ids** (rename bodies/comments only, never ids)
- **HF model ids** `bommina/om-*` + third-party models (nomic/gte/e5/mxbai/distilbert)
- **ALL `StandardAnswer*`** (not a danswer reference)
- **CI secrets** `ONYX_GITHUB_*`
- **Guard test**: `backend/tests/unit/migration_safety/test_no_stray_package_paths.py` allowlists some of these — update it in tandem with any rename, do not blindly strip.

---

## Verification per group
- **Backend**: `pytest backend/tests/unit`, the import-guard `test_no_stray_package_paths.py`, and `python -c "import om"`; rebuild the backend Docker image + apply the new migration (restart container — do NOT run alembic directly, per project rules).
- **Frontend**: `tsc` clean + `npm run build`; e2e specs still import the renamed client.
- **Deployment**: `helm lint` / `helm template`; `docker compose config`; a fresh-DB/fresh-index stand-up (volume/name changes orphan old data).
- **Env keys**: grep for the old name = 0 hits in code AND confirm deploy `.env`/helm values updated in lockstep.
