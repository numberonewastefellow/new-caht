# Community 1040

> 12 nodes · cohesion 0.21

## Key Concepts

- **tqdm** (12 connections) — `phoenix/scripts/perf/postgres/postgres_explain_analyze.py`
- **get_wikidocs.py** (6 connections) — `backend/scripts/get_wikidocs.py`
- **stream_wikipedia_to_zips()** (6 connections) — `backend/scripts/get_wikidocs.py`
- **build_llama_index_rag_data.py** (3 connections) — `phoenix/scripts/data/build_llama_index_rag_data.py`
- **main()** (3 connections) — `backend/scripts/get_wikidocs.py`
- **sanitize_filename()** (3 connections) — `backend/scripts/get_wikidocs.py`
- **create_user_feedback()** (2 connections) — `phoenix/scripts/data/build_llama_index_rag_data.py`
- **Creates RAG dataset for tutorial notebooks and persists to disk.** (1 connections) — `phoenix/scripts/data/build_llama_index_rag_data.py`
- **_summary_      Args:         first_document_relevances (List[Optional[bool]])** (1 connections) — `phoenix/scripts/data/build_llama_index_rag_data.py`
- **Main entry point for the script.** (1 connections) — `backend/scripts/get_wikidocs.py`
- **Sanitize a title for use as a filename.      - Remove special characters     - R** (1 connections) — `backend/scripts/get_wikidocs.py`
- **Stream Wikipedia pages from Hugging Face and write them to zip files.      Args:** (1 connections) — `backend/scripts/get_wikidocs.py`

## Relationships

- [[Community 425]] (2 shared connections)
- [[Community 366]] (2 shared connections)
- [[Community 842]] (2 shared connections)
- [[Community 629]] (2 shared connections)
- [[Community 111]] (1 shared connections)
- [[Community 84]] (1 shared connections)
- [[Salesforce Connector]] (1 shared connections)
- [[Community 751]] (1 shared connections)

## Source Files

- `backend/scripts/get_wikidocs.py`
- `phoenix/scripts/data/build_llama_index_rag_data.py`
- `phoenix/scripts/perf/postgres/postgres_explain_analyze.py`

## Audit Trail

- EXTRACTED: 32 (80%)
- INFERRED: 8 (20%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*