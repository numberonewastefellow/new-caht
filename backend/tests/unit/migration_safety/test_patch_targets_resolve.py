"""Every `@patch("module.Attr")` string target must actually resolve.

A mock patch target is a module path AND an identifier, both buried in a string literal.
Nothing checks it: not the import walk (the test module imports fine), not mypy, not the
type checker. It fails only when that specific test runs -- and it fails as an
`AttributeError: module 'x' has no attribute 'Y'`, which reads like a broken test rather
than a missed rename.

This shipped twice already:

  * Stage 1 renamed the class `OnyxConfluence` -> `OmConfluence`, but
    `@patch("om.connectors.confluence.onyx_confluence.OnyxConfluence.retrieve_...")`
    is a STRING, so the rename never touched it. Five such patch targets were left
    pointing at classes that no longer exist (OnyxConfluence, OnyxAPIClient,
    OnyxDiscordClient, OnyxDBCredentialsProvider, OnyxSalesforceSQLite).
  * EE removal deleted `fetch_ee_implementation_or_noop`, and ~30 patch targets kept
    naming it.

Both were invisible until the affected test was actually executed -- and in the
Confluence case, not even then, because a SEPARATE bug (a broken `tests.unit.om` import)
stopped the file from being collected at all. Two silent failures stacked on each other.

Resolution is env-tolerant: a target whose module needs a third-party dep that is absent
here is SKIPPED, never failed -- the same classification the rest of this suite uses. A
module that imports fine but does not expose the attribute is a real defect.
"""

from __future__ import annotations

import ast
import importlib

from tests.unit.migration_safety.conftest import backend_root
from tests.unit.migration_safety.conftest import import_module_status

_PATCH_FUNCS = {"patch", "object", "dict"}  # patch(...), patch.object(...), patch.dict(...)


def _patch_target_strings() -> list[tuple[str, int, str]]:
    """(file, lineno, target) for every literal string passed to a patch(...) call."""
    out: list[tuple[str, int, str]] = []
    tests_dir = backend_root() / "tests"

    for path in sorted(tests_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name not in _PATCH_FUNCS:
                continue
            # `patch.object(SomeClass, "attr")` takes an object, not a dotted string --
            # only the plain `patch("a.b.C")` form is a string module path.
            if name != "patch":
                continue
            if not node.args:
                continue
            first = node.args[0]
            if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
                continue
            target = first.value
            # Only care about targets into our own package.
            if not target.startswith(("om.", "onyx.", "ee.")):
                continue
            out.append((path.name, node.lineno, target))
    return out


def _resolve(target: str) -> str:
    """Return "ok" | "env" | "missing" for a dotted patch target.

    Walks from the longest importable module prefix, then getattr()s the rest -- a patch
    target can be `module.Class.method`, so the module/attribute boundary is unknown.
    """
    parts = target.split(".")
    for split in range(len(parts) - 1, 0, -1):
        module_path = ".".join(parts[:split])
        status, result = import_module_status(module_path)
        if status == "env":
            return "env"
        if status != "ok":
            continue
        obj = result
        for attr in parts[split:]:
            if not hasattr(obj, attr):
                return "missing"
            obj = getattr(obj, attr)
        return "ok"
    return "missing"


def test_all_patch_targets_resolve() -> None:
    targets = _patch_target_strings()
    assert targets, "Found no patch() targets -- the AST scan is broken"

    failures: list[str] = []
    env_skipped = 0

    for file, lineno, target in targets:
        status = _resolve(target)
        if status == "ok":
            continue
        if status == "env":
            env_skipped += 1
            continue
        failures.append(f"{file}:{lineno}: patch({target!r}) does not resolve")

    print(
        f"[patch_targets] checked={len(targets)} env_skipped={env_skipped} "
        f"failed={len(failures)}"
    )
    assert not failures, (
        "mock patch targets that do not resolve. A patch target is a module path AND an "
        "identifier hidden in a string -- no import, no type check, and no linter sees "
        "it. It fails only when that one test runs:\n" + "\n".join(sorted(failures))
    )
