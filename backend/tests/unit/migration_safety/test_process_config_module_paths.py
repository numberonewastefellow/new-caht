"""Every module/script path in supervisord.conf must resolve.

`backend/supervisord.conf` is what actually launches the Celery workers and helper
processes in the container. Its `command=` lines embed module paths as STRINGS
(`celery -A onyx.background.celery.versioned_apps.X`, `python onyx/utils/...py`).
A missed rename here doesn't fail any Python import at build time -- the worker just
fails to start. This test parses the file and resolves each embedded module.

Rename-agnostic: reads the current file, so it checks `onyx.` today and `om.` after
the rename. Env-tolerant: only `onyx`/`om`/`ee` breakage fails; missing third-party
deps skip.
"""

from __future__ import annotations

import re

import pytest

from tests.unit.migration_safety.conftest import backend_root
from tests.unit.migration_safety.conftest import path_to_module
from tests.unit.migration_safety.conftest import resolve_symbol

_SUPERVISORD = backend_root() / "supervisord.conf"

# `celery -A <module> ...`
_CELERY_A = re.compile(r"celery\s+-A\s+([A-Za-z_][\w.]+)")
# `python <path>.py ...`  (first .py token after `python`)
_PYTHON_SCRIPT = re.compile(r"python\s+([\w./\\-]+\.py)")


def _command_lines() -> list[str]:
    text = _SUPERVISORD.read_text(encoding="utf-8")
    return [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.strip().startswith("command=")
    ]


def _collect_module_paths() -> list[tuple[str, str]]:
    """Return (kind, dotted_module) pairs found in command= lines."""
    found: list[tuple[str, str]] = []
    for cmd in _command_lines():
        for mod in _CELERY_A.findall(cmd):
            found.append(("celery", mod))
        for script in _PYTHON_SCRIPT.findall(cmd):
            found.append(("python", path_to_module(script)))
    return found


def test_supervisord_module_paths_resolve() -> None:
    assert _SUPERVISORD.exists(), f"supervisord.conf not found at {_SUPERVISORD}"
    paths = _collect_module_paths()
    # Sanity floor: 9 celery apps + at least the watchdog script.
    assert len(paths) >= 10, f"Expected many module paths, parsed {len(paths)}: {paths}"

    namespace_failures: list[str] = []
    env_skips: list[str] = []
    for kind, module in paths:
        status = resolve_symbol(module)
        if status in ("namespace", "missing_attr"):
            namespace_failures.append(f"[{kind}] {module} [{status}]")
        elif status == "env":
            env_skips.append(f"[{kind}] {module}")

    if env_skips:
        print(f"[supervisord] env-tolerated {len(env_skips)}: " + ", ".join(env_skips))

    assert not namespace_failures, (
        "Unresolvable supervisord.conf module paths (missed rename / dead string):\n"
        + "\n".join(sorted(namespace_failures))
    )
