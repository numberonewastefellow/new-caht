"""Permission sync for the Folder Connector.

Re-reads OS file permissions for indexed documents and returns updated ACLs.
Used by the periodic permission sync task when access_type=SYNC.
"""

import hashlib
import os
from collections.abc import Generator
from typing import Any

from om.access.models import DocExternalAccess
from om.access.models import ExternalAccess
from om.connectors.folder.connector import _get_file_external_access
from om.db.models import ConnectorCredentialPair
from om.indexing.indexing_heartbeat import IndexingHeartbeatInterface
from om.utils.logger import setup_logger


logger = setup_logger()


def folder_doc_sync(
    cc_pair: ConnectorCredentialPair,
    fetch_all_existing_docs_fn: Any,  # noqa: ARG001
    fetch_all_existing_docs_ids_fn: Any,  # noqa: ARG001
    callback: IndexingHeartbeatInterface | None,
) -> Generator[DocExternalAccess, None, None]:
    """Re-read OS file permissions for all indexed documents.

    Matches the DocSyncFuncType signature:
        (cc_pair, fetch_all_docs_fn, fetch_all_docs_ids_fn, callback)
        -> Generator[ElementExternalAccess, None, None]

    Called by the permission sync infrastructure for FOLDER connectors
    with access_type=SYNC. Yields DocExternalAccess for each file.
    """
    config: dict[str, Any] = cc_pair.connector.connector_specific_config or {}
    folder_paths: list[str] = config.get("folder_paths", [])
    recursive: bool = config.get("recursive", True)

    if not folder_paths:
        logger.warning(
            f"No folder_paths configured for cc_pair {cc_pair.id}, "
            "skipping permission sync"
        )
        return

    # Walk all folders and yield permission info per file
    for folder_path in folder_paths:
        real_folder = os.path.realpath(folder_path)
        if not os.path.isdir(real_folder):
            logger.warning(f"Folder not found during perm sync: {folder_path}")
            continue

        for dirpath, dirnames, filenames in os.walk(real_folder):
            if not recursive and dirpath != real_folder:
                dirnames.clear()
                continue

            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                abs_path = os.path.realpath(file_path)
                path_hash = hashlib.sha256(
                    abs_path.encode("utf-8")
                ).hexdigest()[:32]
                doc_id = f"FOLDER_CONNECTOR__{path_hash}"

                if not os.path.exists(abs_path):
                    yield DocExternalAccess(
                        external_access=ExternalAccess(
                            external_user_emails=set(),
                            external_team_ids=set(),
                            is_public=False,
                        ),
                        doc_id=doc_id,
                    )
                    continue

                ext_access = _get_file_external_access(abs_path)
                yield DocExternalAccess(
                    external_access=ext_access,
                    doc_id=doc_id,
                )

                if callback:
                    if callback.should_stop():
                        raise RuntimeError(
                            "folder_doc_sync: Stop signal detected"
                        )
                    callback.progress("folder_doc_sync", 1)
