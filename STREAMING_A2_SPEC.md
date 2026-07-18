I now have every load-bearing anchor verified against ground truth. Here is the final spec.

---

# Live Streaming for the Code Interpreter — FINAL Implementation Spec (v2, review-hardened)

This supersedes the draft. The adversarial review surfaced **7 blockers + 14 majors**. Every one is resolved below (2 minors deferred with rationale). Three draft "no change" decisions are **overturned** and called out explicitly: (a) the `_FrameWriter`/`redirect_stdout` kernel approach is dropped for **OS fd-level capture**; (b) the CI stream route becomes **async with a dedicated reader thread**; (c) `PythonToolDelta` gains **additive optional fields** (the "no packet change" claim was wrong — reviewers were right that `exit_code`/`duration_ms` must reach the renderer).

---

## 0. Resolution ledger (every blocker + major)

| # | Sev | Finding | Resolution | Where |
|---|---|---|---|---|
| B1 | blk | Raw fd-1 writes (subprocess/C/`os.write`) corrupt single-pipe protocol; strict `json.loads` hard-kills cell; result sentinel forgeable | **Kernel OS-level capture**: dup real pipe → dedicated *protocol fd*; `dup2` private pipes onto fd 1/2; pump threads frame everything. Reader keeps a **tolerant `json.loads`** fallback → passthrough chunk. Protocol fd is `O_CLOEXEC` (non-inheritable) so user code cannot forge frames. | §3, §4 |
| B2 | blk | Output frames from background threads emitted *after* `result` pollute next cell's read | **Per-cell `cell_id`** stamped on every frame + **flush barrier** before `result`; reader **drops frames whose `cell_id` ≠ expected**; result write serialized under the same proto lock | §3 |
| B3 | blk | Stalled (non-disconnecting) client hangs cell; `timeout_ms` never evaluated at a suspended `yield`; lock + worker pinned (DoS) | **Dedicated reader thread** owns the blocking read + a **hard wall-clock deadline**, pushes to a **bounded queue**; kills+restarts on deadline regardless of consumer. Route only polls the queue. | §4, §5 |
| B4 | blk | Backend 50 ms coalescer has no flush timer → "print status, then slow work" shows nothing until the end | **Drop backend coalescing.** Emit one delta per `StreamChunk` **immediately**. Volume is bounded by the pump's 64 KB read chunking, not by print count. Frontend rAF batches rendering. | §6.2, §7.2 |
| B5 | blk | Live stderr trips the red Error block + "failed" status on a zero-exit run (tqdm/logging/warnings) | Status/error is driven by **`exit_code`/`timed_out`**, never by stderr presence. stderr rendered **muted** on zero-exit. Requires `exit_code` on the terminal delta. | §6.3, §7.3 |
| B6 | blk | Terminal delta still re-emits full aggregated stdout/stderr → every char renders twice | Rewrite `python_tool.py:644-671`: terminal delta carries **only** self-heal note + files + `exit_code`/`duration_ms`. Aggregated stdout/stderr stays **LLM-facing only**. | §6.4 |
| B7 | blk | Self-heal streams every attempt into one card → duplicate output + red "failed" on eventual success | **Attempt segmentation**: emit a `reset` boundary delta on each retry; renderer archives the failed attempt as a collapsed superseded block and clears the live pane. Status by `exit_code`. | §6.5, §7.5 |
| M1 | maj | stdout/stderr interleave destroyed; §1 ("one field per delta") contradicts §5.2 (dual-field coalesce) | **One stream per delta, never co-populated** (trivial now that we drop coalescing). Renderer walks deltas **in order** into an ordered segment list. | §6.2, §7.4 |
| M2 | maj | Sync `StreamingResponse` generator pins an anyio worker for the whole cell | Same as B3: reading is on our own thread; the async route holds a worker only for a ≤1 s queue poll. | §4, §5 |
| M3 | maj | Undrained kernel fd 2 can deadlock at ~64 KB | fd 2 is `dup2`'d onto a private pipe **drained by a pump thread** → never fills. | §3 |
| M4 | maj | Reaper races kernel restart / reaps an active long stream (`MAX_LIFETIME`) ignoring `state._lock` | Add `state.is_streaming`; reaper **skips streaming sessions on all three paths** (idle/lifetime/kernel_dead) and `try`-acquires `state._lock`; teardown acquires the lock. Reaper-induced EOF surfaces a distinct `error_kind="session_expired"`, not `timed_out`. | §4.4 |
| M5 | maj | `GeneratorExit`-based disconnect cleanup is non-deterministic for a sync generator | Async route polls **`request.is_disconnected()`** each loop and calls `stream.cancel()` deterministically; worker deadline is the backstop. | §5 |
| M6 | maj | `\r`/ANSI/partial-line handling claimed but absent → tqdm renders as stacked fragments | **Terminal-emulation pass** in the renderer (current-line buffer, `\r` column reset, ANSI strip) — v1, not deferred. | §7.4 |
| M7 | maj | Autoscroll won't stick; no bounded scroll container in FULL mode | Bounded `max-height` scroll pane while streaming; at-bottom measured in `useLayoutEffect` from **pre-commit** metrics; "Jump to latest" affordance. | §7.6 |
| M8 | maj | Elapsed timer reads turn-level `streamingStartTime`; no field carries cell duration | Stamp **per-card** start on first `isExecuting`; thread `duration_ms` on the terminal delta for accurate completion time. | §6.4, §7.3 |
| M9 | maj | Self-heal merges attempts in one card | Same as B7 (segmentation). | §6.5, §7.5 |
| M10 | maj | No DOM windowing; O(bytes × deltas) re-join every delta | **Bounded tail window** (last ~800 committed lines) + "show earlier"; committed lines accumulated in a **ref**, only new deltas folded per render. | §7.4 |
| M11 | maj | Frontend render cost backpressures → can time out kernel; rAF left "optional" | **rAF batching is mandatory** in the drain loop: coalesce multiple `nextPacket()` into one store write per frame. | §7.2 |
| M12 | maj | Mid-stream transport retry replays on a fresh (state-less) session → duplicate output / silent wrong result | `_execute_streaming` returns an **`emitted_any`** flag; connection-retry allowed **only pre-first-byte**; after any byte, emit `[connection lost — partial output above]` and surface the error. **Separate** from self-heal re-run (which always replays, with segmentation). | §6.6 |
| m1 | min | OOM/crash mislabeled `timed_out`; single huge write unbounded in reader memory | On EOF, `poll()` the proc → `error_kind ∈ {oom, kernel_died}` distinct from `timeout`. Pump's 64 KB read chunking bounds a single giant write to many small frames. | §3, §4.2 |
| m2 | min | Double truncation in rewritten blocking `execute_in_session` → two `…[truncated]` markers | Truncate in **exactly one place** (the shared reader). Blocking path takes the concatenation as final; drop the second `truncate_output`. | §4.5 |
| m3 | min | Claimed `EXECUTOR_BACKEND=docker` guard absent | Add explicit **400** when `session_id` is set and backend ≠ docker. | §5 |
| m4 | min | Compact/collapsed card hard-clips live output to 96 px; re-clips finished charts | Thread `isExecuting` into the compact branch → bounded scroll pane while streaming; render artifacts **outside** the clip. | §7.7 |
| **DEFER** | min (R2#10) | Artifact layout not reserved → completion jump | **Defer to fast-follow.** Include a fixed-height skeleton box only; full aspect-ratio reservation needs image dims we don't have pre-decode. Low severity, single settle. | §7.6 |
| **DEFER** | min (R2#11b) | Code doesn't stream token-by-token as written | **Defer — out of scope.** `PYTHON_TOOL_START` carries whole code; incremental tool-arg streaming is a separate transport change. Auto-collapse-on-success (R2#11a) **is** done. | §7.7 |

---

## 1. Revised 5-hop architecture

```
Kernel (_kernel.py)
  fd 1/2 → dup2'd onto PRIVATE pipes → pump threads →  framed JSON on a DEDICATED proto fd:
     {"type":"output","stream":"stdout","data":"…","cell":N}\n     (per pump read, ≤64 KB)
     {"type":"result","exit_code":0,"timed_out":false,"duration_ms":123,"cell":N}\n  ← barrier-gated sentinel
  ▼  (proto fd == parent's kernel_proc.stdout; O_CLOEXEC → user code can't reach it)
SessionManager.stream_session()  → DEDICATED reader THREAD: os.read line-assembly, cell_id filter,
     one-shot truncation, HARD wall-clock deadline → bounded queue.Queue → StreamChunk/StreamResult
  ▼
routes.execute_stream()  ASYNC generator: poll queue via run_in_threadpool(≤1s), race is_disconnected(),
     map to StreamOutputEvent/StreamResultEvent/StreamErrorEvent → SSE  (contract UNCHANGED)
  ▼  event: output / result / error
CodeInterpreterClient.execute_stream()   requests stream=True → typed ('output'|'result'|'error') tuples
  ▼
PythonTool._execute_streaming()   emit ONE PythonToolDelta per chunk (single stream field), aggregate
     for LLM; terminal delta = note + files + exit_code + duration_ms ONLY; emitted_any flag
  ▼  NDJSON {python_tool_delta}
PythonToolRenderer   incremental ordered fold (ref) + terminal emulation + windowing + rAF batch +
     exit_code-driven status + per-card timer + attempt segmentation
```

---

## 2. Packet contract changes (additive, backward-compatible)

`PythonToolDelta` (`backend/om/server/query_and_chat/streaming_models.py:254-260` and `web/src/app/app/services/streamingModels.ts:159-165`) gains **optional** fields (old clients ignore them; old servers omit them):

```python
class PythonToolDelta(BaseObj):
    type: Literal["python_tool_delta"] = StreamingType.PYTHON_TOOL_DELTA.value
    stdout: str = ""
    stderr: str = ""
    file_ids: list[str] = []
    files: list[PythonToolFile] = []
    # NEW — all optional:
    exit_code: int | None = None          # set ONLY on the terminal delta
    timed_out: bool = False               # terminal delta
    duration_ms: int | None = None        # terminal delta → accurate elapsed
    error_kind: Literal["timeout","oom","kernel_died","session_expired"] | None = None
    reset: bool = False                   # self-heal attempt boundary (archive prior, clear live pane)
```

**Invariant enforced by the producer:** a program-output delta sets **exactly one** of `stdout`/`stderr` (never both) → wire order = interleave order. Terminal delta sets `stdout`/`stderr` **empty** except a self-heal note, and sets `exit_code`/`duration_ms`.

---

## 3. Layer A — Kernel (`code-interpreter/code-interpreter/app/services/_kernel.py`)

**Overturns the draft.** Replace `main()` (`L96-147`) and the `io.StringIO`/`redirect_stdout` capture (`L119-131`). Keep `_exec_single_mode` (`L26-51`) and `_capture_open_figures` (`L59-93`) verbatim. Update the docstring (`L8-13`). Add `import os, threading, codecs`.

### 3.1 Startup wiring (fixes B1, M3, B1-forge, m1-memory)

```python
def main():
    user_globals = {"__name__": "__main__"}
    proto_fd = os.dup(1)                    # dedicated protocol channel to the parent pipe
    proto_lock = threading.Lock()
    def write_frame(obj):                   # ALL protocol + user frames go through here
        data = (json.dumps(obj) + "\n").encode("utf-8")
        with proto_lock:                    # serializes pump frames AND the result frame (fixes B2)
            os.write(proto_fd, data)

    # Redirect OS fd 1/2 onto private pipes so subprocess / C-extension / os.write output is captured.
    pout_r, pout_w = os.pipe(); os.dup2(pout_w, 1); os.close(pout_w)
    perr_r, perr_w = os.pipe(); os.dup2(perr_w, 2); os.close(perr_w)
    sys.stdout = os.fdopen(1, "w", buffering=1, encoding="utf-8", errors="replace")
    sys.stderr = os.fdopen(2, "w", buffering=1, encoding="utf-8", errors="replace")

    cell = {"id": 0}
    MARKER = b"\x00\x00__CELL_%d__\x00\x00"      # unique per cell; scanned with a carry buffer
    drained = {"stdout": threading.Event(), "stderr": threading.Event()}

    def pump(rfd, stream):
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        carry = b""
        marker = lambda: MARKER % cell["id"]
        while True:
            data = os.read(rfd, 65536)          # ≤64 KB per frame → bounds in-flight memory (m1)
            if not data: break
            buf = carry + data
            mk = marker()
            if mk in buf:                        # barrier: everything before it is this cell's output
                pre, buf = buf.split(mk, 1)
                if pre: write_frame({"type":"output","stream":stream,"data":dec.decode(pre),"cell":cell["id"]})
                carry = buf
                drained[stream].set()
                continue
            # flush all but the last (len(mk)-1) bytes so a split marker isn't emitted as data
            keep = len(mk) - 1
            emit, carry = buf[:-keep] if keep else buf, buf[-keep:] if keep else b""
            if emit: write_frame({"type":"output","stream":stream,"data":dec.decode(emit),"cell":cell["id"]})

    threading.Thread(target=pump, args=(pout_r,"stdout"), daemon=True).start()
    threading.Thread(target=pump, args=(perr_r,"stderr"), daemon=True).start()
```

- **`proto_fd` non-inheritable:** `os.dup`/`os.pipe` fds are `O_CLOEXEC` by default (PEP 446), so subprocesses inherit only fd 0/1/2 (the capture pipes) and **cannot write to `proto_fd`** → forged `result` sentinels are impossible (B1-forge).
- **Kernel launched with `python -u`** (or `PYTHONUNBUFFERED=1`, already set at `session_manager.py:125`) so writes flush promptly. `sys.stdout` is reopened **line-buffered**.

### 3.2 Per-cell loop + flush barrier (fixes B2, B5-exit_code, m1)

```python
    for line in sys.stdin:                       # stdin (fd 0) is still the parent pipe
        line = line.strip()
        if not line: continue
        cell["id"] += 1
        drained["stdout"].clear(); drained["stderr"].clear()
        try:
            code = json.loads(line).get("code","")
        except json.JSONDecodeError:
            write_frame({"type":"result","exit_code":1,"timed_out":False,"duration_ms":0,"cell":cell["id"]})
            continue

        exit_code = 0; start = time.perf_counter()
        try:
            try: _exec_single_mode(code, user_globals)
            finally: _capture_open_figures("/workspace")     # UNCHANGED — before the barrier/result
        except SystemExit as e: exit_code = e.code if isinstance(e.code,int) else 1
        except Exception: traceback.print_exc(file=sys.stderr); exit_code = 1

        # BARRIER: flush the main thread's bytes, write the marker to BOTH pipes, wait for pumps to
        # confirm they've emitted everything up to it → guarantees result is ordered AFTER cell output.
        sys.stdout.flush(); sys.stderr.flush()
        mk = MARKER % cell["id"]
        os.write(1, mk); os.write(2, mk)
        drained["stdout"].wait(timeout=0.5); drained["stderr"].wait(timeout=0.5)

        write_frame({"type":"result","exit_code":exit_code,"timed_out":False,
                     "duration_ms":int((time.perf_counter()-start)*1000),"cell":cell["id"]})
```

- The barrier guarantees the "result is last for its cell" invariant **even with user threads**: a daemon thread that keeps printing after the barrier produces frames tagged with the *current* `cell["id"]`; the reader for the **next** cell expects a higher id and **drops** them (B2). Late output is never mis-parsed and never crashes the next read.
- `_capture_open_figures` still runs in the inner `finally` **before** the barrier → figure PNGs exist on disk before `result` → snapshot picks them up (figures-at-completion, unchanged).

---

## 4. Layer B — SessionManager (`code-interpreter/code-interpreter/app/services/session_manager.py`)

### 4.1 Imports & state
- Add to `session_manager.py:35-40`: `StreamChunk, StreamResult, StreamEvent` from `executor_base`. Add module-level `import os, selectors, queue` (remove the lazy import at `L440`).
- `SessionState` (`L45-55`): add `is_streaming: bool = False` and `restarting: bool = False`.

### 4.2 Shared frame reader (new private generator) — fixes m1, m2, B1-tolerance, B2-filter

```python
def _read_kernel_frames(self, state, expected_cell, deadline, max_output_bytes):
    """Yield StreamChunk(s) then a terminal StreamResult. Single clock: time.monotonic()."""
    fd = state.kernel_proc.stdout.fileno()
    sel = selectors.DefaultSelector(); sel.register(fd, selectors.EVENT_READ)
    buf = b""; sent = {"stdout":0,"stderr":0}; marked = {"stdout":False,"stderr":False}
    try:
        while True:
            if time.monotonic() >= deadline: raise _KernelTimeout()
            if not sel.select(timeout=0.5): continue
            data = os.read(fd, 65536)
            if not data:                                   # EOF → kernel process died
                rc = state.kernel_proc.poll()
                kind = "oom" if rc in (137, -9) else "kernel_died"
                yield StreamResult(exit_code=rc, timed_out=False, error_kind=kind,
                                   duration_ms=0, files=self._safe_snapshot(state.container_name))
                return
            buf += data
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                if not raw: continue
                try: frame = json.loads(raw.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:               # tolerance (B1): treat as raw stdout
                    frame = {"type":"output","stream":"stdout","data":raw.decode("utf-8","replace"),
                             "cell": expected_cell}
                if frame.get("cell") != expected_cell:     # stale frame from a prior cell (B2)
                    continue
                if frame.get("type") == "output":
                    chunk = self._truncate_stream_chunk(frame["stream"], frame.get("data",""),
                                                        sent, marked, max_output_bytes)
                    if chunk is not None: yield chunk
                elif frame.get("type") == "result":
                    yield StreamResult(exit_code=frame.get("exit_code"),
                                       timed_out=bool(frame.get("timed_out")),
                                       error_kind=frame.get("error_kind"),
                                       duration_ms=frame.get("duration_ms",0),
                                       files=self._extract_workspace_snapshot(state.container_name))
                    return
    finally:
        sel.close()
```

- `_truncate_stream_chunk` applies the per-stream byte cap on already-decoded text (kernel already produced `str`), emitting a **one-time** `"\n…[truncated]"` chunk the first time a stream crosses `max_output_bytes` (uses `BaseExecutor.truncate_output`'s suffix convention, `executor_base.py:207-213`). This is the **only** truncation site (fixes m2).
- `StreamResult` grows an optional `error_kind` field (`executor_base.py:125`), defaulted `None`, so ephemeral results are unaffected.

### 4.3 Streaming API with dedicated reader thread — fixes B3, M2, M5

`stream_session` returns a `SessionStream` handle; the **thread** owns the lock, deadline, and kernel lifecycle, decoupled from HTTP consumption.

```python
_SENTINEL = object()

class SessionStream:
    def __init__(self, mgr, state, code, timeout_ms, max_output_bytes, files):
        self._q = queue.Queue(maxsize=256)
        self._cancel = threading.Event()
        self._t = threading.Thread(target=self._run,
            args=(mgr,state,code,timeout_ms,max_output_bytes,files), daemon=True)
        self._t.start()
    def poll(self, block_timeout):                  # called from route via run_in_threadpool
        try: return self._q.get(timeout=block_timeout)
        except queue.Empty: return None
    def cancel(self): self._cancel.set()

    def _run(self, mgr, state, code, timeout_ms, max_output_bytes, files):
        clean = False
        state._lock.acquire()                       # held for the whole cell; try/finally, NOT `with`
        try:
            state.is_streaming = True               # reaper skips (M4)
            if state.kernel_proc.poll() is not None: raise RuntimeError("kernel exited")
            if files: mgr._stage_files(state, files)
            state._cell_id = getattr(state, "_cell_id", 0) + 1
            state.kernel_proc.stdin.write((json.dumps({"code":code})+"\n").encode()); state.kernel_proc.stdin.flush()
            deadline = time.monotonic() + timeout_ms/1000.0
            try:
                for ev in mgr._read_kernel_frames(state, state._cell_id, deadline, max_output_bytes):
                    state.last_used_at = time.time()             # bump per chunk → reap won't kill active stream
                    self._put(ev, deadline)                      # HARD deadline enforced even if consumer stalls
                    if isinstance(ev, StreamResult): clean = ev.error_kind is None and not ev.timed_out
            except _KernelTimeout:
                self._put(StreamResult(exit_code=None, timed_out=True, error_kind="timeout",
                                       duration_ms=timeout_ms, files=mgr._safe_snapshot(state.container_name)), deadline)
        except Exception as exc:
            with suppress(Exception): self._q.put(RuntimeError(str(exc)), timeout=1)
        finally:
            if not clean:                            # timeout / disconnect / crash → pipe may hold half a cell
                with suppress(Exception): mgr._restart_kernel_guarded(state)
            state.is_streaming = False; state.last_used_at = time.time()
            state._lock.release()
            with suppress(Exception): self._q.put(_SENTINEL, timeout=1)

    def _put(self, ev, deadline):
        while True:                                  # bounded-queue backpressure that still honors the deadline
            if self._cancel.is_set() or time.monotonic() >= deadline: raise _KernelTimeout()
            try: self._q.put(ev, timeout=0.25); return
            except queue.Full: continue

def stream_session(self, session_id, code, timeout_ms=30_000, max_output_bytes=1_000_000, files=None):
    with self._lock: state = self._sessions.get(session_id)
    if state is None: raise ValueError(f"Session '{session_id}' not found")
    return SessionStream(self, state, code, timeout_ms, max_output_bytes, files)
```

- **Hard deadline is consumer-independent** (fixes B3/M2): if the browser stalls, the queue fills, `_put` loops with a 0.25 s timeout and re-checks `deadline`/`cancel`; on breach it raises `_KernelTimeout` → kernel restart → lock released. No suspended-`yield` can pin the session.
- **Disconnect** (M5): the route calls `cancel()`; `_put` observes it and unwinds → restart + release. Deterministic, not GC-dependent.

### 4.4 Reaper made lock-aware — fixes M4

Rewrite `_reap_sessions` (`L483-504`): inside the `self._lock` loop, **skip any `state.is_streaming or state.restarting` session on all three conditions** (idle/lifetime/kernel_dead). Have `_teardown_session` (`L204-212`) acquire `state._lock` (bounded, `acquire(timeout=…)`) before killing. Add `_restart_kernel_guarded` = set `state.restarting=True`, call `_restart_kernel` (`L403-428`), clear the flag — the reaper honors `restarting` so it cannot tear the container down mid-restart. Because the reader thread holds `state._lock` for the whole stream and sets `is_streaming`, the `MAX_LIFETIME` path can no longer reap an active long cell; when a reaper genuinely expires an idle-but-old session between cells, the EOF path yields `error_kind="session_expired"` (distinct from `timeout`).

### 4.5 Rewrite `execute_in_session` on the shared reader — fixes m2, unifies paths

Keep the signature/return (`ExecutionResult`) so `/v1/execute` and the manual Run path are unchanged. Internally (replacing `L252-322`): acquire `state._lock`, bump `state._cell_id`, write request, drain `_read_kernel_frames(state, cell_id, deadline, max_output_bytes)` into two per-stream buffers, take `exit_code`/`timed_out`/`error_kind`/`duration_ms`/`files` from the terminal `StreamResult`. **Do not call `truncate_output` again** (the reader already truncated once) — take the concatenation as final. On `_KernelTimeout` → `_restart_kernel_guarded`. **Delete `_read_line_with_timeout` (`L434-456`)** — one reader for both paths, buffering hazard gone everywhere, single clock everywhere (kills the `perf_counter`/`monotonic` split at `L273-274` vs `L445`).

---

## 5. Layer C — Route (`code-interpreter/code-interpreter/app/api/routes.py:215-257`)

Becomes **`async def`**, takes the `Request`, guards the backend (m3), polls the handle off the anyio pool (M2), races disconnect (M5), emits keepalives.

```python
from starlette.concurrency import run_in_threadpool
from fastapi import Request

@router.post("/execute/stream")
async def execute_stream(req: ExecuteRequest, request: Request) -> StreamingResponse:
    _validate_timeout(req)
    settings = get_settings(); storage = get_file_storage()
    staged_files, input_files_map = _stage_request_files(req, storage)
    mgr = None
    if req.session_id:
        if settings.executor_backend != "docker":                           # m3
            raise HTTPException(400, "session streaming requires the docker executor backend")
        mgr = get_session_manager()
        if not mgr.has_session(req.session_id):                              # pre-stream 404 (mirror L159-163)
            raise HTTPException(404, f"Session '{req.session_id}' not found")

    async def agen():
        if req.session_id:
            stream = mgr.stream_session(req.session_id, req.code, req.timeout_ms,
                                        settings.max_output_bytes, staged_files or None)
            try:
                while True:
                    if await request.is_disconnected(): break
                    ev = await run_in_threadpool(stream.poll, 1.0)           # holds a worker ≤1s, then releases
                    if ev is None: yield ": keepalive\n\n"; continue         # idle-proxy defeat
                    if ev is _SENTINEL: break
                    if isinstance(ev, Exception): yield StreamErrorEvent(message=str(ev)).to_sse(); break
                    yield _event_to_sse(ev, input_files_map, storage)
            finally:
                stream.cancel()                                             # idempotent; guarantees worker cleanup
        else:
            # Ephemeral path unchanged in behavior; wrapped so disconnect still tears the subprocess down.
            gen = execute_python_streaming(code=req.code, stdin=req.stdin, timeout_ms=req.timeout_ms,
                    max_output_bytes=settings.max_output_bytes, cpu_time_limit_sec=settings.cpu_time_limit_sec,
                    memory_limit_mb=settings.memory_limit_mb, files=staged_files,
                    last_line_interactive=req.last_line_interactive)
            try:
                while True:
                    if await request.is_disconnected(): break
                    ev = await run_in_threadpool(_safe_next, gen)
                    if ev is _DONE: break
                    yield _event_to_sse(ev, input_files_map, storage)
            finally:
                gen.close()

    return StreamingResponse(agen(), media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","Connection":"keep-alive","X-Accel-Buffering":"no"})
```

`_event_to_sse` maps `StreamChunk → StreamOutputEvent(stream,data).to_sse()` and `StreamResult → StreamResultEvent(exit_code, timed_out, duration_ms, error_kind, files=_save_workspace_files(...)).to_sse()` — reusing `_save_workspace_files` (`L93-108`) and the mapping at `L235-244` verbatim. `StreamResultEvent` (`schemas.py`) gains an optional `error_kind` field. Optional concurrency cap: if `mgr.is_session_busy(session_id)` (i.e., `state.is_streaming`) return **409** so a second concurrent cell fails fast instead of blocking on `state._lock`.

---

## 6. Layer D — om (`backend/om/tools/tool_implementations/python/`)

### 6.1 `code_interpreter_client.py` — add `execute_stream` (after `execute`, ~L93)

```python
def execute_stream(self, code, *, timeout_ms=30000, files=None, session_id=None):
    """Yield ('output', stream, data) chunks, then ('result', ExecuteResponse)."""
    payload = {"code": code, "timeout_ms": timeout_ms}
    if files: payload["files"] = files
    if session_id: payload["session_id"] = session_id
    with self.session.post(f"{self.base_url}/v1/execute/stream", json=payload, stream=True,
                           timeout=(10, timeout_ms/1000 + 30)) as r:
        r.raise_for_status()
        event = data = None
        for line in r.iter_lines(decode_unicode=True):
            if line.startswith("event: "): event = line[7:]
            elif line.startswith("data: "): data = line[6:]
            elif line == "" and event:
                p = json.loads(data)
                if event == "output": yield ("output", p["stream"], p["data"])
                elif event == "result":
                    yield ("result", ExecuteResponse(stdout="", stderr="", exit_code=p["exit_code"],
                        timed_out=p["timed_out"], duration_ms=p["duration_ms"],
                        error_kind=p.get("error_kind"),
                        files=[WorkspaceFile(**f) for f in p["files"]]))
                elif event == "error": raise RuntimeError(p["message"])
                event = data = None
```
`ExecuteResponse` (`code_interpreter_client.py:20-36`) gains optional `error_kind`. The terminal `ExecuteResponse` carries empty `stdout`/`stderr` (streamed already); the caller aggregates.

### 6.2 `python_tool.py` — `_execute_streaming` (emit-per-chunk, no coalescer) — fixes B4, M1

```python
def _execute_streaming(self, client, placement, code, timeout_ms, files, session_id):
    acc_out, acc_err, emitted_any = [], [], False
    final = None
    for ev in client.execute_stream(code=code, timeout_ms=timeout_ms, files=files, session_id=session_id):
        if ev[0] == "output":
            _, stream, data = ev
            if not data: continue
            (acc_out if stream == "stdout" else acc_err).append(data)
            emitted_any = True
            # ONE stream field per delta → wire order == interleave order (M1). Emit immediately (B4).
            self.emitter.emit(Packet(placement=placement, obj=PythonToolDelta(
                stdout=data if stream == "stdout" else "",
                stderr=data if stream == "stderr" else "", file_ids=[])))
        else:
            final = ev[1]
    return ExecuteResponse(stdout="".join(acc_out), stderr="".join(acc_err),
        exit_code=final.exit_code, timed_out=final.timed_out,
        duration_ms=final.duration_ms, error_kind=final.error_kind, files=final.files), emitted_any
```
No 50 ms timer, no `pend`, no dual-field flush → the "print status then 5 s compute" case shows the status line the instant its frame arrives (B4), and every delta carries exactly one stream (M1). Volume is bounded by the kernel pump's 64 KB reads, so a tight print loop yields ~`bytes/64KB` deltas, not one-per-print.

### 6.3 Wire-up in `_execute_with_retry` (`L266-303`) — fixes M12

Swap `client.execute(...)` for `_execute_streaming(...)`; thread `emitted_any` out. Retry (fresh session) **only when `not emitted_any`** (nothing streamed → safe to replay; note that a fresh session **loses persistent state** — documented). If a retriable error fires **after** any byte streamed, do **not** replay: emit a terminal-style delta `stderr="[connection lost — partial output above]"` and re-raise so the error surfaces (prevents duplicate UI output on a state-less replay). This guard is scoped to connection-retry **only**; self-heal re-runs are separate (§6.5).

### 6.4 Terminal delta = note + files + metadata ONLY — fixes B6, B5, M8

Rewrite `python_tool.py:641-671`. Keep `truncated_stdout`/`truncated_stderr` (from `L561-567`) **exclusively** for `LlmPythonExecutionResult` (`L673-681`) — the LLM still sees full aggregated output. Build a **note-only** pair for the UI and emit the terminal delta without the program streams:

```python
succeeded = response.exit_code == 0
note_stdout = self_heal_note if (self_heal_note and succeeded) else ""
note_stderr = self_heal_note if (self_heal_note and not succeeded) else ""
self.emitter.emit(Packet(placement=placement, obj=PythonToolDelta(
    stdout=note_stdout, stderr=note_stderr,          # NO aggregated program output (B6)
    file_ids=generated_file_ids, files=python_tool_files,
    exit_code=response.exit_code, timed_out=response.timed_out,     # drives status (B5)
    duration_ms=response.duration_ms, error_kind=response.error_kind)))  # accurate elapsed (M8)
```
The self-heal note was never streamed, so putting it (only) on the terminal delta does not double-render. Program stdout/stderr appeared exactly once, live.

### 6.5 Self-heal segmentation — fixes B7, M9, M1(status)

In `_execute_with_self_heal` (`L345-467`), the existing `⚠️ Attempt` status delta (`L400-413`) additionally sets **`reset=True`** — this is the attempt boundary. The renderer, on `reset`, archives the failed attempt's live pane as a collapsed superseded block and clears the live accumulation, so attempt N+1 streams into a clean pane. Because status is `exit_code`-driven (B5) and intermediate program output is scoped per attempt, an eventually-successful run shows **success**, no red block, and no duplicated lines. The aggregated `response` the LLM sees is the final attempt — matching the visible pane (no transcript divergence).

---

## 7. Layer E — Frontend (`web/src/.../renderers/code/PythonToolRenderer.tsx`, `web/src/hooks/useChatController.ts`)

### 7.1 New stream-fold hook (the core of M6/M7/M10/M1)
Add `usePythonStreamBuffer(packets)` that replaces the join-all logic (`PythonToolRenderer.tsx:72-79`). It keeps **refs**: an ordered committed-segment list `[{stream, text}]`, a current-line buffer, a `lastPacketCount` cursor. On render it folds **only new deltas** since the cursor (not the whole array — kills the O(bytes×deltas) re-join, M10), applying terminal emulation (M6):
- append `data`; on `\n` commit the line into a segment tagged with its `stream`; on `\r` reset the current column (overwrite semantics — tqdm renders as a single updating bar); strip a safe subset of ANSI escapes.
- on a delta with `reset:true` (self-heal boundary), push the current segments into an `archivedAttempts` ref and clear live segments (§6.5).
- expose `segments` (ordered — M1 interleave), `archivedAttempts`, and a **windowed** view: last ~800 committed lines + a "show earlier / N more lines" control + a full-log download (M10).

### 7.2 rAF batching — MANDATORY (M11, pairs with B4)
In the drain loop (`useChatController.ts:723-893`), coalesce multiple `nextPacket()` drains into **one** `upsertToCompleteMessageTree` per animation frame (batch around `L853`), so React commit latency can't backpressure the NDJSON socket (and therefore can't inflate the cell's wall-time toward `timeout_ms`). Consume/ack the socket eagerly; render on rAF.

### 7.3 Status/timer driven by exit_code + duration_ms (B5, M8)
Rewrite `status` (`L138-149`): while `isExecuting` → "Running…"; on complete use `exit_code` (now on the terminal delta) — `exit_code===0` → "Analyzed · {duration_ms/1000}s"; `timed_out`/`error_kind` → the matching message ("Timed out" / "Ran out of memory" for `oom` / "Kernel crashed" for `kernel_died`); non-zero exit → "Failed". **Never** derive failure from `stderr.length` (`L89` `hasError` is removed as a status input). Stamp a **per-card** `startedAt` on first `isExecuting` (not the turn-level `streamingStartTime`); show a live elapsed counter only after ~2 s; on completion show `duration_ms` (accurate cell time, not wall-clock).

### 7.4 stderr rendering + interleave (B5, M1, M6)
Render the ordered `segments` in one `<pre>`: stdout segments normal, **stderr segments muted/secondary-tinted on a zero-exit run**, error-tinted only when `exit_code!==0`/`timed_out`. This replaces the separate red "Error:" pane (`L192-201`) for the normal case; a true failure still gets an error treatment, gated on `exit_code`.

### 7.5 Self-heal archive UI (B7, M9)
Render `archivedAttempts` as collapsed "Attempt N (failed)" sub-cards above the live pane; the live pane shows only the current attempt. Matches the UX spec's "errored attempt preserved as a separate superseded card."

### 7.6 Bounded scroll container + sticky autoscroll (M7)
Give the output pane an explicit `max-height ~400px; overflow-y:auto` **while streaming** (so there is a real scroll container, not window scroll). Compute at-bottom in a `useLayoutEffect` from **pre-update** `scrollHeight`/`scrollTop` (measure before the new segment commits), then set `scrollTop=scrollHeight` only if it *was* at bottom (~60 px threshold); otherwise show a "Jump to latest ↓" button. Reserve a `min-height` while executing so completion doesn't collapse the box. Artifact box: a fixed-height **skeleton** on the image grid (`L204-215`) to soften the completion insert (full aspect-ratio reservation deferred).

### 7.7 Memo, compact clip, auto-collapse (M10, m4, R2#11a)
- Wrap the state construction in `useMemo` keyed on `packetCount`; key `imageFiles`/`nonImageFiles` (`L121-128`) on `packetCount` too (the current `[files]` key is defeated by the per-render `flatMap`).
- Thread `isExecuting` into the compact branch (`L269-274`): while streaming use a bounded scroll pane instead of the 96 px `max-h-24` clip; render **artifacts outside** the clip so a finished chart isn't clipped to 96 px (m4).
- On terminal `exit_code===0` **with** ≥1 artifact, **auto-collapse** the code/stdout scaffolding behind the header while keeping the artifact and any user-toggled expand state (R2#11a). Code token-streaming (R2#11b) is **deferred** — out of scope.

---

## 8. Concurrency & security guardrails (consolidated)

- **One writer of truth per pipe.** All kernel frames go through `write_frame` under `proto_lock`; user fd 1/2 output is captured by pumps and framed with a `cell_id`. Protocol fd is `O_CLOEXEC` → user/subprocess code cannot forge or corrupt frames.
- **Deadline is consumer-independent.** The reader thread enforces `timeout_ms` on a monotonic clock in both the read-select loop and the bounded-queue `_put` loop; a wedged client cannot hold `state._lock` past the deadline.
- **Lock discipline.** `state._lock` held via `try/finally` across the whole cell (never `with`, since we push to a queue), released on every exit path. Reaper and teardown are lock-aware and honor `is_streaming`/`restarting`. Optional **409** on a busy session avoids unbounded `acquire` waits.
- **Threadpool safety.** The blocking kernel read runs on our own dedicated thread; the anyio pool is used only for ≤1 s queue polls → `SESSION_MAX_CONCURRENT` streams cannot exhaust the pool or starve `/v1/execute`.
- **Kernel death vs timeout.** EOF → `poll()` → `error_kind ∈ {oom, kernel_died}`; deadline → `timeout`; reaper → `session_expired`. Never all collapsed to `timed_out`.
- **Security envelope unchanged.** No new endpoints, caps, network, or files; container run args (`session_manager.py:110-139`: `--network none`, `--cap-drop ALL`, `--pids-limit 64`, `--security-opt no-new-privileges`) untouched. Session streaming is explicitly **Docker-only** (400 otherwise); k8s ephemeral streaming unaffected.
- **Truncation is single-sourced** and now emits a visible `…[truncated]` marker; om's `_truncate_output` still bounds the LLM-facing text.

---

## 9. Ordered, incrementally-shippable steps (each independently verifiable)

**Step 1 — Kernel fd-level protocol.** `_kernel.py` rewrite `main()`/capture (`L96-147`), add pumps + barrier + `cell_id`; keep `_exec_single_mode`/`_capture_open_figures`. Ensure kernel launched with `-u` (`session_manager.py:167-170`).
Verify: new `session_tests/test_kernel_protocol.py` — feed `{"code":"for i in range(3): print(i)"}`, assert ≥3 `output` frames then one `result` (matching `cell`); a raising cell → `stderr` frames + `result` `exit_code=1`; **`subprocess.run(['echo','hi'])`** and a banner-printing native import → captured as `output`, session survives; **`os.write(1, b'{"type":"result",...}')`** does **not** forge a boundary; a figure cell writes `figure_1.png` before `result`; a daemon thread printing after cell end tags frames with the old `cell_id` (dropped next cell).

**Step 2 — Shared reader + rewrite `execute_in_session`.** Add `_read_kernel_frames`, `_truncate_stream_chunk`, `_KernelTimeout`, `_safe_snapshot`, `_restart_kernel_guarded`; make reaper/teardown lock-aware + `is_streaming`; delete `_read_line_with_timeout` (`L434-456`); rewrite `execute_in_session` (`L252-322`), single truncation.
Verify: existing `session_tests/test_variable_persistence.py`, `test_dataframe_persistence.py`, `test_error_recovery.py`, `test_auto_figure_capture.py` still pass. New regressions: clock-bug (400 ms sleep, `timeout_ms=2000` must not time out); **exactly one** `…[truncated]` marker for an over-cap cell on `/v1/execute`; `os.write(1, b'garbage\n')` doesn't kill the session.

**Step 3 — `stream_session` / `SessionStream`.** Add the handle + reader thread + hard deadline + queue.
Verify: drive directly against a real container — chunks then `StreamResult`; a `while True: pass` cell hits `timeout_ms`, yields `timed_out=True`, kernel restarted; an OOM cell yields `error_kind="oom"`; a **stalled consumer** (stop polling) still restarts within `timeout_ms` and releases the lock (assert a subsequent cell acquires promptly); reaper does not reap a session with `is_streaming=True`.

**Step 4 — Async route branch.** `execute_stream` → `async def` + `Request`, docker guard, disconnect race, keepalive, `_event_to_sse`.
Verify: extend `tests/integration_tests/test_streaming.py` — create session, stream `code="import time\nfor i in range(3):\n print(i); time.sleep(0.05)"` → **multiple** `output` events + one `result`; a second streamed cell proves **state persisted**; unknown `session_id` → 404 (pre-stream); `session_id` under `EXECUTOR_BACKEND=kubernetes` → 400; disconnect mid-stream → server logs restart, next cell works.

**Step 5 — `CodeInterpreterClient.execute_stream`.** Add the SSE parser + `error_kind`.
Verify: `backend/tests/external_dependency_unit/tools/test_python_tool.py` — mock/live SSE, assert ordered `('output',…)` then `('result', ExecuteResponse)` with populated `duration_ms`.

**Step 6 — `_execute_streaming` + terminal-delta + segmentation + retry guard.** `python_tool.py`: add `_execute_streaming`; swap calls in `_execute_with_retry` (`L275-303`) and self-heal (`L378-384`,`L447-453`); `reset=True` on the attempt delta (`L400-413`); rewrite terminal emit (`L644-671`) to note+files+metadata; add `emitted_any` connection-retry guard.
Verify: extend `backend/tests/workflow_creator/test_sandbox_persistence.py` (its parser already counts `python_tool_delta`, `L120-154`) — Message 1 (`for i in range(5): print(i)`) yields **>1** delta and each line appears **exactly once** in the concatenation (proves live + no double-render); Messages 2-3 still prove variable/DataFrame/chart persistence; a broken→fixed self-heal case asserts a `reset` delta, final **success** status, and no duplicated lines.

**Step 7 — Frontend live rendering.** `usePythonStreamBuffer` (fold/terminal-emulation/windowing/interleave/archive); status+timer by `exit_code`/`duration_ms`; bounded scroll + sticky autoscroll; memo fixes; compact-clip + auto-collapse; mandatory rAF batching in `useChatController.ts` (~`L853`).
Verify: RTL test feeds a growing `packets` array (sequential single-stream deltas incl. a `\r` tqdm sequence, an interleaved stderr line, and a `reset` boundary) → asserts monotonic growth, a single collapsed tqdm line, in-order stderr placement, archived failed attempt, fold runs once per `packetCount`. Manual: run the sandbox-persistence flow — lines materialize during Message 1, card holds position, sticky-bottom yields to manual scroll, elapsed after ~2 s, tqdm bar updates in place, a `logging`/`warning` cell shows **no** red box on exit 0, chart appears at completion, `prefers-reduced-motion` disables shimmer.

---

## 10. End-to-end verification plan (acceptance gates)

1. **Liveness:** status-line-then-5 s-compute shows the line at t≈0 (not t≈5 s). Gate: Step 6 timing assertion + manual.
2. **No double-render:** each printed line appears exactly once across deltas, and once on screen. Gate: Step 6 concatenation assertion (blocks merge).
3. **stderr ≠ failure:** tqdm/logging/FutureWarning cell → normal (muted) output, "Analyzed", exit 0. Gate: Step 7 RTL + manual.
4. **Self-heal:** broken→fixed run → failed attempt archived/collapsed, live pane clean, final success, LLM transcript == final attempt. Gate: Step 6 + Step 7.
5. **Robustness:** subprocess/`os.write`/native-banner/forged-sentinel/daemon-thread cases keep the session alive and correctly attributed. Gate: Step 1.
6. **Concurrency/DoS:** stalled client restarts within `timeout_ms` and frees the lock; `SESSION_MAX_CONCURRENT` simultaneous streams do not starve `/v1/execute`. Gate: Step 3 + a load check against the anyio pool size.
7. **Lifecycle:** reaper never kills an active stream; OOM/timeout/crash/expiry each carry the correct `error_kind`. Gate: Step 3.
8. **Persistence + figures unchanged:** variables/DataFrames persist across streamed cells; figures land at completion. Gate: Steps 2, 4, 6 (existing suites).
9. **No regressions:** `/v1/execute` (both modes) and ephemeral `/v1/execute/stream` behavior unchanged; single `…[truncated]` marker in both session paths. Gate: Steps 2, 4.

---

### Key files (absolute)
- `D:\llm\danswer20022026\code-interpreter\code-interpreter\app\services\_kernel.py` — Step 1 (rewrite `main()` L96-147, add pumps/barrier)
- `D:\llm\danswer20022026\code-interpreter\code-interpreter\app\services\session_manager.py` — Steps 2-3 (reader L234-322, delete L434-456, reaper L483-504, restart L403-428, `SessionState` L45-55, add `SessionStream`)
- `D:\llm\danswer20022026\code-interpreter\code-interpreter\app\api\routes.py` — Step 4 (`execute_stream` L215-257 → async)
- `D:\llm\danswer20022026\code-interpreter\code-interpreter\app\services\executor_base.py` — add `StreamResult.error_kind` (L125), reuse `truncate_output` L207-213
- `D:\llm\danswer20022026\code-interpreter\code-interpreter\app\models\schemas.py` — add optional `error_kind` to `StreamResultEvent` (reuse SSE contract L67-109)
- `D:\llm\danswer20022026\backend\om\tools\tool_implementations\python\code_interpreter_client.py` — Step 5 (`execute_stream`, `ExecuteResponse.error_kind`)
- `D:\llm\danswer20022026\backend\om\tools\tool_implementations\python\python_tool.py` — Step 6 (`_execute_streaming`; `_execute_with_retry` L266-303; self-heal L378-453 + `reset` L400-413; terminal emit L644-671)
- `D:\llm\danswer20022026\backend\om\server\query_and_chat\streaming_models.py` — `PythonToolDelta` L254-260 gains 5 optional fields
- `web/src/app/app/services/streamingModels.ts` L159-165 — mirror the new optional fields
- `web/src/app/app/message/messageComponents/timeline/renderers/code/PythonToolRenderer.tsx` — Step 7 (fold L57-101, status L138-149, spinner L155-170, panes L182-201, images L204-215, compact L269-274)
- `web/src/hooks/useChatController.ts` — Step 7 (rAF batch ~L853; per-card start not turn-level `streamingStartTime` L744-749)
- Tests: `backend\tests\workflow_creator\test_sandbox_persistence.py`; `code-interpreter\...\tests\integration_tests\test_streaming.py` + `...\session_tests\*`; `backend\tests\external_dependency_unit\tools\test_python_tool.py`