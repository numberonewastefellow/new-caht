"""No build/config file may reference a DEAD package root.

This is the gate that was missing. `test_process_config_module_paths` covers
supervisord and `test_deploy_module_paths` covers docker-compose, but nothing covered
Dockerfile `COPY` paths, the ROOT pyproject, or `.sh` scripts inside the package. A
stale `COPY ./onyx/__init__.py` therefore survived the rename and only surfaced when
someone ran `docker compose build` on the model_server target -- no Python import, no
test, would ever have flagged it.

Rule: for every git-tracked build/config file, any reference to a package path or module
path rooted at a NON-LIVE candidate root (e.g. `onyx` once the package is `om`) is a
defect. Live-root references are fine; that is the point of the rename.

Everything that legitimately keeps the old word is enumerated in PRESERVE below -- these
are external contracts, not package paths, and each is there for a stated reason.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

from tests.unit.migration_safety.conftest import _CANDIDATE_ROOTS
from tests.unit.migration_safety.conftest import repo_root
from tests.unit.migration_safety.conftest import ROOT_PACKAGE

# Build/config surfaces where a package path can hide. Deliberately includes Dockerfiles
# and the ROOT pyproject -- the two the previous sweep missed.
# NOTE: filesystem walk, not `git ls-files` -- git is NOT installed in the backend image,
# and a gate that silently skips in the environment it is meant to guard is no gate.
#
# `.py` is in this list for a reason. A Python file can hold a package path that is NOT
# an import: a filesystem path assembled from string parts. Two such bugs have already
# slipped through -- `os.path.join(os.getcwd(), "onyx", "document_index", ...)` and the
# `--template` / `--cloud-services-template` argparse defaults in
# scripts/debugging/onyx_vespa_schemas.py. No import walk can see either: the module
# imports fine and only blows up with FileNotFoundError when that code path runs.
_SUFFIXES = (".conf", ".toml", ".ini", ".sh", ".yml", ".yaml", ".template", ".py")
_NAME_PREFIXES = ("Dockerfile",)

_SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".venv",
    ".next",
    "generated",
    "dist",
    "build",
}

# Substrings that mean "this is NOT a package path". Each is an external contract.
PRESERVE = (
    "onyxdotapp/",  # docker image names (registry contract)
    "onyx-dot-app/",  # github repo slug in URLs
    "hub.docker.com",  # image URL
    "onyx.app",  # docs/email URLs
    "github.com",  # any repo URL
    "/var/log/onyx",  # container log dir (owned by the onyx unix user)
    "onyx:onyx",  # unix user:group in COPY --chown
    "groupadd",  # unix user creation
    "useradd",
    "onyx-sandboxes",  # k8s namespace (selector contract)
    "managed-by",  # k8s label value
    "ONYX_",  # env-var KEYS (deploy contract)
    "onyx_",  # cookie names (onyx_tid, onyx_anonymous_user)
    "onyx:celery",  # redis namespace
    "/onyx/deployment",  # a comment about the repo checkout dir, not the package
)

# A path/module reference rooted at <root>: ./<root>/  /app/<root>  backend/<root>
# <root>/<something>  celery -A <root>.  uvicorn <root>.  python -m <root>.
def _patterns(root: str) -> list[re.Pattern[str]]:
    r = re.escape(root)
    return [
        re.compile(rf"\./{r}/"),
        re.compile(rf"/app/{r}\b"),
        re.compile(rf"backend/{r}\b"),
        re.compile(rf"(?<![\w./-]){r}/[a-z_]+"),
        re.compile(rf"celery\s+-A\s+{r}\."),
        re.compile(rf"uvicorn\s+{r}\."),
        re.compile(rf"python\s+-m\s+{r}\."),
    ]


def _iter_py_string_literals(text: str) -> list[tuple[int, str]]:
    """(lineno, value) for every string literal in a .py file, EXCLUDING docstrings.

    Comments and docstrings are prose -- they mention the old name legitimately (this
    very suite's docstrings do). Flagging them is noise that would push someone to
    delete the gate. What actually breaks production is an *executable* string: an
    argparse default, an os.path.join component, a config default path. So parse and
    look at real string constants only.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))

    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            out.append((node.lineno, node.value))
    return out


# Calls that assemble a filesystem path out of separate components.
_JOIN_FUNCS = {"join", "joinpath", "Path", "PurePath"}


def _iter_path_component_strings(text: str) -> list[tuple[int, str]]:
    """(lineno, value) for string args passed to a path-JOINING call.

    `os.path.join(os.getcwd(), "onyx", "document_index", ...)` hides the package name as
    a bare component with no slash, so no path regex can see it -- this was a real
    Stage-1 bug (Vespa schema dir). But a bare "onyx" string on its own is NOT evidence
    of a path: it is legitimately data (connector project names, this suite's own
    _CANDIDATE_ROOTS, test fixtures). The join-call context is what makes it a path.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        fname = getattr(func, "attr", None) or getattr(func, "id", None)
        if fname not in _JOIN_FUNCS:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                out.append((arg.lineno, arg.value))
    return out


def _config_files() -> list:
    """Walk with os.walk so we can PRUNE big dirs in place.

    rglob("*") descends into node_modules/.git before filtering, which takes ~9 minutes
    over a bind-mounted repo. Pruning dirnames keeps this ~1s.
    """
    root = repo_root()
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if name.endswith(_SUFFIXES) or name.startswith(_NAME_PREFIXES):
                found.append(Path(dirpath) / name)
    return found


def test_no_references_to_a_dead_package_root() -> None:
    dead_roots = [r for r in _CANDIDATE_ROOTS if r != ROOT_PACKAGE]
    if not dead_roots:
        pytest.skip("no non-live candidate roots to check")

    root = repo_root()
    offenders: list[str] = []
    scanned = 0

    for path in _config_files():
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1

        if path.suffix == ".py":
            # Executable string literals only -- never comments/docstrings (prose).
            for lineno, value in _iter_py_string_literals(text):
                if any(tok in value for tok in PRESERVE):
                    continue
                for dead in dead_roots:
                    if dead in value and any(
                        pat.search(value) for pat in _patterns(dead)
                    ):
                        offenders.append(f"{rel}:{lineno}: {value!r}")
                        break
            # A path assembled from components -- os.path.join(cwd, "onyx", "x") --
            # where the root is a bare arg with no slash for a regex to latch onto.
            for lineno, value in _iter_path_component_strings(text):
                if value in dead_roots:
                    offenders.append(
                        f"{rel}:{lineno}: dead root {value!r} as a path component"
                    )
            continue

        for lineno, line in enumerate(text.splitlines(), 1):
            if any(tok in line for tok in PRESERVE):
                continue
            for dead in dead_roots:
                if dead not in line:
                    continue
                for pat in _patterns(dead):
                    if pat.search(line):
                        offenders.append(f"{rel}:{lineno}: {line.strip()}")
                        break

    assert scanned > 20, f"Expected to scan many config files, only saw {scanned}"
    assert not offenders, (
        f"Build/config files still point at a dead package root (live root is "
        f"{ROOT_PACKAGE!r}). These do not fail any import -- they fail at "
        f"docker build / container start:\n" + "\n".join(sorted(set(offenders)))
    )
