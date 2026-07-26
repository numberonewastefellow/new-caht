# Community 923

> 14 nodes · cohesion 0.20

## Key Concepts

- **test_no_stray_package_paths.py** (8 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **repo_root()** (6 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **test_no_references_to_a_dead_package_root()** (6 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **_config_files()** (4 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **_iter_path_component_strings()** (3 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **_iter_py_string_literals()** (3 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **_patterns()** (3 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **Pattern** (1 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **The repository root (parent of `backend/`).** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **No build/config file may reference a DEAD package root.  This is the gate that w** (1 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **(lineno, value) for string args passed to a path-JOINING call.      `os.path.joi** (1 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **Walk with os.walk so we can PRUNE big dirs in place.      rglob("*") descends in** (1 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **# NOTE: filesystem walk, not `git ls-files` -- git is NOT installed in the backe** (1 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **(lineno, value) for every string literal in a .py file, EXCLUDING docstrings.** (1 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`

## Relationships

- [[Community 817]] (3 shared connections)
- [[Community 526]] (1 shared connections)

## Source Files

- `backend/tests/unit/migration_safety/conftest.py`
- `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`

## Audit Trail

- EXTRACTED: 36 (90%)
- INFERRED: 4 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*