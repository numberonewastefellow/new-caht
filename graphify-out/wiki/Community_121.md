# Community 121

> 101 nodes · cohesion 0.04

## Key Concepts

- **PostgresBackedFileStore** (45 connections) — `backend/om/file_store/postgres_file_store.py`
- **S3BackedFileStore** (33 connections) — `backend/om/file_store/file_store.py`
- **FileWithMimeType** (25 connections) — `backend/om/utils/file.py`
- **get_session_with_current_tenant_if_none()** (18 connections) — `backend/om/db/engine/sql_engine.py`
- **.save_file()** (13 connections) — `backend/om/file_store/postgres_file_store.py`
- **get_filerecord_by_file_id()** (11 connections) — `backend/om/db/file_record.py`
- **Session** (10 connections) — `backend/om/file_store/file_store.py`
- **Session** (10 connections) — `backend/om/file_store/postgres_file_store.py`
- **._get_s3_client()** (10 connections) — `backend/om/file_store/file_store.py`
- **.save_file()** (10 connections) — `backend/om/file_store/file_store.py`
- **upsert_filerecord()** (9 connections) — `backend/om/db/file_record.py`
- **.change_file_id()** (9 connections) — `backend/om/file_store/file_store.py`
- **.read_file()** (9 connections) — `backend/om/file_store/postgres_file_store.py`
- **file_store.py** (8 connections) — `backend/om/file_store/file_store.py`
- **postgres_file_store.py** (8 connections) — `backend/om/file_store/postgres_file_store.py`
- **_get_raw_connection()** (8 connections) — `backend/om/file_store/postgres_file_store.py`
- **.delete_file()** (8 connections) — `backend/om/file_store/postgres_file_store.py`
- **IO** (7 connections) — `backend/om/file_store/file_store.py`
- **IO** (7 connections) — `backend/om/file_store/postgres_file_store.py`
- **.read_file()** (7 connections) — `backend/om/file_store/file_store.py`
- **.change_file_id()** (7 connections) — `backend/om/file_store/postgres_file_store.py`
- **Session** (6 connections) — `backend/om/db/file_record.py`
- **FileOrigin** (6 connections) — `backend/om/file_store/file_store.py`
- **file_record.py** (6 connections) — `backend/om/db/file_record.py`
- **delete_filerecord_by_file_id()** (6 connections) — `backend/om/db/file_record.py`
- *... and 76 more nodes in this community*

## Relationships

- [[Community 111]] (19 shared connections)
- [[Community 331]] (12 shared connections)
- [[Community 447]] (10 shared connections)
- [[Community 471]] (10 shared connections)
- [[Community 244]] (7 shared connections)
- [[Salesforce Connector]] (5 shared connections)
- [[Community 332]] (4 shared connections)
- [[Document Indexing Adapter]] (4 shared connections)
- [[Community 73]] (3 shared connections)
- [[Community 161]] (3 shared connections)
- [[Backend Agent/API Test Fixtures]] (2 shared connections)
- [[Agent Tracing Processor]] (1 shared connections)

## Source Files

- `backend/om/db/engine/sql_engine.py`
- `backend/om/db/file_record.py`
- `backend/om/file_store/file_store.py`
- `backend/om/file_store/postgres_file_store.py`
- `backend/om/utils/file.py`
- `backend/tests/unit/file_store/test_file_store.py`

## Audit Trail

- EXTRACTED: 332 (64%)
- INFERRED: 189 (36%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*