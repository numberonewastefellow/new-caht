"""Tests for ``POST /v1/run_function`` and the runner behind it.

No Docker needed. The runner is tested against a fake sandbox; the endpoint is tested
through the real auth/tenant/admission stack, with the real runner and Docker sandbox
whose ``docker exec`` is replaced by a local ``python -`` (start/remove are faked).
"""

from __future__ import annotations

import itertools
import sys
import time
from collections.abc import Generator
from dataclasses import dataclass, field

import httpx
import pytest
from fastapi.testclient import TestClient

from app import app_configs
from app.api import routes
from app.api.security import ExecutionLimiter, set_execution_limiter
from app.main import create_app
from app.services.function_sandbox import (
    CappedOutput,
    DockerFunctionSandbox,
    ProgramRun,
    SandboxError,
)
from app.services.run_function import FunctionRunner, RunLimits, classify
from app.services.warm_pool import PoolConfig, WarmContainerPool

TOKEN = "test-token-run-function"  # noqa: S105 - test placeholder
AUTH = {"Authorization": f"Bearer {TOKEN}"}
TENANT_A = {**AUTH, "X-OM-Tenant": "tenant_a"}
TENANT_B = {**AUTH, "X-OM-Tenant": "tenant_b"}

LIMITS = RunLimits(
    cpu_time_limit_sec=5, max_stdout_bytes=1000, max_stderr_bytes=100, max_result_bytes=50
)


def _run(
    exit_code: int | None = 0,
    *,
    stdout: bytes = b"",
    stderr: bytes = b"",
    timed_out: bool = False,
) -> ProgramRun:
    return ProgramRun(
        stdout=CappedOutput(stdout, False),
        stderr=CappedOutput(stderr, False),
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=7,
    )


@dataclass
class FakeSandbox:
    """Records every container's lifecycle; ``next_run`` decides each run's outcome."""

    next_run: ProgramRun = field(default_factory=_run)
    result_file: bytes | None = None
    fail_start: bool = False
    fail_exec: bool = False
    leftovers: list[str] = field(default_factory=list)
    started: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    ran_in: list[str] = field(default_factory=list)
    result_reads: list[str] = field(default_factory=list)

    def start(self, name: str) -> None:
        if self.fail_start:
            raise SandboxError("docker is down")
        self.started.append(name)

    def remove(self, name: str) -> None:
        self.removed.append(name)

    def list_owned(self, *, include_stopped: bool = False) -> list[str]:  # noqa: ARG002
        return [n for n in self.started + self.leftovers if n not in self.removed]

    def remove_owned(self) -> int:
        names = self.list_owned(include_stopped=True)
        for name in names:
            self.remove(name)
        return len(names)

    def run_program(self, name: str, program: str, **_: object) -> ProgramRun:  # noqa: ARG002
        if self.fail_exec:
            raise SandboxError("exec failed")
        self.ran_in.append(name)
        return self.next_run

    def read_result_file(self, name: str, max_bytes: int) -> bytes | None:  # noqa: ARG002
        self.result_reads.append(name)
        return self.result_file


def _drain(runner: FunctionRunner) -> None:
    """Wait for the background removals (shuts the remover down)."""
    runner._remover.shutdown(wait=True)


def _pool(sandbox: FakeSandbox, size: int) -> WarmContainerPool:
    counter = itertools.count()
    pool = WarmContainerPool(
        sandbox,
        PoolConfig(min_size=size, max_size=size, ttl_sec=600),
        name_factory=lambda: f"ci-fn-warm-{next(counter)}",
    )
    pool.maintain()
    pool._starter.shutdown(wait=True)  # let the fills finish
    return pool


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (_run(0), None),
        (_run(1, stderr=b"Traceback ..."), None),
        (_run(None, timed_out=True), "timeout"),
        (_run(152), "timeout"),  # CPU-time rlimit (SIGXCPU)
        (_run(137), "oom"),
        (_run(1, stderr=b"Error response from daemon: No such container: x"), "sandbox_error"),
    ],
)
def test_classify(run: ProgramRun, expected: str | None) -> None:
    assert classify(run) == expected


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def test_warm_run_uses_pool_and_destroys_container() -> None:
    sandbox = FakeSandbox(next_run=_run(0, stdout=b"hi"))
    pool = _pool(sandbox, size=1)
    runner = FunctionRunner(sandbox, LIMITS, pool=pool)

    result = runner.run("print('hi')", 1000)
    _drain(runner)

    assert result.pool_hit is True
    assert result.stdout == "hi"
    assert result.error_kind is None
    assert sandbox.ran_in == ["ci-fn-warm-0"]
    assert sandbox.removed == ["ci-fn-warm-0"]


