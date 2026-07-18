"""Persistent session manager for the Code Interpreter.

Manages long-lived Docker containers with persistent Python kernels.
Each session keeps a ``python-executor-sci`` container alive and runs
``_kernel.py`` inside it.  Code executions are sent to the kernel via
stdin JSON and responses are read from stdout JSON — variables, imports,
and DataFrames survive between calls.
"""

from __future__ import annotations

import io
import json
import logging
import os
import queue
import selectors
import subprocess
import tarfile
import threading
import time
import uuid
from collections.abc import Generator, Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which
from typing import Literal

from app.app_configs import (
    PYTHON_EXECUTOR_DOCKER_BIN,
    PYTHON_EXECUTOR_DOCKER_IMAGE,
    PYTHON_EXECUTOR_DOCKER_RUN_ARGS,
    SESSION_CONTAINER_SLEEP_SEC,
    SESSION_IDLE_TIMEOUT_SEC,
    SESSION_MAX_CONCURRENT,
    SESSION_MAX_LIFETIME_SEC,
)
from app.services.executor_base import (
    EntryKind,
    ExecutionResult,
    StreamChunk,
    StreamEvent,
    StreamResult,
    WorkspaceEntry,
)

logger = logging.getLogger(__name__)

# Sentinel pushed on a session stream's queue to signal end-of-stream to the route.
_STREAM_SENTINEL = object()


class _KernelTimeout(Exception):
    """Raised inside the frame reader when a cell exceeds its wall-clock deadline."""


@dataclass
class SessionState:
    """Tracks a persistent session's container and kernel process."""

    session_id: str
    container_name: str
    kernel_proc: subprocess.Popen[bytes]
    created_at: float
    last_used_at: float
    staged_files: set[str] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    # Monotonically increasing per-cell id, stamped on every request so the frame
    # reader can drop stray late output tagged with an earlier cell.
    cell_id: int = 0
    # Set while a streaming cell is in flight so the reaper leaves it alone; set
    # while the kernel is being restarted so the reaper won't tear it down mid-restart.
    is_streaming: bool = False
    restarting: bool = False


