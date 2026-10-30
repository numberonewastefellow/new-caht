# Flow nodes: operations

## Code-interpreter security

The code-interpreter (`code-interpreter/code-interpreter/`) runs arbitrary Python for
the Python tool and the code node. It is hardened in four layers:

1. A shared API token on every `/v1/*` route.
2. Tenant binding of sessions and files.
3. Admission control (bounded workers and queue).
4. Locked-down sandbox containers or pods.

### Environment variables

**Service (`code-interpreter` container)**

| Variable | Default | Meaning |
|---|---|---|
| `CODE_INTERPRETER_API_TOKEN` | *(empty)* | **Required.** Every `/v1/*` request must send `Authorization: Bearer <token>`. The token is compared in constant time over SHA-256 digests. If it is empty, or still the `change-me…` template placeholder, every `/v1/*` call gets **503** (fail closed) and an error is logged at startup. |
| `CODE_INTERPRETER_ALLOW_UNAUTHENTICATED` | `false` | **Dev only.** When `true` *and* no token is set, `/v1/*` is served without auth and a loud warning is logged at startup. A configured token always wins over this flag. |
| `EXECUTION_MAX_WORKERS` | `8` | Executions that may run at once (`/execute` and `/execute/stream`, sessions included). |
| `EXECUTION_MAX_QUEUE` | `32` | Extra requests that may wait for a worker. Anything beyond workers + queue gets **503 + `Retry-After`** immediately. |
| `EXECUTION_QUEUE_TIMEOUT_SEC` | `60` | Longest a queued request waits before it gets 503. |
| `EXECUTION_RETRY_AFTER_SEC` | `5` | Value of the `Retry-After` header. |
| `EXECUTOR_CPUS` | `1` | `docker run --cpus` for each sandbox container. |
| `EXECUTOR_WORKSPACE_SIZE_MB` | `128` | Size cap of the `/workspace` tmpfs. Input files, outputs and plots all live here, so raise it if users stage large files. |
| `EXECUTOR_TMP_SIZE_MB` | `64` | Size cap of the `/tmp` tmpfs. |
| `EXECUTOR_RUN_AS_NON_ROOT` | `true` | Runs the whole sandbox container as uid/gid 65532 (`--user`). Set `false` only for a custom image that can't run its entry command as non-root. |
| `MAX_WORKSPACE_SNAPSHOT_BYTES` | `67108864` (64 MiB) | Most file content read back from the workspace after a run. A file that would exceed the cap is **skipped** (and logged), never truncated. |

**Backend (`api_server`, `background`, `pulse_worker`, and anything else that sets
`CODE_INTERPRETER_BASE_URL`)**

| Variable | Meaning |
|---|---|
| `CODE_INTERPRETER_API_TOKEN` | Must be the **same value** as on the service. It is sent as the bearer token by `backend/om/tools/tool_implementations/python/code_interpreter_client.py`. |

The client also sends `X-OM-Tenant` with the current tenant id (`get_current_tenant_id()`).
In single-tenant mode that is the default schema.

### What the service enforces

- **Auth.** A pure-ASGI middleware checks the token before routing and before the
  body is read, so unauthenticated uploads are never buffered. `/health`, `/docs`
  and `/openapi.json` stay open.
- **Tenant binding.**
  - Sessions and files record the caller's `X-OM-Tenant` when they are created.
  - Every execute, stream, delete and download must present the same tenant.
    Otherwise the answer is **404** (not 403), so ids don't leak.
  - `GET /v1/files` lists only the caller's own files.
  - A request with no tenant header lands in a private `__unscoped__` bucket.
  - Files written before this change have no tenant, so they are invisible. They
    expire with `FILE_TTL_SEC`.
- **Admission.** The limits above apply. A capacity 503 is retried once by the
  Python tool, using a fresh session.
- **Docker sandbox (ephemeral runs and persistent sessions).**
  - `--network none` and `--read-only` root filesystem.
  - Size-capped tmpfs for `/tmp` and `/workspace`; these are the only writable paths.
  - `--user 65532:65532`, `--cap-drop ALL`, `no-new-privileges`, `--pids-limit 64`.
  - `--cpus`, plus memory equal to swap.
  - Ephemeral runs also keep `--ulimit cpu`.
  - The workspace snapshot is read as a stream, with the byte cap above.
- **Kubernetes sandbox (executor pods).**
  - `automountServiceAccountToken: false` and `enableServiceLinks: false`.
  - `seccompProfile: RuntimeDefault` and `readOnlyRootFilesystem: true`, with
    emptyDir `/workspace` and `/tmp`.
  - `runAsNonRoot`, uid/gid 65532, `drop: [ALL]`, no privilege escalation.
  - stdin is staged as a file and redirected, so `sys.stdin.read()` reaches EOF
    instead of hanging until the timeout.
  - The snapshot read is capped.

