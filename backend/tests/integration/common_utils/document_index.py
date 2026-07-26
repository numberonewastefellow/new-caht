"""OpenSearch-backed integration-test document client.

Replaces the old Vespa ``vespa_fixture``. It reads indexed documents back by id
straight from OpenSearch and returns them in the same
``{"documents": [{"fields": {...}}]}`` shape the previous Vespa client used, so
callers do not have to change how they read fields.

Two projections keep the legacy shape intact:
  * ``access_control_list`` / ``document_sets`` are stored as OpenSearch keyword
    arrays; callers expect a dict they can call ``.keys()`` on, so we re-project
    each array into ``{value: 1}``.
  * OpenSearch keeps ``public`` as its own boolean field (the ACL array excludes
    it); Vespa folded PUBLIC into the ACL. We fold it back in so the
    ``"PUBLIC" in acl_keys`` checks in DocumentManager still hold.
"""

from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.search_settings import get_current_search_settings
from om.document_index.interfaces_new import TenantState
from om.document_index.opensearch.opensearch_document_index import (
    OpenSearchDocumentIndex,
)
from om.indexing.models import IndexingSetting
from shared_configs.configs import MULTI_TENANT
from shared_configs.contextvars import get_current_tenant_id


class DocumentIndexClient:
    """Minimal by-id document reader against the live OpenSearch index."""

    def __init__(self, index_name: str):
        self.index_name = index_name
        with get_session_with_current_tenant() as db_session:
            search_settings = get_current_search_settings(db_session)
        indexing_setting = IndexingSetting.from_db_model(search_settings)
        self._index = OpenSearchDocumentIndex(
            tenant_state=TenantState(
                tenant_id=get_current_tenant_id(), multitenant=MULTI_TENANT
            ),
            index_name=index_name,
            embedding_dim=indexing_setting.final_embedding_dim,
            embedding_precision=indexing_setting.embedding_precision,
        )

    def get_documents_by_id(
        self,
        document_ids: list[str],
        wanted_doc_count: int = 1_000,  # noqa: ARG002 - kept for signature compatibility
    ) -> dict:
        """Return chunks for the given document ids in the legacy Vespa shape.

        ``{"documents": [{"fields": {...}}, ...]}`` with one entry per chunk.
        Missing documents simply contribute no entries (matching the old client,
        which returned only the docs Vespa actually held).
        """
        documents: list[dict] = []
        for document_id in document_ids:
            chunks = self._index.get_document_chunks_without_vectors(document_id)
            for chunk in chunks:
                acl = {key: 1 for key in chunk.access_control_list}
                if chunk.is_public:
                    acl["PUBLIC"] = 1
                documents.append(
                    {
                        "fields": {
                            "document_id": chunk.document_id,
                            "content": chunk.chunk_text,
                            "access_control_list": acl,
                            "document_sets": {
                                doc_set: 1 for doc_set in (chunk.document_sets or [])
                            },
                            # Vespa exposed this as ``image_file_name``; keep the
                            # key so callers reading it are unaffected.
                            "image_file_name": chunk.image_id,
                        }
                    }
                )
        return {"documents": documents}
