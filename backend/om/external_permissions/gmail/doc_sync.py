from collections.abc import Generator
from datetime import datetime
from datetime import timezone

from om.external_permissions.perm_sync_types import FetchAllDocumentsFunction
from om.external_permissions.perm_sync_types import FetchAllDocumentsIdsFunction
from om.access.models import DocExternalAccess
from om.access.models import ElementExternalAccess
from om.access.models import NodeExternalAccess
from om.configs.constants import DocumentSource
from om.connectors.gmail.connector import GmailConnector
from om.connectors.interfaces import GenerateSlimDocumentOutput
from om.connectors.models import HierarchyNode
from om.db.models import ConnectorCredentialPair
from om.indexing.indexing_heartbeat import IndexingHeartbeatInterface
from om.utils.logger import setup_logger

logger = setup_logger()


def _get_slim_doc_generator(
    cc_pair: ConnectorCredentialPair,
    gmail_connector: GmailConnector,
    callback: IndexingHeartbeatInterface | None = None,
) -> GenerateSlimDocumentOutput:
    current_time = datetime.now(timezone.utc)
    start_time = (
        cc_pair.last_time_perm_sync.replace(tzinfo=timezone.utc).timestamp()
        if cc_pair.last_time_perm_sync
        else 0.0
    )

    return gmail_connector.retrieve_all_slim_docs_perm_sync(
        start=start_time,
        end=current_time.timestamp(),
        callback=callback,
    )


def gmail_doc_sync(
    cc_pair: ConnectorCredentialPair,
    fetch_all_existing_docs_fn: FetchAllDocumentsFunction,  # noqa: ARG001
    fetch_all_existing_docs_ids_fn: FetchAllDocumentsIdsFunction,  # noqa: ARG001
    callback: IndexingHeartbeatInterface | None,
) -> Generator[ElementExternalAccess, None, None]:
    """
    Adds the external permissions to the documents and hierarchy nodes in postgres.
    If the document doesn't already exist in postgres, we create
    it in postgres so that when it gets created later, the permissions are
    already populated.
    """
    gmail_connector = GmailConnector(**cc_pair.connector.connector_specific_config)
    credential_json = (
        cc_pair.credential.credential_json.get_value(apply_mask=False)
        if cc_pair.credential.credential_json
        else {}
    )
    gmail_connector.load_credentials(credential_json)

    slim_doc_generator = _get_slim_doc_generator(
        cc_pair, gmail_connector, callback=callback
    )

    for slim_doc_batch in slim_doc_generator:
        for slim_doc in slim_doc_batch:
            if callback:
                if callback.should_stop():
                    raise RuntimeError("gmail_doc_sync: Stop signal detected")

                callback.progress("gmail_doc_sync", 1)

            if isinstance(slim_doc, HierarchyNode):
                # Yield hierarchy node permissions to be processed in outer layer
                if slim_doc.external_access:
                    yield NodeExternalAccess(
                        external_access=slim_doc.external_access,
                        raw_node_id=slim_doc.raw_node_id,
                        source=DocumentSource.GMAIL.value,
                    )
                continue
            if slim_doc.external_access is None:
                logger.warning(f"No permissions found for document {slim_doc.id}")
                continue

            yield DocExternalAccess(
                doc_id=slim_doc.id,
                external_access=slim_doc.external_access,
            )
