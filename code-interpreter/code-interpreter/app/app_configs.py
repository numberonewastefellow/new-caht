from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from functools import lru_cache

# Executor backend selection
EXECUTOR_BACKEND = os.environ.get("EXECUTOR_BACKEND") or "docker"

# Docker executor configuration
PYTHON_EXECUTOR_DOCKER_BIN = os.environ.get("PYTHON_EXECUTOR_DOCKER_BIN") or "docker"
PYTHON_EXECUTOR_DOCKER_IMAGE = (
    os.environ.get("PYTHON_EXECUTOR_DOCKER_IMAGE") or "om/python-executor-sci"
)
# Tag appended to PYTHON_EXECUTOR_DOCKER_IMAGE (ignored when the image already names a
# tag or digest, e.g. "repo/img:1.2" or "repo/img@sha256:...").
PYTHON_EXECUTOR_DOCKER_TAG = os.environ.get("PYTHON_EXECUTOR_DOCKER_TAG") or "latest"
PYTHON_EXECUTOR_DOCKER_RUN_ARGS = os.environ.get("PYTHON_EXECUTOR_DOCKER_RUN_ARGS") or ""


def docker_image_ref(image: str, tag: str) -> str:
    """``image:tag``, unless ``image`` already carries a tag or a digest."""
    last_component = image.rsplit("/", 1)[-1]
    if "@" in image or ":" in last_component:
        return image
    return f"{image}:{tag}"


# Fully qualified executor image every Docker sandbox (ephemeral, session, run_function)
# is started from.
PYTHON_EXECUTOR_DOCKER_IMAGE_REF = docker_image_ref(
    PYTHON_EXECUTOR_DOCKER_IMAGE, PYTHON_EXECUTOR_DOCKER_TAG
)

# Kubernetes executor configuration
KUBERNETES_EXECUTOR_NAMESPACE = os.environ.get("KUBERNETES_EXECUTOR_NAMESPACE") or "default"
KUBERNETES_EXECUTOR_IMAGE = (
    os.environ.get("KUBERNETES_EXECUTOR_IMAGE") or "om/python-executor-sci"
)
KUBERNETES_EXECUTOR_SERVICE_ACCOUNT = os.environ.get("KUBERNETES_EXECUTOR_SERVICE_ACCOUNT") or ""

# Execution limits
MAX_EXEC_TIMEOUT_MS = int(os.environ.get("MAX_EXEC_TIMEOUT_MS") or 60_000)
MAX_OUTPUT_BYTES = int(os.environ.get("MAX_OUTPUT_BYTES") or 1_000_000)
CPU_TIME_LIMIT_SEC = int(os.environ.get("CPU_TIME_LIMIT_SEC") or 5)
MEMORY_LIMIT_MB = int(os.environ.get("MEMORY_LIMIT_MB") or 256)

# API authentication. Every /v1/* route requires ``Authorization: Bearer <token>``.
# With no token configured the service FAILS CLOSED (503 on /v1/*) unless the
# dev-only escape hatch CODE_INTERPRETER_ALLOW_UNAUTHENTICATED=true is set.
CODE_INTERPRETER_API_TOKEN = (os.environ.get("CODE_INTERPRETER_API_TOKEN") or "").strip()
CODE_INTERPRETER_ALLOW_UNAUTHENTICATED = (
    os.environ.get("CODE_INTERPRETER_ALLOW_UNAUTHENTICATED") or ""
).strip().lower() == "true"

# Execution concurrency: at most EXECUTION_MAX_WORKERS executions run at once and at
# most EXECUTION_MAX_QUEUE more wait for a slot (up to EXECUTION_QUEUE_TIMEOUT_SEC).
# Anything beyond that gets 503 + Retry-After so callers back off.
EXECUTION_MAX_WORKERS = max(1, int(os.environ.get("EXECUTION_MAX_WORKERS") or 8))
EXECUTION_MAX_QUEUE = max(0, int(os.environ.get("EXECUTION_MAX_QUEUE") or 32))
EXECUTION_QUEUE_TIMEOUT_SEC = float(os.environ.get("EXECUTION_QUEUE_TIMEOUT_SEC") or 60)
EXECUTION_RETRY_AFTER_SEC = max(1, int(os.environ.get("EXECUTION_RETRY_AFTER_SEC") or 5))

