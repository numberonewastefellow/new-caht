import fnmatch
import hashlib
import mimetypes
import os
import platform
import stat
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from om.access.models import ExternalAccess
from om.configs.app_configs import FOLDER_CONNECTOR_ALLOWED_DIRECTORIES
from om.configs.app_configs import FOLDER_CONNECTOR_MAX_FILE_SIZE_MB
from om.configs.app_configs import FOLDER_CONNECTOR_MAX_WORKERS
from om.configs.app_configs import INDEX_BATCH_SIZE
from om.configs.constants import DocumentSource
from om.connectors.file.utils import _process_file
from om.connectors.interfaces import GenerateDocumentsOutput
from om.connectors.interfaces import GenerateSlimDocumentOutput
from om.connectors.interfaces import LoadConnector
from om.connectors.interfaces import PollConnector
from om.connectors.interfaces import SecondsSinceUnixEpoch
from om.connectors.interfaces import SlimConnector
from om.connectors.models import SlimDocument
from om.utils.logger import setup_logger
from om.utils.threadpool_concurrency import run_functions_tuples_in_parallel


logger = setup_logger()


def _compute_doc_id(abs_path: str) -> str:
    """Stable document ID from absolute file path."""
    path_hash = hashlib.sha256(abs_path.encode("utf-8")).hexdigest()[:32]
    return f"FOLDER_CONNECTOR__{path_hash}"


def _is_path_allowed(real_path: str) -> bool:
    """Check if a path falls within the allowed directories whitelist."""
    allowed = FOLDER_CONNECTOR_ALLOWED_DIRECTORIES.strip()
    if not allowed:
        return True  # No restrictions

    allowed_dirs = [d.strip() for d in allowed.split(",") if d.strip()]
    real_path_lower = real_path.replace("\\", "/").lower()
    for allowed_dir in allowed_dirs:
        normalized = allowed_dir.replace("\\", "/").lower().rstrip("/")
        if real_path_lower.startswith(normalized + "/") or real_path_lower == normalized:
            return True
    return False


def _get_file_external_access(file_path: str) -> ExternalAccess:
    """Read OS file permissions and map to ExternalAccess model.

    Linux: Uses stat() to get owner uid/gid and world-readable bit.
    Windows: Uses win32security to read file DACLs (falls back to basic stat).
    """
    external_user_emails: set[str] = set()
    external_team_ids: set[str] = set()
    is_public = False

    try:
        file_stat = os.stat(file_path)

        if platform.system() != "Windows":
            # Unix: resolve uid to username, gid to group name
            import grp
            import pwd

            try:
                pw = pwd.getpwuid(file_stat.st_uid)
                external_user_emails.add(pw.pw_name)
            except KeyError:
                pass

            try:
                gr = grp.getgrgid(file_stat.st_gid)
                external_team_ids.add(f"folder__{gr.gr_name}")
            except KeyError:
                pass

            # Check world-readable
            is_public = bool(file_stat.st_mode & stat.S_IROTH)
        else:
            # Windows: try win32security, fall back to basic
            try:
                import win32security  # type: ignore

                sd = win32security.GetFileSecurity(
                    file_path, win32security.OWNER_SECURITY_INFORMATION
                )
                owner_sid = sd.GetSecurityDescriptorOwner()
                name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
                external_user_emails.add(f"{domain}\\{name}")
            except Exception:
                # Fall back: mark as public since we can't read ACLs
                is_public = True

    except OSError as e:
        logger.warning(f"Failed to read permissions for {file_path}: {e}")
        # If we can't read permissions, treat as private (safe default)

    return ExternalAccess(
        external_user_emails=external_user_emails,
        external_team_ids=external_team_ids,
        is_public=is_public,
    )


