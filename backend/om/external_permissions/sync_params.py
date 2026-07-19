"""Per-source permission-sync configuration + typed lookups.

A connector source can opt into up to three independent permission behaviours:

* **doc-sync**   — periodically pull each document's ACL from the source system;
* **group-sync** — periodically pull the source's group memberships into
  external-team ACLs;
* **censoring**  — no indexed ACL at all; results are filtered per-user at query
  time instead (see ``post_query_censoring``).

Everything the rest of the system needs to know about "what does source X do for
permissions" is answered here, from a single registry. The registry *values*
(which function, which cadence, which flags) are behavioural facts about each
connector; the registry layout and the lookups are a WS-B clean-room rewrite.
"""

from collections.abc import Generator
from typing import Optional
from typing import TYPE_CHECKING

from pydantic import BaseModel

from om.configs.app_configs import CONFLUENCE_PERMISSION_DOC_SYNC_FREQUENCY
from om.configs.app_configs import CONFLUENCE_PERMISSION_GROUP_SYNC_FREQUENCY
from om.configs.app_configs import DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY
from om.configs.app_configs import GITHUB_PERMISSION_DOC_SYNC_FREQUENCY
from om.configs.app_configs import GITHUB_PERMISSION_GROUP_SYNC_FREQUENCY
from om.configs.app_configs import GOOGLE_DRIVE_PERMISSION_GROUP_SYNC_FREQUENCY
from om.configs.app_configs import JIRA_PERMISSION_DOC_SYNC_FREQUENCY
from om.configs.app_configs import JIRA_PERMISSION_GROUP_SYNC_FREQUENCY
from om.configs.app_configs import SHAREPOINT_PERMISSION_DOC_SYNC_FREQUENCY
from om.configs.app_configs import SHAREPOINT_PERMISSION_GROUP_SYNC_FREQUENCY
from om.configs.app_configs import SLACK_PERMISSION_DOC_SYNC_FREQUENCY
from om.configs.app_configs import TEAMS_PERMISSION_DOC_SYNC_FREQUENCY
from om.configs.constants import DocumentSource
from om.connectors.folder.doc_sync import folder_doc_sync
from om.external_permissions.confluence.doc_sync import confluence_doc_sync
from om.external_permissions.confluence.group_sync import confluence_group_sync
from om.external_permissions.github.doc_sync import github_doc_sync
from om.external_permissions.github.group_sync import github_group_sync
from om.external_permissions.gmail.doc_sync import gmail_doc_sync
from om.external_permissions.google_drive.doc_sync import gdrive_doc_sync
from om.external_permissions.google_drive.group_sync import gdrive_group_sync
from om.external_permissions.jira.doc_sync import jira_doc_sync
from om.external_permissions.jira.group_sync import jira_group_sync
from om.external_permissions.perm_sync_types import CensoringFuncType
from om.external_permissions.perm_sync_types import DocSyncFuncType
from om.external_permissions.perm_sync_types import FetchAllDocumentsFunction
from om.external_permissions.perm_sync_types import FetchAllDocumentsIdsFunction
from om.external_permissions.perm_sync_types import GroupSyncFuncType
from om.external_permissions.salesforce.postprocessing import censor_salesforce_chunks
from om.external_permissions.sharepoint.doc_sync import sharepoint_doc_sync
from om.external_permissions.sharepoint.group_sync import sharepoint_group_sync
from om.external_permissions.slack.doc_sync import slack_doc_sync
from om.external_permissions.teams.doc_sync import teams_doc_sync

if TYPE_CHECKING:
    from om.access.models import DocExternalAccess  # noqa
    from om.db.models import ConnectorCredentialPair  # noqa
    from om.indexing.indexing_heartbeat import IndexingHeartbeatInterface  # noqa


# --------------------------------------------------------------------------- #
# Config shapes (field names are the data contract consumed across the app)
# --------------------------------------------------------------------------- #


class DocSyncConfig(BaseModel):
    doc_sync_frequency: int
    doc_sync_func: DocSyncFuncType
    initial_index_should_sync: bool


class GroupSyncConfig(BaseModel):
    group_sync_frequency: int
    group_sync_func: GroupSyncFuncType
    group_sync_is_cc_pair_agnostic: bool


class CensoringConfig(BaseModel):
    chunk_censoring_func: CensoringFuncType


class SyncConfig(BaseModel):
    """A source's permission behaviour. Any of the three may be ``None`` (absent)."""

    doc_sync_config: DocSyncConfig | None = None
    group_sync_config: GroupSyncConfig | None = None
    censoring_config: CensoringConfig | None = None


def mock_doc_sync(
    cc_pair: "ConnectorCredentialPair",  # noqa: ARG001
    fetch_all_docs_fn: FetchAllDocumentsFunction,  # noqa: ARG001
    fetch_all_docs_ids_fn: FetchAllDocumentsIdsFunction,  # noqa: ARG001
    callback: Optional["IndexingHeartbeatInterface"],  # noqa: ARG001
) -> Generator["DocExternalAccess", None, None]:
    """No-op doc-sync used by the mock connector in tests (perms come from indexing)."""
    yield from ()


# --------------------------------------------------------------------------- #
# Declarative builders keep the registry below readable
# --------------------------------------------------------------------------- #


def _doc(
    func: DocSyncFuncType, frequency: int, *, sync_on_initial_index: bool
) -> DocSyncConfig:
    return DocSyncConfig(
        doc_sync_frequency=frequency,
        doc_sync_func=func,
        initial_index_should_sync=sync_on_initial_index,
    )


