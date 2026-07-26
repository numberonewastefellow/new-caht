# Connectors (Airtable/Asana)

> 508 nodes · cohesion 0.01

## Key Concepts

- **LoadConnector** (253 connections) — `backend/om/connectors/interfaces.py`
- **GenerateDocumentsOutput** (246 connections) — `backend/om/connectors/interfaces.py`
- **PollConnector** (241 connections) — `backend/om/connectors/interfaces.py`
- **CheckpointedConnector** (105 connections) — `backend/om/connectors/interfaces.py`
- **BaseConnector** (58 connections) — `backend/om/connectors/interfaces.py`
- **SlimConnector** (46 connections) — `backend/om/connectors/interfaces.py`
- **OAuthConnector** (34 connections) — `backend/om/connectors/interfaces.py`
- **CheckpointOutputWrapper** (32 connections) — `backend/om/connectors/connector_runner.py`
- **EgnyteConnector** (18 connections) — `backend/om/connectors/egnyte/connector.py`
- **LocalFolderConnector** (17 connections) — `backend/om/connectors/folder/connector.py`
- **LinearConnector** (17 connections) — `backend/om/connectors/linear/connector.py`
- **ConnectorMissingException** (16 connections) — `backend/om/connectors/factory.py`
- **interfaces.py** (16 connections) — `backend/om/connectors/interfaces.py`
- **instantiate_connector()** (15 connections) — `backend/om/connectors/factory.py`
- **GongConnector** (15 connections) — `backend/om/connectors/gong/connector.py`
- **.make_url()** (15 connections) — `backend/om/connectors/gong/connector.py`
- **Document360Connector** (13 connections) — `backend/om/connectors/document360/connector.py`
- **ZulipConnector** (13 connections) — `backend/om/connectors/zulip/connector.py`
- **AsanaConnector** (12 connections) — `backend/om/connectors/asana/connector.py`
- **extract_ids_from_runnable_connector()** (12 connections) — `backend/om/background/celery/celery_utils.py`
- **SlimConnectorExtractionResult** (12 connections) — `backend/om/background/celery/celery_utils.py`
- **ClickupConnector** (12 connections) — `backend/om/connectors/clickup/connector.py`
- **EventConnector** (12 connections) — `backend/om/connectors/interfaces.py`
- **DiscourseConnector** (12 connections) — `backend/om/connectors/discourse/connector.py`
- **._fetch_from_gitlab()** (12 connections) — `backend/om/connectors/gitlab/connector.py`
- *... and 483 more nodes in this community*

## Relationships

- [[Connector Indexing Types]] (271 shared connections)
- [[Connector Checkpoint & Slim Docs]] (210 shared connections)
- [[Community 167]] (43 shared connections)
- [[Document External Access]] (32 shared connections)
- [[Community 135]] (28 shared connections)
- [[Community 144]] (25 shared connections)
- [[Salesforce Connector]] (23 shared connections)
- [[Community 417]] (22 shared connections)
- [[Community 212]] (15 shared connections)
- [[Community 442]] (13 shared connections)
- [[Community 173]] (12 shared connections)
- [[Community 360]] (12 shared connections)

## Source Files

- `backend/om/background/celery/celery_utils.py`
- `backend/om/background/indexing/checkpointing_utils.py`
- `backend/om/connectors/airtable/airtable_connector.py`
- `backend/om/connectors/asana/connector.py`
- `backend/om/connectors/axero/connector.py`
- `backend/om/connectors/bookstack/connector.py`
- `backend/om/connectors/clickup/connector.py`
- `backend/om/connectors/connector_runner.py`
- `backend/om/connectors/discord/connector.py`
- `backend/om/connectors/discourse/connector.py`
- `backend/om/connectors/document360/connector.py`
- `backend/om/connectors/document360/utils.py`
- `backend/om/connectors/dropbox/connector.py`
- `backend/om/connectors/egnyte/connector.py`
- `backend/om/connectors/factory.py`
- `backend/om/connectors/file/connector.py`
- `backend/om/connectors/fireflies/connector.py`
- `backend/om/connectors/folder/connector.py`
- `backend/om/connectors/freshdesk/connector.py`
- `backend/om/connectors/gitbook/connector.py`

## Audit Trail

- EXTRACTED: 1443 (43%)
- INFERRED: 1948 (57%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*