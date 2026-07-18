from collections.abc import Generator

from om.connectors.models import convert_metadata_list_of_strings_to_dict
from om.db.document import get_document_kg_entities_and_relationships
from om.db.document import get_num_chunks_for_document
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.search_settings import get_current_search_settings
from om.document_index.interfaces_new import KGUChunkUpdateRequest
from om.document_index.interfaces_new import TenantState
from om.document_index.opensearch.opensearch_document_index import (
    OpenSearchDocumentIndex,
)
from om.document_index.opensearch.schema import DocumentChunkWithoutVectors
from om.indexing.models import IndexingSetting
from om.kg.models import KGChunkFormat
from om.utils.logger import setup_logger
from shared_configs.configs import MULTI_TENANT

logger = setup_logger()


def _build_opensearch_index(index_name: str, tenant_id: str) -> OpenSearchDocumentIndex:
    """Builds an OpenSearchDocumentIndex for the given index / tenant.

    Unlike the Vespa constructor, OpenSearchDocumentIndex requires the embedding
    dimension and precision (used only if it needs to verify/create the index on
    init in the multitenant cloud path). We pull these from the current search
    settings, which correspond to the primary index used by KG flows.

    TODO(kg): If ``index_name`` ever refers to a non-primary index whose
    embedding dimension differs from the current search settings, the values
    here would be wrong. In practice KG only runs against the primary index, and
    the index already exists (so no create happens), so this is safe today.
    """
    with get_session_with_current_tenant() as db_session:
        search_settings = get_current_search_settings(db_session)
        indexing_setting = IndexingSetting.from_db_model(search_settings)

    return OpenSearchDocumentIndex(
        tenant_state=TenantState(tenant_id=tenant_id, multitenant=MULTI_TENANT),
        index_name=index_name,
        embedding_dim=indexing_setting.final_embedding_dim,
        embedding_precision=indexing_setting.embedding_precision,
    )


def update_kg_chunks_opensearch_info(
    kg_update_requests: list[KGUChunkUpdateRequest],
    index_name: str,
    tenant_id: str,
) -> None:
    """Applies a batch of KG chunk updates to the OpenSearch document index."""
    opensearch_index = _build_opensearch_index(index_name, tenant_id)
    opensearch_index.kg_chunk_updates(
        kg_update_requests=kg_update_requests, tenant_id=tenant_id
    )


def get_kg_opensearch_info_update_requests_for_document(
    document_id: str,
) -> list[KGUChunkUpdateRequest]:
    """Get the kg_info update requests for a document.

    Backend-agnostic: pulls the document's entities/relationships from Postgres
    and the chunk count, then emits one KGUChunkUpdateRequest per chunk. Copied
    verbatim from the Vespa equivalent.
    """
    # get all entities and relationships tied to the document
    with get_session_with_current_tenant() as db_session:
        entities, relationships = get_document_kg_entities_and_relationships(
            db_session, document_id
        )

    # create the kg info
    kg_entities = {entity.id_name for entity in entities}
    kg_relationships = {relationship.id_name for relationship in relationships}

    # get chunks in the document
    with get_session_with_current_tenant() as db_session:
        num_chunks = get_num_chunks_for_document(db_session, document_id)

    # get update requests
    return [
        KGUChunkUpdateRequest(
            document_id=document_id,
            chunk_id=chunk_id,
            core_entity="unused",
            entities=kg_entities,
            relationships=kg_relationships or None,
        )
        for chunk_id in range(num_chunks)
    ]


def get_document_opensearch_contents(
    document_id: str,
    index_name: str,
    tenant_id: str,
    batch_size: int = 8,
) -> Generator[list[KGChunkFormat], None, None]:
    """
    Retrieves chunks from OpenSearch for the given document and converts them to
    KGChunkFormat, yielded in batches.

    Mirrors ``get_document_vespa_contents``. The metadata dict is reconstructed
    from ``metadata_list`` via ``convert_metadata_list_of_strings_to_dict`` (the
    inverse of the dict->list encoding used at index time).

    NOTE: The underlying document-id search is currently capped at a max result
    window; very large documents may need scroll/point-in-time paging.

    Args:
        document_id: ID of the document to fetch chunks for.
        index_name: Name of the OpenSearch index.
        tenant_id: ID of the tenant.
        batch_size: Number of chunks to fetch per batch.

    Yields:
        list[KGChunkFormat]: Batches of chunks ready for KG processing.
    """
    opensearch_index = _build_opensearch_index(index_name, tenant_id)
    chunks: list[DocumentChunkWithoutVectors] = (
        opensearch_index.get_document_chunks_without_vectors(document_id)
    )

    current_batch: list[KGChunkFormat] = []
    for chunk in chunks:
        metadata: dict[str, str | list[str]] | None = None
        if chunk.metadata_tags:
            metadata = convert_metadata_list_of_strings_to_dict(chunk.metadata_tags)

        current_batch.append(
            KGChunkFormat(
                connector_id=None,  # We may need to adjust this
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_index,
                primary_owners=chunk.primary_owners or [],
                secondary_owners=chunk.secondary_owners or [],
                source_type=chunk.source_type,
                title=chunk.title or "",
                content=chunk.chunk_text,
                metadata=metadata,
            )
        )

        if len(current_batch) >= batch_size:
            yield current_batch
            current_batch = []

    # Yield any remaining chunks
    if current_batch:
        yield current_batch