class SessionManager:
    """Manages persistent code execution sessions.

    Each session owns a Docker container with a running ``_kernel.py``
    process.  The kernel accepts JSON-line requests on stdin and writes
    JSON-line responses to stdout, keeping all Python state alive.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = threading.Lock()
        self._docker_binary = self._resolve_docker_binary()
        self._image = PYTHON_EXECUTOR_DOCKER_IMAGE
        self._run_args = PYTHON_EXECUTOR_DOCKER_RUN_ARGS
        self._cleanup_thread: threading.Thread | None = None
        self._shutdown = threading.Event()

    # ------------------------------------------------------------------
    # Docker binary
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_docker_binary() -> str:
        candidate = PYTHON_EXECUTOR_DOCKER_BIN
        docker_path = which(candidate)
        if docker_path is None:
            raise RuntimeError("Docker CLI not found")
        return docker_path

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        memory_limit_mb: int | None = None,
    ) -> str:
        """Create a new persistent session with a running kernel.

        Returns the ``session_id``.
        """
        with self._lock:
            if len(self._sessions) >= SESSION_MAX_CONCURRENT:
                raise RuntimeError(
                    f"Maximum concurrent sessions ({SESSION_MAX_CONCURRENT}) reached"
                )

        session_id = uuid.uuid4().hex
        container_name = f"ci-session-{session_id[:12]}"
        now = time.time()

        # 1. Start a long-lived container (NO --rm)
        cmd: list[str] = [
            self._docker_binary,
            "run",
            "-d",
            "--pull", "never",
            "--network", "none",
            "--name", container_name,
            "--cgroupns", "host",
            "--pids-limit", "64",
            "--security-opt", "no-new-privileges",
            "--cap-drop", "ALL",
            "--cap-add", "CHOWN",
            "--workdir", "/workspace",
            "--tmpfs", "/tmp:rw,size=64m",  # noqa: S108
            "--tmpfs", "/workspace:rw,uid=65532,gid=65532",
            "--env", "PYTHONUNBUFFERED=1",
            "--env", "PYTHONDONTWRITEBYTECODE=1",
            "--env", "PYTHONIOENCODING=utf-8",
            "--env", "MPLCONFIGDIR=/tmp/matplotlib",
        ]

        if memory_limit_mb is not None:
            mem = max(int(memory_limit_mb), 16)
            cmd.extend(["--memory", f"{mem}m", "--memory-swap", f"{mem}m"])

        if self._run_args:
            import shlex
            cmd.extend(shlex.split(self._run_args))

        cmd.extend([self._image, "sleep", str(SESSION_CONTAINER_SLEEP_SEC)])

        result = subprocess.run(cmd, capture_output=True, text=True)  # nosec B603
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start session container: {result.stderr}")

        # 2. Stage the _kernel.py script into the container
        kernel_src = (Path(__file__).parent / "_kernel.py").read_bytes()
        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w") as tar:
            info = tarfile.TarInfo(name="_kernel.py")
            info.size = len(kernel_src)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(kernel_src))
        tar_bytes = tar_buf.getvalue()

        tar_cmd = [
            self._docker_binary, "exec", "-u", "65532:65532", "-i",
            container_name, "tar", "-x", "-C", "/workspace",
        ]
        tar_proc = subprocess.run(tar_cmd, input=tar_bytes, capture_output=True)  # nosec B603
        if tar_proc.returncode != 0:
            self._kill_container(container_name)
            raise RuntimeError(
                f"Failed to stage kernel: {tar_proc.stderr.decode('utf-8', errors='replace')}"
            )

        # 3. Start the persistent kernel process
        kernel_cmd = [
            self._docker_binary, "exec", "-u", "65532:65532", "-i",
            container_name, "python", "/workspace/_kernel.py",
        ]
        kernel_proc = subprocess.Popen(  # nosec B603
            kernel_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )

        state = SessionState(
            session_id=session_id,
            container_name=container_name,
            kernel_proc=kernel_proc,
            created_at=now,
            last_used_at=now,
        )

        with self._lock:
            self._sessions[session_id] = state

        logger.info(f"Session {session_id} created (container={container_name})")
        return session_id

    def delete_session(self, session_id: str) -> None:
        """Destroy a session, its kernel, and its container."""
        with self._lock:
            state = self._sessions.pop(session_id, None)

        if state is None:
            return

        self._teardown_session(state)
        logger.info(f"Session {session_id} deleted")

    def _teardown_session(self, state: SessionState) -> None:
        """Kill the kernel process and container.

        Acquires the session lock (bounded) first so we never tear down a container
        while a streaming reader thread is still reading its kernel pipe.
        """
        acquired = state._lock.acquire(timeout=5)
        try:
            with suppress(Exception):
                if state.kernel_proc.stdin:
                    state.kernel_proc.stdin.close()
                state.kernel_proc.kill()
                state.kernel_proc.wait(timeout=5)
            self._kill_container(state.container_name)
        finally:
            if acquired:
                state._lock.release()

    def _kill_container(self, name: str) -> None:
        with suppress(Exception):
            subprocess.run(
                [self._docker_binary, "kill", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        with suppress(Exception):
            subprocess.run(
                [self._docker_binary, "rm", "-f", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

    # ------------------------------------------------------------------
    # Code execution in session
    # ------------------------------------------------------------------

    def execute_in_session(
        self,
        session_id: str,
        code: str,
        timeout_ms: int = 30_000,
        max_output_bytes: int = 1_000_000,
        files: Sequence[tuple[str, bytes]] | None = None,
    ) -> ExecutionResult:
        """Execute code in a persistent session (blocking; returns the full result).

        Files are staged once; subsequent calls skip already-staged files.
        Variables and imports persist between calls. Output is drained through the
        shared frame reader (the same path streaming uses) so truncation, the
        deadline clock, and cell-id filtering are single-sourced.
        """
        with self._lock:
            state = self._sessions.get(session_id)
        if state is None:
            raise ValueError(f"Session '{session_id}' not found")

        out_parts: list[str] = []
        err_parts: list[str] = []
        result: StreamResult | None = None
        timed_out = False

        with state._lock:
            # Mark the cell in flight and refresh the idle clock up front so the reaper
            # never force-kills a session that was idle-then-active in the middle of a
            # long cell (the reaper skips sessions with is_streaming/restarting set).
            state.is_streaming = True
            state.last_used_at = time.time()
            try:
                if state.kernel_proc.poll() is not None:
                    raise RuntimeError(
                        f"Kernel for session '{session_id}' has exited "
                        f"(code={state.kernel_proc.returncode})"
                    )

                if files:
                    self._stage_files(state, files)

                state.cell_id += 1
                cell_id = state.cell_id
                request = json.dumps({"code": code}) + "\n"
                try:
                    state.kernel_proc.stdin.write(request.encode("utf-8"))  # type: ignore[union-attr]
                    state.kernel_proc.stdin.flush()  # type: ignore[union-attr]
                except (BrokenPipeError, OSError) as e:
                    raise RuntimeError(f"Kernel stdin broken: {e}") from e

                deadline = time.monotonic() + (timeout_ms / 1000.0)
                try:
                    for ev in self._read_kernel_frames(
                        state, cell_id, deadline, max_output_bytes
                    ):
                        if isinstance(ev, StreamChunk):
                            (out_parts if ev.stream == "stdout" else err_parts).append(ev.data)
                        else:
                            result = ev
                            break
                except _KernelTimeout:
                    timed_out = True

                # Restart the kernel while STILL holding state._lock so no concurrent
                # cell can grab the wedged kernel between the failure and the restart.
                if timed_out:
                    logger.warning(
                        f"Session {session_id}: execution timed out, restarting kernel"
                    )
                    self._restart_kernel_guarded(state)
                elif result is not None and result.error_kind in ("oom", "kernel_died"):
                    self._restart_kernel_guarded(state)
            finally:
                state.is_streaming = False
                state.last_used_at = time.time()

        if timed_out:
            return ExecutionResult(
                stdout="".join(out_parts),
                stderr="".join(err_parts) or "Execution timed out",
                exit_code=None,
                timed_out=True,
                duration_ms=timeout_ms,
                files=tuple(),
            )

        if result is None:
            # Kernel closed the pipe without a result frame — surface what we have.
            return ExecutionResult(
                stdout="".join(out_parts),
                stderr="".join(err_parts),
                exit_code=None,
                timed_out=False,
                duration_ms=0,
                files=tuple(),
            )

        return ExecutionResult(
            stdout="".join(out_parts),
            stderr="".join(err_parts),
            exit_code=result.exit_code,
            timed_out=result.timed_out,
            duration_ms=result.duration_ms,
            files=result.files,
        )

    def _read_kernel_frames(
        self,
        state: SessionState,
        expected_cell: int,
        deadline: float,
        max_output_bytes: int,
        cancel: threading.Event | None = None,
    ) -> Generator[StreamEvent, None, None]:
        """Yield StreamChunk(s) then a terminal StreamResult for one cell.

        Reads framed JSON lines from the kernel's protocol pipe on a single
        monotonic clock. Frames tagged with a different cell id (stray late output
        from a prior cell's daemon threads) are dropped. A non-JSON line is treated
        as raw stdout rather than aborting the cell. EOF means the kernel process
        died; the deadline (or a set ``cancel`` event, e.g. client disconnect)
        raises ``_KernelTimeout`` — so even a silent long cell is torn down promptly.
        """
        stdout = state.kernel_proc.stdout
        if stdout is None:
            raise RuntimeError("kernel stdout is not available")
        fd = stdout.fileno()
        sel = selectors.DefaultSelector()
        sel.register(fd, selectors.EVENT_READ)
        buf = b""
        sent = {"stdout": 0, "stderr": 0}
        marked = {"stdout": False, "stderr": False}
        try:
            while True:
                if (cancel is not None and cancel.is_set()) or time.monotonic() >= deadline:
                    raise _KernelTimeout()
                if not sel.select(timeout=0.5):
                    continue
                try:
                    data = os.read(fd, 65536)
                except OSError:
                    data = b""
                if not data:
                    rc = state.kernel_proc.poll()
                    kind = "oom" if rc in (137, -9) else "kernel_died"
                    yield StreamResult(
                        exit_code=rc,
                        timed_out=False,
                        duration_ms=0,
                        files=self._safe_snapshot(state.container_name),
                        error_kind=kind,
                    )
                    return
                buf += data
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    if not raw:
                        continue
                    try:
                        frame = json.loads(raw.decode("utf-8", errors="replace"))
                    except json.JSONDecodeError:
                        frame = {
                            "type": "output",
                            "stream": "stdout",
                            "data": raw.decode("utf-8", errors="replace"),
                            "cell": expected_cell,
                        }
                    if not isinstance(frame, dict) or frame.get("cell") != expected_cell:
                        continue
                    ftype = frame.get("type")
                    if ftype == "output":
                        stream: Literal["stdout", "stderr"] = (
                            "stderr" if frame.get("stream") == "stderr" else "stdout"
                        )
                        chunk = self._truncate_stream_chunk(
                            stream, frame.get("data", ""), sent, marked, max_output_bytes
                        )
                        if chunk is not None:
                            yield chunk
                    elif ftype == "result":
                        yield StreamResult(
                            exit_code=frame.get("exit_code"),
                            timed_out=bool(frame.get("timed_out")),
                            duration_ms=int(frame.get("duration_ms", 0)),
                            files=self._extract_workspace_snapshot(state.container_name),
                            error_kind=frame.get("error_kind"),
                        )
                        return
        finally:
            sel.close()

    @staticmethod
    def _truncate_stream_chunk(
        stream: Literal["stdout", "stderr"],
        data: str,
        sent: dict[str, int],
        marked: dict[str, bool],
        max_output_bytes: int,
    ) -> StreamChunk | None:
        """Apply the per-stream byte cap once; emit a single ``[truncated]`` marker.

        This is the ONLY truncation site for session output (blocking and streaming
        both go through the frame reader), so there is never a double marker.
        """
        if not data or marked[stream]:
            return None
        encoded = data.encode("utf-8")
        remaining = max_output_bytes - sent[stream]
        if remaining <= 0:
            marked[stream] = True
            return StreamChunk(stream=stream, data="\n...[truncated]")
        if len(encoded) <= remaining:
            sent[stream] += len(encoded)
            return StreamChunk(stream=stream, data=data)
        head = encoded[:remaining].decode("utf-8", errors="replace")
        sent[stream] = max_output_bytes
        marked[stream] = True
        return StreamChunk(stream=stream, data=head + "\n...[truncated]")

    def _safe_snapshot(self, container_name: str) -> tuple[WorkspaceEntry, ...]:
        """Best-effort workspace snapshot that never raises (used on error paths)."""
        try:
            return self._extract_workspace_snapshot(container_name)
        except Exception:
            return tuple()

    # ------------------------------------------------------------------
    # File staging
    # ------------------------------------------------------------------

    def _stage_files(
        self, state: SessionState, files: Sequence[tuple[str, bytes]]
    ) -> None:
        """Stage files into the session container (skip already-staged)."""
        new_files = [(p, c) for p, c in files if p not in state.staged_files]
        if not new_files:
            return

        tar_buf = io.BytesIO()
        with tarfile.open(fileobj=tar_buf, mode="w") as tar:
            for file_path, content in new_files:
                info = tarfile.TarInfo(name=file_path)
                info.size = len(content)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(content))

        tar_cmd = [
            self._docker_binary, "exec", "-u", "65532:65532", "-i",
            state.container_name, "tar", "-x", "-C", "/workspace",
        ]
        result = subprocess.run(tar_cmd, input=tar_buf.getvalue(), capture_output=True)  # nosec
        if result.returncode != 0:
            logger.warning(
                f"Failed to stage files in session {state.session_id}: "
                f"{result.stderr.decode('utf-8', errors='replace')}"
            )
            return

        for file_path, _ in new_files:
            state.staged_files.add(file_path)

    # ------------------------------------------------------------------
    # Workspace snapshot
    # ------------------------------------------------------------------

    def _extract_workspace_snapshot(self, container_name: str) -> tuple[WorkspaceEntry, ...]:
        """Extract files from the container workspace."""
        try:
            tar_cmd = [
                self._docker_binary, "exec", container_name,
                "tar", "-c",
                "--exclude=__main__.py",
                "--exclude=_kernel.py",
                "-C", "/workspace", ".",
            ]
            tar_result = subprocess.run(tar_cmd, capture_output=True, timeout=10)
            if tar_result.returncode != 0:
                return tuple()

            entries = []
            with tarfile.open(fileobj=io.BytesIO(tar_result.stdout), mode="r") as tar:
                for member in tar.getmembers():
                    if member.name == ".":
                        continue
                    clean_path = member.name.lstrip("./")
                    if member.isdir():
                        entries.append(
                            WorkspaceEntry(path=clean_path, kind=EntryKind.DIRECTORY, content=None)
                        )
                    elif member.isfile():
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            entries.append(
                                WorkspaceEntry(
                                    path=clean_path, kind=EntryKind.FILE, content=file_obj.read()
                                )
                            )
            return tuple(entries)
        except Exception:
            return tuple()

    # ------------------------------------------------------------------
    # Kernel restart
    # ------------------------------------------------------------------

    def _restart_kernel(self, state: SessionState) -> None:
        """Kill and restart the kernel process inside the container."""
        with suppress(Exception):
            # Kill all python processes in the container
            subprocess.run(
                [self._docker_binary, "exec", state.container_name, "pkill", "-9", "python"],
                capture_output=True,
            )
            if state.kernel_proc.stdin:
                state.kernel_proc.stdin.close()
            state.kernel_proc.kill()
            state.kernel_proc.wait(timeout=5)

        # Restart kernel
        kernel_cmd = [
            self._docker_binary, "exec", "-u", "65532:65532", "-i",
            state.container_name, "python", "/workspace/_kernel.py",
        ]
        state.kernel_proc = subprocess.Popen(  # nosec B603
            kernel_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        logger.info(f"Kernel restarted for session {state.session_id}")

    def _restart_kernel_guarded(self, state: SessionState) -> None:
        """Restart the kernel while flagging the session so the reaper won't tear
        the container down mid-restart."""
        state.restarting = True
        try:
            self._restart_kernel(state)
        finally:
            state.restarting = False

    # ------------------------------------------------------------------
    # Streaming execution
    # ------------------------------------------------------------------

    def stream_session(
        self,
        session_id: str,
        code: str,
        timeout_ms: int = 30_000,
        max_output_bytes: int = 1_000_000,
        files: Sequence[tuple[str, bytes]] | None = None,
    ) -> SessionStream:
        """Start a streaming execution and return a handle to poll for events.

        A dedicated reader thread owns the session lock, the kernel read, and the
        wall-clock deadline; the caller only polls the handle. See ``SessionStream``.
        """
        with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                raise ValueError(f"Session '{session_id}' not found")
            # Claim the session synchronously (under self._lock, before the worker
            # thread starts) so the reaper cannot select it in the gap before the
            # reader thread sets is_streaming, and is_session_busy sees it at once.
            state.is_streaming = True
            state.last_used_at = time.time()
        return SessionStream(self, state, code, timeout_ms, max_output_bytes, files)

    def is_session_busy(self, session_id: str) -> bool:
        """True if a streaming cell is currently in flight for this session."""
        with self._lock:
            state = self._sessions.get(session_id)
        return bool(state and state.is_streaming)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def has_session(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    # ------------------------------------------------------------------
    # Background cleanup
    # ------------------------------------------------------------------

    def start_cleanup_loop(self) -> None:
        """Start background thread that reaps idle/expired sessions."""
        if self._cleanup_thread is not None:
            return
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True, name="session-cleanup"
        )
        self._cleanup_thread.start()

    def _cleanup_loop(self) -> None:
        from app.app_configs import SESSION_CLEANUP_INTERVAL_SEC
        while not self._shutdown.is_set():
            self._shutdown.wait(timeout=SESSION_CLEANUP_INTERVAL_SEC)
            if self._shutdown.is_set():
                break
            self._reap_sessions()

    def _reap_sessions(self) -> None:
        """Remove sessions that are idle or past max lifetime."""
        now = time.time()
        to_remove: list[SessionState] = []

        with self._lock:
            for sid, state in list(self._sessions.items()):
                # Never reap a session with a live streaming cell or one mid-restart.
                if state.is_streaming or state.restarting:
                    continue

                idle = now - state.last_used_at
                age = now - state.created_at
                kernel_dead = state.kernel_proc.poll() is not None

                if idle > SESSION_IDLE_TIMEOUT_SEC or age > SESSION_MAX_LIFETIME_SEC or kernel_dead:
                    reason = (
                        "idle" if idle > SESSION_IDLE_TIMEOUT_SEC
                        else "expired" if age > SESSION_MAX_LIFETIME_SEC
                        else "kernel_dead"
                    )
                    logger.info(f"Reaping session {sid} (reason={reason})")
                    to_remove.append(self._sessions.pop(sid))

        for state in to_remove:
            self._teardown_session(state)

    def shutdown(self) -> None:
        """Stop cleanup and destroy all sessions."""
        self._shutdown.set()
        with self._lock:
            all_states = list(self._sessions.values())
            self._sessions.clear()
        for state in all_states:
            self._teardown_session(state)


class SessionStream:
    """Handle for a live streaming execution of one cell.

    A dedicated reader thread owns the session lock, the kernel read, and the
    wall-clock deadline, pushing ``StreamEvent`` objects onto a bounded queue. The
    HTTP route only calls :meth:`poll` (off the anyio threadpool) and may
    :meth:`cancel` on client disconnect. Because the deadline is enforced by the
    thread itself — in both the read loop and the queue ``put`` — a stalled or
    disconnected client can never pin the kernel or hold the session lock past the
    timeout. On any non-clean exit the kernel is restarted before the lock is
    released, so the pipe never carries half a cell into the next one.

    Queue items are: ``StreamEvent`` (StreamChunk | StreamResult), an ``Exception``
    (fatal setup error), or ``_STREAM_SENTINEL`` (end of stream).
    """

    def __init__(
        self,
        mgr: SessionManager,
        state: SessionState,
        code: str,
        timeout_ms: int,
        max_output_bytes: int,
        files: Sequence[tuple[str, bytes]] | None,
    ) -> None:
        self._q: queue.Queue[object] = queue.Queue(maxsize=256)
        self._cancel = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            args=(mgr, state, code, timeout_ms, max_output_bytes, files),
            daemon=True,
            name=f"ci-stream-{state.session_id[:8]}",
        )
        self._thread.start()

    def poll(self, block_timeout: float) -> object | None:
        """Return the next queued item, or None if none arrived within the timeout."""
        try:
            return self._q.get(timeout=block_timeout)
        except queue.Empty:
            return None

    def cancel(self) -> None:
        """Ask the reader thread to stop (client disconnected)."""
        self._cancel.set()

    def _put(self, ev: object, deadline: float) -> None:
        """Bounded-queue put that still honors the deadline/cancel if the consumer
        stalls (prevents a wedged client from pinning the kernel)."""
        while True:
            if self._cancel.is_set() or time.monotonic() >= deadline:
                raise _KernelTimeout()
            try:
                self._q.put(ev, timeout=0.25)
                return
            except queue.Full:
                continue

    def _run(
        self,
        mgr: SessionManager,
        state: SessionState,
        code: str,
        timeout_ms: int,
        max_output_bytes: int,
        files: Sequence[tuple[str, bytes]] | None,
    ) -> None:
        clean = False
        state._lock.acquire()
        try:
            state.is_streaming = True
            if state.kernel_proc.poll() is not None:
                raise RuntimeError("kernel is not running")
            if files:
                mgr._stage_files(state, files)
            state.cell_id += 1
            cell_id = state.cell_id
            request = json.dumps({"code": code}) + "\n"
            state.kernel_proc.stdin.write(request.encode("utf-8"))  # type: ignore[union-attr]
            state.kernel_proc.stdin.flush()  # type: ignore[union-attr]

            deadline = time.monotonic() + (timeout_ms / 1000.0)
            try:
                # Pass the cancel event so a client disconnect tears down even a
                # SILENT long cell within ~0.5s (not only at the wall-clock deadline).
                for ev in mgr._read_kernel_frames(
                    state, cell_id, deadline, max_output_bytes, cancel=self._cancel
                ):
                    state.last_used_at = time.time()
                    self._put(ev, deadline)
                    if isinstance(ev, StreamResult):
                        clean = ev.error_kind is None and not ev.timed_out
            except _KernelTimeout:
                # Deadline breached or client cancelled → deliver a timeout result
                # (best-effort; skipped if the client is already gone).
                with suppress(Exception):
                    self._put(
                        StreamResult(
                            exit_code=None,
                            timed_out=True,
                            duration_ms=timeout_ms,
                            files=mgr._safe_snapshot(state.container_name),
                            error_kind="timeout",
                        ),
                        time.monotonic() + 1.0,
                    )
        except Exception as exc:  # noqa: BLE001 - surfaced to the route as an error event
            with suppress(Exception):
                self._q.put(RuntimeError(str(exc)), timeout=1.0)
        finally:
            if not clean:
                # timeout / disconnect / crash → the pipe may hold half a cell; reset.
                with suppress(Exception):
                    mgr._restart_kernel_guarded(state)
            state.is_streaming = False
            state.last_used_at = time.time()
            state._lock.release()
            with suppress(Exception):
                self._q.put(_STREAM_SENTINEL, timeout=1.0)
