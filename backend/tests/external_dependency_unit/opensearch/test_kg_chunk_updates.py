"""External-dependency round-trip test for the OpenSearch KG chunk-storage port.

This is the GATE for deleting Vespa: it proves that the ported KG storage
(``OpenSearchDocumentIndex.kg_chunk_updates`` + ``get_document_chunks_without_vectors``)
works end-to-end against a real OpenSearch, including the ``nested``
``kg_relationships`` mapping. It runs on the Docker rebuild (where OpenSearch is
available); it is skipped if OpenSearch is not reachable.

Flow: create index -> index base chunks -> write KG fields -> read back and
assert entities + nested {source, rel_type, target} relationships -> reset ->
assert cleared. Vespa is still present in the tree while this runs, so a failure
has a working reference/rollback.

KG itself stays DISABLED; this exercises only the storage layer.
"""

import uuid
from collections.abc import Generator

import pytest

from om.access.models import DocumentAccess
from om.configs.constants import DocumentSource
from om.db.enums import EmbeddingPrecision
from om.document_index.interfaces_new import KGUChunkUpdateRequest
from om.document_index.interfaces_new import TenantState
from om.document_index.opensearch.client import OpenSearchIndexClient
from om.document_index.opensearch.client import wait_for_opensearch_with_timeout
from om.document_index.opensearch.opensearch_document_index import (
    generate_opensearch_filtered_access_control_list,
)
from om.document_index.opensearch.opensearch_document_index import (
    OpenSearchDocumentIndex,
)
from om.document_index.opensearch.schema import DocumentChunk
from om.document_index.opensearch.schema import DocumentSchema
from om.document_index.opensearch.schema import KGRelationship
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA

_EMBEDDING_DIM = 128


def _patch_single_tenant(monkeypatch: pytest.MonkeyPatch) -> TenantState:
    """Forces single-tenant mode for the schema/id helpers and returns the state."""
    monkeypatch.setattr("shared_configs.configs.MULTI_TENANT", False)
    monkeypatch.setattr("om.document_index.opensearch.schema.MULTI_TENANT", False)
    return TenantState(tenant_id=POSTGRES_DEFAULT_SCHEMA, multitenant=False)


def _make_chunk(
    document_id: str, chunk_index: int, tenant_state: TenantState
) -> DocumentChunk:
    return DocumentChunk(
        document_id=document_id,
        chunk_index=chunk_index,
        title="KG test title",
        title_embedding=[0.2] * _EMBEDDING_DIM,
        chunk_text=f"KG test content {chunk_index}",
        content_embedding=[0.1] * _EMBEDDING_DIM,
        source_type=DocumentSource.FILE.value,
        metadata_tags=None,
        updated_at=None,
        is_public=True,
        access_control_list=generate_opensearch_filtered_access_control_list(
            DocumentAccess.build(
                user_emails=[],
                teams=[],
                external_user_emails=[],
                external_team_ids=[],
                is_public=True,
            )
        ),
        is_hidden=False,
        boost=0,
        display_name="KG test",
        image_id=None,
        source_links=None,
        snippet="KG test blurb",
        document_summary="KG test summary",
        contextual_summary="KG test context",
        document_sets=None,
        user_workspaces=None,
        primary_owners=None,
        secondary_owners=None,
        tenant_id=tenant_state,
    )


@pytest.fixture(scope="module")
def opensearch_available() -> None:
    if not wait_for_opensearch_with_timeout():
        pytest.skip("OpenSearch is not available.")


@pytest.fixture(scope="function")
def kg_index(
    opensearch_available: None,  # noqa: ARG001
) -> Generator[tuple[str, OpenSearchIndexClient], None, None]:
    """Creates a fresh test index with the current schema; yields (name, client)."""
    index_name = f"test_kg_index_{uuid.uuid4().hex[:8]}"
    client = OpenSearchIndexClient(index_name=index_name)
    mappings = DocumentSchema.get_document_schema(
        vector_dimension=_EMBEDDING_DIM, multitenant=False
    )
    settings = DocumentSchema.get_index_settings_based_on_environment()
    client.create_index(mappings=mappings, settings=settings)
    try:
        yield index_name, client
    finally:
        try:
            client.delete_index()
        except Exception:
            pass
        client.close()


def test_kg_chunk_updates_roundtrip(
    kg_index: tuple[str, OpenSearchIndexClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Write KG fields, read them back (nested relationships), then reset."""
    index_name, client = kg_index
    tenant_state = _patch_single_tenant(monkeypatch)
    document_id = "kg-test-doc"
    num_chunks = 2

    # 1) Index the base chunks (partial KG updates require existing docs).
    chunks = [_make_chunk(document_id, i, tenant_state) for i in range(num_chunks)]
    client.bulk_index_documents(documents=chunks, tenant_state=tenant_state)
    client.refresh_index()

    doc_index = OpenSearchDocumentIndex(
        tenant_state=tenant_state,
        index_name=index_name,
        embedding_dim=_EMBEDDING_DIM,
        embedding_precision=EmbeddingPrecision.FLOAT,
    )

    # 2) Write KG fields onto every chunk. Relationship id is
    #    source__rel_type__target and must come back as a nested object.
    entities = {"account:acme", "opportunity:123"}
    relationships = {"account:acme__owns__opportunity:123"}
    write_requests = [
        KGUChunkUpdateRequest(
            document_id=document_id,
            chunk_id=i,
            core_entity="unused",
            entities=entities,
            relationships=relationships,
        )
        for i in range(num_chunks)
    ]
    doc_index.kg_chunk_updates(kg_update_requests=write_requests, tenant_id="")
    client.refresh_index()

    # 3) Read back and assert.
    read_chunks = doc_index.get_document_chunks_without_vectors(document_id)
    assert len(read_chunks) == num_chunks
    for chunk in read_chunks:
        assert set(chunk.kg_entities or []) == entities
        assert chunk.kg_relationships == [
            KGRelationship(
                source="account:acme", rel_type="owns", target="opportunity:123"
            )
        ]

    # 4) Reset (empty sets -> empty arrays) and assert cleared.
    reset_requests = [
        KGUChunkUpdateRequest(
            document_id=document_id,
            chunk_id=i,
            core_entity="unused",
            entities=set(),
            relationships=set(),
            terms=set(),
        )
        for i in range(num_chunks)
    ]
    doc_index.kg_chunk_updates(kg_update_requests=reset_requests, tenant_id="")
    client.refresh_index()

    cleared = doc_index.get_document_chunks_without_vectors(document_id)
    assert len(cleared) == num_chunks
    for chunk in cleared:
        assert not chunk.kg_entities
        assert not chunk.kg_relationships
        assert not chunk.kg_terms
