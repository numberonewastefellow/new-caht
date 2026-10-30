# Flow nodes — code-level reference study (Phase R)

**Date:** 2026-10-30.

**Clones:** `D:/llm/reference-frameworks/`. They are read only, never built or run, and treated as untrusted. Detailed findings with file and line references:
- [research/01-engines.md](research/01-engines.md): LangGraph, graphon (Dify's engine), n8n, Langflow
- [research/02-sandboxes.md](research/02-sandboxes.md): dify-sandbox, Dify/graphon code node, n8n task runners, Windmill nsjail, Activepieces, plus **our code-interpreter**
- [research/03-webhooks-versioning.md](research/03-webhooks-versioning.md): n8n, Windmill, Activepieces, Dify, Langflow

**Licenses and our clean-room rule:**

| Repo | License | How we use it |
|---|---|---|
| LangGraph | MIT | reference |
| graphon | Apache-2.0 | reference |
| Langflow | MIT | reference |
| Activepieces | MIT (core) | reference |
| dify-sandbox | Apache | reference |
| n8n | Sustainable Use License | patterns only, no code copied |
| Windmill | AGPL | patterns only, no code copied |
| Dify main | modified Apache | patterns only, no code copied |

## What changes in our design (deltas vs the approved plan)

### Engine (P0, P2, P3)
| # | Was | Now | Why (source) |
|---|---|---|---|
| E1 | One thread per branch | **The main generator thread is the only coordinator.** It schedules, merges, checkpoints and does all DB work. One **bounded pool per run** (`WORKFLOW_MAX_CONCURRENCY`, default 4), filled as a **sliding window**. Branch threads run only *leaf* steps. Nested containers are scheduled by the coordinator, never inside a branch thread. A single child runs inline. | graphon dispatcher plus its "containers yield their worker" invariant (no nested pools, so no deadlock); LangGraph executor; Langflow's per-layer barrier stalls |
| E2 | Multiplexer polls N buses | **One shared `queue.Queue`.** Each branch's own emitter pushes `(branch_id, packet)` plus a done sentinel. The coordinator does a blocking `get(timeout=0.05)`. Each branch gets its own placement range. | LangGraph stream queue; our `max_turn_index` would collide between branches |
| E3 | Shared `step_outputs` under a lock | **Isolated branch state.** Each branch reads a frozen snapshot and writes its own dict, merged in **declared child order** at the join. Duplicate `output_key` is rejected when the workflow is saved. | LangGraph sorts writes by path and rejects duplicate last-value writes; graphon merges by index |
| E4 | — | **Cooperative cancel**: a per-run `threading.Event` checked between LLM and tool turns, never joining threads. Error modes: `fail_fast`, `continue`, `drop_failed`. | LangGraph can't cancel running sync futures; graphon's three error modes |
| E5 | A container re-runs entirely after a crash | **Progress is saved inside the container**: `containers[cid] = {done: {branch: out}, errors}`, updated as each branch finishes. Resume skips finished branches. Resume is idempotent, keyed by `(branch_id, idx)`. | LangGraph per-task pending writes; its double-apply bug is the pitfall to avoid |
| E6 | Checkpoint after every step | **Throttled checkpoints**: a dirty flag, flushed at most every 1–2 s, and **always** on pause, error and finish. A single writer with a monotonically increasing version. The trace is persisted once per container. | LangGraph "async" durability. This saves DB writes on every step (latency). |
| E7 | Loop: while/for-each | Break condition checked **before and after** each round. An explicit "break" can come from an agent's output. Checkpoint `{index, vars, accumulated}`. A **global step budget** in addition to `max_iterations`. for-each can later reuse the parallel window. | graphon loop and its ExecutionLimitsLayer; Langflow refuses cycles without `max_iterations` |
| E8 | Version the node types | **Also version the run semantics** (`schema_version`) **and the checkpoint schema** (`checkpoint_version`, with read-time migration). | n8n `executionOrder` v0/v1; graphon runtime_state v1→v3 |
| E9 | — | Retry backoff happens **inside the branch thread**, never on the coordinator. | graphon sleeps on its dispatcher thread, which stalls all events |

### Versioning (P0)
| # | Was | Now | Why |
|---|---|---|---|
| V1 | `definition_snapshot` jsonb on every execution | **An immutable `agent_workflow_version` table** with one row per save (number, content hash, JSON, author). Every run records `workflow_version_id` and the hash: chat runs, Pulse runs and webhook runs alike. Resume uses that version. This gives history, diff and revert without duplicating the JSON per run. | Windmill immutable versions; Activepieces locked flow versions; n8n `activeVersion` |
| V2 | — | **Workflow schema migrations are a chain of pure, idempotent N→N+1 steps.** They run lazily in memory on read and are written back only on save. Fixture tests per step. A failure means the workflow refuses to run and a clear error is shown. | Activepieces flow-version migrations v0→v27 (lazy on read) |
| V3 | Upgrade badge | Node upgrades are **opt-in**. Each node type can define an optional `upgrade(config)`; without one, the upgrade is marked *breaking*. The upgrade shows a diff dialog and records an audit event, and **revert** is supported. An unknown version is a **hard error**. Deprecated versions are hidden from the palette but still run. | n8n VersionedNodeType; Activepieces piece upgrade/revert |

### Code node (P1)
| # | Was | Now | Why |
|---|---|---|---|
| C1 | Inputs via stdin, nonce marker | **Harness:** the user source is passed base64-encoded and compiled under `<user_code>`. **Before the user code runs**, the harness saves the real stdout fd with `os.dup` and redirects `sys.stdout` to a 64 KB capped buffer, so prints become logs. It then writes **exactly one** framed result `\x00OMRES:<128-bit nonce>:<len>\x00<json>` to the saved fd. Zero frames, several frames, or a wrong length all fail the node. In v1 the inputs are base64 embedded in the harness, which also avoids a K8s stdin bug. | n8n result pipe and print capture; Dify's *static* tag can be spoofed (pitfall) |
| C2 | "Outputs type-checked" | **Strict host-side validation:** the output keys must equal the declared outputs. Typed values (bool is not an int; NaN/Inf rejected); depth ≤ 5; strings ≤ 100K; arrays ≤ 1000 items; total ≤ 1 MB. Any failure fails the node. *The nonce prevents collisions; this validation is the real trust boundary.* | graphon `code_node.py` and `limits.py` |
| C3 | Timeout 30 s default, 60 s max | **5 s default, 30 s max.** Enforced in three layers: the service timeout, a CPU rlimit, and the HTTP read timeout (+5 s). Fixed error kinds: `timeout`, `oom`, `user_exception` (trace ≤ 8 KB), `invalid_output`, `sandbox_unavailable`. | dify-sandbox 5 s; n8n 60 s |
| C4 | Uses `/v1/execute` as-is | **P1a** runs on the existing endpoint, so nothing changes in the service. **P1b** (latency): a new `POST /v1/run_function` with an out-of-band result channel (a result file), no last-line wrapper, prologue or workspace snapshot, plus a **warm pool of single-use hardened containers**, never reused, refilled in the background. Expected per-node latency drops from about 1 s to about 150 ms. | Activepieces warm engine + fresh isolate (0.2 s vs 2 s); our cold path is `docker run` + 3 exec calls + kill |
| C5 | — | Concurrency: a per-tenant semaphore (4) plus a global one in the backend. In the service, `max_workers` plus a `max_queue` that returns 503. | dify-sandbox |

### Webhooks (P4)
| # | Was | Now | Why |
|---|---|---|---|
| W1 | Verify HMAC | **Run the cheapest checks first:** method → token shape (404, no DB) → `Content-Length` and a hard 1 MB streaming cap (413) → tenant parsed from the token → Redis bucket per IP and per token (429 + `Retry-After`) → hashed lookup with a 30–60 s cache (uniform 404) → Standard Webhooks HMAC over the **raw bytes**, ±5 min, matched against every `v1,` signature (401) → **only then parse the JSON**, with depth and key limits. | Windmill and Activepieces parse before verifying (pitfall); Dify checks `Content-Length` first |
| W2 | Token hash | Token `whk_<tenant>.<secret>`, SHA-256, last 4 characters shown, **2 active hashes during rotation**. The HMAC secret is **encrypted** (it can't be hashed). | SCIM pattern; Standard Webhooks |
| W3 | Dedup unique index | A duplicate returns **202 with the original run id**. Webhook bursts **queue up to N pending runs and then return 429**; they don't reuse run-now's 409. | **None of the five refs deduplicate**, so this is ahead of all of them |
| W4 | "Send test event" | **Listen mode:** `POST /hooks/test/{token}` works only while the owner has "Listen" open (Redis TTL 120–300 s), otherwise 409. It **captures the payload without running** and never consumes production dedup keys. | n8n test webhooks; Activepieces `/test`; Dify debug bus |
| W5 | `{{body.x}}` | `{{payload.a.b}}`: substituted as a string, length-capped, **never re-expanded**, inside a delimited untrusted block. Authorization, Cookie and signature headers are stripped before the payload is stored. Tokens are redacted from access logs. No CORS. Owner access is re-checked when the run starts. | Windmill arg scrubbing; Langflow has no body cap and runs in-process (pitfalls) |

## ⚠️ Pre-existing security issues found in our code (not caused by this feature)
1. **The code-interpreter API has no authentication**, and `GET /v1/files` lists every tenant's files (`code-interpreter/.../api/routes.py:416`). Session ids aren't bound to a tenant.
2. **`docker-compose.dev-windows.yml` publishes it on `0.0.0.0:8000`**, so anyone on the LAN can call it directly.
3. **K8s executor pods** have unrestricted egress (the NetworkPolicy targets the wrong pods), no seccomp profile, a writable root filesystem, and an auto-mounted service-account token.
4. Smaller issues: no `--cpus`, no size cap on `/workspace`, an unbounded workspace snapshot, compilers and curl in the runtime image, and a K8s stdin read that hangs until timeout.

These affect today's Python tool, not only the new code node. The proposed fix goes into a hardening track **H**, done before P1:
- a service token and tenant binding on the API;
- removing the global file listing;
- binding the port to `127.0.0.1`;
- Docker hardening: `--read-only`, `--cpus`, a size cap on `/workspace`, an explicit seccomp profile;
- K8s hardening: deny-all egress, `RuntimeDefault` seccomp, a read-only root filesystem, no service-account token;
- a lean runtime image.
