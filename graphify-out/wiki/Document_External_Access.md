# Document External Access

> 288 nodes · cohesion 0.02

## Key Concepts

- **IndexingHeartbeatInterface** (347 connections) — `backend/om/indexing/indexing_heartbeat.py`
- **ExternalAccess** (303 connections) — `backend/om/access/models.py`
- **DocExternalAccess** (82 connections) — `backend/om/access/models.py`
- **FetchAllDocumentsIdsFunction** (76 connections) — `backend/om/external_permissions/perm_sync_types.py`
- **FetchAllDocumentsFunction** (70 connections) — `backend/om/external_permissions/perm_sync_types.py`
- **GoogleDriveService** (66 connections) — `backend/om/connectors/google_utils/resources.py`
- **NodeExternalAccess** (35 connections) — `backend/om/access/models.py`
- **GoogleDocsService** (22 connections) — `backend/om/connectors/google_utils/resources.py`
- **sync_params.py** (17 connections) — `backend/om/external_permissions/sync_params.py`
- **convert_drive_item_to_document()** (16 connections) — `backend/om/connectors/google_drive/doc_conversion.py`
- **GoogleDriveManager** (15 connections) — `backend/tests/integration/connector_job_tests/google/google_drive_api_utils.py`
- **generic_doc_sync()** (14 connections) — `backend/om/external_permissions/utils.py`
- **slack_doc_sync()** (14 connections) — `backend/om/external_permissions/slack/doc_sync.py`
- **DocumentSource** (12 connections) — `backend/om/external_permissions/sync_params.py`
- **doc_conversion.py** (12 connections) — `backend/om/connectors/google_drive/doc_conversion.py`
- **gdrive_doc_sync()** (12 connections) — `backend/om/external_permissions/google_drive/doc_sync.py`
- **GoogleDriveService** (11 connections) — `backend/om/connectors/google_drive/doc_conversion.py`
- **folder_doc_sync()** (11 connections) — `backend/om/connectors/folder/doc_sync.py`
- **gmail_doc_sync()** (11 connections) — `backend/om/external_permissions/gmail/doc_sync.py`
- **GoogleDriveFileType** (10 connections) — `backend/om/connectors/google_drive/doc_conversion.py`
- **ConnectorCredentialPair** (10 connections) — `backend/om/external_permissions/google_drive/doc_sync.py`
- **ExternalAccess** (10 connections) — `backend/om/external_permissions/google_drive/doc_sync.py`
- **GoogleDriveConnector** (10 connections) — `backend/om/external_permissions/google_drive/doc_sync.py`
- **GoogleDriveFileType** (10 connections) — `backend/om/external_permissions/google_drive/doc_sync.py`
- **GoogleDriveService** (10 connections) — `backend/om/external_permissions/google_drive/doc_sync.py`
- *... and 263 more nodes in this community*

## Relationships

- [[Connector Indexing Types]] (241 shared connections)
- [[Connector Checkpoint & Slim Docs]] (93 shared connections)
- [[Google Drive Connector]] (40 shared connections)
- [[Connectors (Airtable/Asana)]] (32 shared connections)
- [[Community 142]] (28 shared connections)
- [[Community 199]] (27 shared connections)
- [[Confluence Connector]] (19 shared connections)
- [[Salesforce Connector]] (18 shared connections)
- [[Community 83]] (17 shared connections)
- [[Community 320]] (17 shared connections)
- [[Community 109]] (17 shared connections)
- [[Document Indexing Adapter]] (15 shared connections)

## Source Files

- `backend/om/access/models.py`
- `backend/om/connectors/folder/doc_sync.py`
- `backend/om/connectors/github/utils.py`
- `backend/om/connectors/google_drive/doc_conversion.py`
- `backend/om/connectors/google_drive/file_retrieval.py`
- `backend/om/connectors/google_utils/resources.py`
- `backend/om/connectors/interfaces.py`
- `backend/om/connectors/jira/access.py`
- `backend/om/connectors/sharepoint/connector_utils.py`
- `backend/om/connectors/slack/access.py`
- `backend/om/external_permissions/confluence/doc_sync.py`
- `backend/om/external_permissions/github/doc_sync.py`
- `backend/om/external_permissions/gmail/doc_sync.py`
- `backend/om/external_permissions/google_drive/doc_sync.py`
- `backend/om/external_permissions/google_drive/permission_retrieval.py`
- `backend/om/external_permissions/jira/doc_sync.py`
- `backend/om/external_permissions/perm_sync_types.py`
- `backend/om/external_permissions/sharepoint/doc_sync.py`
- `backend/om/external_permissions/slack/channel_access.py`
- `backend/om/external_permissions/slack/doc_sync.py`

## Audit Trail

- EXTRACTED: 705 (32%)
- INFERRED: 1478 (68%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*