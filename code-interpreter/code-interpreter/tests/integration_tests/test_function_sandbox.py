"""Tests for the single-use run_function Docker sandbox.

No Docker needed: command builders are inspected directly, and the output/timeout
handling of ``run_program`` is exercised against a local Python subprocess standing in
for ``docker exec``.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from app import app_configs
from app.app_configs import docker_image_ref
from app.services.function_sandbox import (
    OWNER_LABEL,
    RESULT_FILE_PATH,
    RUN_FUNCTION_LABEL,
    CappedOutput,
    DockerFunctionSandbox,
    ProgramRun,
    SandboxError,
    limited_python_command,
    new_container_name,
)


def _sandbox(**overrides: object) -> DockerFunctionSandbox:
    params: dict[str, object] = {
        "docker_binary": "docker",
        "image": "om/python-executor-sci:latest",
        "owner": "svc-1",
        "memory_limit_mb": 256,
        "lifetime_sec": 700,
    }
    params.update(overrides)
    return DockerFunctionSandbox(**params)  # type: ignore[arg-type]


def _flag_values(cmd: list[str], flag: str) -> list[str]:
    return [cmd[i + 1] for i, part in enumerate(cmd) if part == flag]


# ---------------------------------------------------------------------------
# Image reference
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("image", "tag", "expected"),
    [
        ("om/python-executor-sci", "latest", "om/python-executor-sci:latest"),
        ("om/python-executor-sci", "flowtest", "om/python-executor-sci:flowtest"),
        ("om/img:1.2", "latest", "om/img:1.2"),
        ("registry:5000/om/img", "v3", "registry:5000/om/img:v3"),
        ("om/img@sha256:abc", "latest", "om/img@sha256:abc"),
    ],
)
def test_docker_image_ref(image: str, tag: str, expected: str) -> None:
    assert docker_image_ref(image, tag) == expected


def test_default_image_ref_keeps_latest() -> None:
    # Default behaviour is unchanged: the executor image at :latest.
    if not (
        app_configs.PYTHON_EXECUTOR_DOCKER_TAG == "latest"
        and ":" not in app_configs.PYTHON_EXECUTOR_DOCKER_IMAGE
    ):
        pytest.skip("image/tag overridden in this environment")
    assert app_configs.PYTHON_EXECUTOR_DOCKER_IMAGE_REF.endswith(":latest")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def test_start_command_is_hardened_and_labelled() -> None:
    cmd = _sandbox().build_start_command("ci-fn-x")

    assert cmd[:4] == ["docker", "run", "-d", "--rm"]
    assert "--read-only" in cmd
    assert _flag_values(cmd, "--network") == ["none"]
    assert _flag_values(cmd, "--user") == ["65532:65532"]
    assert _flag_values(cmd, "--cap-drop") == ["ALL"]
    assert _flag_values(cmd, "--pids-limit") == ["64"]
    assert _flag_values(cmd, "--cpus") == [str(app_configs.EXECUTOR_CPUS)]
    assert "no-new-privileges" in _flag_values(cmd, "--security-opt")
    assert _flag_values(cmd, "--memory") == ["256m"]
    assert _flag_values(cmd, "--memory-swap") == ["256m"]
    tmpfs = _flag_values(cmd, "--tmpfs")
    assert any(t.startswith("/tmp:") and "size=" in t for t in tmpfs)  # noqa: S108
    assert any(t.startswith("/workspace:") and "size=" in t for t in tmpfs)
    assert set(_flag_values(cmd, "--label")) == {f"{RUN_FUNCTION_LABEL}=1", f"{OWNER_LABEL}=svc-1"}
    assert _flag_values(cmd, "--name") == ["ci-fn-x"]
    # The idle main process only sleeps, for a bounded lifetime.
    assert cmd[-3:] == ["om/python-executor-sci:latest", "sleep", "700"]


def test_start_command_appends_extra_run_args_before_image() -> None:
    cmd = _sandbox(run_args="--runtime runsc").build_start_command("ci-fn-x")
    assert cmd[-5:-3] == ["--runtime", "runsc"]


def test_exec_command_is_single_unprivileged_exec() -> None:
    cmd = _sandbox().build_exec_command("ci-fn-x", cpu_limit_sec=5)
    assert cmd[:3] == ["docker", "exec", "-i"]
    assert _flag_values(cmd, "-u") == ["65532:65532"]
    assert _flag_values(cmd, "--env") == [f"OM_RESULT_PATH={RESULT_FILE_PATH}"]
    assert cmd[-4:] == ["ci-fn-x", "sh", "-c", limited_python_command(5)]


def test_cpu_limit_command_sends_sigxcpu_before_sigkill() -> None:
    assert limited_python_command(5) == "ulimit -t 6 && ulimit -S -t 5 && exec python -"
    assert limited_python_command(0) == "ulimit -t 2 && ulimit -S -t 1 && exec python -"


def test_list_owned_filters_on_both_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> MagicMock:
        captured.append(cmd)
        return MagicMock(returncode=0, stdout="ci-fn-a\nci-fn-b\n", stderr="")

    monkeypatch.setattr("app.services.function_sandbox.subprocess.run", fake_run)
    assert _sandbox().list_owned(include_stopped=True) == ["ci-fn-a", "ci-fn-b"]
    cmd = captured[0]
    assert cmd[:3] == ["docker", "ps", "-a"]
    assert _flag_values(cmd, "--filter") == [
        f"label={RUN_FUNCTION_LABEL}=1",
        f"label={OWNER_LABEL}=svc-1",
    ]


def test_list_owned_raises_when_docker_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.function_sandbox.subprocess.run",
        lambda *_a, **_k: MagicMock(returncode=1, stdout="", stderr="daemon down"),
    )
    with pytest.raises(SandboxError):
        _sandbox().list_owned()


def test_remove_owned_removes_every_leftover(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> MagicMock:
        calls.append(cmd)
        if cmd[1] == "ps":
            return MagicMock(returncode=0, stdout="ci-fn-old1\nci-fn-old2\n", stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.services.function_sandbox.subprocess.run", fake_run)
    assert _sandbox().remove_owned() == 2
    assert [c for c in calls if c[1] == "rm"] == [
        ["docker", "rm", "-f", "ci-fn-old1"],
        ["docker", "rm", "-f", "ci-fn-old2"],
    ]


def test_failed_start_removes_partial_container(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> MagicMock:
        calls.append(cmd)
        if cmd[1] == "run":
            return MagicMock(returncode=125, stdout="", stderr="no such image")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("app.services.function_sandbox.subprocess.run", fake_run)
    with pytest.raises(SandboxError, match="no such image"):
        _sandbox().start("ci-fn-x")
    assert calls[-1] == ["docker", "rm", "-f", "ci-fn-x"]


def test_read_result_file_reads_one_byte_past_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> MagicMock:
        captured.append(cmd)
        return MagicMock(returncode=0, stdout=b'{"a": 1}')

    monkeypatch.setattr("app.services.function_sandbox.subprocess.run", fake_run)
    assert _sandbox().read_result_file("ci-fn-x", 100) == b'{"a": 1}'
    assert captured[0][-5:] == ["ci-fn-x", "head", "-c", "101", RESULT_FILE_PATH]


def test_missing_result_file_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.function_sandbox.subprocess.run",
        lambda *_a, **_k: MagicMock(returncode=1, stdout=b""),
    )
    assert _sandbox().read_result_file("ci-fn-x", 100) is None


def test_container_names_are_unique() -> None:
    names = {new_container_name() for _ in range(1000)}
    assert len(names) == 1000
    assert all(n.startswith("ci-fn-") for n in names)


# ---------------------------------------------------------------------------
# run_program against a local stand-in for `docker exec`
# ---------------------------------------------------------------------------


def _local_sandbox(monkeypatch: pytest.MonkeyPatch, removed: list[str]) -> DockerFunctionSandbox:
    """A sandbox whose `docker exec` is a local `python -` (reads the program on stdin)."""
    sandbox = _sandbox()
    monkeypatch.setattr(sandbox, "build_exec_command", lambda *_a: [sys.executable, "-"])
    monkeypatch.setattr(sandbox, "remove", removed.append)
    return sandbox


def _run(sandbox: DockerFunctionSandbox, program: str, **overrides: object) -> ProgramRun:
    params: dict[str, object] = {
        "timeout_sec": 20.0,
        "cpu_limit_sec": 5,
        "max_stdout_bytes": 1000,
        "max_stderr_bytes": 1000,
    }
    params.update(overrides)
    return sandbox.run_program("ci-fn-x", program, **params)  # type: ignore[arg-type]


def test_run_program_returns_stdout_stderr_and_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removed: list[str] = []
    program = "import sys\nprint('out')\nprint('err', file=sys.stderr)\nsys.exit(3)\n"
    run = _run(_local_sandbox(monkeypatch, removed), program)

    assert run.stdout == CappedOutput(data=b"out" + _nl(), truncated=False)
    assert run.stderr == CappedOutput(data=b"err" + _nl(), truncated=False)
    assert run.exit_code == 3
    assert run.timed_out is False
    assert removed == []  # only the caller destroys a container after a normal run


def test_run_program_caps_stdout_and_stderr_without_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removed: list[str] = []
    program = "import sys\nsys.stdout.write('o' * 5_000_000)\nsys.stderr.write('e' * 5_000_000)\n"
    run = _run(
        _local_sandbox(monkeypatch, removed),
        program,
        max_stdout_bytes=1000,
        max_stderr_bytes=10,
    )
    assert run.exit_code == 0
    assert run.stdout == CappedOutput(data=b"o" * 1000, truncated=True)
    assert run.stderr == CappedOutput(data=b"e" * 10, truncated=True)


def test_run_program_timeout_kills_and_removes_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    removed: list[str] = []
    run = _run(
        _local_sandbox(monkeypatch, removed),
        "print('started', flush=True)\nimport time\ntime.sleep(60)\n",
        timeout_sec=1.0,
    )
    assert run.timed_out is True
    assert run.exit_code is None
    assert run.stdout.data.startswith(b"started")
    assert run.duration_ms < 10_000
    assert removed == ["ci-fn-x"]


def test_run_program_receives_eof_on_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    removed: list[str] = []
    program = "import sys\nprint(repr(sys.stdin.read()))\n"
    run = _run(_local_sandbox(monkeypatch, removed), program, timeout_sec=10.0)
    assert run.timed_out is False
    assert run.stdout.data.strip() == b"''"


def test_docker_failure_signature() -> None:
    gone = ProgramRun(
        stdout=CappedOutput(b"", False),
        stderr=CappedOutput(b"Error response from daemon: No such container: x", False),
        exit_code=1,
        timed_out=False,
        duration_ms=5,
    )
    user_error = ProgramRun(
        stdout=CappedOutput(b"", False),
        stderr=CappedOutput(b"Traceback ...", False),
        exit_code=1,
        timed_out=False,
        duration_ms=5,
    )
    assert gone.is_docker_failure
    assert not user_error.is_docker_failure


def _nl() -> bytes:
    return b"\r\n" if sys.platform == "win32" else b"\n"