def test_empty_pool_falls_back_to_cold_start() -> None:
    sandbox = FakeSandbox()
    pool = _pool(sandbox, size=0)
    runner = FunctionRunner(sandbox, LIMITS, pool=pool)

    result = runner.run("pass", 1000)
    _drain(runner)

    assert result.pool_hit is False
    assert result.error_kind is None
    assert len(sandbox.started) == 1
    assert sandbox.ran_in == sandbox.started
    assert sandbox.removed == sandbox.started


def test_pool_disabled_always_cold() -> None:
    sandbox = FakeSandbox()
    runner = FunctionRunner(sandbox, LIMITS, pool=None)
    for _ in range(3):
        assert runner.run("pass", 1000).pool_hit is False
    _drain(runner)
    assert len(sandbox.started) == 3
    assert sorted(sandbox.removed) == sorted(sandbox.started)


def test_containers_are_never_reused_across_runs_or_tenants() -> None:
    sandbox = FakeSandbox()
    pool = _pool(sandbox, size=2)
    runner = FunctionRunner(sandbox, LIMITS, pool=pool)
    for _ in range(5):  # 2 warm + 3 cold
        runner.run("pass", 1000)
    _drain(runner)
    assert len(sandbox.ran_in) == 5
    assert len(set(sandbox.ran_in)) == 5
    assert sorted(sandbox.removed) == sorted(sandbox.ran_in)


def test_cold_start_failure_is_a_sandbox_error_not_an_exception() -> None:
    sandbox = FakeSandbox(fail_start=True)
    runner = FunctionRunner(sandbox, LIMITS, pool=None)
    result = runner.run("pass", 1000)
    assert result.error_kind == "sandbox_error"
    assert result.exit_code is None
    assert sandbox.ran_in == []


def test_exec_failure_still_destroys_container() -> None:
    sandbox = FakeSandbox(fail_exec=True)
    runner = FunctionRunner(sandbox, LIMITS, pool=None)
    result = runner.run("pass", 1000)
    _drain(runner)
    assert result.error_kind == "sandbox_error"
    assert sandbox.removed == sandbox.started


def test_unexpected_error_still_destroys_container() -> None:
    sandbox = FakeSandbox()

    def boom(*_a: object, **_k: object) -> ProgramRun:
        raise ValueError("unexpected")

    sandbox.run_program = boom  # type: ignore[method-assign]
    runner = FunctionRunner(sandbox, LIMITS, pool=None)
    with pytest.raises(ValueError):
        runner.run("pass", 1000)
    _drain(runner)
    assert sandbox.removed == sandbox.started


def test_result_file_returned_when_requested() -> None:
    sandbox = FakeSandbox(result_file=b'{"ok": true}')
    runner = FunctionRunner(sandbox, LIMITS, pool=None)
    assert runner.run("pass", 1000).result_payload is None  # not requested
    assert sandbox.result_reads == []
    result = runner.run("pass", 1000, read_result_file=True)
    assert result.result_payload == '{"ok": true}'
    assert result.result_error is None


@pytest.mark.parametrize(
    ("content", "payload", "error"),
    [
        (None, None, None),  # program wrote no file
        (b"x" * 51, None, "too_large"),  # one byte over the 50-byte cap: rejected
        (b"x" * 50, "x" * 50, None),
        (b"\xff\xfe", None, "invalid_utf8"),
    ],
)
def test_result_file_limits(content: bytes | None, payload: str | None, error: str | None) -> None:
    sandbox = FakeSandbox(result_file=content)
    runner = FunctionRunner(sandbox, LIMITS, pool=None)
    result = runner.run("pass", 1000, read_result_file=True)
    assert result.result_payload == payload
    assert result.result_error == error


