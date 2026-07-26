# Community 332

> 44 nodes · cohesion 0.08

## Key Concepts

- **get_default_file_store()** (48 connections) — `backend/om/file_store/file_store.py`
- **utils.py** (16 connections) — `backend/om/file_store/utils.py`
- **UUID** (8 connections) — `backend/om/file_store/utils.py`
- **load_user_file()** (8 connections) — `backend/om/file_store/utils.py`
- **store_user_file_plaintext()** (8 connections) — `backend/om/file_store/utils.py`
- **verify_knowledge_files()** (8 connections) — `backend/om/file_store/utils.py`
- **TestFileStoreInterface** (7 connections) — `backend/tests/unit/file_store/test_file_store.py`
- **load_chat_file_by_id()** (7 connections) — `backend/om/file_store/utils.py`
- **load_in_memory_chat_files()** (7 connections) — `backend/om/file_store/utils.py`
- **validate_knowledge_files_ownership()** (7 connections) — `backend/om/file_store/utils.py`
- **get_knowledge_files()** (6 connections) — `backend/om/file_store/utils.py`
- **knowledge_file_id_to_plaintext_file_name()** (6 connections) — `backend/om/file_store/utils.py`
- **Session** (5 connections) — `backend/om/file_store/utils.py`
- **save_file()** (5 connections) — `backend/om/file_store/utils.py`
- **mime_type_to_chat_file_type()** (5 connections) — `backend/om/server/query_and_chat/chat_utils.py`
- **save_file_from_base64()** (4 connections) — `backend/om/file_store/utils.py`
- **get_image_type_from_bytes()** (4 connections) — `backend/om/utils/b64.py`
- **InMemoryChatFile** (3 connections) — `backend/om/file_store/utils.py`
- **.test_file_store_defaults_to_s3()** (3 connections) — `backend/tests/unit/file_store/test_file_store.py`
- **.test_file_store_postgres_when_configured()** (3 connections) — `backend/tests/unit/file_store/test_file_store.py`
- **.test_file_store_s3_when_configured()** (3 connections) — `backend/tests/unit/file_store/test_file_store.py`
- **save_file_from_url()** (3 connections) — `backend/om/file_store/utils.py`
- **get_image_type()** (3 connections) — `backend/om/utils/b64.py`
- **KnowledgeFile** (2 connections) — `backend/om/file_store/utils.py`
- **ChatFileType** (2 connections) — `backend/om/server/query_and_chat/chat_utils.py`
- *... and 19 more nodes in this community*

## Relationships

- [[Chat Datetime & OAuth Tokens]] (5 shared connections)
- [[Community 69]] (4 shared connections)
- [[Community 121]] (4 shared connections)
- [[Community 111]] (4 shared connections)
- [[Community 144]] (3 shared connections)
- [[Community 62]] (3 shared connections)
- [[Community 296]] (3 shared connections)
- [[Agent Chat Packets & Citations]] (3 shared connections)
- [[Community 135]] (2 shared connections)
- [[Document Indexing Adapter]] (2 shared connections)
- [[Community 85]] (2 shared connections)
- [[Community 447]] (2 shared connections)

## Source Files

- `backend/om/file_store/file_store.py`
- `backend/om/file_store/utils.py`
- `backend/om/server/query_and_chat/chat_utils.py`
- `backend/om/utils/b64.py`
- `backend/tests/unit/file_store/test_file_store.py`

## Audit Trail

- EXTRACTED: 127 (63%)
- INFERRED: 76 (37%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*