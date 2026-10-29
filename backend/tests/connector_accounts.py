"""Skip (instead of fail) connector tests whose external account is not configured.

Many connector tests talk to a real third-party account (Slack workspace, Google Drive, Jira, ...).
They read credentials with ``os.environ["NAME"]``; when that account has not been provisioned yet the
test would die with a KeyError. This helper statically reads the hard-required variables of a test
module (and of the ``conftest.py`` files above it, up to the suite root) and turns "not provisioned" into
a clear skip. Provision an account, set its variables, and its tests start running with no code change.

A module can also declare extra requirements explicitly: ``REQUIRES_ENV = ["SOME_VAR", ...]``.
The per-connector list of accounts and data to create is in ``backend/tests/daily/ACCOUNTS.md``.
"""

import os
import re
from pathlib import Path

import pytest

_HARD_ENV = re.compile(r"""os\.environ\[\s*["']([A-Z][A-Z0-9_]*)["']\s*\]""")
_DECLARED = re.compile(r"""^REQUIRES_ENV\s*=\s*\[([^\]]*)\]""", re.M)
# REQUIRES_ANY_ENV = ["A", "B"]: the account is provisioned when at least ONE of the names is set.
_DECLARED_ANY = re.compile(r"""^REQUIRES_ANY_ENV\s*=\s*\[([^\]]*)\]""", re.M)
_cache: dict[Path, frozenset[str]] = {}
_any_cache: dict[Path, tuple[tuple[str, ...], ...]] = {}


def _any_groups_in(path: Path) -> tuple[tuple[str, ...], ...]:
    if path not in _any_cache:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        _any_cache[path] = tuple(
            tuple(re.findall(r"""["']([A-Z][A-Z0-9_]*)["']""", block))
            for block in _DECLARED_ANY.findall(text)
        )
    return _any_cache[path]


def _names_in(path: Path) -> frozenset[str]:
    if path in _cache:
        return _cache[path]
    names: set[str] = set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    names.update(_HARD_ENV.findall(text))
    for block in _DECLARED.findall(text):
        names.update(re.findall(r"""["']([A-Z][A-Z0-9_]*)["']""", block))
    _cache[path] = frozenset(names)
    return _cache[path]


def required_env(test_file: Path, suite_root: Path) -> list[str]:
    """Environment variables the test module and its conftests need, sorted."""
    names: set[str] = set(_names_in(test_file))
    directory = test_file.parent
    while True:
        conftest = directory / "conftest.py"
        if conftest.exists():
            names.update(_names_in(conftest))
        if directory == suite_root or directory.parent == directory:
            break
        directory = directory.parent
    return sorted(names)


def required_any_env(test_file: Path, suite_root: Path) -> list[tuple[str, ...]]:
    """Groups of alternative variables (one of each group must be set)."""
    groups: list[tuple[str, ...]] = list(_any_groups_in(test_file))
    directory = test_file.parent
    while True:
        conftest = directory / "conftest.py"
        if conftest.exists():
            groups.extend(_any_groups_in(conftest))
        if directory == suite_root or directory.parent == directory:
            break
        directory = directory.parent
    return [g for g in groups if g]


def skip_unprovisioned(items: list[pytest.Item], suite_root: Path, accounts_doc: str) -> None:
    """``pytest_collection_modifyitems`` body: add a skip marker to tests with missing variables."""
    root = suite_root.resolve()
    for item in items:
        path = Path(str(item.fspath)).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        missing = [n for n in required_env(path, root) if not os.environ.get(n)]
        for group in required_any_env(path, root):
            if not any(os.environ.get(n) for n in group):
                missing.append(" or ".join(group))
        if missing:
            item.add_marker(
                pytest.mark.skip(
                    reason=f"external account not provisioned: set {', '.join(missing)} (see {accounts_doc})"
                )
            )
