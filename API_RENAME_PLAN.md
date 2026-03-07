# API Endpoint Prefix Rename Plan

## Overview

Rename all API route prefixes to distinctive, AI/modern-style names. Prefix-only rename (sub-route paths stay the same). Hard cutover — no backward-compatible aliases. Python function names remain unchanged.

## Prefix Mapping

| Current Prefix | New Prefix | Example |
|----------------|------------|---------|
| `/chat` | `/converse` | `/api/converse/rename-chat-session` |
| `/manage` | `/nexus` | `/api/nexus/connector-status` |
| `/federated` | `/bridges` | `/api/bridges/oauth-status` |
| `/user/projects` | `/workspaces` | `/api/workspaces/create` |
| `/input_prompt` | `/prompts` | `/api/prompts` |
| `/admin/input_prompt` | `/admin/prompts` | `/admin/prompts/{id}` |
| `/notifications` | `/signals` | `/api/signals` |
| `/health` | `/heartbeat` | `/api/heartbeat` |

## Scope

- ~101 backend routes across 7 FastAPI routers
- ~63 frontend files (fetch calls, useSWR hooks, fetchSS calls)
- No Next.js route files to change (catch-all proxy at `web/src/app/api/[...path]/route.ts` handles all)

## Architecture

- **Backend**: Each router has a `prefix=` parameter in its `APIRouter()`. Changing this one string renames ALL routes under that router.
- **Frontend**: URL strings like `"/api/chat/..."` in fetch/useSWR calls need find-and-replace.
- **Server-side fetch**: `fetchSS("/manage/...")` calls use paths WITHOUT the `/api/` prefix — these need updating too.

## Changes by Phase

### Phase 1: Low-risk (few frontend files)

| Change | Backend File | Frontend Files |
|--------|-------------|----------------|
| `/notifications` -> `/signals` | `backend/onyx/server/features/notifications/api.py` | 3 files: `UserAvatarPopover.tsx`, `AppSidebar.tsx`, `NotificationsPopover.tsx` |
| `/input_prompt` -> `/prompts` | `backend/onyx/server/features/input_prompt/api.py` | 2 files: `usePromptShortcuts.ts`, `SettingsPage.tsx` |
| `/health` -> `/heartbeat` | `backend/onyx/server/manage/get_state.py` + `auth_check.py` | 2 files: `healthcheck.tsx`, `SystemHealthDot.tsx` |
| `/user/projects` -> `/workspaces` | `backend/onyx/server/features/projects/api.py` | 4 files: `useProjects.ts`, `projectsService.ts`, 2 e2e tests |

### Phase 2: Medium-risk

| Change | Backend File | Frontend Files |
|--------|-------------|----------------|
| `/chat` -> `/converse` | `backend/onyx/server/query_and_chat/chat_backend.py` | 9 files: `services/lib.tsx`, `useChatSessions.ts`, `useChatController.ts`, `CodeBlock.tsx`, `MemoizedTextComponents.tsx`, `DocumentFeedbackBlock.tsx`, 3 e2e tests |
| `/federated` -> `/bridges` | `backend/onyx/server/federated/api.py` | 5 files: `UserAvatarPopover.tsx`, `hooks.ts`, `useFederatedOAuthStatus.ts`, `FederatedConnectorForm.tsx`, `oauth/callback/page.tsx` |

### Phase 3: High-risk (most files)

| Change | Backend File | Frontend Files |
|--------|-------------|----------------|
| `/manage` -> `/nexus` | `backend/onyx/server/documents/connector.py` | 38 files across connectors, document sets, users, groups, bots, google drive/gmail, admin pages |

### Phase 4: Backend registration and auth

- `backend/onyx/main.py` — update router registration comments/tags
- `backend/onyx/auth/auth_check.py` — update public routes list (`/health` -> `/heartbeat`)
- Check Docker healthcheck configs and CI/CD workflows for `/health` references

## Nginx & Deployment Files

The nginx `app.conf` does NOT reference specific API routes (it proxies `/api/` generically) — **no nginx config changes needed**.

However, `/health` is referenced in these deployment files (change to `/heartbeat`):

| File | Reference |
|------|-----------|
| `deployment/data/nginx/run-nginx.sh` | `curl ... "http://.../health"` |
| `deployment/docker_compose/docker-compose.yml` | `urlopen('http://localhost:8080/health')` (x3) |
| `deployment/docker_compose/init-letsencrypt.sh` | `curl ... "http://localhost/api/health"` |
| `deployment/aws_ecs_fargate/.../onyx_nginx_service_template.yaml` | `HealthCheckPath: /api/health` |
| `deployment/helm/charts/onyx/values.yaml` | `path: /health` (x6, some commented) |
| `deployment/helm/charts/onyx/templates/mcp-server-deployment.yaml` | `path: /health` (x2) |

**Note**: Minio healthcheck paths (`/minio/health/live`) and Vespa paths (`/state/v1/health`) are UNRELATED — do NOT change those.

## Swagger/OpenAPI

No manual changes needed. The routers don't use explicit `tags=` for the prefixes being renamed. Swagger docs auto-generate from router prefixes, so they update automatically.

## Backend Tests (19 occurrences, 9 files)

| File | Count | Endpoints Referenced |
|------|-------|---------------------|
| `tests/regression/answer_quality/api_utils.py` | 7 | `/chat/`, `/manage/` |
| `tests/unit/onyx/server/test_pool_metrics.py` | 6 | `/api/chat/send-message`, `/api/health` |
| `tests/api/test_api.py` | 3 | Various |
| `tests/integration/tests/dev_apis/test_simple_chat_api.py` | 3 | `/chat/` |
| `tests/external_dependency_unit/answer/test_stream_chat_message.py` | 1 | `/api/chat/file/` |
| `tests/external_dependency_unit/answer/stream_test_assertions.py` | 2 | `/api/chat/file/` |
| `tests/unit/onyx/server/test_prometheus_instrumentation.py` | 1 | endpoint ref |
| `tests/integration/tests/dev_apis/test_knowledge_chat.py` | 1 | `/chat/` |
| `tests/integration/mock_services/` (3 files) | 3 | Various |
| `tests/workflow_creator/curl.txt` | 3 | `/api/chat/` curl commands |

## Watch Out For

1. **`/manage` prefix touches 38 frontend files** — highest risk, do careful grep before and after
2. **OAuth callback**: `/federated/oauth/callback` is a Next.js PAGE route (not just API). May need page directory rename + backend callback URL update
3. **Deployment healthchecks**: See table above — 8+ deployment files reference `/health`
4. **`fetchSS()` calls**: Use paths without `/api/` prefix (e.g., `fetchSS("/manage/connector")`) — need updating too
5. **E2E tests**: Several test files reference endpoints directly
6. **GitHub Actions**: Check `.github/workflows/` for `/health` endpoint references

## Verification Checklist

- [ ] Grep for ALL old prefix strings — zero matches in code files
- [ ] Backend starts without errors
- [ ] Frontend builds without errors (`npm run build`)
- [ ] Browser Network tab shows new endpoint names
- [ ] E2E tests pass
