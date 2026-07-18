import time

from redis.lock import Lock as RedisLock

from om.configs.constants import CELERY_GENERIC_BEAT_LOCK_TIMEOUT
from om.configs.constants import DocumentSource
from om.db.document import get_num_chunks_for_document
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.models import Connector
from om.db.models import DocumentByConnectorCredentialPair
from om.db.models import KGEntityType
from om.document_index.interfaces_new import KGUChunkUpdateRequest
from om.kg.opensearch.opensearch_interactions import update_kg_chunks_opensearch_info
from om.kg.utils.lock_utils import extend_lock
from om.utils.logger import setup_logger

logger = setup_logger()


def _reset_opensearch_for_doc(
    document_id: str, tenant_id: str, index_name: str
) -> None:
    """Clears the KG fields (kg_entities, kg_relationships, kg_terms) for every
    chunk of a document by full-replacing them with empty arrays.

    Empty (non-None) sets cause kg_chunk_updates to write empty arrays, which is
    how a reset clears the fields.
    """
    with get_session_with_current_tenant() as db_session:
        num_chunks = get_num_chunks_for_document(db_session, document_id)

    reset_requests: list[KGUChunkUpdateRequest] = [
        KGUChunkUpdateRequest(
            document_id=document_id,
            chunk_id=chunk_num,
            core_entity="unused",
            entities=set(),
            relationships=set(),
            terms=set(),
        )
        for chunk_num in range(num_chunks)
    ]

    update_kg_chunks_opensearch_info(reset_requests, index_name, tenant_id)


def reset_opensearch_kg_index(
    tenant_id: str, index_name: str, lock: RedisLock, source_name: str | None = None
) -> None:
    """
    Reset the kg info in OpenSearch for all documents of a given source name,
    or all documents from kg grounded sources if source_name is None.
    """
    logger.info(
        "Resetting kg opensearch index %s for tenant %s, source: %s",
        index_name,
        tenant_id,
        source_name if source_name else "all",
    )

    last_lock_time = time.monotonic()

    # Get all documents that need an OpenSearch reset
    with get_session_with_current_tenant() as db_session:
        if source_name:
            # get all connectors of the given source name
            kg_connectors = [
                connector.id
                for connector in db_session.query(Connector)
                .filter(Connector.source == DocumentSource(source_name))
                .all()
            ]
        else:
            # get all connectors that have kg enabled
            kg_sources = [
                DocumentSource(et.grounded_source_name)
                for et in db_session.query(KGEntityType)
                .filter(
                    KGEntityType.grounded_source_name.is_not(None),
                    KGEntityType.active.is_(True),
                )
                .distinct()
                .all()
            ]
            kg_connectors = [
                connector.id
                for connector in db_session.query(Connector)
                .filter(Connector.source.in_(kg_sources))
                .all()
            ]

        # Get all the documents for the given connectors
        document_ids = [
            cc_pair.id
            for cc_pair in db_session.query(DocumentByConnectorCredentialPair)
            .filter(DocumentByConnectorCredentialPair.connector_id.in_(kg_connectors))
            .all()
        ]

    # Reset the kg fields
    for document_id in document_ids:
        _reset_opensearch_for_doc(document_id, tenant_id, index_name)
        last_lock_time = extend_lock(
            lock, CELERY_GENERIC_BEAT_LOCK_TIMEOUT, last_lock_time
        )

    logger.info(
        "Finished resetting kg opensearch index %s for tenant %s, source: %s",
        index_name,
        tenant_id,
        source_name if source_name else "all",
    )
