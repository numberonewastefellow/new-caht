"""Shared fixtures/helpers for the migration-safety suite.

This suite verifies that every STATIC and STRING/dynamic module reference in the
backend resolves. It is an *invariant* suite: it must pass on the current tree
(baseline) and again after the `onyx` -> `om` rename + EE removal. Any string that
was missed by the rename turns a test red.

IMPORTANT: everything here is written to be rename-agnostic. The root package name
is auto-detected (`onyx` today, `om` post-rename), and the AST-driven tests read
whatever the current source says. There is nothing to hand-edit after the rename.
"""

from __future__ import annotations

import ast
import importlib
import os
from pathlib import Path
from types import ModuleType
from typing import Iterator

# --- Quiet telemetry BEFORE any backend module is imported. ---------------------
# This used to also force ENABLE_PAID_ENTERPRISE_EDITION_FEATURES=true, to pin the EE
# resolution path for the golden snapshot: the baseline had to capture TODAY'S EE-ON
# runtime inventory (every EE celery task, every EE beat entry), because snapshotting
# with EE OFF would have captured the MIT-only subset and happily "passed" while the
# merged tree silently dropped EE tasks on the floor.
#
# That flag is gone. There is one edition and it is always on, so there is no longer an
# EE/non-EE resolution path to pin -- the baseline it produced (980 modules / 55 celery
# tasks / 22 beat tasks) is simply what the tree does now.
os.environ["DISABLE_TELEMETRY"] = "true"

import pytest  # noqa: E402
from celery import Celery  # noqa: E402


# --- Root package auto-detection (rename-agnostic) ------------------------------
_CANDIDATE_ROOTS = ("onyx", "om")


def _detect_root_package() -> str:
    for name in _CANDIDATE_ROOTS:
        try:
            importlib.import_module(name)
            return name
        except ImportError:
            continue
    raise RuntimeError(
        f"None of the candidate root packages {_CANDIDATE_ROOTS} could be imported. "
        "Add the new name to _CANDIDATE_ROOTS in conftest.py."
    )


ROOT_PACKAGE = _detect_root_package()


def package_source_root() -> Path:
    """Filesystem dir of the root package (e.g. backend/onyx or backend/om)."""
    pkg = importlib.import_module(ROOT_PACKAGE)
    pkg_file = getattr(pkg, "__file__", None)
    if not pkg_file:
        raise RuntimeError(f"Cannot locate __file__ for package {ROOT_PACKAGE!r}")
    return Path(pkg_file).parent


def backend_root() -> Path:
    """The `backend/` dir (parent of the root package)."""
    return package_source_root().parent


def repo_root() -> Path:
    """The repository root (parent of `backend/`)."""
    return backend_root().parent


def path_to_module(rel_path: str) -> str:
    """Convert a repo/backend-relative script path to a dotted module.

    e.g. "onyx/utils/supervisord_watchdog.py" -> "om.utils.supervisord_watchdog".
    """
    p = rel_path.strip().replace("\\", "/")
    if p.endswith(".py"):
        p = p[: -len(".py")]
    return p.strip("/").replace("/", ".")


def strip_root(dotted: str) -> str:
    """Normalize a dotted path so the tree compares equal ACROSS BOTH migrations.

    Two normalizations, one for each migration:

    1. Rename (`onyx` -> `om`): strip the root package, so `onyx.x` and `om.x` both
       become `<root>.x`.

    2. EE removal (`ee.<root>.x` -> `<root>.x`): COLLAPSE the EE mirror onto its MIT
       path. This is not cosmetic -- it *models the merge*. EE removal moves
       `ee/om/db/license.py` to `om/db/license.py`, so before/after must normalize to
       the same `<root>.db.license`. EE OVERRIDES (a file present in both trees, e.g.
       `access/access.py`) collapse onto the single MIT entry they merge into.

    The payoff: the module inventory becomes a ZERO-DIFF invariant across EE removal.
    Any EE module that fails to make it into the merged tree -- dropped, mis-pathed,
    or left behind -- shows up as a `removed=[...]` diff instead of silently vanishing.
    """
    for root in _CANDIDATE_ROOTS:
        # EE mirror first: `ee.om.x` must not be mistaken for anything else. Collapse
        # it onto the MIT path it merges into.
        if dotted == "ee." + root:
            return "<root>"
        if dotted.startswith("ee." + root + "."):
            return "<root>." + dotted[len("ee." + root + ".") :]
        if dotted == root:
            return "<root>"
        if dotted.startswith(root + "."):
            return "<root>." + dotted[len(root) + 1 :]
    return dotted