def test_result_file_not_read_after_timeout() -> None:
    sandbox = FakeSandbox(next_run=_run(None, timed_out=True), result_file=b"{}")
    runner = FunctionRunner(sandbox, LIMITS, pool=None)
    result = runner.run("pass", 1000, read_result_file=True)
    assert result.error_kind == "timeout"
    assert result.result_payload is None
    assert sandbox.result_reads == []


def test_start_removes_orphans_and_shutdown_removes_pool() -> None:
    sandbox = FakeSandbox(leftovers=["ci-fn-orphan-1", "ci-fn-orphan-2"])
    counter = itertools.count()
    pool = WarmContainerPool(
        sandbox,
        PoolConfig(min_size=2, max_size=2, ttl_sec=600, maintenance_interval_sec=0.05),
        name_factory=lambda: f"ci-fn-warm-{next(counter)}",
    )
    runner = FunctionRunner(sandbox, LIMITS, pool=pool)
    runner.start()
    assert {"ci-fn-orphan-1", "ci-fn-orphan-2"} <= set(sandbox.removed)

    deadline = time.monotonic() + 5
    while pool.stats().idle < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert pool.stats().idle == 2

    runner.shutdown()
    assert sandbox.list_owned(include_stopped=True) == []


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@pytest.fixture()
def token_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_API_TOKEN", TOKEN)
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_ALLOW_UNAUTHENTICATED", False)


@pytest.fixture(autouse=True)
def _reset_globals() -> Generator[None, None, None]:
    set_execution_limiter(None)
    yield
    set_execution_limiter(None)
    routes.set_function_runner(None)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture()
def local_runner(monkeypatch: pytest.MonkeyPatch) -> Generator[FunctionRunner, None, None]:
    """Real runner + Docker sandbox; `docker exec` is a local `python -`."""
    sandbox = DockerFunctionSandbox(
        docker_binary="docker",
        image="om/python-executor-sci:latest",
        owner="test",
        memory_limit_mb=256,
        lifetime_sec=60,
    )
    monkeypatch.setattr(sandbox, "build_exec_command", lambda *_a: [sys.executable, "-"])
    monkeypatch.setattr(sandbox, "start", lambda _name: None)
    monkeypatch.setattr(sandbox, "remove", lambda _name: None)
    runner = FunctionRunner(sandbox, LIMITS, pool=None)
    routes.set_function_runner(runner)
    yield runner
    _drain(runner)


def _post(
    client: TestClient, body: dict[str, object], headers: dict[str, str] | None = None
) -> httpx.Response:
    return client.post("/v1/run_function", json=body, headers=headers or TENANT_A)


