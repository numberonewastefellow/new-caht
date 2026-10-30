"""Single-use Docker sandboxes for ``POST /v1/run_function``.

A function sandbox is an idle container started with the same hardened flag set as
every other sandbox (``hardened_docker_run_flags``: no network, read-only root,
size-capped tmpfs, non-root, every capability dropped, pids/CPU/memory caps). Its main
process only sleeps. A program runs in it with exactly one ``docker exec``: the source
is streamed to ``python -`` on stdin, so nothing is staged and no workspace snapshot
is taken. The caller destroys the container afterwards; it is never reused.

Every container carries two labels so this service instance can find (and remove)
its own containers after a crash, without touching anybody else's:

* ``om.code-interpreter.run-function=1`` marks a run_function sandbox;
* ``om.code-interpreter.owner=<owner>`` names the service instance.

As a last line of defence each container also expires on its own: the ``sleep``
lifetime is bounded and the container is started with ``--rm``.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
import threading
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from typing import IO

from app.services.sandbox_hardening import SANDBOX_USER, hardened_docker_run_flags

logger = logging.getLogger(__name__)

RUN_FUNCTION_LABEL = "om.code-interpreter.run-function"
OWNER_LABEL = "om.code-interpreter.owner"

# Where a program may write its out-of-band result (exported as $OM_RESULT_PATH).
# /tmp is a private, size-capped tmpfs of the single-use container.
RESULT_FILE_PATH = "/tmp/result"  # noqa: S108 - path inside the sandbox container

_CONTAINER_PREFIX = "ci-fn-"
# Budgets for the short docker CLI calls around a run (not the program itself).
_START_TIMEOUT_SEC = 60
_AUX_TIMEOUT_SEC = 15
# How long to wait for the output pipes to drain once the docker CLI has exited.
_DRAIN_TIMEOUT_SEC = 5
_READ_CHUNK_BYTES = 64 * 1024
# The docker CLI reports daemon-side failures (container gone, not running) like this.
_DOCKER_ERROR_PREFIX = b"Error response from daemon:"


class SandboxError(RuntimeError):
    """A sandbox container could not be started, listed or driven."""


@dataclass(frozen=True, slots=True)
class CappedOutput:
    """Bytes read from a stream, cut at a cap (``truncated`` is True if cut)."""

    data: bytes
    truncated: bool


@dataclass(frozen=True, slots=True)
class ProgramRun:
    """Raw outcome of one program run inside a sandbox container."""

    stdout: CappedOutput
    stderr: CappedOutput
    # None when the run timed out (the process was killed by the service).
    exit_code: int | None
    timed_out: bool
    duration_ms: int

    @property
    def is_docker_failure(self) -> bool:
        """True when the docker CLI, not the program, failed (e.g. container gone).

        A program could print the same text to fake this, but it would only mislabel
        its own run.
        """
        return (
            self.exit_code not in (None, 0)
            and not self.stdout.data
            and self.stderr.data.startswith(_DOCKER_ERROR_PREFIX)
        )


def new_container_name() -> str:
    return f"{_CONTAINER_PREFIX}{uuid.uuid4().hex[:20]}"


def limited_python_command(cpu_limit_sec: int) -> str:
    """Shell command that applies the CPU-time rlimit and then becomes ``python -``.

    The soft limit is one second below the hard one, so a runaway program first gets
    SIGXCPU (exit 152, reported as a timeout) rather than an anonymous SIGKILL (137,
    which is reserved for the OOM killer). The hard limit is lowered first: dash
    rejects a hard limit below the current soft one.
    """
    soft = max(1, int(cpu_limit_sec))
    return f"ulimit -t {soft + 1} && ulimit -S -t {soft} && exec python -"


class _CappedReader:
    """Drains a pipe on a daemon thread, keeping at most ``cap`` bytes.

    Everything past the cap is read and discarded, so a chatty program can neither
    block on a full pipe nor grow the service's memory.
    """

    def __init__(self, stream: IO[bytes], cap: int, name: str) -> None:
        self._stream = stream
        self._cap = max(0, cap)
        self._buf = bytearray()
        self._total = 0
        self._thread = threading.Thread(target=self._drain, daemon=True, name=name)
        self._thread.start()

    def _drain(self) -> None:
        with suppress(OSError, ValueError):
            while chunk := self._stream.read(_READ_CHUNK_BYTES):
                room = self._cap - len(self._buf)
                if room > 0:
                    self._buf += chunk[:room]
                self._total += len(chunk)

    def result(self, timeout: float) -> CappedOutput:
        self._thread.join(timeout)
        return CappedOutput(data=bytes(self._buf), truncated=self._total > self._cap)


def _feed_stdin(proc: subprocess.Popen[bytes], data: bytes) -> None:
    """Write the program to stdin and close it (a thread, so the deadline holds)."""

    def _write() -> None:
        if proc.stdin is None:
            return
        with suppress(OSError, ValueError):
            proc.stdin.write(data)
        with suppress(OSError, ValueError):
            proc.stdin.close()

    threading.Thread(target=_write, daemon=True, name="fn-stdin").start()


class DockerFunctionSandbox:
    """Starts, drives and removes single-use run_function containers."""

    def __init__(
        self,
        *,
        docker_binary: str,
        image: str,
        owner: str,
        memory_limit_mb: int,
        lifetime_sec: int,
        run_args: str = "",
    ) -> None:
        self.docker_binary = docker_binary
        self.image = image
        self.owner = owner
        self.memory_limit_mb = memory_limit_mb
        self.lifetime_sec = lifetime_sec
        self.run_args = run_args

    # ------------------------------------------------------------------
    # Container lifecycle
    # ------------------------------------------------------------------

    def build_start_command(self, name: str) -> list[str]:
        """The ``docker run`` command for one idle, hardened sandbox container."""
        memory = f"{max(int(self.memory_limit_mb), 16)}m"
        cmd: list[str] = [
            self.docker_binary,
            "run",
            "-d",
            "--rm",
            *hardened_docker_run_flags(name),
            "--memory",
            memory,
            "--memory-swap",
            memory,
            "--label",
            f"{RUN_FUNCTION_LABEL}=1",
            "--label",
            f"{OWNER_LABEL}={self.owner}",
        ]
        if self.run_args:
            cmd.extend(shlex.split(self.run_args))
        cmd.extend([self.image, "sleep", str(int(self.lifetime_sec))])
        return cmd

    def start(self, name: str) -> None:
        """Start an idle sandbox container named ``name``.

        Raises:
            SandboxError: docker could not start it (any partial container is removed).
        """
        try:
            proc = subprocess.run(
                self.build_start_command(name),
                capture_output=True,
                text=True,
                timeout=_START_TIMEOUT_SEC,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.remove(name)
            raise SandboxError(f"failed to start sandbox container: {exc}") from exc
        if proc.returncode != 0:
            self.remove(name)
            raise SandboxError(f"failed to start sandbox container: {proc.stderr.strip()}")

    def remove(self, name: str) -> None:
        """Kill and remove a container. Idempotent; never raises."""
        with suppress(Exception):
            subprocess.run(
                [self.docker_binary, "rm", "-f", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=_AUX_TIMEOUT_SEC,
                check=False,
            )

    def list_owned(self, *, include_stopped: bool = False) -> list[str]:
        """Names of this owner's run_function containers (running ones by default).

        Raises:
            SandboxError: docker could not list containers.
        """
        cmd = [self.docker_binary, "ps"]
        if include_stopped:
            cmd.append("-a")
        cmd.extend(
            [
                "--filter",
                f"label={RUN_FUNCTION_LABEL}=1",
                "--filter",
                f"label={OWNER_LABEL}={self.owner}",
                "--format",
                "{{.Names}}",
            ]
        )
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=_AUX_TIMEOUT_SEC, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SandboxError(f"failed to list sandbox containers: {exc}") from exc
        if proc.returncode != 0:
            raise SandboxError(f"failed to list sandbox containers: {proc.stderr.strip()}")
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    def remove_owned(self) -> int:
        """Remove every container of this owner (orphans of an earlier process included).

        Returns how many were removed; logs and returns 0 if docker can't list them.
        """
        try:
            names = self.list_owned(include_stopped=True)
        except SandboxError as exc:
            logger.warning(f"run_function: could not list leftover sandboxes: {exc}")
            return 0
        for name in names:
            self.remove(name)
        return len(names)

    # ------------------------------------------------------------------
    # Running a program
    # ------------------------------------------------------------------

    def build_exec_command(self, name: str, cpu_limit_sec: int) -> list[str]:
        """The single ``docker exec`` that runs a program read from stdin."""
        return [
            self.docker_binary,
            "exec",
            "-i",
            "-u",
            SANDBOX_USER,
            "--env",
            f"OM_RESULT_PATH={RESULT_FILE_PATH}",
            name,
            "sh",
            "-c",
            limited_python_command(cpu_limit_sec),
        ]

    def run_program(
        self,
        name: str,
        program: str,
        *,
        timeout_sec: float,
        cpu_limit_sec: int,
        max_stdout_bytes: int,
        max_stderr_bytes: int,
    ) -> ProgramRun:
        """Run ``program`` in container ``name`` with one ``docker exec``.

        On timeout the whole container is removed at once, so the program can't keep
        burning CPU after the request has returned.

        Raises:
            SandboxError: the docker CLI could not be launched.
        """
        cmd = self.build_exec_command(name, cpu_limit_sec)
        start = time.perf_counter()
        try:
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except OSError as exc:
            raise SandboxError(f"failed to run docker exec: {exc}") from exc
        if proc.stdout is None or proc.stderr is None:
            raise SandboxError("failed to open docker exec pipes")

        stdout = _CappedReader(proc.stdout, max_stdout_bytes, "fn-stdout")
        stderr = _CappedReader(proc.stderr, max_stderr_bytes, "fn-stderr")
        _feed_stdin(proc, program.encode("utf-8"))

        timed_out = False
        try:
            proc.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            timed_out = True
            self.remove(name)
            proc.kill()
            proc.wait()
        duration_ms = int((time.perf_counter() - start) * 1000)

        return ProgramRun(
            stdout=stdout.result(_DRAIN_TIMEOUT_SEC),
            stderr=stderr.result(_DRAIN_TIMEOUT_SEC),
            exit_code=None if timed_out else proc.returncode,
            timed_out=timed_out,
            duration_ms=duration_ms,
        )

    def read_result_file(self, name: str, max_bytes: int) -> bytes | None:
        """Up to ``max_bytes + 1`` bytes of the program's result file, or None if the
        program wrote none (one byte over the cap tells the caller it is too large)."""
        cmd = [
            self.docker_binary,
            "exec",
            "-u",
            SANDBOX_USER,
            name,
            "head",
            "-c",
            str(max(0, max_bytes) + 1),
            RESULT_FILE_PATH,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=_AUX_TIMEOUT_SEC, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning(f"run_function: could not read the result file: {exc}")
            return None
        if proc.returncode != 0:
            return None
        return proc.stdout
