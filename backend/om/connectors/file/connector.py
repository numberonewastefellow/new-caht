import json
import os
from pathlib import Path
from typing import Any

from om.configs.app_configs import INDEX_BATCH_SIZE
from om.connectors.file.utils import _process_file
from om.connectors.interfaces import GenerateDocumentsOutput
from om.connectors.interfaces import LoadConnector
from om.connectors.models import Document
from om.connectors.models import HierarchyNode
from om.file_store.file_store import get_default_file_store
from om.utils.logger import setup_logger


logger = setup_logger()


class LocalFileConnector(LoadConnector):
    """
    Connector that reads files from Postgres and yields Documents, including
    embedded image extraction without summarization.

    file_locations are S3/Filestore UUIDs
    file_names are the names of the files
    """

    # Note: file_names is a required parameter, but should not break backwards compatibility.
    # If add_file_names migration is not run, old file connector configs will not have file_names.
    # file_names is only used for display purposes in the UI and file_locations is used as a fallback.
    def __init__(
        self,
        file_locations: list[Path | str],
        file_names: list[str] | None = None,  # noqa: ARG002
        zip_metadata_file_id: str | None = None,
        zip_metadata: dict[str, Any] | None = None,  # Deprecated, for backwards compat
        batch_size: int = INDEX_BATCH_SIZE,
    ) -> None:
        self.file_locations = [str(loc) for loc in file_locations]
        self.batch_size = batch_size
        self.pdf_pass: str | None = None
        self._zip_metadata_file_id = zip_metadata_file_id
        self._zip_metadata_deprecated = zip_metadata

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        self.pdf_pass = credentials.get("pdf_password")

        return None

    def load_from_state(self) -> GenerateDocumentsOutput:
        """
        Iterates over each file path, fetches from Postgres, tries to parse text
        or images, and yields Document batches.
        """
        # Load metadata dict at start (from file store or deprecated inline format)
        zip_metadata: dict[str, Any] = {}
        if self._zip_metadata_file_id:
            try:
                file_store = get_default_file_store()
                metadata_io = file_store.read_file(
                    file_id=self._zip_metadata_file_id, mode="b"
                )
                metadata_bytes = metadata_io.read()
                loaded_metadata = json.loads(metadata_bytes)
                if isinstance(loaded_metadata, list):
                    zip_metadata = {d["filename"]: d for d in loaded_metadata}
                else:
                    zip_metadata = loaded_metadata
            except Exception as e:
                logger.warning(f"Failed to load metadata from file store: {e}")
        elif self._zip_metadata_deprecated:
            logger.warning(
                "Using deprecated inline zip_metadata dict. "
                "Re-upload files to use the new file store format."
            )
            zip_metadata = self._zip_metadata_deprecated

        documents: list[Document | HierarchyNode] = []

        for file_id in self.file_locations:
            file_store = get_default_file_store()
            file_record = file_store.read_file_record(file_id=file_id)
            if not file_record:
                # typically an unsupported extension
                logger.warning(f"No file record found for '{file_id}' in PG; skipping.")
                continue

            metadata = zip_metadata.get(
                file_record.display_name, {}
            ) or zip_metadata.get(os.path.basename(file_record.display_name), {})
            file_io = file_store.read_file(file_id=file_id, mode="b")
            new_docs = _process_file(
                file_id=file_id,
                file_name=file_record.display_name,
                file=file_io,
                metadata=metadata,
                pdf_pass=self.pdf_pass,
                file_type=file_record.file_type,
            )
            documents.extend(new_docs)

            if len(documents) >= self.batch_size:
                yield documents

                documents = []

        if documents:
            yield documents


if __name__ == "__main__":
    connector = LocalFileConnector(
        file_locations=[os.environ["TEST_FILE"]],
        file_names=[os.environ["TEST_FILE"]],
    )
    connector.load_credentials({"pdf_password": os.environ.get("PDF_PASSWORD")})
    doc_batches = connector.load_from_state()
    for batch in doc_batches:
        print("BATCH:", batch)