# --- Import-error classification ------------------------------------------------
# The suite only asserts on NAMESPACE resolution (the rename/EE-removal concern).
# A failure whose missing top-level module is a root/ee namespace is a real defect;
# anything else (a third-party dependency absent from a partial env) is an
# environment gap that must be skipped, never failed -- otherwise the suite is
# unrunnable outside the full backend image.
_NAMESPACE_ROOTS = {"onyx", "om", "ee"}


def missing_top_module(exc: BaseException) -> str | None:
    name = getattr(exc, "name", None)
    if not name:
        return None
    return name.split(".")[0]


def is_namespace_import_error(exc: BaseException) -> bool:
    if not isinstance(exc, ImportError):
        return False
    return missing_top_module(exc) in _NAMESPACE_ROOTS


def import_module_status(module_path: str) -> tuple[str, object]:
    """Return ("ok", module) | ("namespace", exc) | ("env", exc).

    "namespace" = a rename/EE defect (fail on it). "env" = missing third-party dep
    or import-time side effect absent in this environment (skip on it).
    """
    try:
        return "ok", importlib.import_module(module_path)
    except ImportError as exc:
        return ("namespace" if is_namespace_import_error(exc) else "env"), exc
    except Exception as exc:  # noqa: BLE001 - import-time RuntimeError/etc -> env
        return "env", exc


def _mit_and_ee_variants(module: str) -> list[str]:
    """Candidate real modules for a versioned string.

    A `fetch_versioned_implementation` string names the MIT module, but the impl may
    live ONLY in the EE mirror (`ee.<module>`) -- e.g. external_permissions,
    enterprise_settings. So "resolves" means the MIT path OR its EE mirror imports.
    Post-migration (EE merged into the renamed root), only the MIT path exists, which
    still passes; a genuine missed rename leaves neither and fails.
    """
    variants = [module]
    for root in ("onyx", "om"):
        if module.startswith(root + "."):
            variants.append("ee." + module)
        if module.startswith("ee." + root + "."):
            variants.append(module[len("ee.") :])
    return variants


def resolve_symbol(module: str, attribute: str | None = None) -> str:
    """Return "ok" | "missing_attr" | "namespace" | "env" using MIT-or-EE variants."""
    saw_env = False
    saw_import_ok = False
    for variant in _mit_and_ee_variants(module):
        status, result = import_module_status(variant)
        if status == "ok":
            saw_import_ok = True
            if attribute is None or hasattr(result, attribute):
                return "ok"
        elif status == "env":
            saw_env = True
    # env takes priority: if any variant failed to load here (partial env), we cannot
    # claim the attribute is truly missing -- the variant that owns it (often the EE
    # mirror) may just be unimportable locally. In the full image it resolves to "ok".
    if saw_env:
        return "env"
    if saw_import_ok:
        return "missing_attr"  # imported everywhere possible, attribute absent
    return "namespace"


# Non-importable scaffolding shipped inside the package (standalone scripts/templates
# for the sandbox container). Excluded from mypy in pyproject.toml for the same reason.
_NON_IMPORTABLE_SUBPATHS = (
    "server/features/build/sandbox/kubernetes/docker/skills/",
    "server/features/build/sandbox/kubernetes/docker/templates/",
)


def iter_package_modules(root_pkg: str) -> list[str]:
    """Every importable dotted module under a package, INCLUDING namespace dirs.

    `pkgutil.walk_packages` only recurses into dirs that have `__init__.py`. Large parts
    of this codebase are implicit namespace packages with NO `__init__.py` -- notably the
    whole `background/celery/**` tree (apps, configs, tasks, versioned_apps). Walking with
    pkgutil silently MISSES ~339 files there, i.e. exactly the code this migration is most
    likely to break. So enumerate .py files on disk and derive module names instead.
    """
    try:
        pkg = importlib.import_module(root_pkg)
    except ImportError:
        return []
    pkg_file = getattr(pkg, "__file__", None)
    if not pkg_file:
        return []
    root_dir = Path(pkg_file).parent

    modules: list[str] = []
    for path in sorted(root_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root_dir).as_posix()
        if any(rel.startswith(skip) for skip in _NON_IMPORTABLE_SUBPATHS):
            continue
        if rel.endswith("__init__.py"):
            rel = rel[: -len("/__init__.py")] if "/" in rel else ""
            if not rel:
                continue  # the package root itself
            dotted = f"{root_pkg}." + rel.replace("/", ".")
        else:
            dotted = f"{root_pkg}." + rel[: -len(".py")].replace("/", ".")
        modules.append(dotted)
    return modules


