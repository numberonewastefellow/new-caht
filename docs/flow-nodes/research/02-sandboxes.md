# Reference study 2 — code sandboxes (for the Python code node)

Sources: `D:/llm/reference-frameworks/` (2026-10-30).

| Project | License | How we used it |
|---|---|---|
| dify-sandbox | Apache | reference |
| graphon | Apache | reference |
| Activepieces | MIT | reference |
| Dify main | modified Apache | read-only, patterns only |
| n8n | SUL | read-only, patterns only |
| Windmill | AGPL | read-only, patterns only |

All descriptions below are in our own words.

## Reference systems

**dify-sandbox (Go)**
- **Isolation:**
  - A fresh Python process per request; there is no warm pool.
  - UIDs come from a pool, and the environment is kept minimal.
  - User code arrives over a pipe on fd 3, never through argv or a file.
  - Setup order: chroot into a copied Python tree → `no_new_privs` → seccomp filter (default action kills the process, applied with TSYNC) → drop groups/gid/uid.
- **Syscall allowlist:** file I/O, memory, futex and time. `clone`/`mkdir` return an errno, so user code cannot create threads or subprocesses. Socket syscalls are added only when network is enabled.
- **Limits:** a wall-clock timer kills the process. There are no rlimits, memory caps or output caps of its own; the container is expected to supply them.
- **Concurrency:** a `max_workers` semaphore, and `max_requests` returns 503 when exceeded.
- **Defaults:** 4 workers, 50 requests, 5 s timeout, and **network ON** (an unsafe default). Auth is one static API key.

**Dify caller + graphon code node**
- **Template:** the user's code, then a trailer that base64-decodes the inputs, calls `main(**inputs)`, and prints the result between a fixed `<<RESULT>>` tag. The parser is a greedy regex.
  - **Weakness:** because the tag is static, any print that contains it corrupts or spoofs the result.
- **Output validation** (`graphon/src/graphon/nodes/code/code_node.py` and `limits.py`) — the part to copy as a pattern:
  - Every declared output must be present, and extra keys are rejected.
  - Per-type checks: string length, number range, float precision, array length caps per element type, and a depth limit.
  - Untyped lists must be homogeneous, and unsupported types fail closed.

**n8n task runners (read-only)**
- **Protocol:** the runner opens a websocket to the broker using a single-use grant token. It sends time-limited offers, and rejects an accept when it is at `max_concurrency` (default 5).
- **Process:** one forkserver subprocess per task.
- **Result channel:** results go over a dedicated pipe as length-prefixed JSON, **never via stdout**. `print` is replaced so prints are captured separately, capped at 100 calls.
- **In-process hardening:**
  - An AST validator blocks dunders, frame/traceback introspection, `__import__`, relative imports and format-string tricks.
  - Import allowlists for stdlib and external packages, **empty by default**.
  - A builtins denylist covering eval, exec, open, getattr and type.
  - `sys.modules` is sanitized, and `os.environ` is cleared.
- **Modes:** "all items" or "each item". Defaults: 60 s timeout, 1 GiB maximum payload.

**Windmill (read-only)**
- **Isolation:** nsjail per job.
  - time limit, address-space limit, and rlimits for cpu, fsize and nofile;
  - new user and network namespaces;
  - read-only bind mounts of the system and site-packages, with only `args.json` and `result.json` writable;
  - no seccomp in this config.
- **Network** is off only when the script has the `no_network` annotation. The environment is cleared and rebuilt, and stdin is set to null.
- **I/O:** inputs go in via a file and the result comes back via `result.json`, out of band. NaN, Infinity and `\u0000` are converted to null.
- **Dependencies:** installed per requirement with uv and cached as tarballs in S3.
- **Latency:** "dedicated workers" keep a long-lived process that reads jobs from stdin. This uses an in-band result prefix and runs **outside nsjail**, so it trades security for speed.

**Activepieces (MIT)**
- **Code-only mode** (recommended for multi-tenant use): a fresh `isolated-vm` context per Code step, 128 MB, no `require`, disposed after the step. Inputs are passed as JSON-roundtripped copies.
- **Process mode:** ioi/isolate namespaces. It starts cold on every run and needs CAP_SYS_ADMIN.
- **Python/Deno path:** Deno with no permissions.
- **Latency:** `AP_REUSE_SANDBOX` keeps the engine process warm while each step still gets a fresh isolate: about 0.2 s warm versus about 2 s cold.

## Gaps in OUR code-interpreter (`code-interpreter/`, `backend/om/tools/tool_implementations/python/`)