# Sandbox container hardening (Docker executor + persistent sessions)
# CPU share for each sandbox container (`docker run --cpus`).
EXECUTOR_CPUS = os.environ.get("EXECUTOR_CPUS") or "1"
# Size cap of the writable /workspace tmpfs (the root filesystem is read-only).
EXECUTOR_WORKSPACE_SIZE_MB = max(1, int(os.environ.get("EXECUTOR_WORKSPACE_SIZE_MB") or 128))
# Size cap of the writable /tmp tmpfs.
EXECUTOR_TMP_SIZE_MB = max(1, int(os.environ.get("EXECUTOR_TMP_SIZE_MB") or 64))
# Run the whole sandbox container as the unprivileged sandbox uid/gid 65532
# (`docker run --user 65532:65532`), not just the user-code process. Set to "false"
# only if a custom executor image can't run its entry command as a non-root user.
EXECUTOR_RUN_AS_NON_ROOT = (
    os.environ.get("EXECUTOR_RUN_AS_NON_ROOT") or "true"
).strip().lower() != "false"
# Max bytes of file content read back from the workspace snapshot after a run.
# Files that would push the total over the cap are skipped (logged), never truncated.
MAX_WORKSPACE_SNAPSHOT_BYTES = int(
    os.environ.get("MAX_WORKSPACE_SNAPSHOT_BYTES") or 64 * 1024 * 1024
)

# Low-latency /v1/run_function (Docker executor). Every call runs in its own fresh,
# single-use sandbox container that is destroyed afterwards; the warm pool only
# pre-starts identical hardened containers so a call skips the `docker run`.
RUN_FUNCTION_POOL_ENABLED = (
    os.environ.get("RUN_FUNCTION_POOL_ENABLED") or "true"
).strip().lower() != "false"
# Idle containers the pool keeps ready (it grows toward the max under bursts).
# A max below the min wins: the min is lowered to it.
RUN_FUNCTION_POOL_MAX = max(0, int(os.environ.get("RUN_FUNCTION_POOL_MAX") or 8))
RUN_FUNCTION_POOL_MIN = min(
    RUN_FUNCTION_POOL_MAX, max(0, int(os.environ.get("RUN_FUNCTION_POOL_MIN") or 2))
)
# Idle pooled containers older than this are destroyed and replaced.
RUN_FUNCTION_POOL_TTL_SEC = max(10, int(os.environ.get("RUN_FUNCTION_POOL_TTL_SEC") or 600))
# Owner label on this instance's run_function containers. Startup and shutdown remove
# every container carrying it, so instances sharing one Docker daemon need distinct
# owners (the default, the hostname, already differs per container).
RUN_FUNCTION_POOL_OWNER = os.environ.get("RUN_FUNCTION_POOL_OWNER") or socket.gethostname()
# Most stderr bytes returned by /v1/run_function (stdout is capped by MAX_OUTPUT_BYTES).
RUN_FUNCTION_MAX_STDERR_BYTES = max(
    1, int(os.environ.get("RUN_FUNCTION_MAX_STDERR_BYTES") or 64 * 1024)
)
# Most bytes of the optional out-of-band result file (/tmp/result) returned as
# result_payload. A bigger file is rejected (result_error="too_large"), never truncated.
RUN_FUNCTION_MAX_RESULT_BYTES = max(
    1, int(os.environ.get("RUN_FUNCTION_MAX_RESULT_BYTES") or 1024 * 1024)
)

# API server configuration
HOST = os.environ.get("HOST") or "0.0.0.0"  # noqa: S104
PORT = int(os.environ.get("PORT") or "8000")

# File storage configuration
FILE_STORAGE_DIR = (
    os.environ.get("FILE_STORAGE_DIR") or "/tmp/code-interpreter-files"  # noqa: S108
)
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB") or 100)
FILE_TTL_SEC = int(os.environ.get("FILE_TTL_SEC") or 3600)

# Session configuration
SESSION_IDLE_TIMEOUT_SEC = int(os.environ.get("SESSION_IDLE_TIMEOUT_SEC") or 1800)
SESSION_MAX_LIFETIME_SEC = int(os.environ.get("SESSION_MAX_LIFETIME_SEC") or 86400)
SESSION_MAX_CONCURRENT = int(os.environ.get("SESSION_MAX_CONCURRENT") or 20)
SESSION_CONTAINER_SLEEP_SEC = int(os.environ.get("SESSION_CONTAINER_SLEEP_SEC") or 7200)
SESSION_CLEANUP_INTERVAL_SEC = int(os.environ.get("SESSION_CLEANUP_INTERVAL_SEC") or 60)


@dataclass(frozen=True, slots=True)
class Settings:
    max_exec_timeout_ms: int
    max_output_bytes: int
    cpu_time_limit_sec: int
    memory_limit_mb: int
    file_storage_dir: str
    max_file_size_mb: int
    file_ttl_sec: int

    @staticmethod
    def from_env() -> Settings:
        return Settings(
            max_exec_timeout_ms=MAX_EXEC_TIMEOUT_MS,
            max_output_bytes=MAX_OUTPUT_BYTES,
            cpu_time_limit_sec=CPU_TIME_LIMIT_SEC,
            memory_limit_mb=MEMORY_LIMIT_MB,
            file_storage_dir=FILE_STORAGE_DIR,
            max_file_size_mb=MAX_FILE_SIZE_MB,
            file_ttl_sec=FILE_TTL_SEC,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
