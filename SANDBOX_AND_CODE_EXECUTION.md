# Sandbox & Code Execution Setup

This guide covers how to enable and run the two code execution features in Onyx:

1. **Onyx Craft (Sandbox)** - AI-powered app builder at `/craft/v1`
2. **Code Interpreter** - Run Python code snippets during chat

---

## Quick Start

### 1. Create / edit the `.env` file

File: `deployment/docker_compose/.env`

```env
# Enable Craft sandbox (AI app builder)
ENABLE_CRAFT=true

# Enable Code Interpreter (Python execution in chat)
CODE_INTERPRETER_BETA_ENABLED=true
# Tell the api_server where the code-interpreter service lives
CODE_INTERPRETER_BASE_URL=http://code-interpreter:8000
```

### 2. Rebuild the backend images

`ENABLE_CRAFT` must be set at **build time** because the Dockerfile conditionally
installs Node.js 20 and the `opencode` CLI.

```bash
cd deployment/docker_compose

docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml build api_server background --no-cache
```

### 3. Start the stack

```bash
docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml up -d
```

Or with the dev.bat helper:

```bash
dev.bat up
```

### 4. Verify in the UI

- **Craft**: A "Craft" button appears in the left sidebar. Click it to open `/craft/v1`.
- **Code Interpreter**: Appears as a toggle ("Code Interpreter") in the Agent Editor
  (Admin Panel > Assistants > Edit). When enabled on an agent, the chat can run Python.

---

## Feature Details

### Onyx Craft (Sandbox)

| Item | Detail |
|------|--------|
| **What it does** | Provides an isolated environment where an AI agent builds web apps, documents, and presentations using your connected data |
| **URL** | `/craft/v1` |
| **Backend mode** | `SANDBOX_BACKEND=local` (default, uses filesystem directories - no Kubernetes needed) |
| **Sandbox location** | `/tmp/onyx-sandboxes/` inside the `api_server` container |
| **Preview delivery** | Proxied through the API at `/api/build/sessions/{id}/webapp` (no extra ports needed) |
| **Templates** | Baked into the image at build time via `scripts/setup_craft_templates.sh` |

#### How it works

1. User opens `/craft/v1` in the browser
2. Backend provisions a sandbox directory with a Next.js template, Python venv, and demo data
3. User sends messages; the `opencode` AI agent processes them, editing files and running code
4. Results stream back in real-time (ACP protocol)
5. Built web apps are previewed live through the API proxy

#### Key environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_CRAFT` | `false` | Master toggle (build-time + runtime) |
| `SANDBOX_BACKEND` | `local` | `local` for Docker Desktop, `kubernetes` for production |
| `SANDBOX_BASE_PATH` | `/tmp/onyx-sandboxes` | Where sandbox directories are created |
| `SANDBOX_IDLE_TIMEOUT_SECONDS` | `3600` | Auto-cleanup idle sandboxes after this many seconds |
| `SANDBOX_MAX_CONCURRENT_PER_ORG` | `10` | Max concurrent sandboxes per organization |

### Code Interpreter

| Item | Detail |
|------|--------|
| **What it does** | Lets the AI run Python code during chat conversations |
| **Docker image** | `onyxdotapp/code-interpreter:latest` |
| **Port** | `8000` (exposed in dev compose files) |
| **Execution model** | Docker-out-of-Docker (mounts host Docker socket) |

#### How to use it

1. Enable the env var (`CODE_INTERPRETER_BETA_ENABLED=true`)
2. Restart the stack
3. Go to **Admin Panel > Assistants > Edit an agent**
4. Under Tools, toggle **Code Interpreter** on
5. Chat with that agent - it can now generate and execute Python code

---

## Troubleshooting

### Craft button not visible in sidebar

- Ensure `ENABLE_CRAFT=true` is set as **both** a build arg and runtime env var
- The image must be rebuilt (`--no-cache`) after changing this
- If you use PostHog, the feature flag `onyx-craft-enabled` must be enabled for the user
- Without PostHog (self-hosted default), the `ENABLE_CRAFT` env var is used directly

### Craft page redirects to /app

- The craft layout checks `settings.onyx_craft_enabled` server-side
- This means `ENABLE_CRAFT=true` must be set on the `api_server` container
- Restart `api_server` after changing the env var

### Code Interpreter tool not available in Agent Editor

- Ensure `CODE_INTERPRETER_BETA_ENABLED=true` in `.env`
- Check that the `code-interpreter` container is running: `docker compose ps`
- Verify the container is healthy: `docker compose logs code-interpreter`

### Build fails during template setup

- The `setup_craft_templates.sh` script runs at build time when `ENABLE_CRAFT=true`
- It needs network access to run `npm install` for the Next.js template
- If behind a proxy, configure Docker build args for HTTP_PROXY/HTTPS_PROXY

---

## Architecture Overview

```
Browser
  |
  ├─ /craft/v1          → Craft UI (React)
  |    |
  |    └─ POST /api/build/sessions/{id}/messages  → api_server
  |         |
  |         └─ LocalSandboxManager
  |              ├─ /tmp/onyx-sandboxes/{sandbox_id}/sessions/{session_id}/
  |              ├─ opencode agent (stdin/stdout, ACP protocol)
  |              └─ Next.js dev server (proxied via /api/build/sessions/{id}/webapp)
  |
  └─ Chat with agent    → api_server
       |
       └─ Code Interpreter tool
            |
            └─ code-interpreter container (port 8000)
                 └─ Executes Python in isolated Docker containers
```

---

## Files Reference

| Path | Purpose |
|------|---------|
| `deployment/docker_compose/.env` | Environment variables for both features |
| `backend/Dockerfile` | Conditional Node.js/opencode install (`ENABLE_CRAFT`) |
| `backend/scripts/setup_craft_templates.sh` | Template setup (npm install, venv, demo data) |
| `backend/onyx/server/features/build/configs.py` | All sandbox configuration variables |
| `backend/onyx/server/features/build/sandbox/local/local_sandbox_manager.py` | Local sandbox implementation |
| `backend/onyx/server/features/build/utils.py` | Feature flag logic (`is_onyx_craft_enabled`) |
| `web/src/sections/sidebar/AppSidebar.tsx` | Sidebar Craft button (line 653) |
| `web/src/app/craft/` | Craft frontend (React/TypeScript) |
