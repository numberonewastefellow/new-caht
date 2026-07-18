# Knowledge Graph on OpenSearch (storage-only port)

**Status: KG is DISABLED.** This directory exists because when Vespa was removed,
the KG chunk-**storage** layer had to move to OpenSearch so nothing stranded a
`om.document_index.vespa.*` import. Only *storage* was ported. No extraction
trigger, clustering schedule, or search tool was added — KG remains exactly as
disabled as it was before, just OpenSearch-ready instead of Vespa-coupled.

This is intentional and matches the reference repo, which is in the same broken
state (stub tool, no trigger, no KG search layer).

---

## What is stored on OpenSearch

The document chunk mapping (`om/document_index/opensearch/schema.py`,
`get_document_schema`) gained three KG fields (mapping is `dynamic: strict`, so
they must be declared; they are additive, so **no reindex** is required — they
are added to an existing index via `put_mapping` on startup):

| Field | Constant | OpenSearch type | Shape |
|-------|----------|-----------------|-------|
| `kg_entities` | `KG_ENTITIES_FIELD_NAME` | `keyword` | array of entity id strings |
| `kg_terms` | `KG_TERMS_FIELD_NAME` | `keyword` | array of term strings |
| `kg_relationships` | `KG_RELATIONSHIPS_FIELD_NAME` | `nested` | array of `{source, rel_type, target}` (each a `keyword` subfield) |

`kg_relationships` is a **`nested`** type on purpose: a relationship id
(`source__rel_type__target`, split by `split_relationship_id`) is exploded into
its three endpoints so each is independently queryable (`source`, `rel_type`,
`target`). Changing this from `nested` later would require a reindex, so it was
chosen up front. See `class KGRelationship` in `schema.py` and
`DocumentChunkWithoutVectors.kg_relationships`.

---

## Storage API surface (the only new KG code)

**Write** — `OpenSearchDocumentIndex.kg_chunk_updates(...)`
(`opensearch/opensearch_document_index.py`). Mirrors the normal `update()`
path: partial `{"doc": {...}}` merges via `client.bulk_update_documents`, which
full-replaces each array (matching Vespa's `{"assign": [...]}` semantics).
Relationship ids are exploded into the nested `{source, rel_type, target}` dicts.
The write is payload-batched.

**Read** — `OpenSearchDocumentIndex.get_document_chunks_without_vectors(document_id)`
returns raw `DocumentChunkWithoutVectors` models (preserving `metadata_list`,
owners, and the KG fields). `om/kg/opensearch/opensearch_interactions.py`'s
`get_document_opensearch_contents(...)` wraps it into the `KGChunkFormat` batches
the (dead) clustering code expects.

**Reset** — `reset_opensearch_kg_index(...)` in `om/kg/resets/reset_opensearch.py`
writes `{"kg_entities": [], "kg_relationships": [], "kg_terms": []}` back onto a
document's chunks via `bulk_update_documents`.

**Backend-agnostic call sites** — `om/kg/opensearch/opensearch_interactions.py`
exposes `update_kg_chunks_opensearch_info` and
`get_kg_opensearch_info_update_requests_for_document`; the storage contract is
`KGUChunkUpdateRequest` (`om/document_index/interfaces_new.py`):
`{document_id, chunk_id, core_entity, entities: set, relationships: set|None, terms: set|None}`.

---

## The gating round-trip test

`backend/tests/external_dependency_unit/opensearch/test_kg_chunk_updates.py`
exercises the **entire** new KG surface against a real OpenSearch:

1. index a doc,
2. `kg_chunk_updates(...)` known entities / relationships / terms,
3. read them back via `get_document_opensearch_contents(...)` and assert exact match,
4. `reset_opensearch_kg_index(...)` and assert the fields are cleared.

It was the gate for deleting Vespa (Vespa stayed in the tree as a rollback
reference until this passed). Run it against the dev stack:

```
pytest backend/tests/external_dependency_unit/opensearch/test_kg_chunk_updates.py -v
```

---

## How to test KG end-to-end once it is REVIVED

None of this works today (see gaps below). Once the revival pieces exist:

1. Enable KG for the tenant (`PUT /admin/kg/config`) and define entity types.
2. Ingest documents, then run extraction + clustering (whatever trigger the
   revival adds).
3. Verify the KG fields land on the chunks — either through the gating test's
   read path (`get_document_opensearch_contents`) or directly:
   `GET <opensearch>/<index>/_search` filtering on `kg_entities` /
   nested `kg_relationships`.

---

## What a future KG revival STILL needs (not built here, absent in the reference too)

Storage is ready; the rest of the pipeline is not. A revival must add:

1. **A trigger.** `kg_extraction()` and `kg_clustering()` have no callers, no
   celery task, and no beat entry. Revival needs a celery task + beat schedule
   entry (with a RedisLock) that drives them.
2. **A real tool.** `KnowledgeGraphTool.run` raises `NotImplementedError`, and
   its `tool_constructor` branch is commented out ("broken in the refactor").
   Revival needs a working `run` and the constructor branch un-commented.
3. **A search/query layer.** There is no KG search path (there never was one for
   OpenSearch — this port is storage-only). Revival needs to build retrieval over
   the `kg_entities` / `kg_relationships` / `kg_terms` fields.

Until all three exist, KG stays disabled and these OpenSearch fields simply
remain empty on every chunk.