def test_endpoint_requires_token(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    body = {"program": "print(1)", "timeout_ms": 5000}
    assert client.post("/v1/run_function", json=body).status_code == 401
    wrong = {"Authorization": "Bearer nope", "X-OM-Tenant": "tenant_a"}
    assert _post(client, body, wrong).status_code == 401
    assert _post(client, body).status_code == 200


def test_endpoint_fails_closed_without_configured_token(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, local_runner: FunctionRunner
) -> None:
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_API_TOKEN", "")
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_ALLOW_UNAUTHENTICATED", False)
    assert _post(client, {"program": "pass", "timeout_ms": 1000}).status_code == 503


def test_endpoint_validates_tenant_header(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    body = {"program": "pass", "timeout_ms": 1000}
    assert _post(client, body, {**AUTH, "X-OM-Tenant": "bad tenant!"}).status_code == 400
    assert _post(client, body, TENANT_B).status_code == 200
    assert _post(client, body, AUTH).status_code == 200  # header-less: unscoped bucket


def test_endpoint_runs_program_verbatim(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    # No last-line wrapper: a bare trailing expression prints nothing.
    program = "import sys\nprint('out')\nsys.stderr.write('err')\n40 + 2\n"
    resp = _post(client, {"program": program, "timeout_ms": 10_000})
    assert resp.status_code == 200
    body = resp.json()
    assert body["stdout"].strip() == "out"
    assert body["stderr"] == "err"
    assert body["exit_code"] == 0
    assert body["timed_out"] is False
    assert body["error_kind"] is None
    assert body["pool_hit"] is False
    assert body["stdout_truncated"] is False
    assert body["result_payload"] is None
    assert set(body) == {
        "stdout",
        "stderr",
        "exit_code",
        "timed_out",
        "duration_ms",
        "error_kind",
        "stdout_truncated",
        "stderr_truncated",
        "result_payload",
        "result_error",
        "pool_hit",
    }


def test_endpoint_caps_stdout_and_stderr(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    program = "import sys\nsys.stdout.write('o' * 100_000)\nsys.stderr.write('e' * 100_000)\n"
    body = _post(client, {"program": program, "timeout_ms": 10_000}).json()
    assert body["stdout"] == "o" * LIMITS.max_stdout_bytes
    assert body["stdout_truncated"] is True
    assert body["stderr"] == "e" * LIMITS.max_stderr_bytes
    assert body["stderr_truncated"] is True


def test_endpoint_timeout(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    body = _post(client, {"program": "import time\ntime.sleep(30)\n", "timeout_ms": 500}).json()
    assert body["timed_out"] is True
    assert body["exit_code"] is None
    assert body["error_kind"] == "timeout"


def test_endpoint_oom_exit_is_reported(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    # 137 is what `docker exec` reports when the cgroup OOM killer SIGKILLs the program.
    body = _post(client, {"program": "import os\nos._exit(137)\n", "timeout_ms": 10_000}).json()
    assert body["exit_code"] == 137
    assert body["error_kind"] == "oom"
    assert body["timed_out"] is False


def test_endpoint_user_error_is_not_an_error_kind(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    body = _post(client, {"program": "raise ValueError('bad')\n", "timeout_ms": 10_000}).json()
    assert body["exit_code"] == 1
    assert body["error_kind"] is None
    assert "ValueError: bad" in body["stderr"]


def test_endpoint_rejects_timeout_over_max(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    too_long = app_configs.get_settings().max_exec_timeout_ms + 1
    assert _post(client, {"program": "pass", "timeout_ms": too_long}).status_code == 422
    assert _post(client, {"program": "pass", "timeout_ms": 0}).status_code == 422
    assert _post(client, {"program": "pass"}).status_code == 422  # timeout is required


def test_endpoint_rejects_oversized_program(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    from app.models.schemas import RUN_FUNCTION_MAX_PROGRAM_CHARS

    program = "#" * (RUN_FUNCTION_MAX_PROGRAM_CHARS + 1)
    assert _post(client, {"program": program, "timeout_ms": 1000}).status_code == 422


def test_endpoint_admission_control(
    token_auth: None, client: TestClient, local_runner: FunctionRunner
) -> None:
    limiter = ExecutionLimiter(max_workers=1, max_queue=0, queue_timeout_sec=0.1)
    set_execution_limiter(limiter)
    held = limiter.acquire()
    try:
        resp = _post(client, {"program": "pass", "timeout_ms": 1000})
        assert resp.status_code == 503
        assert resp.headers["retry-after"] == str(app_configs.EXECUTION_RETRY_AFTER_SEC)
    finally:
        held.release()
    for _ in range(3):
        assert _post(client, {"program": "pass", "timeout_ms": 5000}).status_code == 200
    assert limiter.admitted == 0  # every slot released


def test_endpoint_not_initialized_is_503(
    token_auth: None, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(routes, "EXECUTOR_BACKEND", "docker")
    assert _post(client, {"program": "pass", "timeout_ms": 1000}).status_code == 503


def test_endpoint_needs_docker_backend(
    token_auth: None, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The backend client maps this (like a 404 from an older service) to
    # RunFunctionUnsupportedError and falls back to /v1/execute.
    monkeypatch.setattr(routes, "EXECUTOR_BACKEND", "kubernetes")
    assert _post(client, {"program": "pass", "timeout_ms": 1000}).status_code == 501
