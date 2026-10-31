# TODO — Port: Local LLM providers (Ollama, LM Studio, OpenAI-compatible) — Lane L5

**Backlog:** `TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD` §4, row "LLM provider layer" (P1). This lane is the **local-provider subset** only.
**Process:** per-feature workflow, `TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD` §1.5. Worked example: `TODO_MD_PORT_PDFIUM.MD`.
**Status:** Phase B DONE (2026-10-30) — code + tests in worktree, uncommitted; awaiting user Docker rebuild + M1–M6 + review/commit.

> **Resuming in a new session?** Read the "Progress tracker" (§11). Pick the first unchecked item, and tick it with the date when done.

---

## 1. Scope
- **What users get:** on-prem / air-gapped gov installs can point VirtualAI at a **local LLM server**. This is the same story as Cortex for embeddings and reranking (`cortex/README.md`), but for chat models:
  - **Ollama** already works in our tree. This lane hardens it (API key on model fetch, `num_ctx` precedence, a Docker-correct default URL).
  - **LM Studio** (new): a first-class provider. Its native `/api/v1/models` endpoint gives model list, context length, and vision/reasoning flags.
  - **OpenAI-compatible** (new): any server that speaks `/v1/models` + `/v1/chat/completions`, e.g. vLLM, llama.cpp server, LocalAI, TGI's OpenAI mode, or a future Cortex chat container. API key optional.
- **What already works in ours (verified 2026-10-30):**
  - `LlmProviderNames.OLLAMA_CHAT`, Ollama display-name and vendor maps (`om/llm/constants.py`).
  - `OLLAMA_API_KEY` custom-config → Bearer header (`om/llm/factory.py::_build_provider_extra_headers`).
  - `num_ctx` from the configured max input tokens (`factory.py::_build_model_kwargs`).
  - Ollama-specific `api_base` and api-key handling in `om/llm/multi_llm.py::LitellmLLM.__init__`.
  - Ollama function-calling registrations (`om/llm/litellm_singleton/config.py`) and the Ollama history formatter (`om/chat/llm_step.py`).
  - `POST /admin/llm/ollama/available-models` (`/api/tags` + `/api/show`, syncs into `model_configuration`).
  - Web: `OllamaForm.tsx` and `OllamaOnboardingForm.tsx` (with jest test). Unit tests: `tests/unit/om/llm/test_factory.py`, `tests/unit/om/server/manage/llm/test_fetch_models_api.py`.
  - A workaround exists today: the **Custom** form with provider `openai` + `api_base` behaves like OpenAI-compatible. But there is no model fetch, `getForm.tsx` treats it as a "fake OpenAI", and `is_true_openai_model` may push it onto the Responses API. A dedicated provider fixes all three.
- **Source → target:**

| Upstream | Ours (target) | Action |
|---|---|---|
| `UP:om/llm/constants.py` (`LM_STUDIO`, `OPENAI_COMPATIBLE`, display names, aggregator set) | `backend/om/llm/constants.py` | add 2 enum members + display names; add to `WELL_KNOWN_PROVIDER_NAMES`, `AGGREGATOR_PROVIDERS` |
| `UP:om/llm/well_known_providers/constants.py` (`LM_STUDIO_PROVIDER_NAME`, `LM_STUDIO_API_KEY_CONFIG_KEY`, `OPENAI_COMPATIBLE_PROVIDER_NAME`) | `backend/om/llm/well_known_providers/constants.py` | add constants |
| `UP:om/llm/well_known_providers/llm_provider_options.py` (dynamic `[]` model lists, display names) | `backend/om/llm/well_known_providers/llm_provider_options.py` | add both providers to `_get_provider_to_models_map()` and `get_provider_display_name()` |
| `UP:om/llm/api_surfaces.py` + `multi_llm.py` (LM Studio `/v1` coercion and empty key; OpenAI-compatible → `custom_llm_provider="openai"`, placeholder key, `/v1` coercion) | `backend/om/llm/multi_llm.py` + new `backend/om/llm/local_providers.py` | **rebuild small**: one helper `resolve_local_provider_routing(provider, api_base, api_key) -> (custom_llm_provider, api_base, api_key)`. Do not port the full API-surface framework (that is for gateways, out of scope) |
| `UP:om/llm/custom_config_mapping.py` (LM Studio key → `api_key`) | `backend/om/llm/multi_llm.py` custom-config loop | add an `elif` branch, same style as the existing Ollama branch |
| `UP:om/llm/factory.py` (special-API-key providers) | `backend/om/llm/factory.py` | extend `_build_provider_extra_headers` only if LiteLLM's `api_key` is not enough (verify in Phase B) |
| `UP:om/llm/cost.py` `_LOCALLY_HOSTED_PROVIDERS` | `backend/om/llm/cost.py` | local providers → cost 0 (only if our cost path otherwise logs "unknown model" noise; check first) |
| `UP:om/server/manage/llm/api.py` `get_lm_studio_available_models`, `get_openai_compatible_server_available_models`, `_get_openai_compatible_server_response`, `_resolve_api_key` | `backend/om/server/manage/llm/api.py` | add `get_lm_studio_available_models` + `get_openai_compatible_available_models` (names per §1a), in our style (`current_admin_user`, `HTTPException`, `provider_name` sync via `om/db/llm.py::sync_model_configurations`) |
| `UP:om/server/manage/llm/models.py` (`LMStudioModelsRequest/FinalModelResponse`, `OpenAICompatibleModelsRequest/FinalModelResponse`) | `backend/om/server/manage/llm/models.py` | add 4 Pydantic models; add optional `api_key` to `OllamaModelsRequest` |
| `UP:om/server/manage/llm/utils.py` `lm_studio_capability_enabled`, `is_non_chat_model` | `backend/om/server/manage/llm/utils.py` | add as `parse_lm_studio_capability` (utils) and `local_providers.is_non_chat_model_id` (see §1a) |
| `UP:web/src/sections/modals/languageModels/LMStudioModal.tsx`, `OpenAICompatibleModal.tsx`, `UP:web/src/lib/languageModels/svc.ts` | `web/src/app/admin/configuration/llm/forms/LMStudioForm.tsx`, `OpenAICompatibleForm.tsx` (new), `.../llm/utils.ts` | **rebuild in our form framework**; never paste upstream UI (§4) |

