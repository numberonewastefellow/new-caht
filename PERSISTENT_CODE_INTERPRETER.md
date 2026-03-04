# Persistent Code Interpreter — Implementation Plan

## Problem

The current Code Interpreter is **stateless** — every `POST /v1/execute` call:

1. Spawns a fresh `python-executor-sci` Docker container
2. Tars code + files into it
3. Runs `python /workspace/__main__.py`
4. Tars outputs out
5. Kills the container

**Nothing survives between tool calls** — no variables, no imports, no files.

ChatGPT keeps a persistent Jupyter-like kernel where `df = pd.read_csv(...)` in call 1
is available as `df.describe()` in call 2. Ours can't do this.

## Solution: Persistent Sessions with Kernel

Add a **session layer** to the code-interpreter service. A session keeps a Docker
container alive and runs a persistent Python kernel inside it.

```
BEFORE (stateless):
  Tool call → create container → run code → kill container
  Tool call → create container → run code → kill container  (variables lost!)

AFTER (persistent session):
  create_session → start container + start kernel
  Tool call → send code to kernel → get output  (variables alive!)
  Tool call → send code to kernel → get output  (df still exists!)
  delete_session → kill container
```

## Architecture

### Current Flow (Stateless)

```
PythonTool.run()
  → CodeInterpreterClient.execute(code)
    → POST http://code-interpreter:8000/v1/execute
      → DockerExecutor.execute_python()
        → docker run --rm python-executor-sci sleep ...
        → docker exec ... tar -x (stage files)
        → docker exec ... python __main__.py
        → docker exec ... tar -c (extract outputs)
        → docker kill (destroy)
```

### New Flow (Persistent Sessions)

```
PythonTool.run()  [first call]
  → CodeInterpreterClient.create_session()
    → POST http://code-interpreter:8000/v1/sessions
      → SessionManager.create_session()
        → docker run -d python-executor-sci  (stays alive)
        → docker exec ... python _kernel.py  (persistent REPL)
        → return session_id

PythonTool.run()  [subsequent calls]
  → CodeInterpreterClient.execute(code, session_id=...)
    → POST http://code-interpreter:8000/v1/execute  {session_id: "abc"}
      → SessionManager.execute_in_session("abc", code)
        → send code to existing kernel via stdin
        → read output from kernel stdout
        → extract new files from container
        → return result  (container NOT killed)

Chat session ends or idle timeout:
  → CodeInterpreterClient.delete_session(session_id)
    → DELETE http://code-interpreter:8000/v1/sessions/{id}
      → SessionManager.delete_session()
        → docker kill (destroy)
```

## Craft vs Code Interpreter — Clarification

These are **two completely separate systems**:

| | Craft (Build Mode) | Code Interpreter (PythonTool) |
|---|---|---|
| Purpose | AI app/dashboard builder | Run Python code in chat |
| Image | `onyxdotapp/sandbox` / built into api_server | `onyxdotapp/code-interpreter` (separate) |
| Execution | `opencode acp` CLI via subprocess | HTTP API `/v1/execute` on port 8000 |
| Enabled by | `ENABLE_CRAFT=true` (build-time) | `CODE_INTERPRETER_BETA_ENABLED=true` (runtime) |
| Sandbox | opencode CLI + ACP protocol | Docker-out-of-Docker, spawns `python-executor-sci` containers |

This plan modifies **only the Code Interpreter**, not Craft.

## Source Code Location

The code-interpreter service source is open source:
- **Repo**: https://github.com/onyx-dot-app/code-interpreter
- **License**: MIT
- **Current image**: `onyxdotapp/code-interpreter:latest`

We clone it into our project at `code-interpreter/` (outside `backend/`) to have full control:

```
d:\llm\danswer20022026\
├── backend\                         ← Onyx backend (unchanged)
├── web\                             ← Frontend (unchanged)
├── deployment\                      ← Docker compose configs
└── code-interpreter\                ← CLONED HERE
    ├── app\
    │   ├── main.py                  ← FastAPI server
    │   ├── app_configs.py           ← Configuration
    │   ├── api\routes.py            ← /v1/execute, /v1/files, /v1/sessions (NEW)
    │   ├── models\schemas.py        ← Request/response models
    │   └── services\
    │       ├── executor_docker.py   ← Docker container management
    │       ├── executor_base.py     ← Base class
    │       ├── executor_factory.py  ← Backend selection
    │       ├── file_storage.py      ← File management
    │       └── session_manager.py   ← NEW: persistent session management
    ├── Dockerfile
    ├── pyproject.toml
    └── entrypoint.sh
```