def iter_source_files() -> Iterator[Path]:
    """Every .py file under the root package (excludes __pycache__)."""
    for path in package_source_root().rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def parse_source(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None


# --- Celery helpers -------------------------------------------------------------
# The runtime entrypoints referenced by supervisord.conf / `celery -A` are the
# versioned_apps stubs; each resolves its real Celery app via a STRING module path.
VERSIONED_APP_MODULES = [
    "background.celery.versioned_apps.primary",
    "background.celery.versioned_apps.light",
    "background.celery.versioned_apps.heavy",
    "background.celery.versioned_apps.background",
    "background.celery.versioned_apps.monitoring",
    "background.celery.versioned_apps.docprocessing",
    "background.celery.versioned_apps.docfetching",
    "background.celery.versioned_apps.user_file_processing",
    "background.celery.versioned_apps.beat",
]


def qualified(suffix: str) -> str:
    """Prefix a package-relative dotted path with the detected root."""
    return f"{ROOT_PACKAGE}.{suffix}"


def celery_app_from_module(mod: ModuleType) -> Celery | None:
    """Extract the Celery instance a versioned-app stub exposes.

    Stubs expose the app either as a module attribute (`app` / `celery_app`) or via
    a `get_app()` factory -- handle all shapes so the test is not brittle.
    """
    for attr in ("app", "celery_app"):
        obj = getattr(mod, attr, None)
        if isinstance(obj, Celery):
            return obj
    getter = getattr(mod, "get_app", None)
    if callable(getter):
        obj = getter()
        if isinstance(obj, Celery):
            return obj
    return None


@pytest.fixture(scope="session")
def worker_celery_apps() -> list[tuple[str, Celery]]:
    """Import every versioned-app stub, finalize it (forces autodiscovery imports),
    and return (module_suffix, Celery) pairs. Raises if a stub yields no app."""
    apps: list[tuple[str, Celery]] = []
    for suffix in VERSIONED_APP_MODULES:
        status, result = import_module_status(qualified(suffix))
        if status == "namespace":
            raise AssertionError(
                f"Namespace/rename error importing {qualified(suffix)}: {result}"
            )
        if status == "env":
            pytest.skip(
                f"Env gap importing {qualified(suffix)} (missing dep): {result}. "
                "Run inside the full backend image for the real baseline."
            )
        mod = result  # type: ignore[assignment]
        app = celery_app_from_module(mod)  # type: ignore[arg-type]
        assert app is not None, f"No Celery app exposed by {qualified(suffix)}"
        try:
            # `autodiscover_tasks(force=False)` does NOT import on finalize() -- it
            # defers to the `import_modules` signal, which only fires on worker boot.
            # `import_default_modules()` sends that signal, which is what actually
            # imports every STRING module path in the autodiscover lists (the whole
            # point of this suite). Without it the task registry comes back empty.
            app.loader.import_default_modules()
            app.finalize()
        except Exception as exc:  # noqa: BLE001
            if is_namespace_import_error(exc):
                raise AssertionError(
                    f"Namespace/rename error discovering tasks for "
                    f"{qualified(suffix)}: {exc}"
                ) from exc
            pytest.skip(f"Env gap discovering tasks for {qualified(suffix)}: {exc}")
        apps.append((suffix, app))
    return apps


@pytest.fixture(scope="session")
def union_task_registry(worker_celery_apps: list[tuple[str, Celery]]) -> set[str]:
    """Union of registered task names across all finalized worker apps."""
    names: set[str] = set()
    for _suffix, app in worker_celery_apps:
        names.update(app.tasks.keys())
    return names