### Ports

| Compose file | Mapping |
|---|---|
| `docker-compose.yml`, prod files | Not published. Other containers reach it at `http://code-interpreter:8000` on the compose network. |
| `docker-compose.dev-windows.yml`, `docker-compose.dev.yml` | `127.0.0.1:8000:8000`: loopback only. Never publish it on `0.0.0.0`. |

Any caller on the compose network still needs the token.

### Setting the token

| Environment | How |
|---|---|
| Local dev (Windows) | `dev.bat up` / `dev.bat build` check `deployment/docker_compose/.env`. If `CODE_INTERPRETER_API_TOKEN` is missing or still `change-me`, they append a random 256-bit hex token. The file is local and git-ignored; never commit it. |
| Other compose setups | Add `CODE_INTERPRETER_API_TOKEN=<openssl rand -hex 32>` to `.env`. Every compose file that defines `code-interpreter` or a caller passes it through to both sides. |
| Helm (`deployment/helm/charts/onyx`) | Set `auth.codeinterpreter.enabled=true` and either supply `auth.codeinterpreter.values.code_interpreter_api_token` or point `auth.codeinterpreter.existingSecret` at your own Secret. The parent chart injects it into every backend pod. The code-interpreter subchart reads the same Secret (`codeInterpreter.auth.existingSecret`, key `code_interpreter_api_token`). If you rename the Secret, change both. |
| Standalone code-interpreter chart | Use `auth.existingSecret` + `auth.existingSecretKey`, or `auth.apiToken` (creates `<fullname>-auth`). |

### Token rotation

The service accepts exactly one token, so rotation is a short, coordinated restart:

1. Generate a new value: `openssl rand -hex 32`.
2. Update it everywhere it is configured: `.env`, or the Kubernetes Secret.
3. Recreate the code-interpreter **and** every caller so they read the new value:
   - Compose: `docker compose up -d --force-recreate code-interpreter api_server background pulse_worker`.
   - Kubernetes: `kubectl rollout restart` the code-interpreter and backend
     deployments. The pod template doesn't hash the Secret, so a restart is
     required.
4. Expect brief failures during the switch:
   - Requests in flight between steps 2 and 3 can get 401.
   - The Python tool surfaces these as a clear "API token is missing or wrong"
     error, and a 401 is not retried.
   - Persistent sessions survive a backend restart, but **not** a code-interpreter
     restart, and that is unchanged by this work.

### The dev override

`CODE_INTERPRETER_ALLOW_UNAUTHENTICATED=true` exists only so you can poke the
service locally without a token, for example with curl from the host. It only takes
effect while no token is set, and it logs a warning at every startup. Never set it in
a shared or production environment, and never combine it with publishing the port
beyond loopback.

### Kubernetes notes

- **Executor egress.** The code-interpreter chart now installs
  `<release>-code-interpreter-executor-deny-all` (`executorNetworkPolicy.enabled`,
  default `true`).
  - It lives in the executor namespace.
  - It selects `app=code-interpreter, component=executor`.
  - It denies all ingress and egress, DNS included.
  - The service drives pods through the API server and kubelet `exec`, which this
    policy doesn't affect.
  - It needs a CNI that enforces NetworkPolicy, such as Calico or Cilium. On a CNI
    that doesn't, executor pods still have open egress.
- **Service pods.** The older `networkPolicy` block still targets the service pods
  and stays opt-in.
- **Service account.** The *service* still needs its service-account token, because
  it creates pods. Only the executor pods have automount disabled. Keep the
  executor namespace free of other workloads.
- **Stronger isolation.** For stronger isolation, run executor pods under gVisor
  through a `RuntimeClass`. This is not wired into the chart yet.

### Migration note for existing deployments

**This is a breaking change. After upgrading, the code-interpreter rejects every
`/v1/*` call with 503 until a token is configured.** The Python tool and the code
node are then unavailable.

Before or while upgrading:

1. Set `CODE_INTERPRETER_API_TOKEN` (the same value) on the code-interpreter and on
   every backend service that calls it.
2. Recreate those containers or pods.
3. If you use a custom env file or orchestrator that doesn't go through the shipped
   compose files or charts, add the variable there too.
4. Sandbox session ids saved on existing chats belong to no tenant after the
   upgrade. The first call gets 404, and the Python tool transparently creates a
   fresh session, as it already does for expired sessions. Variables held in old
   sessions are lost once.
5. If a custom executor image can't run as uid 65532 or with a read-only root
   filesystem, set `EXECUTOR_RUN_AS_NON_ROOT=false` and report it. The read-only
   root stays on.