def _group(
    func: GroupSyncFuncType, frequency: int, *, cc_pair_agnostic: bool = False
) -> GroupSyncConfig:
    return GroupSyncConfig(
        group_sync_frequency=frequency,
        group_sync_func=func,
        group_sync_is_cc_pair_agnostic=cc_pair_agnostic,
    )


# The single source of truth. Sources absent from this map do no permission sync.
# NOTE: Slack and Teams intentionally have no group-sync — their access is per-user
# at the channel level, so there are no source groups to map.
_SYNC_REGISTRY: dict[DocumentSource, SyncConfig] = {
    DocumentSource.GOOGLE_DRIVE: SyncConfig(
        doc_sync_config=_doc(
            gdrive_doc_sync, DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY, sync_on_initial_index=True
        ),
        group_sync_config=_group(
            gdrive_group_sync, GOOGLE_DRIVE_PERMISSION_GROUP_SYNC_FREQUENCY
        ),
    ),
    DocumentSource.CONFLUENCE: SyncConfig(
        doc_sync_config=_doc(
            confluence_doc_sync,
            CONFLUENCE_PERMISSION_DOC_SYNC_FREQUENCY,
            sync_on_initial_index=False,
        ),
        group_sync_config=_group(
            confluence_group_sync,
            CONFLUENCE_PERMISSION_GROUP_SYNC_FREQUENCY,
            cc_pair_agnostic=True,
        ),
    ),
    DocumentSource.JIRA: SyncConfig(
        doc_sync_config=_doc(
            jira_doc_sync, JIRA_PERMISSION_DOC_SYNC_FREQUENCY, sync_on_initial_index=True
        ),
        group_sync_config=_group(
            jira_group_sync, JIRA_PERMISSION_GROUP_SYNC_FREQUENCY, cc_pair_agnostic=True
        ),
    ),
    DocumentSource.GITHUB: SyncConfig(
        doc_sync_config=_doc(
            github_doc_sync, GITHUB_PERMISSION_DOC_SYNC_FREQUENCY, sync_on_initial_index=True
        ),
        group_sync_config=_group(
            github_group_sync, GITHUB_PERMISSION_GROUP_SYNC_FREQUENCY
        ),
    ),
    DocumentSource.SHAREPOINT: SyncConfig(
        doc_sync_config=_doc(
            sharepoint_doc_sync,
            SHAREPOINT_PERMISSION_DOC_SYNC_FREQUENCY,
            sync_on_initial_index=True,
        ),
        group_sync_config=_group(
            sharepoint_group_sync, SHAREPOINT_PERMISSION_GROUP_SYNC_FREQUENCY
        ),
    ),
    DocumentSource.SLACK: SyncConfig(
        doc_sync_config=_doc(
            slack_doc_sync, SLACK_PERMISSION_DOC_SYNC_FREQUENCY, sync_on_initial_index=True
        ),
    ),
    DocumentSource.TEAMS: SyncConfig(
        doc_sync_config=_doc(
            teams_doc_sync, TEAMS_PERMISSION_DOC_SYNC_FREQUENCY, sync_on_initial_index=True
        ),
    ),
    DocumentSource.GMAIL: SyncConfig(
        doc_sync_config=_doc(
            gmail_doc_sync, DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY, sync_on_initial_index=False
        ),
    ),
    DocumentSource.FOLDER: SyncConfig(
        doc_sync_config=_doc(
            folder_doc_sync, DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY, sync_on_initial_index=True
        ),
    ),
    DocumentSource.MOCK_CONNECTOR: SyncConfig(
        doc_sync_config=_doc(
            mock_doc_sync, DEFAULT_PERMISSION_DOC_SYNC_FREQUENCY, sync_on_initial_index=True
        ),
    ),
    # Censoring-only: no indexed ACL; chunks are filtered per-user at query time.
    DocumentSource.SALESFORCE: SyncConfig(
        censoring_config=CensoringConfig(chunk_censoring_func=censor_salesforce_chunks),
    ),
}


# --------------------------------------------------------------------------- #
# Lookups — all share a single ``.get()`` so an unknown source is simply "no sync"
# --------------------------------------------------------------------------- #


def get_source_perm_sync_config(source: DocumentSource) -> SyncConfig | None:
    """The full permission-sync config for a source, or ``None`` if it has none."""
    return _SYNC_REGISTRY.get(source)


def check_if_valid_sync_source(source: DocumentSource) -> bool:
    return source in _SYNC_REGISTRY


def source_requires_doc_sync(source: DocumentSource) -> bool:
    config = _SYNC_REGISTRY.get(source)
    return config is not None and config.doc_sync_config is not None


def source_requires_external_group_sync(source: DocumentSource) -> bool:
    config = _SYNC_REGISTRY.get(source)
    return config is not None and config.group_sync_config is not None


def source_group_sync_is_cc_pair_agnostic(source: DocumentSource) -> bool:
    config = _SYNC_REGISTRY.get(source)
    return bool(
        config
        and config.group_sync_config
        and config.group_sync_config.group_sync_is_cc_pair_agnostic
    )


def source_should_fetch_permissions_during_indexing(source: DocumentSource) -> bool:
    config = _SYNC_REGISTRY.get(source)
    return bool(
        config
        and config.doc_sync_config
        and config.doc_sync_config.initial_index_should_sync
    )


def get_all_cc_pair_agnostic_group_sync_sources() -> set[DocumentSource]:
    return {
        source
        for source, config in _SYNC_REGISTRY.items()
        if config.group_sync_config is not None
        and config.group_sync_config.group_sync_is_cc_pair_agnostic
    }


def get_all_censoring_enabled_sources() -> set[DocumentSource]:
    return {
        source
        for source, config in _SYNC_REGISTRY.items()
        if config.censoring_config is not None
    }
