# Community 817

> 17 nodes · cohesion 0.15

## Key Concepts

- **backend_root()** (9 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **iter_source_files()** (8 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **package_source_root()** (7 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Path** (6 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **iter_package_modules()** (5 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **test_full_package_imports_without_namespace_errors()** (5 connections) — `backend/tests/unit/migration_safety/test_package_import_walk.py`
- **_walk_module_names()** (4 connections) — `backend/tests/unit/migration_safety/test_package_import_walk.py`
- **test_dockerfile_copy_sources_exist()** (3 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **test_package_import_walk.py** (3 connections) — `backend/tests/unit/migration_safety/test_package_import_walk.py`
- **Every importable dotted module under a package, INCLUDING namespace dirs.      `** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Every .py file under the root package (excludes __pycache__).** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Filesystem dir of the root package (e.g. backend/onyx or backend/om).** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **The `backend/` dir (parent of the root package).** (1 connections) — `backend/tests/unit/migration_safety/conftest.py`
- **Every `COPY <src>` in the backend Dockerfiles must name a path that EXISTS.** (1 connections) — `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- **Walk-import every module in the root package and fail on namespace breakage.  St** (1 connections) — `backend/tests/unit/migration_safety/test_package_import_walk.py`
- **All modules under the root package + the EE mirror (if present).      File-based** (1 connections) — `backend/tests/unit/migration_safety/test_package_import_walk.py`
- **Every submodule imports; no leftover onyx/om/ee namespace import error.      Nam** (1 connections) — `backend/tests/unit/migration_safety/test_package_import_walk.py`

## Relationships

- [[Community 526]] (5 shared connections)
- [[Community 968]] (3 shared connections)
- [[Community 923]] (3 shared connections)
- [[Community 1027]] (2 shared connections)
- [[Community 1409]] (1 shared connections)
- [[Community 1450]] (1 shared connections)
- [[Community 1199]] (1 shared connections)
- [[Community 1200]] (1 shared connections)
- [[Salesforce Connector]] (1 shared connections)

## Source Files

- `backend/tests/unit/migration_safety/conftest.py`
- `backend/tests/unit/migration_safety/test_no_stray_package_paths.py`
- `backend/tests/unit/migration_safety/test_package_import_walk.py`

## Audit Trail

- EXTRACTED: 42 (72%)
- INFERRED: 16 (28%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*