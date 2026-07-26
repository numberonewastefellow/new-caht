# Google Drive Connector

> 163 nodes · cohesion 0.03

## Key Concepts

- **GoogleDriveConnector** (54 connections) — `backend/om/connectors/google_drive/connector.py`
- **GoogleDriveCheckpoint** (34 connections) — `backend/om/connectors/google_drive/connector.py`
- **SecondsSinceUnixEpoch** (32 connections) — `backend/om/connectors/google_drive/connector.py`
- **RetrievedDriveFile** (28 connections) — `backend/om/connectors/google_drive/connector.py`
- **DriveFileFieldType** (27 connections) — `backend/om/connectors/google_drive/connector.py`
- **connector.py** (20 connections) — `backend/om/connectors/google_drive/connector.py`
- **execute_paginated_retrieval()** (18 connections) — `backend/om/connectors/google_utils/google_utils.py`
- **get_drive_service()** (18 connections) — `backend/om/connectors/google_utils/resources.py`
- **file_retrieval.py** (17 connections) — `backend/om/connectors/google_drive/file_retrieval.py`
- **._get_new_ancestors_for_files()** (13 connections) — `backend/om/connectors/google_drive/connector.py`
- **GoogleDriveFileType** (12 connections) — `backend/om/connectors/google_drive/file_retrieval.py`
- **._extract_docs_from_google_drive()** (12 connections) — `backend/om/connectors/google_drive/connector.py`
- **._manage_service_account_retrieval()** (12 connections) — `backend/om/connectors/google_drive/connector.py`
- **gdrive_group_sync()** (12 connections) — `backend/om/external_permissions/google_drive/group_sync.py`
- **Resource** (11 connections) — `backend/om/connectors/google_drive/file_retrieval.py`
- **._manage_oauth_retrieval()** (11 connections) — `backend/om/connectors/google_drive/connector.py`
- **get_all_files_in_my_drive_and_shared()** (11 connections) — `backend/om/connectors/google_drive/file_retrieval.py`
- **group_sync.py** (11 connections) — `backend/om/external_permissions/google_drive/group_sync.py`
- **resources.py** (11 connections) — `backend/om/connectors/google_utils/resources.py`
- **_get_google_service()** (11 connections) — `backend/om/connectors/google_utils/resources.py`
- **SecondsSinceUnixEpoch** (10 connections) — `backend/om/connectors/google_drive/file_retrieval.py`
- **._impersonate_user_for_retrieval()** (10 connections) — `backend/om/connectors/google_drive/connector.py`
- **._extract_slim_docs_from_google_drive()** (9 connections) — `backend/om/connectors/google_drive/connector.py`
- **get_all_files_for_oauth()** (9 connections) — `backend/om/connectors/google_drive/file_retrieval.py`
- **_get_files_in_parent()** (9 connections) — `backend/om/connectors/google_drive/file_retrieval.py`
- *... and 138 more nodes in this community*

## Relationships

- [[Connector Indexing Types]] (121 shared connections)
- [[Document External Access]] (40 shared connections)
- [[Connector Checkpoint & Slim Docs]] (23 shared connections)
- [[Salesforce Connector]] (6 shared connections)
- [[Community 320]] (5 shared connections)
- [[Community 72]] (3 shared connections)
- [[Community 303]] (2 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 360]] (1 shared connections)
- [[Community 142]] (1 shared connections)
- [[Community 915]] (1 shared connections)
- [[Community 654]] (1 shared connections)

## Source Files

- `backend/om/connectors/google_drive/connector.py`
- `backend/om/connectors/google_drive/file_retrieval.py`
- `backend/om/connectors/google_utils/google_utils.py`
- `backend/om/connectors/google_utils/resources.py`
- `backend/om/external_permissions/google_drive/folder_retrieval.py`
- `backend/om/external_permissions/google_drive/group_sync.py`
- `backend/tests/daily/connectors/google_drive/test_link_visibility_filter.py`

## Audit Trail

- EXTRACTED: 702 (76%)
- INFERRED: 220 (24%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*