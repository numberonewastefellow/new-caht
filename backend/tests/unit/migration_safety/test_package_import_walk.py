"""Walk-import every module in the root package and fail on namespace breakage.

Static `import onyx.x` breakage fails loudly at startup; this test surfaces it in
CI before deploy. It focuses on RENAME-related failures: a module that fails to
import with a ModuleNotFoundError/ImportError naming a root package (`onyx`/`om`/
the `ee.` mirror) is a missed rename and hard-fails. Other import errors (e.g. a
genuinely optional dependency) are reported but not treated as rename failures --
the golden-snapshot tier is what proves the importable SET is unchanged.
"""

from __future__ import annotations

import importlib

from tests.unit.migration_safety.conftest import is_namespace_import_error
from tests.unit.migration_safety.conftest import iter_package_modules
from tests.unit.migration_safety.conftest import package_source_root
from tests.unit.migration_safety.conftest import ROOT_PACKAGE


def _walk_module_names() -> list[str]:
    """All modules under the root package + the EE mirror (if present).

    File-based (see conftest.iter_package_modules) because pkgutil skips the many
    namespace-package dirs here (e.g. the whole background/celery tree).
    """
    names = iter_package_modules(ROOT_PACKAGE)
    names += iter_package_modules("ee")  # EE mirror; empty list once EE is removed
    return names


def test_full_package_imports_without_namespace_errors() -> None:
    """Every submodule imports; no leftover onyx/om/ee namespace import error.

    Namespace errors (missing top module in {onyx, om, ee}) hard-fail. Missing
    third-party deps in a partial env are reported but tolerated -- the
    golden-snapshot tier proves the importable SET is unchanged.
    """
    assert package_source_root().exists()

    namespace_failures: list[str] = []
    env_failures: list[str] = []

    for name in _walk_module_names():
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - classify, don't abort the walk
            entry = f"{name}: {type(exc).__name__}: {exc}"
            if is_namespace_import_error(exc):
                namespace_failures.append(entry)
            else:
                env_failures.append(entry)

    if env_failures:
        print(
            f"\n[import-walk] {len(env_failures)} non-namespace (env) import errors "
            "tolerated:\n" + "\n".join(env_failures)
        )

    assert not namespace_failures, (
        "Modules failed to import with a namespace/rename-related error "
        f"(root={ROOT_PACKAGE!r}):\n" + "\n".join(namespace_failures)
    )
