# Community 1032

> 12 nodes · cohesion 0.17

## Key Concepts

- **DatabaseValidators** (7 connections) — `phoenix/scripts/ci/test_helm.py`
- **.aws_iam_auth()** (4 connections) — `phoenix/scripts/ci/test_helm.py`
- **.custom_database_url()** (4 connections) — `phoenix/scripts/ci/test_helm.py`
- **.no_database_url_set()** (4 connections) — `phoenix/scripts/ci/test_helm.py`
- **.postgresql_credentials_set()** (4 connections) — `phoenix/scripts/ci/test_helm.py`
- **.sqlite_in_memory_url()** (4 connections) — `phoenix/scripts/ci/test_helm.py`
- **Validators specific to database configuration (beyond PostgreSQL).** (1 connections) — `phoenix/scripts/ci/test_helm.py`
- **Validate AWS RDS IAM authentication configuration.** (1 connections) — `phoenix/scripts/ci/test_helm.py`
- **Validate that PHOENIX_SQL_DATABASE_URL is set to sqlite:///:memory:** (1 connections) — `phoenix/scripts/ci/test_helm.py`
- **Validate that PostgreSQL credentials are set in ConfigMap (not using database.ur** (1 connections) — `phoenix/scripts/ci/test_helm.py`
- **Validate that PHOENIX_SQL_DATABASE_URL is NOT set (for SQLite persistent mode).** (1 connections) — `phoenix/scripts/ci/test_helm.py`
- **Validate that custom database URL is set.** (1 connections) — `phoenix/scripts/ci/test_helm.py`

## Relationships

- [[Community 581]] (5 shared connections)
- [[Community 511]] (5 shared connections)
- [[Community 421]] (1 shared connections)

## Source Files

- `phoenix/scripts/ci/test_helm.py`

## Audit Trail

- EXTRACTED: 33 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*