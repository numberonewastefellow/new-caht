from collections.abc import Generator

from om.external_permissions.perm_sync_types import FetchAllDocumentsFunction
from om.external_permissions.perm_sync_types import FetchAllDocumentsIdsFunction
from om.external_permissions.utils import generic_doc_sync
from om.access.models import ElementExternalAccess
from om.configs.constants import DocumentSource
from om.connectors.jira.connector import JiraConnector
from om.db.models import ConnectorCredentialPair
from om.indexing.indexing_heartbeat import IndexingHeartbeatInterface
from om.utils.logger import setup_logger

logger = setup_logger()

JIRA_DOC_SYNC_TAG = "jira_doc_sync"


def jira_doc_sync(
    cc_pair: ConnectorCredentialPair,
    fetch_all_existing_docs_fn: FetchAllDocumentsFunction,  # noqa: ARG001
    fetch_all_existing_docs_ids_fn: FetchAllDocumentsIdsFunction,
    callback: IndexingHeartbeatInterface | None = None,
) -> Generator[ElementExternalAccess, None, None]:
    jira_connector = JiraConnector(
        **cc_pair.connector.connector_specific_config,
    )
    credential_json = (
        cc_pair.credential.credential_json.get_value(apply_mask=False)
        if cc_pair.credential.credential_json
        else {}
    )
    jira_connector.load_credentials(credential_json)

    yield from generic_doc_sync(
        cc_pair=cc_pair,
        fetch_all_existing_docs_ids_fn=fetch_all_existing_docs_ids_fn,
        callback=callback,
        doc_source=DocumentSource.JIRA,
        slim_connector=jira_connector,
        label=JIRA_DOC_SYNC_TAG,
    )
