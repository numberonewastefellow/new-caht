"""Every `from tests.…` import must resolve to a real path in the test tree.

This closes a hole that stayed open for the whole rename. The Stage-1 rename rewrote
module paths `onyx.*` -> `om.*` everywhere, and that swept up intra-test imports too:

    from tests.unit.onyx.connectors.utils import load_everything_from_checkpoint_connector
                    ^^^^                     became      tests.unit.om.connectors.utils

...but the test DIRECTORY was still `tests/unit/onyx/`. So 12 test modules imported a
package that did not exist and died at COLLECTION. And a collection error is invisible in
exactly the wrong way: pytest reports it as an error on that file, the other 1500 tests
still pass, and nobody notices that a dozen files stopped running entirely. It survived
the rename, a full deploy, and the whole backend EE removal.

Nothing else in this suite could see it: the import-walk and the golden snapshot walk the
`om` PACKAGE, not `tests/`. So check the test tree explicitly.

AST-only -- resolves `from tests.x.y import z` against the filesystem. It does not import
anything, so a missing third-party dep cannot make it flake.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.unit.migration_safety.conftest import backend_root


def _test_module_exists(dotted: str, backend: Path) -> bool:
    """`tests.unit.om.db.conftest` -> tests/unit/om/db/conftest.py OR .../conftest/."""
    rel = Path(*dotted.split("."))
    return (backend / rel).with_suffix(".py").exists() or (backend / rel).is_dir()


def test_intra_test_imports_resolve() -> None:
    backend = backend_root()
    tests_dir = backend / "tests"
    offenders: list[str] = []
    scanned = 0

    for path in sorted(tests_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        scanned += 1

        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            # level > 0 is a relative import -- not our concern.
            if node.level or not node.module:
                continue
            if node.module != "tests" and not node.module.startswith("tests."):
                continue
            if not _test_module_exists(node.module, backend):
                offenders.append(
                    f"{path.relative_to(backend).as_posix()}:{node.lineno}: "
                    f"imports {node.module!r}, which does not exist on disk"
                )

    assert scanned > 100, f"Expected to scan the test tree, only saw {scanned} files"
    assert not offenders, (
        "Test modules import a `tests.…` path that does not exist. These do not fail a "
        "test -- they fail COLLECTION, so the file silently stops running while the rest "
        "of the suite stays green:\n" + "\n".join(offenders)
    )