- **Dropped / out of scope (later lanes):** bifrost, portkey, vercel AI gateway, nebius token factory, LiteLLM-proxy model fetch, typesafe; price tables and cost overrides; token budget; cancellation; decision / router models and `/model-routing`; the full model catalog and capabilities rewrite (`UP:om/llm/model_catalog.py`, `model_capabilities.py`); upstream's permission system (`require_permission(MANAGE_LLMS)`). We keep `current_admin_user`.
- **Dependencies:** none on other backlog items. Uses `httpx` and `litellm==1.81.6`, both already pinned.

## 1a. Naming & structure (ours)
Upstream is **reference only**. Every folder, file, identifier, route and component below is **ours**, named after our existing Ollama pieces (`om/llm/`, `/admin/llm/ollama/available-models`, `OllamaForm`, `fetchOllamaModels`, `OllamaModelsRequest`). Route prefix `/admin/llm` is not in our rename map (`rename-audit/DECISIONS.md`, `backend/tests/route_rename/endpoint_catalog.py` `ROUTE_RENAME_MAP`), so new routes sit beside our Ollama route.

| Upstream reference concept | OURS (folder / file / identifier / route / component) | Reason |
|---|---|---|
| API-surface framework (`api_surfaces.py`, surface enum, static/selectable maps) | `backend/om/llm/local_providers.py` with `LOCAL_PROVIDER_NAMES`, `resolve_local_provider_routing()` | we only need local routing; one small module named for what it does |
| `/v1` base coercion inlined in `multi_llm.py` (twice) | `local_providers.normalize_openai_v1_base(url)` | single shared helper used by runtime and fetch |
| LM Studio "strip `/v1`" for the native endpoint | `local_providers.strip_openai_v1_suffix(url)` | explicit inverse of the helper above |
| `is_non_chat_model` | `local_providers.is_non_chat_model_id(model_id)` | `_id` makes clear it is a name heuristic, not a capability lookup |
| `lm_studio_capability_enabled` | `om/server/manage/llm/utils.py::parse_lm_studio_capability(value)` | verb-first, matches our `generate_ollama_display_name` style |
| `_resolve_api_key` (by provider id) | `api.py::_resolve_stored_api_key_for_fetch(api_key, api_key_changed, provider_name, api_base, db_session)` | ours keys sync by `provider_name`, and the name says when it applies |
| `custom_config_mapping.py` table | branch in our existing custom-config loop in `LitellmLLM.__init__` | no new module; same place as our Ollama branch |
| `LlmProviderNames.LM_STUDIO` / `OPENAI_COMPATIBLE` | same members in `om/llm/constants.py` (values `lm_studio`, `openai_compatible`) | value = stored DB string and LiteLLM-adjacent; enum style matches `OLLAMA_CHAT` |
| `LM_STUDIO_API_KEY_CONFIG_KEY` | `LM_STUDIO_API_KEY_CONFIG_KEY = "LM_STUDIO_API_KEY"` in `well_known_providers/constants.py` | mirrors our `OLLAMA_API_KEY_CONFIG_KEY` |
| `POST .../lm-studio/available-models` | `POST /admin/llm/lm-studio/available-models` → `get_lm_studio_available_models` | mirrors `/admin/llm/ollama/available-models` → `get_ollama_available_models` |
| `POST .../openai-compatible/available-models` | `POST /admin/llm/openai-compatible/available-models` → `get_openai_compatible_available_models` | same pattern; kebab-case path like our others |
| `_get_openai_compatible_server_response` / generic fetch | `api.py::_fetch_models_json(url, headers, timeout)` | one HTTP helper for all three local fetches |
| LM Studio / OpenAI-compatible request and response models | `LMStudioModelsRequest`, `LMStudioFinalModelResponse`, `OpenAICompatibleModelsRequest`, `OpenAICompatibleFinalModelResponse` in `om/server/manage/llm/models.py` | follow our `OllamaModelsRequest` / `OllamaFinalModelResponse` naming |
| Typed model-sync entry | reuse our dict-based `sync_model_configurations(provider_name=...)` | no new type; our sync already exists |
| `LMStudioModal.tsx` / `OpenAICompatibleModal.tsx` (sections/modals) | `web/src/app/admin/configuration/llm/forms/LMStudioForm.tsx`, `OpenAICompatibleForm.tsx` | our forms live in `forms/` and end in `Form` |
| Onboarding modal entries | `web/src/refresh-components/onboarding/forms/LMStudioOnboardingForm.tsx`, `OpenAICompatibleOnboardingForm.tsx` | mirrors `OllamaOnboardingForm.tsx` |
| Web fetch service (`lib/languageModels/svc.ts`) | `fetchLMStudioModels`, `fetchOpenAICompatibleModels` in `.../llm/utils.ts`; params `LMStudioFetchParams`, `OpenAICompatibleFetchParams` in `interfaces.ts` | mirrors `fetchOllamaModels` / `OllamaFetchParams` |
| Web provider enum | `LLMProviderName.LM_STUDIO`, `LLMProviderName.OPENAI_COMPATIBLE` | our existing enum |
| Tests | `tests/unit/om/llm/test_local_providers.py`, new classes in `tests/unit/om/server/manage/llm/test_fetch_models_api.py` | our test tree layout |
| Cross-verification fixtures (§10a) | `backend/tests/unit/om/llm/fixtures/local_providers/*.json` | our fixture convention (as in the PDFium port) |

