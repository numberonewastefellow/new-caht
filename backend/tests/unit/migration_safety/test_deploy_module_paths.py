"""Every module path in docker-compose service commands must resolve.

Compose `command:`/`entrypoint:` strings launch the app processes and embed module
paths (`uvicorn om.main:app`, `python -m om.mcp_server_main`, `celery -A ...`).
Like supervisord, a missed rename here fails only at container start, not at import.
This parses every `deployment/docker_compose/docker-compose*.yml` and resolves the
embedded modules. Rename-agnostic + env-tolerant.
"""

from __future__ import annotations

import re

import pytest

from tests.unit.migration_safety.conftest import path_to_module
from tests.unit.migration_safety.conftest import repo_root
from tests.unit.migration_safety.conftest import resolve_symbol

yaml = pytest.importorskip("yaml")

_COMPOSE_DIR = repo_root() / "deployment" / "docker_compose"

_PATTERNS = [
    re.compile(r"uvicorn\s+([A-Za-z_][\w.]+):"),  # uvicorn om.main:app
    re.compile(r"python\s+-m\s+([A-Za-z_][\w.]+)"),  # python -m om.mcp_server_main
    re.compile(r"celery\s+-A\s+([A-Za-z_][\w.]+)"),  # celery -A onyx....
]
_PY_SCRIPT = re.compile(r"python\s+([\w./\\-]+\.py)")


def _compose_files() -> list:
    return sorted(_COMPOSE_DIR.glob("docker-compose*.yml"))


def _command_strings(doc: object) -> list[str]:
    """Flatten every service command/entrypoint into shell strings."""
    strings: list[str] = []
    services = (doc or {}).get("services", {}) if isinstance(doc, dict) else {}
    for svc in services.values():
        if not isinstance(svc, dict):
            continue
        for key in ("command", "entrypoint"):
            val = svc.get(key)
            if isinstance(val, str):
                strings.append(val)
            elif isinstance(val, list):
                strings.append(" ".join(str(x) for x in val))
    return strings


def _collect_modules() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path in _compose_files():
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        for cmd in _command_strings(doc):
            for pat in _PATTERNS:
                for mod in pat.findall(cmd):
                    found.append((path.name, mod))
            for script in _PY_SCRIPT.findall(cmd):
                found.append((path.name, path_to_module(script)))
    return found


def test_compose_module_paths_resolve() -> None:
    if not _COMPOSE_DIR.exists():
        pytest.skip(f"compose dir not found: {_COMPOSE_DIR}")
    modules = _collect_modules()
    if not modules:
        pytest.skip("No module paths found in compose commands (may use supervisord)")

    namespace_failures: list[str] = []
    env_skips: list[str] = []
    for fname, module in modules:
        status = resolve_symbol(module)
        if status in ("namespace", "missing_attr"):
            namespace_failures.append(f"{fname}: {module} [{status}]")
        elif status == "env":
            env_skips.append(f"{fname}: {module}")

    if env_skips:
        print(f"[compose] env-tolerated {len(env_skips)} module paths")

    assert not namespace_failures, (
        "Unresolvable compose command module paths (missed rename / dead string):\n"
        + "\n".join(sorted(set(namespace_failures)))
    )