### Executor runtime image

`code-interpreter/executor/Dockerfile` is now a two-stage build:

- Compilers, headers and `curl` stay in the build stage.
- The runtime image holds only `python:3.11-slim`, the prebuilt venv and `procps`.
  `procps` is needed for the timeout `pkill`, which was missing before.
- Every scientific package installs from a manylinux wheel with its native libraries
  bundled, so nothing needs the build-stage system libraries at runtime.
- Rebuild it with `docker build -t om/python-executor-sci code-interpreter/executor`
  and restart the code-interpreter.

Known, pre-existing gaps:

- `import cv2` fails in both the old and the new image (`libGL.so.1` is missing).
- `matplotlib_inline` needs IPython, which isn't installed.

## Low-latency run_function + warm pool

`POST /v1/run_function` runs one self-contained Python program (for example the code
node's harness) in a fresh, hardened sandbox. It skips everything `/v1/execute` adds
around user code:

- no last-line-interactive wrapper and no figure prologue;
- no file staging, no workspace snapshot, no upload or download.

The program is streamed to `python -` with a single `docker exec`. With the warm pool,
that exec is the only Docker call on the request path.

### API

The endpoint sits behind the same layers as `/v1/execute`:

- the bearer-token middleware;
- `X-OM-Tenant` validation (the call is stateless, so nothing is bound to the tenant);
- the admission limiter (`EXECUTION_MAX_WORKERS` / `EXECUTION_MAX_QUEUE`, 503 +
  `Retry-After`).

Request:

| Field | Type | Meaning |
|---|---|---|
| `program` | string, ≤ 8,000,000 chars | The program, run as-is. |
| `timeout_ms` | int ≥ 1, required | Wall-clock timeout. Above `MAX_EXEC_TIMEOUT_MS` → 422. |
| `read_result_file` | bool, default `false` | Also return the result file (see below). |

Response (200):

| Field | Meaning |
|---|---|
| `stdout` | Cut at `MAX_OUTPUT_BYTES` (default 1,000,000). |
| `stderr` | Cut at `RUN_FUNCTION_MAX_STDERR_BYTES` (default 64 KiB). |
| `stdout_truncated`, `stderr_truncated` | `true` if that stream was cut. Nothing is appended to the text. |
| `exit_code` | Exit code of the program; `null` on a wall-clock timeout. |
| `timed_out` | The wall-clock timeout fired. The container is removed at once. |
| `duration_ms` | Time spent running the program. |
| `error_kind` | `timeout` (wall clock, or the CPU-time limit: exit 152), `oom` (exit 137), `sandbox_error` (the sandbox could not be started or driven), or `null`. With `null`, a user exception shows up as a non-zero `exit_code` plus the traceback on stderr. |
| `result_payload` | The result file as UTF-8 text, or `null`. |
| `result_error` | `too_large` or `invalid_utf8` when a written result file was **rejected**. A result file is never truncated. |
| `pool_hit` | `true` if the run used a pre-started container. |

Other answers:

- 401/503 for auth, as on every `/v1/*` route.
- 400 for an invalid tenant header.
- 422 for a bad body or timeout.
- 503 + `Retry-After` at capacity.
- **501** when the service runs the Kubernetes backend.
- An older service without the endpoint answers **404**.

`CodeInterpreterClient.run_function()` raises `RunFunctionUnsupportedError` on both
404 and 501, so a caller can fall back to `execute()`. Every other error maps exactly as
it does for `execute()`.

**Result channel.** stdout is always returned, so the code node's nonce-framed stdout
parser keeps working unchanged. Optionally, the program can write its result to
`$OM_RESULT_PATH` (`/tmp/result`, on the container's private tmpfs). With
`read_result_file: true` the service then reads that file after the run with one
extra `docker exec head -c`:

- It is returned as `result_payload`, capped at `RUN_FUNCTION_MAX_RESULT_BYTES`
  (1 MiB).
- The read is skipped after a timeout.
- It costs one extra exec (tens of ms), which is why it is opt-in.

This channel can't be corrupted by stray prints. It is still written by the program
itself, though, so host-side output validation remains the trust boundary.

### Warm pool (Docker executor)

- **Single use, never shared.**
  - A request takes one idle container out of the pool. The pool forgets it at that
    moment.
  - The request runs exactly one program in it, and the container is then removed
    (`docker rm -f`, off the request path).
  - A container is never reused, so no state can cross executions or tenants.
- **Same hardening as every sandbox.**
  - Pool containers are started with the shared `hardened_docker_run_flags`:
    `--network none`, `--read-only`, size-capped `/tmp` and `/workspace` tmpfs,
    `--user 65532:65532`, `--cap-drop ALL`, `no-new-privileges`, `--pids-limit 64`,
    `--cpus`.
  - Memory is capped at `MEMORY_LIMIT_MB` (swap equal to memory).
  - The program runs as uid 65532 under a CPU-time rlimit of `CPU_TIME_LIMIT_SEC`. The
    soft limit sends SIGXCPU (reported as `timeout`); the hard limit is one second
    later.
- **Empty pool.** The request cold-starts its own container instead, and never fails
  for lack of a warm one. A miss also grows the pool by one, up to the max. After 60 s
  without a miss, it shrinks back by one step at a time, never below the min.
- **TTL.** Idle containers older than `RUN_FUNCTION_POOL_TTL_SEC` are destroyed and
  replaced. Every 30 s, idle entries whose container vanished (for example after a
  daemon restart) are dropped.
- **Lifecycle.**
  - Startup removes every container labelled with this instance's owner (orphans of a
    crashed process), then fills the pool.
  - Graceful shutdown removes the pool and any leftovers.
  - As a backstop, each container runs `sleep` for TTL + `MAX_EXEC_TIMEOUT_MS` + 60 s
    with `--rm`, so it disappears on its own even if the service is killed.
- **Labels.**
  - `om.code-interpreter.run-function=1`.
  - `om.code-interpreter.owner=<RUN_FUNCTION_POOL_OWNER>`.
  - List them with `docker ps --filter label=om.code-interpreter.run-function=1`.

| Variable | Default | Meaning |
|---|---|---|
| `RUN_FUNCTION_POOL_ENABLED` | `true` | `false` = every call cold-starts its own container. |
| `RUN_FUNCTION_POOL_MIN` | `2` | Idle containers kept ready. |
| `RUN_FUNCTION_POOL_MAX` | `8` | Cap on idle + starting containers. A max below the min lowers the min. `0` disables the pool. |
| `RUN_FUNCTION_POOL_TTL_SEC` | `600` | Idle containers older than this are recycled (minimum 10). |
| `RUN_FUNCTION_POOL_OWNER` | hostname | Owner label. Instances that share one Docker daemon must use **distinct** values, because startup removes every container with this owner. The default (the container hostname) already differs per container. |
| `RUN_FUNCTION_MAX_STDERR_BYTES` | `65536` | stderr cap. |
| `RUN_FUNCTION_MAX_RESULT_BYTES` | `1048576` | Result-file cap; a bigger file is rejected. |
| `PYTHON_EXECUTOR_DOCKER_TAG` | `latest` | Tag of `PYTHON_EXECUTOR_DOCKER_IMAGE`, for every Docker sandbox (ephemeral, session, run_function). It is ignored if the image already names a tag or digest. |

**Sizing.**

- An idle pool container is only a sleeping process (a few MB of RAM, no CPU), so
  idle capacity is cheap.
- Set `RUN_FUNCTION_POOL_MIN` to the number of code nodes you expect to start within
  about one second of each other. A refill takes roughly one `docker run`
  (≈ 0.3–0.5 s).
- Set `RUN_FUNCTION_POOL_MAX` up to `EXECUTION_MAX_WORKERS`; more than that can never
  be in use at once.
- Memory is reserved only while a program runs. The worst case is still
  `EXECUTION_MAX_WORKERS × MEMORY_LIMIT_MB`, exactly as for `/v1/execute`.
- `CPU_TIME_LIMIT_SEC` (default 5) applies to run_function as it does to
  `/v1/execute`. Raise it if code nodes legitimately need more CPU seconds than that,
  up to their timeout.

**Measured latency.**

- Setup: Docker Desktop on Windows, service in a container driving the host daemon
  over the socket, a trivial `print('ok')`, 30 sequential calls per series, with 1 s
  between calls.
- Times are end to end from the host, measured on 2026-10-30.

| Path | p50 | p95 |
|---|---|---|
| `run_function`, warm pool | 123 ms | 143–174 ms |
| `run_function`, real code-node harness, warm | 173–192 ms | 240–276 ms |
| `run_function`, cold (pool disabled) | 434–459 ms | 461–544 ms |
| `/v1/execute` (ephemeral) | 709–855 ms | 874–1283 ms |

Back-to-back calls with no pause drain a pool of 2 faster than it refills. In that
burst test 28 of 30 calls were warm, and the misses fell back to a cold start.

**Kubernetes: deferred.** With `EXECUTOR_BACKEND=kubernetes` the endpoint answers 501,
and callers keep using `/v1/execute`. A pod pool needs its own design: pre-created
pods, `exec` through the API server, and pod-level TTL and orphan cleanup by label.