def _process_single_file(
    file_path: str,
    folder_root: str,
    pdf_pass: str | None,
    include_permissions: bool = False,
) -> tuple[list[Any], ExternalAccess | None]:
    """Process a single file from the filesystem.

    Returns a tuple of (documents, external_access).
    """
    abs_path = os.path.realpath(file_path)
    file_id = _compute_doc_id(abs_path)
    relative_path = os.path.relpath(file_path, folder_root)
    mime_type, _ = mimetypes.guess_type(file_path)

    try:
        with open(file_path, "rb") as f:
            docs = _process_file(
                file_id=file_id,
                file_name=relative_path,
                file=f,
                metadata={"folder_path": folder_root, "relative_path": relative_path},
                pdf_pass=pdf_pass,
                file_type=mime_type,
                default_source=DocumentSource.FOLDER,
                doc_id_prefix="FOLDER_CONNECTOR__",
            )
    except Exception as e:
        logger.error(f"Failed to process file {file_path}: {e}")
        return [], None

    # For SYNC mode, read OS-level permissions
    ext_access = None
    if include_permissions:
        ext_access = _get_file_external_access(file_path)

    return docs, ext_access


class LocalFolderConnector(LoadConnector, PollConnector, SlimConnector):
    """
    Connector that reads local filesystem folders recursively and yields Documents.
    Supports parallel file extraction and OS-level permission syncing.
    """

    def __init__(
        self,
        folder_paths: list[str],
        file_extensions: list[str] | None = None,
        recursive: bool = True,
        follow_symlinks: bool = False,
        exclude_patterns: list[str] | None = None,
        max_file_size_mb: int | None = None,
        batch_size: int = INDEX_BATCH_SIZE,
    ) -> None:
        self.folder_paths = [str(Path(p).resolve()) for p in folder_paths]
        self.file_extensions = (
            [ext.lower().lstrip(".") for ext in file_extensions]
            if file_extensions
            else None
        )
        self.recursive = recursive
        self.follow_symlinks = follow_symlinks
        self.exclude_patterns = exclude_patterns or []
        self.max_file_size_mb = max_file_size_mb or FOLDER_CONNECTOR_MAX_FILE_SIZE_MB
        self.batch_size = batch_size
        self.pdf_pass: str | None = None

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        self.pdf_pass = credentials.get("pdf_password")
        return None

    def validate_connector_settings(self) -> None:
        """Validate folder paths exist, are directories, and are within allowed directories."""
        for folder_path in self.folder_paths:
            real_path = os.path.realpath(folder_path)

            if not _is_path_allowed(real_path):
                raise ValueError(
                    f"Folder path '{folder_path}' is not within allowed directories. "
                    f"Allowed: {FOLDER_CONNECTOR_ALLOWED_DIRECTORIES}"
                )

            if not os.path.exists(real_path):
                raise ValueError(f"Folder path '{folder_path}' does not exist.")

            if not os.path.isdir(real_path):
                raise ValueError(f"Path '{folder_path}' is not a directory.")

    def _walk_all_files(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[tuple[str, str]]:
        """Walk all folders and return list of (file_path, folder_root) tuples.

        If start/end are provided, only includes files with mtime in [start, end].
        """
        results: list[tuple[str, str]] = []

        for folder_path in self.folder_paths:
            real_folder = os.path.realpath(folder_path)

            if not os.path.exists(real_folder):
                logger.warning(
                    f"Skipping missing folder path: {folder_path} "
                    f"(resolved to {real_folder}). "
                    "If this folder was removed, consider removing it from the "
                    "connector configuration and running a prune."
                )
                continue

            if not os.path.isdir(real_folder):
                logger.warning(
                    f"Skipping non-directory path: {folder_path} "
                    f"(resolved to {real_folder})"
                )
                continue

            if not _is_path_allowed(real_folder):
                logger.warning(
                    f"Skipping disallowed folder: {folder_path} "
                    f"(resolved to {real_folder}). "
                    f"Allowed directories: {FOLDER_CONNECTOR_ALLOWED_DIRECTORIES}"
                )
                continue

            for dirpath, dirnames, filenames in os.walk(
                real_folder, followlinks=self.follow_symlinks
            ):
                if not self.recursive and dirpath != real_folder:
                    dirnames.clear()
                    continue

                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)

                    # Resolve symlinks for security check
                    real_file = os.path.realpath(file_path)
                    if not _is_path_allowed(real_file):
                        continue

                    # Exclude patterns
                    if any(
                        fnmatch.fnmatch(filename, pat)
                        or fnmatch.fnmatch(
                            os.path.relpath(file_path, real_folder), pat
                        )
                        for pat in self.exclude_patterns
                    ):
                        continue

                    # Extension filter
                    ext = os.path.splitext(filename)[1].lower().lstrip(".")
                    if self.file_extensions and ext not in self.file_extensions:
                        continue

                    # File size check
                    try:
                        file_size = os.path.getsize(file_path)
                        if self.max_file_size_mb and file_size > (
                            self.max_file_size_mb * 1024 * 1024
                        ):
                            logger.debug(
                                f"Skipping large file ({file_size} bytes): {file_path}"
                            )
                            continue
                    except OSError:
                        continue

                    # mtime filter for incremental polling
                    if start or end:
                        try:
                            mtime = datetime.fromtimestamp(
                                os.path.getmtime(file_path), tz=timezone.utc
                            )
                            if start and mtime < start:
                                continue
                            if end and mtime > end:
                                continue
                        except OSError:
                            continue

                    results.append((file_path, real_folder))

        return results

    def _yield_folder_documents(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        include_permissions: bool = False,
    ) -> GenerateDocumentsOutput:
        """Core logic: walk directories, parallel extract, batch yield."""
        all_files = self._walk_all_files(start=start, end=end)

        if not all_files:
            logger.info("No files found to index in folder connector.")
            return

        logger.info(f"Found {len(all_files)} files to process in folder connector.")

        # Process files in batches with parallel extraction
        for batch_start in range(0, len(all_files), self.batch_size):
            batch_files = all_files[batch_start : batch_start + self.batch_size]

            # Build parallel function calls
            functions_with_args = [
                (
                    _process_single_file,
                    (file_path, folder_root, self.pdf_pass, include_permissions),
                )
                for file_path, folder_root in batch_files
            ]

            # Execute in parallel
            results = run_functions_tuples_in_parallel(
                functions_with_args,
                allow_failures=True,
                max_workers=FOLDER_CONNECTOR_MAX_WORKERS,
            )

            # Collect documents from results
            batch_docs = []
            for result in results:
                if result is None:
                    continue
                docs, ext_access = result
                for doc in docs:
                    # Attach external access if available (SYNC mode)
                    if ext_access is not None:
                        doc.external_access = ext_access
                    batch_docs.append(doc)

            if batch_docs:
                yield batch_docs

    def load_from_state(self) -> GenerateDocumentsOutput:
        """Full scan: index all files in all folders."""
        yield from self._yield_folder_documents()

    def poll_source(
        self, start: SecondsSinceUnixEpoch, end: SecondsSinceUnixEpoch
    ) -> GenerateDocumentsOutput:
        """Incremental: only files modified since last sync."""
        start_dt = datetime.fromtimestamp(start, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(end, tz=timezone.utc)
        yield from self._yield_folder_documents(start=start_dt, end=end_dt)

    def retrieve_all_slim_docs(self) -> GenerateSlimDocumentOutput:
        """For pruning: yields SlimDocument IDs for every file currently in folders.

        The pruning system compares these against the index and removes stale documents
        for files that have been deleted from the filesystem.
        """
        all_files = self._walk_all_files()

        slim_docs: list[SlimDocument] = []
        for file_path, _ in all_files:
            abs_path = os.path.realpath(file_path)
            doc_id = _compute_doc_id(abs_path)
            slim_docs.append(SlimDocument(id=doc_id, perm_sync_data=None))

            if len(slim_docs) >= self.batch_size:
                yield slim_docs
                slim_docs = []

        if slim_docs:
            yield slim_docs


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python connector.py <folder_path> [<folder_path2> ...]")
        sys.exit(1)

    connector = LocalFolderConnector(folder_paths=sys.argv[1:])
    connector.load_credentials({})
    for batch in connector.load_from_state():
        for doc in batch:
            print(f"DOC: {doc.id} | {doc.semantic_identifier} | {len(doc.sections)} sections")
