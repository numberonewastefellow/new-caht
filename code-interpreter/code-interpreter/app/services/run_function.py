"""``POST /v1/run_function``: run one self-contained program in a fresh sandbox.

Unlike ``/v1/execute`` there is no last-line-interactive wrapper, no figure prologue,
no file staging and no workspace snapshot: the program (e.g. the backend's code-node
harness) is streamed to ``python -`` with a single ``docker exec``.

Isolation: every call gets its own container, taken from the warm pool when one is
ready and cold-started otherwise, and that container is destroyed right after the
call. Containers are never reused across executions or tenants.

Results: stdout (capped at ``MAX_OUTPUT_BYTES``) and stderr (capped at
``RUN_FUNCTION_MAX_STDERR_BYTES``) are returned as text. Optionally the program may
also write its result to ``$OM_RESULT_PATH`` (``/tmp/result``); with
``read_result_file`` the service returns that file as ``result_payload``, a channel
separate from stdout, capped at ``RUN_FUNCTION_MAX_RESULT_BYTES`` (bigger results are
rejected, never truncated).
"""

from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from shutil import which
from typing import Literal, Protocol

from app import app_configs
from app.app_configs import Settings
from app.services.function_sandbox import (
    DockerFunctionSandbox,
    ProgramRun,
    SandboxError,
    new_container_name,
)
from app.services.warm_pool import PoolConfig, WarmContainerPool

logger = logging.getLogger(__name__)

ErrorKind = Literal["timeout", "oom", "sandbox_error"]
ResultError = Literal["too_large", "invalid_utf8"]

# Exit status of a process killed by SIGKILL (the cgroup OOM killer) or by SIGXCPU
# (the CPU-time rlimit), as reported by `docker exec`.
_EXIT_SIGKILL = 137
_EXIT_SIGXCPU = 152
# Headroom on top of the TTL and the longest run before an idle container's own
# `sleep` ends (it is a backstop: the service normally removes containers first).
_LIFETIME_GRACE_SEC = 60
_MAX_PARALLEL_REMOVALS = 4

_SANDBOX_UNAVAILABLE = "The sandbox could not be started."


class FunctionSandbox(Protocol):
    """What the runner needs from a sandbox runtime (see ``DockerFunctionSandbox``)."""

    def start(self, name: str) -> None: ...

    def remove(self, name: str) -> None: ...

    def list_owned(self, *, include_stopped: bool = False) -> list[str]: ...

    def remove_owned(self) -> int: ...

    def run_program(
        self,
        name: str,
        program: str,
        *,
        timeout_sec: float,
        cpu_limit_sec: int,
        max_stdout_bytes: int,
        max_stderr_bytes: int,
    ) -> ProgramRun: ...

    def read_result_file(self, name: str, max_bytes: int) -> bytes | None: ...


@dataclass(frozen=True, slots=True)
class RunLimits:
    cpu_time_limit_sec: int
    max_stdout_bytes: int
    max_stderr_bytes: int
    max_result_bytes: int


@dataclass(frozen=True, slots=True)
class FunctionRunResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    error_kind: ErrorKind | None
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    result_payload: str | None = None
    result_error: ResultError | None = None
    pool_hit: bool = False


def classify(run: ProgramRun) -> ErrorKind | None:
    """Map a raw run onto the error taxonomy (None: the program ran to an exit).

    * ``timeout``: the wall-clock timeout fired, or the CPU-time rlimit did (SIGXCPU);
    * ``oom``: SIGKILL, which in a memory-capped sandbox is the OOM killer;
    * ``sandbox_error``: docker itself failed (e.g. the container vanished).
    """
    if run.timed_out or run.exit_code == _EXIT_SIGXCPU:
        return "timeout"
    if run.exit_code == _EXIT_SIGKILL:
        return "oom"
    if run.is_docker_failure:
        return "sandbox_error"
    return None


def _decode_result(raw: bytes | None, max_bytes: int) -> tuple[str | None, ResultError | None]:
    if raw is None:
        return None, None
    if len(raw) > max_bytes:
        return None, "too_large"
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError:
        return None, "invalid_utf8"


