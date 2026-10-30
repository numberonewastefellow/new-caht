# TODO: Port build/image optimizations from upstream

**Status:** Phase A, plan written 2026-10-30. **Waiting:** user approval. Start only after batch 1 (`upgrade/batch1-review`) has been tested in Docker, so a build problem can't be mistaken for a feature bug.

Upstream is **reference only**. Every change below is written by us, in our files and in our style.

## 1. Scope
| # | Change | Our file(s) | Reference idea | Expected gain |
|---|---|---|---|---|
| B1 | Install only the headless Chromium shell | `backend/Dockerfile:86` `playwright install chromium` → `playwright install --only-shell chromium` | Upstream skips the full headed browser | about −360 MB |
| B2 | jemalloc allocator for all backend processes | `backend/Dockerfile`: add `libjemalloc2` to the runtime apt install; `ENV LD_PRELOAD=libjemalloc.so.2` **after** the last `RUN` | Lower and steadier memory for long-running Python | Lower RSS for 4 uvicorn workers plus celery |
| B3 | Drop the unused `nltk` | `backend/Dockerfile:120-124` (download step); `nltk` in `pyproject.toml` / `default.txt` | No `om` code imports it (checked 2026-10-30) | Size and build time |
| B4 | Drop the unused `ddtrace` | `pyproject.toml` / `default.txt` | No imports | Size and fewer CVEs |
| B5 | Dev/test packages out of the runtime image (`pytest*`, `mypy`, `boto3-stubs`/`mypy-boto3-s3`) | `pyproject.toml` (move them to the dev group), re-export `default.txt`. **First** move `from mypy_boto3_s3 import S3Client` under `if TYPE_CHECKING:` in the 4 files that import it (see §3) | Stubs are needed only for type checking | about −30 to −60 MB |
| B6 | Runtime image without debug tools; separate `dev` target | `backend/Dockerfile`: `nano`, `vim`, `postgresql-client` move to a final `dev` stage. `curl` is **still needed while building** (`:57` nodesource, `:67` opencode), so remove it after those steps or install it in the dev target only. Compose: default `target: runtime`; the dev overlay uses `target: dev` | Smaller image, fewer CVEs | −50 to −80 MB |
| B7 | Hash-locked install with no re-resolve | export `default.txt` (and `pulse.txt`) with hashes from `uv.lock`; Dockerfile `uv pip install --system --no-deps --require-hashes` | Reproducible, faster builds | Build time; no drift |
| B8 | Healthcheck-based startup ordering | `deployment/docker_compose/docker-compose.yml`: api `start_period` 25s → long enough for migrations (e.g. 300s); add a `web_server` healthcheck; nginx `depends_on: {api_server: {condition: service_healthy}, web_server: {condition: service_healthy}}`; mirror the change in `prod*.yml` | No 502s while the api is still migrating | Reliability |
| B9 | Smaller web build context | `web/.dockerignore`: add `src/**/*.test.ts`, `src/**/*.test.tsx`, `lib/opal/dist` | Upstream keeps co-located tests out | Faster web build |
| B10 (follow-up) | Multi-stage backend build (builder → os → runtime) | `backend/Dockerfile` (+ check that `Dockerfile.pulse` still builds on it) | Cache the Playwright and apt layers separately from Python deps | Large rebuild-time win |

**Not ported, on purpose:**
- **Removing the lightweight background worker:** our setup uses less memory.
- **The model-server torch image:** we use Cortex.
- **npm → bun, Python 3.11 → 3.13:** too big for now.
- **Dropping `unstructured`:** it is still imported at runtime (`om/file_processing/unstructured.py:57`).

Our BuildKit uv/npm cache mounts, the alpine web base and CRLF stripping stay as they are; they're better than upstream's.

## 2. DB / model / UI
No migration, no model change, no UI change.

## 3. Regression scope
| Area | Risk | How it's tested |
|---|---|---|
| Web connector and Highspot (Playwright) | B1: anything that needs the headed browser | Our launch sites use `headless=True` (`om/connectors/web/connector.py`, `om/connectors/highspot/utils.py`). Grep for `channel=`. Manual: index one web connector page |
| All backend processes | B2: a jemalloc load failure | `docker logs` for `ld.so` errors; compare `docker stats` RSS before and after |
| Imports of `mypy_boto3_s3` | B5: ImportError at runtime | `om/file_store/file_store.py`, `om/connectors/blob/connector.py`, `om/server/features/build/indexing/persistent_document_writer.py`, `om/server/features/build/s3/s3_client.py`. Move each under `TYPE_CHECKING` and use string annotations; then the unit suite plus file upload and a blob connector |
| Scripts that use `psql`/`curl` inside the container | B6 | Grep `backend/scripts`, `supervisord.conf` and the entrypoints (none found 2026-10-30). Compose healthchecks use `python -c` |
| Dependency set | B3/B4/B7 | `pip check` in the image; full unit suite; `python -c "import om.main"` |
| Startup ordering | B8 | `docker compose up -d --wait` on a **scratch project**; nginx starts only after the api is healthy |

## 4. Measurements (before → after, recorded here)
- `docker images` size of the backend and web images.
- A cold build and a warm rebuild after touching a `.py` file, timed with `time docker compose build api_server`.
- Idle RSS from `docker stats` for `api_server` and `background`, 10 minutes after start.
- Done on a **separate scratch compose project**, so no existing volume or DB is touched.

## 5. Progress tracker
- [x] 2026-10-30 Upstream survey done (read-only), and key claims checked against our files (correction: `unstructured` stays)
- [ ] User approval of this doc
- [ ] Batch 1 tested by the user (prerequisite)
- [ ] Baseline measurements (§4)
- [ ] B1–B2
- [ ] B3–B5 (+ `TYPE_CHECKING` imports, re-export the requirements)
- [ ] B6
- [ ] B7
- [ ] B8
- [ ] B9
- [ ] After-measurements recorded; unit suite unchanged; scratch stack smoke-tested
- [ ] B10 multi-stage (separate decision)
