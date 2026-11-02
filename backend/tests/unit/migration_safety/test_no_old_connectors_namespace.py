"""The connectors package moved to ``om/datasource``; no reference to the old path may remain.

A stale import fails loudly, but stale strings don't: registry ``module_path`` values,
``mock.patch`` targets and paths in CI or deploy files only fail when that code runs.
"""

from __future__ import annotations

import re
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[3]
_REPO = _BACKEND.parent

_OLD_PATH = re.compile(
    r"(?<![\w.])(?<!UP:)om[./]connectors\b"
    r"|\btests[./](?:unit[./]om|daily|external_dependency_unit)[./]connectors\b"
)
_SCANNED_SUFFIXES = {".py", ".toml", ".ini", ".cfg", ".conf", ".yml", ".yaml", ".sh", ".bat"}
_SCANNED_NAMES = {"Dockerfile", ".gitignore", ".dockerignore"}
_SKIPPED_DIRS = {"__pycache__", ".venv", "node_modules", "phoenix", "graphify-out", ".git"}


def _is_scanned(path: Path) -> bool:
    if path.resolve() == Path(__file__).resolve():
        return False
    if _SKIPPED_DIRS.intersection(path.parts):
        return False
    return path.suffix in _SCANNED_SUFFIXES or path.name.startswith(tuple(_SCANNED_NAMES))


def test_old_package_folders_are_gone() -> None:
    for old in (
        "om/connectors",
        "tests/unit/om/connectors",
        "tests/daily/connectors",
        "tests/external_dependency_unit/connectors",
    ):
        leftovers = [
            p for p in (_BACKEND / old).rglob("*") if p.is_file() and p.suffix != ".pyc"
        ]
        assert not leftovers, f"{old} still has files: {leftovers[:5]}"


def test_no_reference_to_old_package_path() -> None:
    # The deployment and CI folders exist only when run from a full checkout.
    roots = [_BACKEND, _REPO / "deployment", _REPO / ".github"]
    hits = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or not _is_scanned(path):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for number, line in enumerate(text.splitlines(), start=1):
                if _OLD_PATH.search(line):
                    hits.append(f"{path}:{number}: {line.strip()[:100]}")
    assert not hits, "old package path still referenced:\n" + "\n".join(hits[:30])