| Area | Finding | Severity |
|---|---|---|
| **API auth / tenancy** | **No auth on `/v1/*`.** `GET /v1/files` lists every tenant's files (`routes.py:416`). Session IDs aren't bound to a tenant. | **HIGH** (affects today's Python tool) |
| **K8s network** | Executor pods have **unrestricted egress**. The chart's NetworkPolicy is disabled and selects service pods, not `component: executor`. | **HIGH** in K8s mode |
| K8s pod hardening | No `seccompProfile`, `readOnlyRootFilesystem: False`, service-account token auto-mounted, service-link env vars injected. | MEDIUM |
| Result spoofing | The ephemeral path returns raw stdout, so any marker parsed from it can be forged. The session protocol fd is CLOEXEC (which only blocks subprocesses), and in-process code can write to it. Cell ids are predictable. | MEDIUM (needs a design) |
| Cold start | Every ephemeral run does `docker run` + 3 `docker exec` + `kill` (`executor_docker.py:356-394`), about 0.5–1.5 s. K8s creates a pod and polls, taking several seconds. **No warm pool.** | latency |
| Reuse | Sessions are warm but stateful (shared globals in `_kernel.py:108`), so they can't be shared across users or runs. | — |
| Limits | Has pids 64 and memory = swap. CPU is only `ulimit cpu=5` (no `--cpus`), and sessions have no CPU ulimit. The `/workspace` tmpfs has no size cap, and the workspace snapshot is read back unbounded. | MEDIUM |
| Image | Ships build-essential, gfortran and curl, with no package allowlist. | LOW–MEDIUM |
| K8s stdin bug | `write_stdin` never closes stdin, so `sys.stdin.read()` hangs until the timeout (`executor_kubernetes.py:527`). | bug |
| Errors | No error taxonomy on the ephemeral path. | — |
| Good already | Docker mode: `--network none`, only 4 explicit env vars, cap-drop ALL, no-new-privileges, pids limit. | ✅ |

## Recommended code-node design (adopted)

**Harness (generated by the backend)**
- User source goes in as base64, is `compile`d under `<user_code>`, and cannot break the template.
- **Before the user code runs**, the harness:
  - saves the real stdout fd with `os.dup`;
  - redirects `sys.stdout` to a capped 64 KB buffer, so prints become logs.
- It then checks that `main` is callable and takes one argument, and calls `main(inputs)`.
- The result is serialized with `json.dumps(allow_nan=False)` and a size check, then written as **one frame** to the saved fd.
- Run it without the last-line wrapper and without the figure prologue.

**Inputs**
- Phase 0: base64 JSON embedded in the harness (no service change; also sidesteps the K8s stdin bug). Capped at 1–2 MB.
- Phase 1: a new endpoint with an `inputs` field.

**Result frame**
- Format: `\x00OMRES:<nonce>:<len>\x00<json>`, where the nonce is a 128-bit value (`secrets.token_hex(16)`) per run, generated by the backend.
- Accept **exactly one** frame with a matching length. Zero frames, several frames, or a length mismatch fails the run.
- What the nonce does and doesn't do:
  - User code shares the process, so it can still forge its own result.
  - The nonce prevents *collisions* between data and the marker, and confusion between runs.
  - **The real trust boundary is host-side validation.**

**Output validation** (backend, graphon-style)
- **Shape:** the result must be a dict whose keys **equal** the declared outputs.
- **Types:**
  - string;
  - number, with int and float kept distinct and bool not counted as an int;
  - boolean;
  - object;
  - array of string, number, object or boolean.
- **Limits:**
  - depth ≤ 5;
  - strings ≤ 100K characters;
  - arrays ≤ 1000 items (≤ 100 for arrays of objects);
  - total size ≤ 1 MB;
  - integers within ±2^53.
- Reject NaN/Inf and non-string keys. Any failure fails the node.

**Timeouts** — default 5 s, maximum 30 s, enforced in three layers:
1. the service's `timeout_ms`;
2. a CPU rlimit inside the container;
3. the HTTP read timeout = node timeout + 5 s.

**Error kinds:** `timeout`, `oom` (137), `user_exception` (trace capped at 8 KB), `invalid_output`, `sandbox_unavailable`.

**Concurrency**
- Backend: a semaphore per tenant (default 4) plus a global one.
- Service: fixed `max_workers`, and `max_queue` returns 503 so callers back off.

**Warm pool (no state shared across tenants)**
- Keep pre-started, hardened, **single-use** containers.
- Each request pops one container, runs a single `docker exec`, destroys the container, and refills the pool in the background. Expected latency is about 100–200 ms instead of about 1 s.
- Containers are never reused. Heavy libraries are imported lazily.

**Fail-closed rules:** any of these fails the run, and there is never a local fallback:
- no frame, a malformed frame, or several frames;
- a non-zero exit code even when a frame is present;
- output over the cap (fail, never truncate);
- the service is unreachable;
- an unknown output type.

**Service additions (sequenced into P1, or a separate hardening track)**
1. **API auth:** a shared service token plus tenant ID on sessions and files; remove the global `GET /v1/files` listing.
2. **`POST /v1/run_function`:** takes `{harness, inputs_b64, nonce, timeout_ms}`.
   - It skips the last-line wrapper, the prologue and the workspace snapshot.
   - The result comes back over a channel that isn't stdout (`/tmp/result.json` or fd 3), with a size cap.
   - It returns `error_kind`.
3. **Docker hardening:** `--read-only`, a size cap on `/workspace`, `--cpus`, an explicit seccomp profile, and a non-root user set at `run` time.
4. **K8s hardening:**
   - `automountServiceAccountToken: false` and `enableServiceLinks: false`;
   - `seccompProfile: RuntimeDefault` and `readOnlyRootFilesystem: true`;
   - a deny-all NetworkPolicy on executor pods, ideally with gVisor.
5. **Warm pool**, with min, max and TTL settings.
6. **Lean runtime image** (no compilers or curl), with a pinned package allowlist.
7. **Fixes:** cap the workspace snapshot size, and send EOF on K8s stdin.