## Files Changed (Summary)

### Code Interpreter Service (code-interpreter/)

| # | File | Action | What |
|---|------|--------|------|
| 1 | `app/services/session_manager.py` | **CREATE** | Session lifecycle: create/execute/delete/cleanup |
| 2 | `app/models/schemas.py` | **MODIFY** | Add `session_id` to `ExecuteRequest`, add `CreateSessionResponse` |
| 3 | `app/api/routes.py` | **MODIFY** | Add `POST/DELETE /v1/sessions`, modify `/v1/execute` for sessions |
| 4 | `app/services/executor_docker.py` | **MODIFY** | Split into create/execute/destroy (reusable containers) |
| 5 | `app/main.py` | **MODIFY** | Start cleanup background task on startup |
| 6 | `app/app_configs.py` | **MODIFY** | Add session config (idle timeout, max sessions) |

### Persistent Kernel (inside python-executor-sci container)

| # | File | Action | What |
|---|------|--------|------|
| 7 | `_kernel.py` | **CREATE** | Persistent Python REPL — runs once, accepts code via stdin JSON |

### Onyx Backend (backend/)

| # | File | Action | What |
|---|------|--------|------|
| 8 | `code_interpreter_client.py` | **MODIFY** | Add `create_session()`, `delete_session()`, `session_id` in `execute()` |
| 9 | `python_tool.py` | **MODIFY** | Use sessions: create on first call, reuse, stop deleting files |

### Deployment

| # | File | Action | What |
|---|------|--------|------|
| 10 | `docker-compose.yml` | **MODIFY** | Build from local `code-interpreter/` instead of pulling image |
| 11 | `docker-compose.dev-windows.yml` | **MODIFY** | Same build context change |

## Detailed Design

### 1. Session Manager (`session_manager.py`)

```python
class SessionState:
    session_id: str
    container_name: str
    kernel_process: subprocess.Popen  # persistent Python REPL
    created_at: float
    last_used_at: float
    staged_files: set[str]  # file_ids already in container

class SessionManager:
    _sessions: dict[str, SessionState]
    _lock: threading.Lock

    create_session() -> str
        # 1. Generate session_id
        # 2. docker run -d (NO --rm) --network none python-executor-sci sleep 7200
        # 3. docker exec -d ... python /workspace/_kernel.py (start kernel)
        # 4. Store in _sessions
        # 5. Return session_id

    execute_in_session(session_id, code, files) -> ExecutionResult
        # 1. Look up session
        # 2. Stage only NEW files (skip already-staged ones)
        # 3. Send code to kernel via stdin JSON
        # 4. Read response from kernel stdout JSON
        # 5. Extract new workspace files via tar
        # 6. Update last_used_at
        # 7. Return result

    delete_session(session_id)
        # 1. docker kill container
        # 2. Remove from _sessions

    cleanup_idle_sessions(max_idle_sec=1800)
        # Background task every 60s
        # Kill sessions idle > 30 minutes
```

### 2. Persistent Kernel (`_kernel.py`)

Runs inside the `python-executor-sci` container. Started once, stays alive.

```python
# Protocol: JSON lines over stdin/stdout
# Input:  {"code": "import pandas as pd\ndf = pd.read_csv('data.csv')"}
# Output: {"stdout": "...", "stderr": "...", "exit_code": 0, "duration_ms": 123}

- Uses exec() with persistent globals dict
- Variables, imports, DataFrames survive between calls
- Captures stdout/stderr per execution
- Handles exceptions gracefully (kernel stays alive)
- Supports matplotlib savefig (files persist in /workspace/)
```

### 3. API Changes

```
POST /v1/sessions
  Request: {} (empty)
  Response: {"session_id": "abc123"}

DELETE /v1/sessions/{session_id}
  Response: 204 No Content

POST /v1/execute  (MODIFIED — backward compatible)
  Request: {
    "code": "...",
    "session_id": "abc123",    ← NEW (optional)
    "timeout_ms": 30000,
    "files": [...]
  }
  Response: (unchanged)

  Behavior:
    - If session_id is None: old stateless behavior (ephemeral container)
    - If session_id is set: execute in persistent session
```

### 4. Client Changes (`code_interpreter_client.py`)

