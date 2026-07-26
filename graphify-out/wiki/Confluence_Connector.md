# Confluence Connector

> 199 nodes · cohesion 0.02

## Key Concepts

- **OmConfluence** (70 connections) — `backend/om/connectors/confluence/onyx_confluence.py`
- **ConfluenceConnector** (40 connections) — `backend/om/connectors/confluence/connector.py`
- **SecondsSinceUnixEpoch** (23 connections) — `backend/om/connectors/confluence/connector.py`
- **Any** (22 connections) — `backend/om/connectors/confluence/connector.py`
- **ConfluenceCheckpoint** (22 connections) — `backend/om/connectors/confluence/connector.py`
- **Any** (20 connections) — `backend/om/connectors/confluence/onyx_confluence.py`
- **HierarchyNode** (19 connections) — `backend/om/connectors/confluence/connector.py`
- **._fetch_page_attachments()** (17 connections) — `backend/om/connectors/confluence/connector.py`
- **utils.py** (17 connections) — `backend/om/connectors/confluence/utils.py`
- **MockCredentialsProvider** (15 connections) — `backend/tests/daily/connectors/confluence/test_confluence_user_email_overrides.py`
- **._convert_page_to_document()** (14 connections) — `backend/om/connectors/confluence/connector.py`
- **.retrieve_all_slim_docs()** (12 connections) — `backend/om/connectors/confluence/connector.py`
- **extract_text_from_confluence_html()** (12 connections) — `backend/om/connectors/confluence/onyx_confluence.py`
- **._paginate_url()** (12 connections) — `backend/om/connectors/confluence/onyx_confluence.py`
- **._fetch_document_batches()** (11 connections) — `backend/om/connectors/confluence/connector.py`
- **onyx_confluence.py** (10 connections) — `backend/om/connectors/confluence/onyx_confluence.py`
- **Any** (9 connections) — `backend/om/connectors/confluence/utils.py`
- **._maybe_yield_page_hierarchy_node()** (9 connections) — `backend/om/connectors/confluence/connector.py`
- **test_onyx_confluence.py** (9 connections) — `backend/tests/unit/om/connectors/confluence/test_onyx_confluence.py`
- **process_attachment()** (9 connections) — `backend/om/connectors/confluence/utils.py`
- **space_access.py** (8 connections) — `backend/om/external_permissions/confluence/space_access.py`
- **_create_http_error()** (8 connections) — `backend/tests/unit/om/connectors/confluence/test_onyx_confluence.py`
- **_create_mock_response()** (8 connections) — `backend/tests/unit/om/connectors/confluence/test_onyx_confluence.py`
- **AttachmentProcessingResult** (8 connections) — `backend/om/connectors/confluence/utils.py`
- **build_confluence_document_id()** (8 connections) — `backend/om/connectors/confluence/utils.py`
- *... and 174 more nodes in this community*

## Relationships

- [[Connector Checkpoint & Slim Docs]] (67 shared connections)
- [[Connector Indexing Types]] (32 shared connections)
- [[Document External Access]] (19 shared connections)
- [[Connectors (Airtable/Asana)]] (10 shared connections)
- [[Salesforce Connector]] (6 shared connections)
- [[Community 135]] (4 shared connections)
- [[Community 878]] (4 shared connections)
- [[Community 88]] (3 shared connections)
- [[Community 139]] (3 shared connections)
- [[Community 142]] (2 shared connections)
- [[Community 360]] (1 shared connections)
- [[Community 1037]] (1 shared connections)

## Source Files

- `backend/om/connectors/confluence/access.py`
- `backend/om/connectors/confluence/connector.py`
- `backend/om/connectors/confluence/onyx_confluence.py`
- `backend/om/connectors/confluence/user_profile_override.py`
- `backend/om/connectors/confluence/utils.py`
- `backend/om/connectors/cross_connector_utils/miscellaneous_utils.py`
- `backend/om/external_permissions/confluence/page_access.py`
- `backend/om/external_permissions/confluence/space_access.py`
- `backend/tests/daily/connectors/confluence/test_confluence_user_email_overrides.py`
- `backend/tests/unit/om/connectors/confluence/test_onyx_confluence.py`
- `backend/tests/unit/om/connectors/confluence/test_rate_limit_handler.py`

## Audit Trail

- EXTRACTED: 672 (74%)
- INFERRED: 238 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*