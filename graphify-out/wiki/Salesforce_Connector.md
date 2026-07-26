# Salesforce Connector

> 182 nodes · cohesion 0.02

## Key Concepts

- **RuntimeError** (304 connections)
- **OmSalesforceSQLite** (45 connections) — `backend/om/connectors/salesforce/sqlite_functions.py`
- **OmSalesforce** (33 connections) — `backend/om/connectors/salesforce/onyx_salesforce.py`
- **SalesforceConnector** (26 connections) — `backend/om/connectors/salesforce/connector.py`
- **ImapConnector** (17 connections) — `backend/om/connectors/imap/connector.py`
- **GenerateDocumentsOutput** (14 connections) — `backend/om/connectors/salesforce/connector.py`
- **SecondsSinceUnixEpoch** (14 connections) — `backend/om/connectors/salesforce/connector.py`
- **ConnectorCheckpoint** (14 connections)
- **connector.py** (14 connections) — `backend/om/connectors/imap/connector.py`
- **._load_from_checkpoint()** (14 connections) — `backend/om/connectors/imap/connector.py`
- **.cursor()** (14 connections) — `backend/om/connectors/salesforce/sqlite_functions.py`
- **OmSalesforce** (13 connections) — `backend/om/connectors/salesforce/connector.py`
- **OmSalesforceSQLite** (13 connections) — `backend/om/connectors/salesforce/connector.py`
- **ImapCheckpoint** (12 connections) — `backend/om/connectors/imap/connector.py`
- **IMAP4_SSL** (11 connections) — `backend/om/connectors/imap/connector.py`
- **._delta_sync()** (10 connections) — `backend/om/connectors/salesforce/connector.py`
- **._make_context()** (10 connections) — `backend/om/connectors/salesforce/connector.py`
- **Message** (9 connections) — `backend/om/connectors/imap/connector.py`
- **SecondsSinceUnixEpoch** (9 connections) — `backend/om/connectors/imap/connector.py`
- **convert_sf_query_result_to_doc()** (9 connections) — `backend/om/connectors/salesforce/doc_conversion.py`
- **_extract_section()** (9 connections) — `backend/om/connectors/salesforce/doc_conversion.py`
- **Any** (8 connections) — `backend/om/connectors/imap/connector.py`
- **CheckpointOutput** (8 connections) — `backend/om/connectors/imap/connector.py`
- **EmailHeaders** (8 connections) — `backend/om/connectors/imap/connector.py`
- **_convert_email_headers_and_body_into_document()** (8 connections) — `backend/om/connectors/imap/connector.py`
- *... and 157 more nodes in this community*

## Relationships

- [[Connector Indexing Types]] (82 shared connections)
- [[Connector Checkpoint & Slim Docs]] (32 shared connections)
- [[Connectors (Airtable/Asana)]] (23 shared connections)
- [[Document External Access]] (18 shared connections)
- [[Community 123]] (15 shared connections)
- [[Community 85]] (9 shared connections)
- [[Document Access & Indexing]] (8 shared connections)
- [[Community 144]] (7 shared connections)
- [[Community 233]] (7 shared connections)
- [[Confluence Connector]] (6 shared connections)
- [[Google Drive Connector]] (6 shared connections)
- [[Community 483]] (6 shared connections)

## Source Files

- `backend/om/connectors/gmail/connector.py`
- `backend/om/connectors/google_drive/connector.py`
- `backend/om/connectors/imap/connector.py`
- `backend/om/connectors/salesforce/connector.py`
- `backend/om/connectors/salesforce/doc_conversion.py`
- `backend/om/connectors/salesforce/onyx_salesforce.py`
- `backend/om/connectors/salesforce/salesforce_calls.py`
- `backend/om/connectors/salesforce/sqlite_functions.py`
- `backend/scripts/tenant_cleanup/mark_connectors_for_deletion.py`
- `backend/tests/daily/connectors/slack/test_slack_perm_sync.py`
- `backend/tests/unit/om/connectors/salesforce/test_salesforce_sqlite.py`

## Audit Trail

- EXTRACTED: 602 (55%)
- INFERRED: 500 (45%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*