```python
class CodeInterpreterClient:
    def create_session(self) -> str:
        resp = self.session.post(f"{self.base_url}/v1/sessions", timeout=30)
        resp.raise_for_status()
        return resp.json()["session_id"]

    def delete_session(self, session_id: str) -> None:
        resp = self.session.delete(
            f"{self.base_url}/v1/sessions/{session_id}", timeout=10
        )
        resp.raise_for_status()

    def execute(self, code, session_id=None, ...):  # add session_id
        payload["session_id"] = session_id  # None = stateless (backward compat)
        ...
```

### 5. PythonTool Changes (`python_tool.py`)

```python
class PythonTool(Tool):
    # Class-level session cache: chat_session_id -> ci_session_id
    _session_cache: dict[str, str] = {}

    def run(self, placement, override_kwargs, **llm_kwargs):
        client = CodeInterpreterClient()

        # Get or create session for this chat
        chat_session_id = self._get_chat_session_id()  # from context
        ci_session_id = self._session_cache.get(chat_session_id)

        if ci_session_id is None:
            ci_session_id = client.create_session()
            self._session_cache[chat_session_id] = ci_session_id

        # Stage only NEW files (skip already-staged)
        # Execute with session_id
        response = client.execute(
            code=code,
            session_id=ci_session_id,
            timeout_ms=...,
            files=new_files_only,
        )

        # Do NOT delete files after execution (they persist in session)
        # Only download generated output files to Onyx file store
```

## Backward Compatibility

All changes are **backward compatible**:

- `session_id` is optional on `POST /v1/execute`
- If omitted → old stateless behavior (ephemeral container, destroyed after)
- If provided → persistent session behavior
- Existing personas/agents that don't pass session_id work unchanged
- Only PythonTool needs updating to use sessions

## Configuration

New environment variables for code-interpreter service:

```
SESSION_IDLE_TIMEOUT_SEC=1800    # Kill sessions idle > 30min (default)
SESSION_MAX_LIFETIME_SEC=86400   # Force-kill sessions after 24hr (default)
SESSION_MAX_CONCURRENT=20        # Max concurrent sessions (default)
SESSION_CONTAINER_TIMEOUT=7200   # Container sleep duration in seconds (default)
```

## Test Plan

### Unit Test: Session Lifecycle

```python
# 1. Create session
session_id = client.create_session()
assert session_id is not None

# 2. Execute with variable assignment
r1 = client.execute("x = 42; print(x)", session_id=session_id)
assert "42" in r1.stdout

# 3. Execute using same variable (PERSISTENCE TEST)
r2 = client.execute("print(x + 8)", session_id=session_id)
assert "50" in r2.stdout  # x=42 survived from call 1!

# 4. Execute with pandas
r3 = client.execute(
    "import pandas as pd; df = pd.read_csv('data.csv'); print(len(df))",
    session_id=session_id,
    files=[{"path": "data.csv", "file_id": uploaded_id}]
)

# 5. Use df from previous call
r4 = client.execute("print(df.columns.tolist())", session_id=session_id)
assert r4.exit_code == 0  # df survived!

# 6. Delete session
client.delete_session(session_id)
```

### Integration Test: Stateless Still Works

```python
# No session_id — should work exactly as before
r = client.execute("print('hello')")
assert "hello" in r.stdout
```

### Integration Test: File Persistence

```python
session_id = client.create_session()

# Call 1: Create a file
client.execute("open('output.txt','w').write('hello')", session_id=session_id)

# Call 2: Read the file (it persists!)
r = client.execute("print(open('output.txt').read())", session_id=session_id)
assert "hello" in r.stdout

client.delete_session(session_id)
```

## Implementation Order

| Step | What | Depends On |
|------|------|------------|
| 1 | Clone repo to `code-interpreter/` | — |
| 2 | Wire docker-compose to build from local source | Step 1 |
| 3 | Verify existing stateless flow still works | Step 2 |
| 4 | Create `_kernel.py` (persistent REPL) | — |
| 5 | Create `session_manager.py` | Step 4 |
| 6 | Modify `schemas.py` (add session_id) | — |
| 7 | Modify `routes.py` (add session endpoints) | Steps 5, 6 |
| 8 | Modify `executor_docker.py` (reusable containers) | — |
| 9 | Modify `main.py` (cleanup task) | Step 5 |
| 10 | Rebuild code-interpreter image | Steps 4-9 |
| 11 | Update `code_interpreter_client.py` | Step 10 |
| 12 | Update `python_tool.py` | Step 11 |
| 13 | Run tests | Steps 10-12 |
