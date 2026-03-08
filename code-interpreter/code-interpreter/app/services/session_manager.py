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
import subprocess
import tarfile
import threading
import time
import uuid
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which

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
    BaseExecutor,
    EntryKind,
    ExecutionResult,
    WorkspaceEntry,
)

logger = logging.getLogger(__name__)


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
        """Kill the kernel process and container."""
        with suppress(Exception):
            if state.kernel_proc.stdin:
                state.kernel_proc.stdin.close()
            state.kernel_proc.kill()
            state.kernel_proc.wait(timeout=5)

        self._kill_container(state.container_name)

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
        """Execute code in a persistent session.

        Files are staged once; subsequent calls skip already-staged files.
        Variables and imports persist between calls.
        """
        with self._lock:
            state = self._sessions.get(session_id)
        if state is None:
            raise ValueError(f"Session '{session_id}' not found")

        with state._lock:
            # Check kernel is still alive
            if state.kernel_proc.poll() is not None:
                raise RuntimeError(
                    f"Kernel for session '{session_id}' has exited "
                    f"(code={state.kernel_proc.returncode})"
                )

            # Stage new files into the container
            if files:
                self._stage_files(state, files)

            # Send code to kernel
            request = json.dumps({"code": code}) + "\n"
            try:
                state.kernel_proc.stdin.write(request.encode("utf-8"))  # type: ignore[union-attr]
                state.kernel_proc.stdin.flush()  # type: ignore[union-attr]
            except (BrokenPipeError, OSError) as e:
                raise RuntimeError(f"Kernel stdin broken: {e}") from e

            # Read response (with timeout)
            start = time.perf_counter()
            deadline = start + (timeout_ms / 1000.0)
            response_line = self._read_line_with_timeout(
                state.kernel_proc.stdout,  # type: ignore[arg-type]
                deadline,
            )

            state.last_used_at = time.time()

        if response_line is None:
            # Timeout — kill the kernel process and restart it
            logger.warning(f"Session {session_id}: execution timed out, restarting kernel")
            self._restart_kernel(state)
            return ExecutionResult(
                stdout="",
                stderr="Execution timed out",
                exit_code=None,
                timed_out=True,
                duration_ms=timeout_ms,
                files=tuple(),
            )

        try:
            resp = json.loads(response_line)
        except json.JSONDecodeError:
            return ExecutionResult(
                stdout=response_line,
                stderr="",
                exit_code=0,
                timed_out=False,
                duration_ms=int((time.perf_counter() - start) * 1000),
                files=tuple(),
            )

        duration_ms = resp.get("duration_ms", int((time.perf_counter() - start) * 1000))

        # Extract workspace files
        workspace_files = self._extract_workspace_snapshot(state.container_name)

        stdout = resp.get("stdout", "")
        stderr = resp.get("stderr", "")

        return ExecutionResult(
            stdout=BaseExecutor.truncate_output(stdout.encode(), max_output_bytes),
            stderr=BaseExecutor.truncate_output(stderr.encode(), max_output_bytes),
            exit_code=resp.get("exit_code", 0),
            timed_out=False,
            duration_ms=duration_ms,
            files=workspace_files,
        )

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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_line_with_timeout(
        stream: io.BufferedReader,
        deadline: float,
    ) -> str | None:
        """Read one line from stream with a deadline. Returns None on timeout."""
        import selectors

        sel = selectors.DefaultSelector()
        sel.register(stream, selectors.EVENT_READ)
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            events = sel.select(timeout=remaining)
            if not events:
                return None
            line = stream.readline()
            if not line:
                return None
            return line.decode("utf-8", errors="replace").rstrip("\n")
        finally:
            sel.close()

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
