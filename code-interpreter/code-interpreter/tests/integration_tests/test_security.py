"""Security hardening tests: API auth, tenant isolation, admission control, and the
sandbox (Docker + Kubernetes) hardening flags.

None of these need Docker or a cluster: executors/session managers are either faked
or only asked to *build* their commands/manifests.
"""

from __future__ import annotations

import io
import json
import tarfile
import threading
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import app_configs
from app.api import routes
from app.api.security import (
    UNSCOPED_TENANT,
    CapacityExceededError,
    ExecutionLimiter,
    set_execution_limiter,
    tokens_match,
)
from app.main import create_app
from app.services.executor_base import ExecutionResult
from app.services.file_storage import FileStorageService
from app.services.sandbox_hardening import read_workspace_tar
from app.services.session_manager import SessionManager, SessionState

TOKEN = "test-token-change-me"  # noqa: S105 - test placeholder
AUTH = {"Authorization": f"Bearer {TOKEN}"}
TENANT_A = {**AUTH, "X-OM-Tenant": "tenant_a"}
TENANT_B = {**AUTH, "X-OM-Tenant": "tenant_b"}


@pytest.fixture()
def token_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service configured with a token; dev override off."""
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_API_TOKEN", TOKEN)
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_ALLOW_UNAUTHENTICATED", False)


@pytest.fixture()
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FileStorageService:
    svc = FileStorageService(tmp_path / "files")
    monkeypatch.setattr(routes, "_file_storage", svc)
    return svc


@pytest.fixture()
def client() -> TestClient:
    # Not used as a context manager: the lifespan (docker image check, session
    # manager) is not needed for these tests.
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _reset_limiter() -> Generator[None, None, None]:
    set_execution_limiter(None)
    yield
    set_execution_limiter(None)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_missing_token_returns_401(token_auth: None, client: TestClient) -> None:
    resp = client.get("/v1/files")
    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


def test_wrong_token_returns_401(token_auth: None, client: TestClient) -> None:
    resp = client.get("/v1/files", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_non_bearer_scheme_returns_401(token_auth: None, client: TestClient) -> None:
    resp = client.get("/v1/files", headers={"Authorization": f"Basic {TOKEN}"})
    assert resp.status_code == 401


def test_correct_token_is_accepted(
    token_auth: None, client: TestClient, storage: FileStorageService
) -> None:
    resp = client.get("/v1/files", headers=AUTH)
    assert resp.status_code == 200
    # Scheme is case-insensitive.
    resp = client.get("/v1/files", headers={"Authorization": f"bearer {TOKEN}"})
    assert resp.status_code == 200


def test_auth_checked_before_upload_body(token_auth: None, client: TestClient) -> None:
    files = {"file": ("x.txt", io.BytesIO(b"x" * 1024), "text/plain")}
    resp = client.post("/v1/files", files=files)
    assert resp.status_code == 401


def test_unconfigured_token_fails_closed_with_503(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_API_TOKEN", "")
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_ALLOW_UNAUTHENTICATED", False)
    for method, path in (
        ("get", "/v1/files"),
        ("post", "/v1/sessions"),
        ("post", "/v1/execute"),
    ):
        resp = getattr(client, method)(path, headers={"Authorization": "Bearer anything"})
        assert resp.status_code == 503, (method, path)
        assert "not configured" in resp.json()["detail"]


def test_placeholder_token_counts_as_unconfigured(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """The env template's `change-me` must never work as a real shared secret."""
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_API_TOKEN", "change-me")
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_ALLOW_UNAUTHENTICATED", False)
    resp = client.get("/v1/files", headers={"Authorization": "Bearer change-me"})
    assert resp.status_code == 503


def test_dev_override_allows_unauthenticated(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, storage: FileStorageService
) -> None:
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_API_TOKEN", "")
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_ALLOW_UNAUTHENTICATED", True)
    assert client.get("/v1/files").status_code == 200


