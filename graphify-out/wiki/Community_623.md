# Community 623

> 24 nodes · cohesion 0.16

## Key Concepts

- **runDBRestore()** (11 connections) — `tools/ods/cmd/db_restore.go`
- **GitRoot()** (7 connections) — `tools/ods/internal/paths/paths.go`
- **SnapshotsDir()** (7 connections) — `tools/ods/internal/paths/paths.go`
- **db_restore.go** (6 connections) — `tools/ods/cmd/db_restore.go`
- **runDBRestoreSeeded()** (6 connections) — `tools/ods/cmd/db_restore.go`
- **fetch.go** (6 connections) — `tools/ods/internal/s3/fetch.go`
- **NewDBRestoreCommand()** (5 connections) — `tools/ods/cmd/db_restore.go`
- **paths.go** (5 connections) — `tools/ods/internal/paths/paths.go`
- **BackendDir()** (5 connections) — `tools/ods/internal/paths/paths.go`
- **FetchToFile()** (5 connections) — `tools/ods/internal/s3/fetch.go`
- **fetchUnsigned()** (5 connections) — `tools/ods/internal/s3/fetch.go`
- **completeSnapshotFiles()** (4 connections) — `tools/ods/cmd/db_restore.go`
- **resolveInputPath()** (4 connections) — `tools/ods/cmd/db_restore.go`
- **S3URL** (4 connections) — `tools/ods/internal/s3/fetch.go`
- **DBRestoreOptions** (3 connections) — `tools/ods/cmd/db_restore.go`
- **fetchWithAWSCLI()** (3 connections) — `tools/ods/internal/s3/fetch.go`
- **humanizeBytes()** (3 connections) — `tools/ods/internal/s3/fetch.go`
- **ParseS3URL()** (3 connections) — `tools/ods/internal/s3/fetch.go`
- **CopyToContainer()** (2 connections) — `tools/ods/internal/docker/docker.go`
- **DataDir()** (2 connections) — `tools/ods/internal/paths/paths.go`
- **EnsureSnapshotsDir()** (2 connections) — `tools/ods/internal/paths/paths.go`
- **.HTTPEndpoint()** (2 connections) — `tools/ods/internal/s3/fetch.go`
- **Command** (2 connections) — `tools/ods/cmd/db_restore.go`
- **ShellCompDirective** (1 connections) — `tools/ods/cmd/db_restore.go`

## Relationships

- [[Community 310]] (8 shared connections)
- [[Community 821]] (3 shared connections)
- [[Community 513]] (2 shared connections)
- [[Community 820]] (1 shared connections)
- [[Community 606]] (1 shared connections)
- [[Community 286]] (1 shared connections)
- [[Community 258]] (1 shared connections)

## Source Files

- `tools/ods/cmd/db_restore.go`
- `tools/ods/internal/docker/docker.go`
- `tools/ods/internal/paths/paths.go`
- `tools/ods/internal/s3/fetch.go`

## Audit Trail

- EXTRACTED: 77 (75%)
- INFERRED: 26 (25%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*