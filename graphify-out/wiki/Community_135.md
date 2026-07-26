# Community 135

> 94 nodes · cohesion 0.04

## Key Concepts

- **extract_file_text.py** (27 connections) — `backend/om/file_processing/extract_file_text.py`
- **extract_text_and_images()** (22 connections) — `backend/om/file_processing/extract_file_text.py`
- **extract_file_text()** (21 connections) — `backend/om/file_processing/extract_file_text.py`
- **IO** (20 connections) — `backend/om/file_processing/extract_file_text.py`
- **parse_html_page_basic()** (19 connections) — `backend/om/file_processing/html_utils.py`
- **Any** (15 connections) — `backend/om/file_processing/extract_file_text.py`
- **get_file_ext()** (15 connections) — `backend/om/file_processing/extract_file_text.py`
- **read_docx_file()** (13 connections) — `backend/om/file_processing/extract_file_text.py`
- **_download_and_extract_sections_basic()** (13 connections) — `backend/om/connectors/google_drive/doc_conversion.py`
- **_process_file()** (12 connections) — `backend/om/connectors/file/utils.py`
- **LoopioConnector** (12 connections) — `backend/om/connectors/loopio/connector.py`
- **store_image_and_create_section()** (11 connections) — `backend/om/file_processing/image_utils.py`
- **web_html_cleanup()** (10 connections) — `backend/om/file_processing/html_utils.py`
- **._process_entries()** (10 connections) — `backend/om/connectors/loopio/connector.py`
- **read_pdf_file()** (9 connections) — `backend/om/file_processing/extract_file_text.py`
- **read_text_file()** (9 connections) — `backend/om/file_processing/extract_file_text.py`
- **html_utils.py** (9 connections) — `backend/om/file_processing/html_utils.py`
- **format_document_soup()** (9 connections) — `backend/om/file_processing/html_utils.py`
- **pptx_to_text()** (8 connections) — `backend/om/file_processing/extract_file_text.py`
- **.load_from_state()** (8 connections) — `backend/om/connectors/google_site/connector.py`
- **._extract_field_values()** (7 connections) — `backend/om/connectors/airtable/airtable_connector.py`
- **Any** (7 connections) — `backend/om/connectors/loopio/connector.py`
- **GenerateDocumentsOutput** (7 connections) — `backend/om/connectors/loopio/connector.py`
- **detect_encoding()** (7 connections) — `backend/om/file_processing/extract_file_text.py`
- **extract_result_from_text_file()** (7 connections) — `backend/om/file_processing/extract_file_text.py`
- *... and 69 more nodes in this community*

## Relationships

- [[Connector Indexing Types]] (30 shared connections)
- [[Connectors (Airtable/Asana)]] (28 shared connections)
- [[Connector Checkpoint & Slim Docs]] (6 shared connections)
- [[Community 167]] (5 shared connections)
- [[Community 224]] (5 shared connections)
- [[Document External Access]] (5 shared connections)
- [[Confluence Connector]] (4 shared connections)
- [[Community 303]] (4 shared connections)
- [[Community 918]] (3 shared connections)
- [[Community 173]] (2 shared connections)
- [[Community 161]] (2 shared connections)
- [[Community 106]] (2 shared connections)

## Source Files

- `backend/om/configs/llm_configs.py`
- `backend/om/connectors/airtable/airtable_connector.py`
- `backend/om/connectors/axero/connector.py`
- `backend/om/connectors/file/utils.py`
- `backend/om/connectors/google_drive/doc_conversion.py`
- `backend/om/connectors/google_site/connector.py`
- `backend/om/connectors/highspot/utils.py`
- `backend/om/connectors/loopio/connector.py`
- `backend/om/file_processing/extract_file_text.py`
- `backend/om/file_processing/html_utils.py`
- `backend/om/file_processing/image_utils.py`
- `backend/tests/unit/om/connectors/cross_connector_utils/test_html_utils.py`

## Audit Trail

- EXTRACTED: 353 (72%)
- INFERRED: 135 (28%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*