class FunctionRunner:
    """Runs programs in single-use sandboxes, warm from the pool when possible."""

    def __init__(
        self,
        sandbox: FunctionSandbox,
        limits: RunLimits,
        *,
        pool: WarmContainerPool | None = None,
    ) -> None:
        self._sandbox = sandbox
        self._limits = limits
        self._pool = pool
        # Used containers are destroyed off the request path.
        self._remover = ThreadPoolExecutor(
            max_workers=_MAX_PARALLEL_REMOVALS, thread_name_prefix="fn-remove"
        )

    @property
    def pool(self) -> WarmContainerPool | None:
        return self._pool

    def start(self) -> None:
        """Remove containers left by an earlier process, then start the pool."""
        removed = self._sandbox.remove_owned()
        if removed:
            logger.info(f"run_function: removed {removed} leftover sandbox container(s)")
        if self._pool is not None:
            self._pool.start()

    def shutdown(self) -> None:
        """Destroy pooled containers and wait for pending removals."""
        if self._pool is not None:
            self._pool.shutdown()
        self._remover.shutdown(wait=True)
        self._sandbox.remove_owned()

    def run(
        self, program: str, timeout_ms: int, *, read_result_file: bool = False
    ) -> FunctionRunResult:
        """Run ``program`` once in a fresh sandbox, then destroy the sandbox."""
        name, pool_hit = self._acquire()
        if name is None:
            return FunctionRunResult(
                stdout="",
                stderr=_SANDBOX_UNAVAILABLE,
                exit_code=None,
                timed_out=False,
                duration_ms=0,
                error_kind="sandbox_error",
                pool_hit=False,
            )
        try:
            return self._run_in(name, program, timeout_ms, read_result_file, pool_hit)
        finally:
            self._destroy(name)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _acquire(self) -> tuple[str | None, bool]:
        """A container for exactly one run: (name, came from the pool)."""
        if self._pool is not None:
            pooled = self._pool.take()
            if pooled is not None:
                return pooled.name, True
        name = new_container_name()
        try:
            self._sandbox.start(name)
        except SandboxError as exc:
            logger.error(f"run_function: cold start failed: {exc}")
            return None, False
        return name, False

    def _run_in(
        self,
        name: str,
        program: str,
        timeout_ms: int,
        read_result_file: bool,
        pool_hit: bool,
    ) -> FunctionRunResult:
        limits = self._limits
        try:
            run = self._sandbox.run_program(
                name,
                program,
                timeout_sec=timeout_ms / 1000.0,
                cpu_limit_sec=limits.cpu_time_limit_sec,
                max_stdout_bytes=limits.max_stdout_bytes,
                max_stderr_bytes=limits.max_stderr_bytes,
            )
        except SandboxError as exc:
            logger.error(f"run_function: exec failed in {name}: {exc}")
            return FunctionRunResult(
                stdout="",
                stderr=_SANDBOX_UNAVAILABLE,
                exit_code=None,
                timed_out=False,
                duration_ms=0,
                error_kind="sandbox_error",
                pool_hit=pool_hit,
            )

        error_kind = classify(run)
        payload: str | None = None
        payload_error: ResultError | None = None
        if read_result_file and error_kind not in ("timeout", "sandbox_error"):
            raw = self._sandbox.read_result_file(name, limits.max_result_bytes)
            payload, payload_error = _decode_result(raw, limits.max_result_bytes)

        return FunctionRunResult(
            stdout=run.stdout.data.decode("utf-8", errors="replace"),
            stderr=run.stderr.data.decode("utf-8", errors="replace"),
            exit_code=run.exit_code,
            timed_out=run.timed_out,
            duration_ms=run.duration_ms,
            error_kind=error_kind,
            stdout_truncated=run.stdout.truncated,
            stderr_truncated=run.stderr.truncated,
            result_payload=payload,
            result_error=payload_error,
            pool_hit=pool_hit,
        )

    def _destroy(self, name: str) -> None:
        try:
            self._remover.submit(self._sandbox.remove, name)
        except RuntimeError:  # shutting down: remove inline
            self._sandbox.remove(name)


def build_function_runner(settings: Settings) -> FunctionRunner:
    """A runner for the Docker executor, configured from ``settings`` and ``app_configs``.

    Raises:
        RuntimeError: the docker CLI is not installed.
    """
    docker_binary = which(app_configs.PYTHON_EXECUTOR_DOCKER_BIN)
    if docker_binary is None:
        raise RuntimeError("Docker CLI not found")

    ttl_sec = app_configs.RUN_FUNCTION_POOL_TTL_SEC
    longest_run_sec = math.ceil(settings.max_exec_timeout_ms / 1000)
    sandbox = DockerFunctionSandbox(
        docker_binary=docker_binary,
        image=app_configs.PYTHON_EXECUTOR_DOCKER_IMAGE_REF,
        owner=app_configs.RUN_FUNCTION_POOL_OWNER,
        memory_limit_mb=settings.memory_limit_mb,
        lifetime_sec=ttl_sec + longest_run_sec + _LIFETIME_GRACE_SEC,
        run_args=app_configs.PYTHON_EXECUTOR_DOCKER_RUN_ARGS,
    )
    pool: WarmContainerPool | None = None
    if app_configs.RUN_FUNCTION_POOL_ENABLED and app_configs.RUN_FUNCTION_POOL_MAX > 0:
        pool = WarmContainerPool(
            sandbox,
            PoolConfig(
                min_size=app_configs.RUN_FUNCTION_POOL_MIN,
                max_size=app_configs.RUN_FUNCTION_POOL_MAX,
                ttl_sec=ttl_sec,
            ),
            name_factory=new_container_name,
        )
    limits = RunLimits(
        cpu_time_limit_sec=settings.cpu_time_limit_sec,
        max_stdout_bytes=settings.max_output_bytes,
        max_stderr_bytes=app_configs.RUN_FUNCTION_MAX_STDERR_BYTES,
        max_result_bytes=app_configs.RUN_FUNCTION_MAX_RESULT_BYTES,
    )
    return FunctionRunner(sandbox, limits, pool=pool)
