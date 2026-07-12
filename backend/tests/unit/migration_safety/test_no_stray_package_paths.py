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
_SUFFIXES = (".conf", ".toml", ".ini", ".sh", ".yml", ".yaml", ".template")
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