## 2. DB migration plan
**None needed.** Reasons:
- `llm_provider.provider` is a free `String` column (`om/db/models.py::LLMProvider`). The Pydantic validator only strips and lowercases it. `"lm_studio"` and `"openai_compatible"` store as-is.
- Optional API keys live in the existing `custom_config` JSONB (`LM_STUDIO_API_KEY`) or the existing `api_key` column (OpenAI-compatible).
- Model capabilities use the existing `model_configuration` columns (`max_input_tokens`, `display_name`) plus the existing `llm_model_flow` rows (`CHAT`, `VISION`).
- **Reasoning flag:** upstream persists it as a `REASONING` flow type. Ours computes `supports_reasoning` at view time (`server/manage/llm/models.py:274`). Decision: **do not add a `REASONING` flow** in this lane. We return `supports_reasoning` from the fetch endpoints for display only. (If it is ever needed: `llm_model_flow.llm_model_flow_type` is `VARCHAR(20)`, non-native enum, so adding `"reasoning"` would still not need a migration.)
- Our current Alembic head: `0001_om_baseline` (only file in `backend/alembic/versions/`). If a later Phase B finding forces a change, the migration would be `revision="0002_llm_local_providers"` (24 chars), `down_revision="0001_om_baseline"`. L5 is the only lane allowed one. Never run alembic manually; the container applies it on restart.

## 3. Model mapping
- **Provider strings (stored in `llm_provider.provider`):** `ollama_chat` (existing), `lm_studio` (new), `openai_compatible` (new).
- **LiteLLM routing at call time (`multi_llm.py`):**
  - `lm_studio` → LiteLLM's native `lm_studio/<model>` prefix. Coerce `api_base` to end with `/v1`. Always pass `api_key` (empty string if unset), because LiteLLM otherwise injects a fake key that LM Studio rejects. Verify the `lm_studio` prefix exists in litellm 1.81.6; fallback is `custom_llm_provider="openai"`.
  - `openai_compatible` → `custom_llm_provider="openai"`, model `openai/<model>`. Coerce `api_base` to `/v1`. Placeholder key `"not-needed"` when none is set. Must **not** go through `is_true_openai_model` / Responses API (it already returns False for unknown providers; add a test).
  - Max tokens: LiteLLM's model map has no entry for these, so `max_input_tokens` must come from `model_configuration`, which the fetch endpoints fill. Check `get_llm_max_input_tokens` honours it before the `GEN_AI_MODEL_FALLBACK_MAX_TOKENS` fallback.
- **New API routes** (admin router, prefix `/admin/llm`, not renamed per `backend/tests/route_rename/endpoint_catalog.py`):
  - `POST /admin/llm/lm-studio/available-models` — body `{api_base, api_key?, api_key_changed?, provider_name?}` → `[{name, display_name, max_input_tokens, supports_image_input, supports_reasoning}]`. Calls `GET {base}/api/v1/models`, strips a trailing `/v1`, keeps `type == "llm"`.
  - `POST /admin/llm/openai-compatible/available-models` — body `{api_base, api_key?, api_key_changed?, provider_name?}` → same shape. Calls `GET {base}/v1/models`, skips non-chat ids (embed/rerank/tts/whisper…). Vision comes from `model_supports_image_input`, else False, and the admin can tick it.
  - `POST /admin/llm/ollama/available-models` gains optional `api_key` (sent as Bearer to `/api/tags` and `/api/show`, for Ollama behind an auth proxy). Upstream fix ported: `num_ctx` from `/api/show` wins over `<arch>.context_length`.
  - **Masked-key rule:** when editing, the form sends a masked key. With `api_key_changed=False`, resolve the stored key by `provider_name` and use it only if the stored `api_base` equals the request's (our `_resolve_stored_api_key_for_fetch`, keyed by `provider_name`).
