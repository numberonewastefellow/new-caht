"""Shared sandbox hardening for the Docker executor and persistent sessions.

Both the ephemeral executor (``executor_docker.py``) and the session manager
(``session_manager.py``) start sandbox containers; they share the flag set below so
the two paths can't drift apart. The workspace-snapshot reader is shared with the
Kubernetes executor as well.
"""

from __future__ import annotations

import logging
import subprocess
import tarfile
import threading
from contextlib import suppress
from typing import IO

from app.app_configs import (
    EXECUTOR_CPUS,
    EXECUTOR_RUN_AS_NON_ROOT,
    EXECUTOR_TMP_SIZE_MB,
    EXECUTOR_WORKSPACE_SIZE_MB,
)
from app.services.executor_base import EntryKind, WorkspaceEntry

logger = logging.getLogger(__name__)

# Unprivileged uid/gid that owns /workspace and runs user code.
SANDBOX_UID = 65532
SANDBOX_GID = 65532
SANDBOX_USER = f"{SANDBOX_UID}:{SANDBOX_GID}"

# Wall-clock budget for reading the workspace snapshot back out of a container.
_SNAPSHOT_TIMEOUT_SEC = 10


def hardened_docker_run_flags(container_name: str) -> list[str]:
    """Flags common to every sandbox ``docker run`` (no image/command, no limits).

    * no network, read-only root filesystem, size-capped tmpfs for the only two
      writable paths (/tmp, /workspace);
    * every capability dropped, no-new-privileges, pids limit, CPU share cap;
    * the whole container (not only user code) runs as the unprivileged sandbox user,
      so ``docker exec`` without ``-u`` is unprivileged too.
    """
    flags: list[str] = [
        "--pull",
        "never",
        "--network",
        "none",
        "--name",
        container_name,
        "--cgroupns",
        "host",  # Use host cgroup namespace to avoid cgroup v2 issues in DinD
        "--pids-limit",
        "64",
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "--read-only",
        "--cpus",
        str(EXECUTOR_CPUS),
        "--workdir",
        "/workspace",
        "--tmpfs",
        f"/tmp:rw,size={EXECUTOR_TMP_SIZE_MB}m",  # noqa: S108 - constrained container tmpfs
        "--tmpfs",
        # Workspace tmpfs owned by the sandbox user, size-capped.
        f"/workspace:rw,size={EXECUTOR_WORKSPACE_SIZE_MB}m,uid={SANDBOX_UID},gid={SANDBOX_GID}",
        "--env",
        "PYTHONUNBUFFERED=1",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "PYTHONIOENCODING=utf-8",
        "--env",
        "MPLCONFIGDIR=/tmp/matplotlib",
    ]
    if EXECUTOR_RUN_AS_NON_ROOT:
        flags.extend(["--user", SANDBOX_USER])
    else:
        # The image's default (root) user only needs CHOWN to hand /workspace over.
        flags.extend(["--cap-add", "CHOWN"])
    return flags


def read_workspace_tar(
    fileobj: IO[bytes],
    max_total_bytes: int,
    exclude: frozenset[str] = frozenset(),
) -> tuple[WorkspaceEntry, ...]:
    """Parse a workspace tar stream into entries, reading at most ``max_total_bytes``
    of file content into memory.

    The tar is read in streaming mode (``r|``) so memory is bounded by the cap, not by
    the workspace size. A file that would push the total over the cap is skipped (and
    logged), never truncated. A truncated/corrupt stream yields the entries parsed
    before the damage instead of raising.
    """
    entries: list[WorkspaceEntry] = []
    total = 0
    skipped: list[str] = []
    try:
        with tarfile.open(fileobj=fileobj, mode="r|") as tar:
            for member in tar:
                # Skip the root directory
                if member.name in (".", "./"):
                    continue

                # Clean up the path (remove leading ./)
                clean_path = member.name.lstrip("./")
                if clean_path in exclude:
                    continue

                if member.isdir():
                    entries.append(
                        WorkspaceEntry(path=clean_path, kind=EntryKind.DIRECTORY, content=None)
                    )
                elif member.isfile():
                    if total + member.size > max_total_bytes:
                        skipped.append(clean_path)
                        continue
                    file_obj = tar.extractfile(member)
                    if file_obj is None:
                        continue
                    content = file_obj.read()
                    total += len(content)
                    entries.append(
                        WorkspaceEntry(path=clean_path, kind=EntryKind.FILE, content=content)
                    )
    except (tarfile.TarError, EOFError, OSError) as e:
        logger.warning(f"Workspace snapshot stream ended early: {e}")

    if skipped:
        logger.warning(
            f"Workspace snapshot cap ({max_total_bytes} bytes) reached; skipped "
            f"{len(skipped)} file(s): {skipped[:10]}"
        )
    return tuple(entries)


def stream_workspace_snapshot(
    tar_cmd: list[str], max_total_bytes: int
) -> tuple[WorkspaceEntry, ...]:
    """Run ``tar_cmd`` (a ``docker exec ... tar -c`` producing the workspace on stdout)
    and parse its output with a bounded memory budget. Never raises.

    The tar is parsed as it streams (never buffered whole via ``capture_output``), so a
    workspace full of output can't balloon the service process.
    """
    try:
        proc = subprocess.Popen(  # nosec B603
            tar_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        logger.warning(f"Failed to start workspace snapshot: {e}")
        return tuple()

    # Watchdog: a wedged ``docker exec`` must not hang the request forever.
    watchdog = threading.Timer(_SNAPSHOT_TIMEOUT_SEC, proc.kill)
    watchdog.daemon = True
    watchdog.start()
    try:
        if proc.stdout is None:
            return tuple()
        entries = read_workspace_tar(proc.stdout, max_total_bytes)
        # Drain whatever is left so tar can exit, without keeping it.
        with suppress(Exception):
            while proc.stdout.read(65536):
                pass
        proc.wait(timeout=_SNAPSHOT_TIMEOUT_SEC)
        if proc.returncode != 0:
            return tuple()
        return entries
    except Exception as e:
        logger.warning(f"Workspace snapshot failed: {e}")
        with suppress(Exception):
            proc.kill()
        return tuple()
    finally:
        watchdog.cancel()
        if proc.stdout is not None:
            with suppress(Exception):
                proc.stdout.close()