def test_token_wins_over_dev_override(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """If a token IS configured, the override never opens the API."""
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_API_TOKEN", TOKEN)
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_ALLOW_UNAUTHENTICATED", True)
    assert client.get("/v1/files").status_code == 401


def test_health_stays_open_when_misconfigured(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_API_TOKEN", "")
    monkeypatch.setattr(app_configs, "CODE_INTERPRETER_ALLOW_UNAUTHENTICATED", False)
    from app.services.executor_base import HealthCheck

    fake = MagicMock()
    fake.check_health.return_value = HealthCheck(status="ok")
    with patch("app.main.get_executor", return_value=fake):
        resp = client.get("/health")
    assert resp.status_code == 200


def test_tokens_match_is_exact() -> None:
    assert tokens_match("abc", "abc")
    assert not tokens_match("abc", "abd")
    assert not tokens_match("abc", "abc ")
    assert not tokens_match("", "abc")


# ---------------------------------------------------------------------------
# Tenant isolation: files
# ---------------------------------------------------------------------------


def _upload(client: TestClient, headers: dict[str, str], content: bytes = b"secret") -> str:
    resp = client.post(
        "/v1/files",
        files={"file": ("a.txt", io.BytesIO(content), "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["file_id"])


def test_file_of_tenant_a_is_invisible_to_tenant_b(
    token_auth: None, client: TestClient, storage: FileStorageService
) -> None:
    file_id = _upload(client, TENANT_A)

    # B can't download, delete, or list it -- and gets 404, not 403.
    assert client.get(f"/v1/files/{file_id}", headers=TENANT_B).status_code == 404
    assert client.delete(f"/v1/files/{file_id}", headers=TENANT_B).status_code == 404
    listed_b = client.get("/v1/files", headers=TENANT_B).json()["files"]
    assert listed_b == []

    # B can't stage it into an execution either (rejected before any executor runs).
    resp = client.post(
        "/v1/execute",
        json={"code": "print(1)", "files": [{"path": "a.txt", "file_id": file_id}]},
        headers=TENANT_B,
    )
    assert resp.status_code == 404

    # A still has full access.
    dl = client.get(f"/v1/files/{file_id}", headers=TENANT_A)
    assert dl.status_code == 200
    assert dl.content == b"secret"
    listed_a = client.get("/v1/files", headers=TENANT_A).json()["files"]
    assert [f["file_id"] for f in listed_a] == [file_id]
    assert client.delete(f"/v1/files/{file_id}", headers=TENANT_A).status_code == 204


def test_headerless_caller_is_its_own_bucket(
    token_auth: None, client: TestClient, storage: FileStorageService
) -> None:
    file_id = _upload(client, TENANT_A)
    assert client.get(f"/v1/files/{file_id}", headers=AUTH).status_code == 404
    unscoped_id = _upload(client, AUTH)
    assert client.get(f"/v1/files/{unscoped_id}", headers=TENANT_A).status_code == 404
    meta = storage.get_file(unscoped_id, UNSCOPED_TENANT)[1]
    assert meta.tenant_id == UNSCOPED_TENANT


def test_invalid_tenant_header_is_rejected(
    token_auth: None, client: TestClient, storage: FileStorageService
) -> None:
    resp = client.get("/v1/files", headers={**AUTH, "X-OM-Tenant": "../etc"})
    assert resp.status_code == 400


def test_malformed_file_id_is_404(storage: FileStorageService) -> None:
    for bad in ("..", "nonexistent-id", "x.meta.json"):
        with pytest.raises(FileNotFoundError):
            storage.get_file(bad, "tenant_a")


def test_legacy_file_without_tenant_is_invisible(storage: FileStorageService) -> None:
    file_id = storage.save_file(b"old", "old.txt", "tenant_a")
    meta_path = storage.storage_dir / f"{file_id}.meta.json"
    legacy = {"file_id": file_id, "filename": "old.txt", "size_bytes": 3, "upload_time": 0}
    meta_path.write_text(json.dumps(legacy), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        storage.get_file(file_id, "tenant_a")


# ---------------------------------------------------------------------------
# Tenant isolation: sessions
# ---------------------------------------------------------------------------


def _manager_with_session(session_id: str, tenant_id: str) -> SessionManager:
    mgr = SessionManager.__new__(SessionManager)
    mgr._sessions = {}
    mgr._lock = threading.Lock()
    proc = MagicMock()
    proc.poll.return_value = None
    mgr._sessions[session_id] = SessionState(
        session_id=session_id,
        container_name=f"ci-session-{session_id[:12]}",
        kernel_proc=proc,
        created_at=time.time(),
        last_used_at=time.time(),
        tenant_id=tenant_id,
    )
    return mgr


def test_session_of_tenant_a_is_invisible_to_tenant_b(
    token_auth: None,
    client: TestClient,
    storage: FileStorageService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sid = "a" * 32
    mgr = _manager_with_session(sid, "tenant_a")
    executed: list[str] = []
    deleted: list[str] = []

    def fake_execute(session_id: str, **_: object) -> ExecutionResult:
        executed.append(session_id)
        return ExecutionResult(
            stdout="2\n", stderr="", exit_code=0, timed_out=False, duration_ms=1, files=()
        )

    monkeypatch.setattr(mgr, "execute_in_session", fake_execute)
    monkeypatch.setattr(mgr, "delete_session", lambda s: deleted.append(s))
    monkeypatch.setattr(routes, "_session_manager", mgr)

    body = {"code": "print(1+1)", "session_id": sid}
    # B: execute, stream, and delete all look like "no such session".
    assert client.post("/v1/execute", json=body, headers=TENANT_B).status_code == 404
    assert client.post("/v1/execute/stream", json=body, headers=TENANT_B).status_code == 404
    assert client.delete(f"/v1/sessions/{sid}", headers=TENANT_B).status_code == 404
    assert executed == [] and deleted == []

    # A: works.
    resp = client.post("/v1/execute", json=body, headers=TENANT_A)
    assert resp.status_code == 200, resp.text
    assert resp.json()["stdout"] == "2\n"
    assert client.delete(f"/v1/sessions/{sid}", headers=TENANT_A).status_code == 204
    assert executed == [sid] and deleted == [sid]


def test_create_session_records_caller_tenant(
    token_auth: None, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    mgr = MagicMock()
    mgr.create_session.return_value = "b" * 32
    monkeypatch.setattr(routes, "_session_manager", mgr)
    resp = client.post("/v1/sessions", headers=TENANT_A)
    assert resp.status_code == 201
    assert mgr.create_session.call_args.kwargs["tenant_id"] == "tenant_a"


def test_has_session_checks_tenant() -> None:
    sid = "c" * 32
    mgr = _manager_with_session(sid, "tenant_a")
    assert mgr.has_session(sid, "tenant_a")
    assert not mgr.has_session(sid, "tenant_b")
    assert not mgr.has_session("missing", "tenant_a")


# ---------------------------------------------------------------------------
# Admission control
# ---------------------------------------------------------------------------


def test_queue_full_returns_503_with_retry_after(
    token_auth: None, client: TestClient, storage: FileStorageService
) -> None:
    limiter = ExecutionLimiter(max_workers=1, max_queue=0, queue_timeout_sec=0.1)
    set_execution_limiter(limiter)
    held = limiter.acquire()  # the only worker is busy
    try:
        for path in ("/v1/execute", "/v1/execute/stream"):
            resp = client.post(path, json={"code": "print(1)"}, headers=TENANT_A)
            assert resp.status_code == 503, path
            assert resp.headers["retry-after"] == str(app_configs.EXECUTION_RETRY_AFTER_SEC)
    finally:
        held.release()
    assert limiter.admitted == 0


def test_limiter_queues_then_rejects() -> None:
    limiter = ExecutionLimiter(max_workers=1, max_queue=1, queue_timeout_sec=5)
    first = limiter.acquire()

    got: list[object] = []
    waiter = threading.Thread(target=lambda: got.append(limiter.acquire()))
    waiter.start()
    deadline = time.time() + 2
    while limiter.admitted < 2 and time.time() < deadline:
        time.sleep(0.01)
    assert limiter.admitted == 2  # one running, one queued

    # Worker busy + queue full -> immediate rejection.
    with pytest.raises(CapacityExceededError):
        limiter.acquire()

    first.release()
    waiter.join(timeout=2)
    assert len(got) == 1  # the queued request got the slot
    got[0].release()  # type: ignore[attr-defined]
    first.release()  # idempotent
    assert limiter.admitted == 0


def test_limiter_queue_wait_times_out() -> None:
    limiter = ExecutionLimiter(max_workers=1, max_queue=5, queue_timeout_sec=0.05)
    held = limiter.acquire()
    with pytest.raises(CapacityExceededError):
        limiter.acquire()
    held.release()
    assert limiter.admitted == 0


def test_slot_released_after_execution(
    token_auth: None, client: TestClient, storage: FileStorageService
) -> None:
    limiter = ExecutionLimiter(max_workers=1, max_queue=0, queue_timeout_sec=0.1)
    set_execution_limiter(limiter)
    result = ExecutionResult(
        stdout="2\n", stderr="", exit_code=0, timed_out=False, duration_ms=1, files=()
    )
    with patch("app.api.routes.execute_python", return_value=result):
        for _ in range(3):
            resp = client.post("/v1/execute", json={"code": "print(1+1)"}, headers=TENANT_A)
            assert resp.status_code == 200
    assert limiter.admitted == 0


# ---------------------------------------------------------------------------
# Sandbox hardening
# ---------------------------------------------------------------------------


def _flag_value(cmd: list[str], flag: str) -> list[str]:
    return [cmd[i + 1] for i, part in enumerate(cmd) if part == flag]


def test_docker_run_command_is_hardened() -> None:
    from app.services.executor_docker import DockerExecutor

    ex = DockerExecutor.__new__(DockerExecutor)
    ex.docker_binary = "docker"
    ex.image = "om/python-executor-sci"
    ex.run_args = ""
    cmd = ex._build_run_command("code-exec-x", 5, 256, 1000)

    assert "--read-only" in cmd
    assert _flag_value(cmd, "--network") == ["none"]
    assert _flag_value(cmd, "--user") == ["65532:65532"]
    assert _flag_value(cmd, "--cpus") == [str(app_configs.EXECUTOR_CPUS)]
    assert _flag_value(cmd, "--cap-drop") == ["ALL"]
    assert _flag_value(cmd, "--cap-add") == []
    assert _flag_value(cmd, "--pids-limit") == ["64"]
    assert "no-new-privileges" in _flag_value(cmd, "--security-opt")
    tmpfs = _flag_value(cmd, "--tmpfs")
    assert any(t.startswith("/tmp:") and "size=" in t for t in tmpfs)  # noqa: S108
    assert any(
        t.startswith("/workspace:")
        and f"size={app_configs.EXECUTOR_WORKSPACE_SIZE_MB}m" in t
        and "uid=65532" in t
        for t in tmpfs
    )
    assert _flag_value(cmd, "--memory") == ["256m"]
    assert _flag_value(cmd, "--ulimit") == ["cpu=5:5"]


def test_session_container_is_hardened(monkeypatch: pytest.MonkeyPatch) -> None:
    mgr = SessionManager.__new__(SessionManager)
    mgr._sessions = {}
    mgr._lock = threading.Lock()
    mgr._docker_binary = "docker"
    mgr._image = "om/python-executor-sci"
    mgr._run_args = ""
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_: object) -> MagicMock:
        captured.append(cmd)
        return MagicMock(returncode=1, stderr="stop here")

    monkeypatch.setattr("app.services.session_manager.subprocess.run", fake_run)
    with pytest.raises(RuntimeError):
        mgr.create_session(memory_limit_mb=256, tenant_id="tenant_a")

    cmd = captured[0]
    assert "--read-only" in cmd
    assert _flag_value(cmd, "--network") == ["none"]
    assert _flag_value(cmd, "--user") == ["65532:65532"]
    assert _flag_value(cmd, "--cpus") == [str(app_configs.EXECUTOR_CPUS)]
    assert any("size=" in t for t in _flag_value(cmd, "--tmpfs") if t.startswith("/workspace"))


def test_kubernetes_pod_spec_is_hardened() -> None:
    from app.services.executor_kubernetes import KubernetesExecutor

    ex = KubernetesExecutor.__new__(KubernetesExecutor)
    ex.namespace = "ns"
    ex.image = "img"
    ex.service_account = ""
    pod = ex._create_pod_manifest("code-exec-x", memory_limit_mb=256, cpu_time_limit_sec=5)
    spec = pod.spec

    assert spec.automount_service_account_token is False
    assert spec.enable_service_links is False
    assert spec.security_context["runAsNonRoot"] is True
    assert spec.security_context["seccompProfile"] == {"type": "RuntimeDefault"}

    container = spec.containers[0]
    sc = container.security_context
    assert sc["readOnlyRootFilesystem"] is True
    assert sc["runAsNonRoot"] is True
    assert sc["allowPrivilegeEscalation"] is False
    assert sc["capabilities"] == {"drop": ["ALL"]}
    assert sc["seccompProfile"] == {"type": "RuntimeDefault"}
    # Writable paths are emptyDir mounts.
    mounts = {m["mountPath"] for m in container.volume_mounts}
    assert {"/workspace", "/tmp"} <= mounts  # noqa: S108
    assert {v["name"] for v in spec.volumes} == {"workspace", "tmp"}
    assert all("emptyDir" in v for v in spec.volumes)
    # The NetworkPolicy selects executor pods by these labels.
    assert pod.metadata.labels == {"app": "code-interpreter", "component": "executor"}


def test_kubernetes_rejects_reserved_stdin_path() -> None:
    from app.services.executor_kubernetes import KubernetesExecutor

    ex = KubernetesExecutor.__new__(KubernetesExecutor)
    with pytest.raises(ValueError):
        ex._create_tar_archive("print(1)", [(".ci_stdin", b"x")])


def _tar_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(name=f"./{name}")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def test_workspace_snapshot_is_capped() -> None:
    data = _tar_bytes({"small.txt": b"a" * 10, "big.bin": b"b" * 5000, "plot.png": b"c" * 20})
    entries = read_workspace_tar(io.BytesIO(data), max_total_bytes=100)
    got = {e.path: e.content for e in entries}
    # The oversize file is skipped, never truncated; smaller ones still come back.
    assert got == {"small.txt": b"a" * 10, "plot.png": b"c" * 20}


def test_workspace_snapshot_tolerates_truncated_stream() -> None:
    data = _tar_bytes({"one.txt": b"1" * 600, "two.txt": b"2" * 600})
    entries = read_workspace_tar(io.BytesIO(data[:1600]), max_total_bytes=10_000)
    assert [e.path for e in entries] == ["one.txt"]
