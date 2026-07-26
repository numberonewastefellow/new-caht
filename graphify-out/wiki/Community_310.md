# Community 310

> 46 nodes · cohesion 0.08

## Key Concepts

- **alembic.go** (14 connections) — `tools/ods/internal/alembic/alembic.go`
- **runDBDump()** (10 connections) — `tools/ods/cmd/db_dump.go`
- **docker.go** (10 connections) — `tools/ods/internal/docker/docker.go`
- **Run()** (9 connections) — `tools/ods/internal/alembic/alembic.go`
- **Schema** (8 connections) — `tools/ods/internal/alembic/alembic.go`
- **FindPostgresContainer()** (8 connections) — `tools/ods/internal/docker/docker.go`
- **runDBDrop()** (7 connections) — `tools/ods/cmd/db_drop.go`
- **Config** (7 connections) — `tools/ods/internal/postgres/postgres.go`
- **NewConfigFromEnv()** (7 connections) — `tools/ods/internal/postgres/postgres.go`
- **runLocally()** (6 connections) — `tools/ods/internal/alembic/alembic.go`
- **db_dump.go** (5 connections) — `tools/ods/cmd/db_dump.go`
- **buildAlembicEnv()** (4 connections) — `tools/ods/internal/alembic/alembic.go`
- **Current()** (4 connections) — `tools/ods/internal/alembic/alembic.go`
- **detectPostgresHost()** (4 connections) — `tools/ods/internal/alembic/alembic.go`
- **History()** (4 connections) — `tools/ods/internal/alembic/alembic.go`
- **runViaDockerExec()** (4 connections) — `tools/ods/internal/alembic/alembic.go`
- **shouldUseDockerExec()** (4 connections) — `tools/ods/internal/alembic/alembic.go`
- **NewDBDropCommand()** (4 connections) — `tools/ods/cmd/db_drop.go`
- **NewDBDumpCommand()** (4 connections) — `tools/ods/cmd/db_dump.go`
- **ExecWithEnv()** (4 connections) — `tools/ods/internal/docker/docker.go`
- **IsPortExposed()** (4 connections) — `tools/ods/internal/docker/docker.go`
- **Downgrade()** (3 connections) — `tools/ods/internal/alembic/alembic.go`
- **FindAlembicBinary()** (3 connections) — `tools/ods/internal/alembic/alembic.go`
- **findAlembicContainer()** (3 connections) — `tools/ods/internal/alembic/alembic.go`
- **Upgrade()** (3 connections) — `tools/ods/internal/alembic/alembic.go`
- *... and 21 more nodes in this community*

## Relationships

- [[Community 623]] (8 shared connections)
- [[Community 820]] (4 shared connections)
- [[Community 286]] (1 shared connections)
- [[Community 606]] (1 shared connections)

## Source Files

- `tools/ods/cmd/db_drop.go`
- `tools/ods/cmd/db_dump.go`
- `tools/ods/internal/alembic/alembic.go`
- `tools/ods/internal/docker/docker.go`
- `tools/ods/internal/postgres/postgres.go`

## Audit Trail

- EXTRACTED: 141 (78%)
- INFERRED: 39 (22%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*