- **Route-rename snapshots:** new endpoints only add operations. `test_no_missing_endpoints` checks for removals, so no snapshot edit is needed.
- **Env vars:** none planned. If one becomes necessary (e.g. fetch timeout), add it only inside a `# --- llm-local-providers ---` block in `om/configs/app_configs.py`.
- **OpenSearch / Celery / Redis:** untouched. No re-index.

## 4. UI refactor (our design system)
Rebuild in **our** admin LLM form framework (`web/src/app/admin/configuration/llm/`), modelled on our `OllamaForm.tsx` and `OpenRouterForm.tsx`. Never paste upstream modal code.
- **New forms:**
  - `forms/LMStudioForm.tsx`: Display name, API base (default `http://host.docker.internal:1234`), optional API key (`PasswordInputTypeInField`, stored in `custom_config.LM_STUDIO_API_KEY`), auto-fetch models.
  - `forms/OpenAICompatibleForm.tsx`: Display name, API base (required, placeholder `http://host.docker.internal:8000/v1`), optional API key (`api_key`), `FetchModelsButton`, plus manual model entry for servers whose `/v1/models` is missing.
  - Both reuse `FormWrapper`, `DisplayNameField`, `DisplayModels`, `SingleDefaultModelField`, `AdvancedOptions`, `FormActionButtons`, and `formUtils.ts`. No new generic components.
- **Wiring:**
  - `interfaces.ts`: `LLMProviderName.LM_STUDIO`, `OPENAI_COMPATIBLE`, fetch-param types.
  - `forms/getForm.tsx`: both switches.
  - `LLMConfiguration.tsx`: two new `PROVIDER_TILES`.
  - `utils.ts`:
    - `fetchLMStudioModels`, `fetchOpenAICompatibleModels`
    - `fetchModels` switch and `canProviderFetchModels`
    - `AGGREGATOR_PROVIDERS`
    - `getProviderIcon` fallback, using a generic icon such as `SvgCpu` from `@opal/icons`. No upstream brand assets.
- **Colours:** `providerColors.ts` holds per-brand Tailwind colours for existing tiles (keep as-is). The two new tiles have no brand, so they use the **accent variables**, e.g. `bg-[var(--virtualai-accent-subtle)]`, `text-[var(--virtualai-accent,var(--theme-primary-05))]`, a border/gradient from `--theme-primary-04/06`. These adapt to light/dark and Ocean/Emerald/Violet. No hardcoded hex.
- **Docker hint (shown in all three local forms):** helper text: "Inside Docker, `localhost` is the container. Use `http://host.docker.internal:<port>` for a server on the host." Compose already maps `host.docker.internal:host-gateway` for `api_server`, `background`, `pulse_worker` (`deployment/docker_compose/docker-compose.yml`), so this also works on Linux hosts.
- **Ollama default URL:** change `OllamaForm.tsx` `DEFAULT_API_BASE` from `http://127.0.0.1:11434` to `http://host.docker.internal:11434`. This is an intended behaviour change for **new** forms only; existing providers keep their stored URL.
- **Onboarding (first-run):** add LM Studio + OpenAI-compatible cards to `web/src/refresh-components/onboarding/forms/getOnboardingForm.tsx` with two small onboarding forms mirroring `OllamaOnboardingForm.tsx` (open question Q2).
- No admin-nav change (same LLM page). Not workflow-editor related, so the dual-editor rule does not apply. Per-agent / per-step model pickers list providers by `LLMProvider.name`, so new providers appear automatically.

## 5. Enterprise parts
None. All of this is open-source upstream code; no `ee/` folders.

