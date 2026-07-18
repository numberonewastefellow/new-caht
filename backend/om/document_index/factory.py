from om.configs.app_configs import DISABLE_VECTOR_DB
from om.db.models import SearchSettings
from om.document_index.disabled import DisabledDocumentIndex
from om.document_index.interfaces_new import DocumentIndex
from om.document_index.interfaces_new import TenantState
from om.document_index.opensearch.opensearch_document_index import (
    OpenSearchDocumentIndex,
)
from om.document_index.opensearch.opensearch_document_index import OpenSearchIndexPair
from om.indexing.models import IndexingSetting
from shared_configs.configs import MULTI_TENANT
from shared_configs.contextvars import get_current_tenant_id


def _build_tenant_state() -> TenantState:
    return TenantState(tenant_id=get_current_tenant_id(), multitenant=MULTI_TENANT)


def _build_opensearch_pair(
    search_settings: SearchSettings,
    secondary_search_settings: SearchSettings | None,
) -> OpenSearchIndexPair:
    tenant_state = _build_tenant_state()
    indexing_setting = IndexingSetting.from_db_model(search_settings)
    primary = OpenSearchDocumentIndex(
        tenant_state=tenant_state,
        index_name=search_settings.index_name,
        embedding_dim=indexing_setting.final_embedding_dim,
        embedding_precision=indexing_setting.embedding_precision,
    )
    if secondary_search_settings is None:
        return OpenSearchIndexPair(primary=primary, secondary=None)
    secondary_indexing_setting = IndexingSetting.from_db_model(
        secondary_search_settings
    )
    secondary = OpenSearchDocumentIndex(
        tenant_state=tenant_state,
        index_name=secondary_search_settings.index_name,
        embedding_dim=secondary_indexing_setting.final_embedding_dim,
        embedding_precision=secondary_indexing_setting.embedding_precision,
    )
    return OpenSearchIndexPair(
        primary=primary,
        secondary=secondary,
        secondary_embedding_dim=secondary_indexing_setting.final_embedding_dim,
        secondary_embedding_precision=secondary_indexing_setting.embedding_precision,
    )


def get_default_document_index(
    search_settings: SearchSettings,
    secondary_search_settings: SearchSettings | None,
) -> DocumentIndex:
    """Gets the default document index for retrieval.

    Returns one DocumentIndex (the primary+secondary pair, with secondary None
    when no second search settings exist). OpenSearch is the only backend. For
    indexing flows that need to write to *all* configured indices, use
    `get_all_document_indices`.
    """
    if DISABLE_VECTOR_DB:
        return DisabledDocumentIndex()

    return _build_opensearch_pair(search_settings, secondary_search_settings)


def get_all_document_indices(
    search_settings: SearchSettings,
    secondary_search_settings: SearchSettings | None,
) -> list[DocumentIndex]:
    """Gets every document index that should be written to.

    OpenSearch is the only backend, so this is the OpenSearch primary+secondary
    pair (or the disabled index when DISABLE_VECTOR_DB is set).
    """
    if DISABLE_VECTOR_DB:
        return [DisabledDocumentIndex()]

    return [_build_opensearch_pair(search_settings, secondary_search_settings)]
