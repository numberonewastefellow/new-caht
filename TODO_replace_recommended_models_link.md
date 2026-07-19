# TODO: Replace external onyx GitHub link for LLM recommended-models with our own API-served JSON

> Status: **Planned — not started.** Do later.

## Context

The backend's "Auto mode" LLM feature reads a `recommended-models.json` config that decides
default/visible models per provider. Today the default source is an **external upstream URL**:

```
https://raw.githubusercontent.com/onyx-dot-app/onyx/main/backend/onyx/llm/well_known_providers/recommended-models.json
```

This ties our deployment to onyx's public GitHub repo — a source we don't control and don't want as a
runtime dependency. The equivalent JSON is **already bundled in our code** at
`backend/om/llm/well_known_providers/recommended-models.json`.

**Goal:** stop pointing at the git URL. Serve the bundled JSON from **our own public API endpoint** so
any client can fetch it, and change the config so the backend fetches from that API URL instead of the
git URL. In short: *git URL → our API URL*, backed by the JSON in our code.

## Task checklist

- [ ] **1. Extract a reusable bundled-JSON loader.**
  `get_recommendations()` in
  [llm_provider_options.py:44-56](backend/om/llm/well_known_providers/llm_provider_options.py#L44-L56)
  inlines the file read. Extract it into a helper (place in
  [auto_update_service.py](backend/om/llm/well_known_providers/auto_update_service.py) to avoid a new
  import cycle):

  ```python
  def load_bundled_recommendations() -> LLMRecommendations:
      """Load the recommended-models config bundled with the code."""
      json_path = pathlib.Path(__file__).parent / "recommended-models.json"
      with open(json_path, "r") as f:
          return LLMRecommendations.model_validate(json.load(f))
  ```

  Update `get_recommendations()` to call this helper for its fallback branch (replacing lines 51-55).

- [ ] **2. Add a public API endpoint that serves the bundled JSON.**
  Add to `basic_router` (prefix `/llm`) in [api.py](backend/om/server/manage/llm/api.py) — **no user
  `Depends`**, so it is public, mirroring the public pattern in
  [get_state.py:27-29](backend/om/server/manage/get_state.py#L27-L29):

  ```python
  @basic_router.get("/recommended-models", tags=PUBLIC_API_TAGS)
  def get_recommended_models() -> dict:
      """Public config of recommended/default LLM models per provider (served from bundled JSON)."""
      return load_bundled_recommendations().model_dump(mode="json")
  ```

  - Import `load_bundled_recommendations` from `auto_update_service` and `PUBLIC_API_TAGS` from
    `om.configs.constants`.
  - Publicly reachable at `{WEB_DOMAIN}/api/llm/recommended-models` (API served under `{WEB_DOMAIN}/api`,
    confirmed by OpenAPI server URL in [main.py:392](backend/om/main.py#L392)).
  - `basic_router` already mounted in [main.py:136](backend/om/main.py#L136); no wiring needed.

- [ ] **3. Replace the git URL default with our API URL.**
  In [app_configs.py:924-928](backend/om/configs/app_configs.py#L924-L928), swap the onyx git URL for
  our own API URL built from `WEB_DOMAIN` (already defined at line 82 — no import/cycle issue):

  ```python
  # Auto LLM Configuration - recommended-models config served by our own public API endpoint
  AUTO_LLM_CONFIG_URL = os.environ.get(
      "AUTO_LLM_CONFIG_URL",
      f"{WEB_DOMAIN.rstrip('/')}/api/llm/recommended-models",
  )
  ```

  Default stays non-empty, so all existing `if AUTO_LLM_CONFIG_URL` guards
  ([beat_schedule.py:214](backend/om/background/celery/tasks/beat_schedule.py#L214),
  [tasks.py:29](backend/om/background/celery/tasks/llm_model_update/tasks.py#L29),
  [auto_update_service.py:64](backend/om/llm/well_known_providers/auto_update_service.py#L64)) keep
  working. Periodic sync stays enabled, just sourced from our API. On fetch failure the existing
  fallback to the bundled file still applies. Self-hosters can still override `AUTO_LLM_CONFIG_URL`.

- [ ] **4. Update "GitHub" wording in comments/docstrings** (no behavior change; keep function name
  `fetch_llm_recommendations_from_github` to avoid churn across callers + the 6 test mocks that patch
  it):
  - [auto_update_service.py](backend/om/llm/well_known_providers/auto_update_service.py) — module
    docstring (lines 1-9), `fetch_llm_recommendations_from_github` and `sync_llm_models_from_github`
    docstrings.
  - [llm_provider_options.py:45](backend/om/llm/well_known_providers/llm_provider_options.py#L45) and
    [:315](backend/om/llm/well_known_providers/llm_provider_options.py#L315).
  - [api.py:434](backend/om/server/manage/llm/api.py#L434) comment; `get_auto_config` docstring + its
    502 error message ([api.py:497-512](backend/om/server/manage/llm/api.py#L497-L512)).
  - [tasks.py:23-27](backend/om/background/celery/tasks/llm_model_update/tasks.py#L23-L27) docstring.
  - [provisioning.py:299](backend/om/server/tenants/provisioning.py#L299) docstring.

## Files to modify

- `backend/om/configs/app_configs.py` — swap git URL → API URL default.
- `backend/om/llm/well_known_providers/auto_update_service.py` — add `load_bundled_recommendations()`;
  docstring wording.
- `backend/om/llm/well_known_providers/llm_provider_options.py` — use the new loader; wording.
- `backend/om/server/manage/llm/api.py` — new public `GET /llm/recommended-models` endpoint; wording.
- `backend/om/background/celery/tasks/llm_model_update/tasks.py` — docstring wording.
- `backend/om/server/tenants/provisioning.py` — docstring wording.

The bundled `backend/om/llm/well_known_providers/recommended-models.json` stays as-is (already present).

## Verification

1. **Static:** from `backend/`, `python -c "import om.main"` (or mypy/lint) — no import cycles, new
   imports resolve.
2. **Endpoint:** start backend and `curl http://localhost:8080/llm/recommended-models` (or
   `{WEB_DOMAIN}/api/llm/recommended-models`) — expect bundled JSON, no auth, HTTP 200.
3. **Fetch path:** `fetch_llm_recommendations_from_github()` hits the API URL and returns valid
   `LLMRecommendations`; `/admin/llm/auto-config` returns the config (was 502 on git failure).
4. **Fallback:** point `AUTO_LLM_CONFIG_URL` at an unreachable URL — `get_recommendations()` still
   returns the bundled config.
5. **Tests:** run `backend/tests/external_dependency_unit/llm/test_llm_provider_auto_mode.py` and
   `backend/tests/integration/tests/llm_auto_update/test_auto_llm_update.py` — should stay green (they
   mock the fetch fn / set `AUTO_LLM_CONFIG_URL` explicitly).
6. **Grep:** `grep -rn "raw.githubusercontent.com/onyx-dot-app" backend/om` returns nothing.

## Notes / non-goals

- Not renaming `fetch_llm_recommendations_from_github` (keeps callers + test mocks stable). Optional
  future cleanup.
- Not removing the remote-fetch mechanism or env override — the URL simply now defaults to our own API.
