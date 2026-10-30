from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileMetadata:
    file_id: str
    filename: str
    size_bytes: int
    upload_time: float
    # Tenant that created the file. ``None`` only for legacy metadata written before
    # tenant binding existed; such files are never visible to any tenant.
    tenant_id: str | None = None


def _is_valid_file_id(file_id: str) -> bool:
    """File ids are server-generated UUID4 strings; reject anything else so a crafted
    id can never address a path outside the storage dir or a ``.meta.json`` file."""
    try:
        return str(uuid.UUID(file_id)) == file_id
    except ValueError:
        return False


class FileStorageService:
    """Service for managing uploaded files with UUID-based storage.

    Every file records the tenant that created it; reads, deletes and listings are
    scoped to the calling tenant. Another tenant's file looks exactly like a missing
    one (callers answer 404, never 403).
    """

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, file_id: str) -> Path:
        """Get the filesystem path for a file ID."""
        return self.storage_dir / file_id

    def _get_metadata_path(self, file_id: str) -> Path:
        """Get the filesystem path for file metadata."""
        return self.storage_dir / f"{file_id}.meta.json"

    def save_file(self, content: bytes, filename: str, tenant_id: str) -> str:
        """Save file content and return a unique file ID.

        Args:
            content: Raw file bytes to store
            filename: Original filename for metadata
            tenant_id: Tenant that owns the file (recorded in its metadata)

        Returns:
            UUID string identifying the stored file
        """
        file_id = str(uuid.uuid4())
        file_path = self._get_file_path(file_id)
        metadata_path = self._get_metadata_path(file_id)

        # Write file content
        file_path.write_bytes(content)

        # Write metadata
        metadata = FileMetadata(
            file_id=file_id,
            filename=filename,
            size_bytes=len(content),
            upload_time=time.time(),
            tenant_id=tenant_id,
        )
        metadata_path.write_text(json.dumps(asdict(metadata)), encoding="utf-8")

        return file_id

    def _read_metadata(self, file_id: str) -> FileMetadata | None:
        """Return the file's metadata, or None if it is missing or unreadable."""
        metadata_path = self._get_metadata_path(file_id)
        if not metadata_path.exists():
            return None
        try:
            meta_dict = json.loads(metadata_path.read_text(encoding="utf-8"))
            return FileMetadata(**meta_dict)
        except (json.JSONDecodeError, TypeError, OSError):
            return None

    def _owned_metadata(self, file_id: str, tenant_id: str) -> FileMetadata | None:
        """Metadata for ``file_id`` if it exists AND belongs to ``tenant_id``."""
        if not _is_valid_file_id(file_id) or not self._get_file_path(file_id).is_file():
            return None
        metadata = self._read_metadata(file_id)
        if metadata is None or metadata.tenant_id != tenant_id:
            return None
        return metadata

    def get_file(self, file_id: str, tenant_id: str) -> tuple[bytes, FileMetadata]:
        """Retrieve file content and metadata by ID.

        Args:
            file_id: UUID of the file to retrieve
            tenant_id: Tenant making the request; must own the file

        Returns:
            Tuple of (file_content, metadata)

        Raises:
            FileNotFoundError: If file_id doesn't exist or belongs to another tenant
        """
        metadata = self._owned_metadata(file_id, tenant_id)
        if metadata is None:
            raise FileNotFoundError(f"File with ID '{file_id}' not found")
        return self._get_file_path(file_id).read_bytes(), metadata

    def delete_file(self, file_id: str, tenant_id: str) -> bool:
        """Delete a file and its metadata by ID.

        Args:
            file_id: UUID of the file to delete
            tenant_id: Tenant making the request; must own the file

        Returns:
            True if the file was deleted, False if it didn't exist or isn't the tenant's
        """
        if self._owned_metadata(file_id, tenant_id) is None:
            return False
        return self._delete(file_id)

    def _delete(self, file_id: str) -> bool:
        """Remove a file and its metadata unconditionally (internal use only)."""
        file_path = self._get_file_path(file_id)
        metadata_path = self._get_metadata_path(file_id)

        existed = file_path.exists()

        # Remove both file and metadata if they exist
        if file_path.exists():
            file_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()

        return existed

    def list_files(self, tenant_id: str) -> list[FileMetadata]:
        """List the stored files that belong to ``tenant_id``.

        Returns:
            List of FileMetadata objects for the tenant's files only
        """
        result: list[FileMetadata] = []

        for metadata_path in self.storage_dir.glob("*.meta.json"):
            try:
                meta_dict = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata = FileMetadata(**meta_dict)
            except (json.JSONDecodeError, TypeError):
                # Skip invalid metadata files
                continue
            if metadata.tenant_id == tenant_id:
                result.append(metadata)

        return result

    def cleanup_expired_files(self, max_age_sec: int) -> int:
        """Remove files older than the specified age (across all tenants).

        Args:
            max_age_sec: Maximum age in seconds before files are deleted

        Returns:
            Number of files deleted
        """
        current_time = time.time()
        deleted_count = 0

        for metadata_path in self.storage_dir.glob("*.meta.json"):
            try:
                meta_dict = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata = FileMetadata(**meta_dict)

                if current_time - metadata.upload_time > max_age_sec and self._delete(
                    metadata.file_id
                ):
                    deleted_count += 1
            except (json.JSONDecodeError, TypeError, FileNotFoundError):
                # Skip invalid or already-deleted files
                continue

        return deleted_count