## 6. Reuse first
- Model sync: reuse `om/db/llm.py::sync_model_configurations` (already used by Ollama/OpenRouter/Bedrock).
- Display names / vendor grouping: reuse `generate_ollama_display_name`, `extract_vendor_from_model_name`, `is_reasoning_model` in `om/server/manage/llm/utils.py`.
- New shared module `om/llm/local_providers.py` (small, pure): `LOCAL_PROVIDER_NAMES`, `normalize_openai_v1_base(url)`, `resolve_local_provider_routing(...)`, `is_non_chat_model_id(model_id)`, `strip_openai_v1_suffix(url)`. Both the runtime (`multi_llm.py`) and the fetch endpoints use it, so the `/v1` logic exists once. A future Cortex chat service or gateway lane reuses it.
- HTTP fetch helper: one `_fetch_models_json(url, headers, timeout)` in `api.py`, shared by the three local endpoints (Ollama's `_get_ollama_available_model_names` moves onto it).

## 7. Existing features touched (regression scope)

| Feature / caller | Path | Risk | Covered by |
|---|---|---|---|
| OpenAI, Anthropic, Azure, Bedrock, Vertex, OpenRouter, Custom providers at runtime | `om/llm/multi_llm.py::LitellmLLM.__init__` / `_completion` | new branches must not change kwargs for other providers | new `test_local_providers_routing.py` asserts **unchanged** `model`, `base_url`, `custom_llm_provider`, `api_key` for each existing provider; existing `test_multi_llm.py` |
| Responses-API selection | `om/llm/utils.py::is_true_openai_model` | `openai_compatible` must stay on chat-completions | extend `tests/unit/om/llm/test_true_openai_model.py` |
| Ollama runtime (headers, `num_ctx`, `api_base`) | `om/llm/factory.py`, `multi_llm.py` | unchanged | existing `tests/unit/om/llm/test_factory.py` (Ollama cases) |
| Ollama model fetch + sync | `api.py::get_ollama_available_models` | api-key + `num_ctx` change | existing `test_fetch_models_api.py::TestGetOllamaAvailableModels` + new cases |
| Provider upsert / test / delete / default / default-vision | `api.py` `PUT /provider`, `POST /test`, `POST /provider/{id}/default*` | none (string provider) | new upsert + `/test` (mock LLM) cases for both new providers; existing `tests/external_dependency_unit/llm/test_llm_provider*.py` |
| Default-model selection | `om/db/llm.py`, `LLMConfiguration.tsx` | new provider can be default | manual check M3; existing external-dependency tests |
| Per-agent and per-workflow-step model override | `factory.py::get_llm_for_agent`, `om/workflows/workflow_engine.py:451` (by provider **name**) | none expected | manual check M4 (one workflow step pinned to the local provider) |
| Image-input capability checks | `om/llm/utils.py::model_supports_image_input` (DB VISION flow first, LiteLLM fallback) | new providers rely on DB flow | new test: synced `supports_image_input=True` → VISION flow → True; LiteLLM fallback False without crash |
| Reasoning detection / temperature | `model_is_reasoning_model` | unknown provider prefix must return False, not raise | new unit case |
| Max input tokens | `om/llm/utils.py` max-token chain | must use `model_configuration.max_input_tokens` | new unit case |
| Cost tracking | `om/llm/cost.py` | no error log spam for unknown local models | new unit case (cost 0 / None) |
| Provider display names in chat model picker | `llm_provider_options.py::get_provider_display_name` | new names | extend `tests/unit/om/llm/test_llm_provider_options.py` |
| Admin LLM page + onboarding (web) | `web/src/app/admin/configuration/llm/*`, `refresh-components/onboarding/forms/*` | type changes in shared enums/switches | `npx tsc --noEmit`; existing jest `CustomForm.test.tsx`, `OllamaOnboardingForm.test.tsx` |

**Intended behaviour changes:** new Ollama forms default to `host.docker.internal`; Ollama fetch accepts an optional API key; `num_ctx` from `/api/show` takes precedence.

**Manual in-app checks (user, after Docker rebuild):**
- M1: Ollama on the host (`ollama serve`, pull a small model) → Admin › LLM › Ollama → URL `http://host.docker.internal:11434` → models listed → save → chat answers.
- M2: LM Studio server on `:1234` → LM Studio tile → models with vision/reasoning flags → save → chat; repeat once with API auth enabled.
- M3: OpenAI-compatible (e.g. vLLM or llama.cpp `--api`) → fetch models → set as **default** → new chat uses it.
- M4: pin one agent and one workflow step to the local provider; run; the other steps still use the cloud default.
- M5: existing OpenAI/Azure provider still chats; the "Test" button still passes.
- M6: switch accent theme (Default/Ocean/Emerald/Violet) × light/dark → the new tiles stay readable.

## 8. Tests
- **New unit tests:**
  - `backend/tests/unit/om/llm/test_local_providers.py`: `/v1` normalisation, routing tuple per provider, non-chat filter, no-change for existing providers.
  - `backend/tests/unit/om/server/manage/llm/test_fetch_models_api.py`: add `TestGetLMStudioAvailableModels` and `TestGetOpenAICompatibleAvailableModels` (httpx mocked: happy path, `/v1` suffix handling, empty list → 400, masked-key resolution, sync to DB), plus Ollama api-key / `num_ctx` cases.
  - `backend/tests/unit/om/server/manage/llm/test_llm_provider_utils.py`: `parse_lm_studio_capability` (bool, options object, `["off"]` only).
  - `backend/tests/unit/om/llm/test_multi_llm.py`: `litellm.completion` kwargs for `lm_studio` and `openai_compatible` (mocked).
- **Web:** `npx tsc --noEmit` (lint and local `next build` are broken on this machine). Optional jest for the two new forms, using paste not type (slow typing gotcha).
- Note pre-existing unrelated failures separately (e.g. `test_websearch_utils.py` cp1252 on Windows).

## 9. Gates
- [x] Naming grep: no upstream product name in new or changed files. (2026-10-30, see tracker "B8 Gates")
- [x] `pytest backend/tests/unit/om/llm backend/tests/unit/om/server/manage/llm backend/tests/unit/om/db/test_llm_sync.py` (2026-10-30: 341 passed, 4 pre-existing failures)
- [x] `pytest backend/tests/unit/migration_safety` (2026-10-30: only the expected added module; baseline regenerated at integration). **Do not touch** `snapshots/baseline.json`. If the new module `om/llm/local_providers.py` makes it fail, stop and ask the integrator; don't edit it here.
- [x] `backend/tests/route_rename` (new routes are additive). (2026-10-30: 2 pre-existing failures, none LLM)
- [x] `npx tsc --noEmit` in `web/`. (2026-10-30: clean except the known dotenv noise)
- [ ] `python -I rename-audit/build_inventory.py --check`: **not run by this lane** (it rewrites tracked files); the user runs it at commit time.

## 10. Rollout
- Files this lane owns: `backend/om/llm/constants.py`, `backend/om/llm/local_providers.py` (new), `backend/om/llm/multi_llm.py` (local-provider branches only), `backend/om/llm/factory.py` (if needed), `backend/om/llm/cost.py` (local set), `backend/om/llm/well_known_providers/{constants,llm_provider_options}.py`, `backend/om/server/manage/llm/{api,models,utils}.py`, `web/src/app/admin/configuration/llm/**`, `web/src/refresh-components/onboarding/forms/**` (LLM cards), and the tests above.
- Shared hot files: `om/configs/app_configs.py` only inside `# --- llm-local-providers ---` (not expected to be needed). No change to `baseline.json`. **No new dependencies** (`httpx`, `litellm` already present).
- The user reviews and rebuilds the Docker images (`api_server`, `background`, `pulse_worker`, `web_server`). No migration, no re-index. No commit unless asked.

## 10a. Post-implementation cross-verification (after Phase B)
Goal: show that our clean-room code behaves like the upstream reference on the cases that matter, without copying or importing it.
- **How to run:**
  - Build a case table from **reading** the upstream reference: inputs plus expected outputs.
  - Store it as JSON fixtures under `backend/tests/unit/om/llm/fixtures/local_providers/`: `url_cases.json`, `ollama_tags.json` + `ollama_show_*.json`, `lm_studio_models.json`, `openai_models.json`, `routing_cases.json`.
  - Parametrised tests in `backend/tests/unit/om/llm/test_local_providers_crosscheck.py` feed them to **our** functions. httpx is mocked; no network.
  - **Never** import, vendor or path-add the upstream tree, and never put its path in our repo. Fixtures are hand-written payloads (scrub any upstream names).
  - Record each case's pass/differs result in the tracker below. An intentional difference gets a one-line reason here.
- **Cases:**

| Area | Input → expected (ours) |
|---|---|
| `normalize_openai_v1_base` | `http://h:8000` → `http://h:8000/v1`; `http://h:8000/` → `.../v1`; `http://h:8000/v1` → unchanged; `http://h:8000/v1/` → `.../v1`; `  http://h:1234  ` → trimmed + `/v1`; `http://h/proxy/v1` → unchanged |
| `strip_openai_v1_suffix` (LM Studio native) | `http://h:1234/v1` → `http://h:1234`; `http://h:1234/` → `http://h:1234`; `""` → 400 "API base URL is required" |
| OpenAI-compatible list URL | base `http://h:8000` → GET `http://h:8000/v1/models`; base `http://h:8000/v1` → GET `http://h:8000/v1/models` (no `/v1/v1`) |
| Ollama `/api/tags` + `/api/show` | 3 tags (chat model, vision model with `capabilities:["completion","vision"]`, embedding-only model) → 2 results, vision flag right, embedding skipped; `num_ctx` present → wins over `<arch>.context_length`; `/api/show` 500 for one model → still listed with `max_input_tokens=None`; empty tags → 400 |
| LM Studio `/api/v1/models` | entries `type:"llm"` (vision `true`), `type:"llm"` (reasoning `{"allowed_options":["off","on"]}`), `type:"llm"` (reasoning `{"allowed_options":["off"]}`), `type:"embedding"` → 3 results, reasoning true/true/false as appropriate, embedding skipped; missing `key` skipped; `display_name` fallback to key; `max_context_length` → `max_input_tokens` |
| OpenAI `/v1/models` | `{"data":[{"id":"llama-3.1-8b"},{"id":"text-embedding-3-small"},{"id":"whisper-1"},{"id":"qwen2.5-vl","context_length":32768}]}` → 2 chat models sorted by name, `context_length` mapped; empty `data` → 400 |
| Masked key | edit with masked key + same api_base → stored key used; changed api_base → stored key **not** used |
| LiteLLM routing (`resolve_local_provider_routing` + `_completion` kwargs, `litellm.completion` mocked) | `lm_studio` + `http://host.docker.internal:1234` → model `lm_studio/<m>`, base `.../v1`, `api_key=""`; `openai_compatible` no key → `custom_llm_provider="openai"`, model `openai/<m>`, `api_key="not-needed"`, base `.../v1`, **not** `openai/responses/...`; `openai_compatible` with key → key passed through; `ollama_chat` → unchanged from today (`ollama_chat/<m>`, raw base, Bearer header); `openai`, `azure`, `anthropic`, `bedrock`, `vertex_ai`, `openrouter` → byte-identical kwargs before/after (golden capture taken **before** B2) |

## 11. Progress tracker
- [x] 2026-10-30 Phase A research: upstream provider modules/routes/forms, our LLM layer, DB model (free-string provider, head `0001_om_baseline`), web admin forms, Docker host mapping
- [x] 2026-10-30 Phase A plan doc written (this file)
- [x] 2026-10-30 User approval of this plan (+ answers to §12, recorded there)
- [x] 2026-10-30 B1 `om/llm/local_providers.py` + constants + display names + provider options. Deviation: LM_STUDIO/OPENAI_COMPATIBLE NOT added to `WELL_KNOWN_PROVIDER_NAMES` (that list feeds `/built-in/options` → first-run onboarding cards; Q2 = admin page only). Added to `AGGREGATOR_PROVIDERS`, `PROVIDER_DISPLAY_NAMES`, `DYNAMIC_LLM_PROVIDERS`, provider-options map/display names.
- [x] 2026-10-30 B2 `multi_llm.py` routing via `resolve_local_provider_routing` (`_litellm_model_prefix`; LM Studio custom-config key branch). litellm 1.81.6 has native `lm_studio` provider (used). Note: litellm's lm_studio transform turns an empty key into `fake-api-key` (harmless when LM Studio auth is off; real key passed when set).
- [x] 2026-10-30 B3 Verified: max tokens = `model_configuration.max_input_tokens` first (`get_max_input_tokens_from_llm_provider`); image input = DB VISION flow first; cost.py already returns 0 + debug log for unknown models (no change); `model_is_reasoning_model` printed LiteLLM "Provider List" noise for `openai_compatible` on every call → fixed via `local_providers.litellm_lookup_provider` (looks it up as `openai`). factory.py unchanged (LiteLLM `api_key` is enough).
- [x] 2026-10-30 B4 API: `POST /admin/llm/lm-studio/available-models`, `POST /admin/llm/openai-compatible/available-models`; shared `_fetch_models_json`, `_resolve_stored_api_key_for_fetch`, `_sync_fetched_models`, `_bearer_headers`; Ollama gains optional `api_key`/`api_key_changed` (Bearer on tags+show) + `num_ctx` precedence; Q4: `_ensure_fetch_target_allowed` blocks private/internal targets on all three fetches when `MULTI_TENANT=true` (reuses `om/utils/url.py` validator).
- [x] 2026-10-30 B5 Backend unit tests green: `tests/unit/om/llm` + `server/manage/llm` + `db/test_llm_sync.py` = 307 passed, 4 failed (PRE-EXISTING, same on main tree: test_model_is_reasoning, test_model_map partial match, test_true_openai o1_preview/o1_mini — litellm model-map data).
- [x] 2026-10-30 B6 Web: `LLMProviderName.LM_STUDIO/OPENAI_COMPATIBLE`, fetch-param + response types, `fetchLMStudioModels`/`fetchOpenAICompatibleModels` (shared `fetchLocalServerModels`), `fetchModels`/`canProviderFetchModels`/`AGGREGATOR_PROVIDERS`, icons `SvgCpu`/`SvgServer`, `getForm` both switches, 2 `PROVIDER_TILES`, accent-var tile colours (`providerColors.ts` `localServerAccentColor`), `LMStudioForm.tsx`, `OpenAICompatibleForm.tsx` (fetch + manual model entry), `LOCAL_SERVER_DOCKER_HINT`; Ollama default `http://host.docker.internal:11434` + hint + sends key/`api_key_changed` on fetch.
- [x] 2026-10-30 B7 DROPPED per Q2 (admin page only); no onboarding cards; providers kept out of `WELL_KNOWN_PROVIDER_NAMES` so onboarding does not list them.
- [x] 2026-10-30 B8 Gates: naming grep 0 hits; pytest llm+manage/llm+db sync 341 pass / 4 pre-existing fail; migration_safety golden snapshot fails ONLY on added module `<root>.llm.local_providers` (baseline.json untouched, integrator to regen); route_rename 2 fails pre-existing (80 missing legacy/EE endpoints, none LLM) — NOTE that test run rewrites tracked `snapshots/before/*`, reverted; `npx tsc --noEmit` clean except dotenv noise; jest CustomForm 7 fails pre-existing (same 7/7 on main tree), OllamaOnboardingForm passes.
- [x] 2026-10-30 C0 Golden capture BEFORE B2: `fixtures/local_providers/golden_existing_provider_kwargs.json` (10 cases: openai, openai+custom base, azure, anthropic, bedrock, vertex, openrouter, ollama ×2, mistral; plain + tools) via `test_local_providers_routing.capture_completion_kwargs`; asserted byte-equal after B2 — 10/10 pass.
- [x] 2026-10-30 C1 Fixtures written by hand from reading the reference (`url_cases`, `ollama_tags` + 3 `ollama_show_*`, `lm_studio_models`, `openai_models`, `routing_cases`); no upstream import; names scrubbed. Scratch scripts in d:/tmp/upgrade-xverify/llm-local-providers/.
- [x] 2026-10-30 C2 URL normalisation cases — result: 12/12 PASS (normalize ×6, strip ×2, empty LM Studio base → 400, OpenAI-compat + LM Studio list URLs, no /v1/v1).
- [x] 2026-10-30 C3 Ollama tags/show parsing cases — result: 3/3 PASS (embedding skipped, vision flag, num_ctx 8192 wins over 131072, /api/show 500 → listed with None, empty tags → 400).
- [x] 2026-10-30 C4 LM Studio `/api/v1/models` parsing cases — result: PASS (3 llm kept, embedding + keyless skipped, reasoning true/true(heuristic-free)/false, display_name fallback, max_context_length mapped).
- [x] 2026-10-30 C5 OpenAI `/v1/models` parsing + masked-key cases — result: 5/5 PASS (2 chat models sorted, context_length mapped, empty → 400; masked key used for same base incl. /v1-less spelling, NOT sent to changed host).
- [x] 2026-10-30 C6 LiteLLM routing per provider + golden no-change — result: PASS: 5 routing cases (lm_studio ±key, openai_compatible ±key, ollama unchanged) + 10/10 existing-provider golden kwargs byte-identical.
- [x] 2026-10-30 C7 Intentional differences: (a) LM Studio reasoning uses the name heuristic only when `capabilities.reasoning` is absent (reference ORs both); (b) OpenAI-compatible vision is always False at fetch (no catalog in our tree; admin ticks it); (c) also reads `max_model_len` (vLLM) as fallback for context; (d) masked key resolved by `provider_name` and /v1-normalised base compare; (e) providers not in onboarding (Q2).
- [x] 2026-10-30 Docker rebuild (api, background, web, pulse) + headless Chrome walk-through: Admin → Language Models shows the LM Studio and OpenAI-Compatible tiles; both forms open (Docker hint, manual model entry). With no local server running, the LM Studio fetch said only "[Errno 101] Network is unreachable" (httpx reports the last address tried, IPv6). `_fetch_models_json` now explains connect / timeout / HTTP status / non-JSON failures (`_describe_fetch_error`, test `test_connect_error_explains_unreachable_server`; `tests/unit/om/server/manage/llm` 76 passed).
- [ ] User: manual checks M1–M4 against a real LM Studio / vLLM server (save provider, chat with it)
- [ ] User: review + commit (run `build_inventory.py --check` first)
- [ ] Mirror status in the backlog table (`TODO_MD_UPSTREAM_PORT_CONNECTORS_AND_FEATURES.MD` §4)

## 12. Open questions for the user
**Decided 2026-10-30:** (1) yes, `host.docker.internal` defaults; (2) admin page only, NOT first-run onboarding (B7 dropped); (3) Cortex chat-model profile = later follow-up; (4) YES, block private-IP targets on the fetch endpoints when `MULTI_TENANT=true`; (5) LM Studio reasoning flag display-only; (6) generic icons; (7) leave existing Custom-openai providers untouched.

1. **Default URLs:** OK to switch the Ollama form default to `http://host.docker.internal:11434`, with LM Studio `:1234` and OpenAI-compatible `:8000/v1` similarly? (Bare-metal dev installs would then need to edit the URL.)
2. **Onboarding:** add LM Studio + OpenAI-compatible to the first-run onboarding cards, or the admin page only?
3. **Cortex chat model:** should we also add an optional `cortex_llm_vllm` compose profile (vLLM serving a chat model) and pre-fill the OpenAI-compatible form with `http://cortex_llm:8000/v1`? That would be a separate small follow-up, not in this lane.
4. **SSRF in multi-tenant mode:** the fetch endpoints (like today's Ollama one) accept any URL, including private IPs, because local servers need that. Keep it open for admins, or block private ranges when `MULTI_TENANT=true`?
5. **Reasoning flag:** fine to show LM Studio's `supports_reasoning` for display only (no persisted `REASONING` flow, no migration)?
6. **Icons:** a generic CPU/server icon for LM Studio and OpenAI-compatible, or do you want a custom SVG made?
7. **Existing "Custom + openai + api_base" providers:** leave as they are (recommended), or offer a one-click "convert to OpenAI-compatible" later?
