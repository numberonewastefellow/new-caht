"""Tests for the LocalFolderConnector.

Covers:
  1. Full-scan ingestion (load_from_state)
  2. Incremental polling (poll_source with mtime filtering)
  3. Slim document retrieval for pruning (retrieve_all_slim_docs)
  4. Access control — OS permission mapping (_get_file_external_access)
  5. Parallel extraction and per-file error handling
  6. Path security (allowed directories whitelist)
  7. File filtering (extensions, exclude patterns, size limits)
  8. Document ID stability
  9. Doc sync (permission sync function)
  10. Registry integration

Run with:
  pytest tests/unit/onyx/connectors/folder/test_folder_connector.py -v
"""

import hashlib
import os
import stat
import time
from datetime import datetime
from datetime import timezone
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Lazy imports — avoid triggering the full import chain at collection time.
# The folder connector imports file/utils.py → image_utils → file_store →
# puremagic, which may not be installed in all test environments.
# We mock the problematic import before loading the connector module.
# ---------------------------------------------------------------------------

# Pre-mock the heavy dependency chain so the connector can be imported
# even when puremagic / file_store deps are not installed.
import sys
from types import ModuleType

_MOCK_MODULES = [
    "puremagic",
    "onyx.file_store.file_store",
    "onyx.file_processing.image_utils",
]

_original_modules: dict[str, ModuleType | None] = {}
for _mod_name in _MOCK_MODULES:
    if _mod_name not in sys.modules:
        _original_modules[_mod_name] = None
        sys.modules[_mod_name] = MagicMock()
    else:
        _original_modules[_mod_name] = sys.modules[_mod_name]

# Now safe to import the connector and its helpers
from onyx.configs.constants import DocumentSource  # noqa: E402
from onyx.connectors.folder.connector import _compute_doc_id  # noqa: E402
from onyx.connectors.folder.connector import _get_file_external_access  # noqa: E402
from onyx.connectors.folder.connector import _is_path_allowed  # noqa: E402
from onyx.connectors.folder.connector import LocalFolderConnector  # noqa: E402
from onyx.connectors.folder.doc_sync import folder_doc_sync  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_folder(tmp_path: Path) -> Path:
    """Create a temp directory with mixed file types for testing."""
    (tmp_path / "readme.txt").write_text("Hello from readme")
    (tmp_path / "notes.md").write_text("# Notes\n\nSome markdown content here.")

    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "deep.txt").write_text("Deep nested file content")
    (sub / "data.csv").write_text("col1,col2\na,b\nc,d")

    sub2 = tmp_path / "subdir2"
    sub2.mkdir()
    (sub2 / "report.txt").write_text("Quarterly report content")

    return tmp_path


@pytest.fixture
def connector(temp_folder: Path) -> LocalFolderConnector:
    """Create a connector pointed at the temp folder."""
    c = LocalFolderConnector(folder_paths=[str(temp_folder)])
    c.load_credentials({})
    return c


# ---------------------------------------------------------------------------
# Mock _process_file — returns a lightweight Document per file
# ---------------------------------------------------------------------------


def _mock_process_file(
    file_id: str,
    file_name: str,
    file: object,
    metadata: dict | None,
    pdf_pass: str | None,
    file_type: str | None,
    default_source: DocumentSource = DocumentSource.FILE,
    doc_id_prefix: str = "FILE_CONNECTOR__",
) -> list:
    from onyx.connectors.models import Document
    from onyx.connectors.models import TextSection

    text = ""
    try:
        content = file.read()  # type: ignore
        text = (
            content.decode("utf-8", errors="replace")
            if isinstance(content, bytes)
            else str(content)
        )
    except Exception:
        text = f"content of {file_name}"

    doc = Document(
        id=f"{doc_id_prefix}{file_id}",
        sections=[TextSection(text=text, link=None)],
        source=default_source,
        semantic_identifier=file_name,
        title=file_name,
        doc_updated_at=datetime.now(timezone.utc),
        metadata={},
    )
    return [doc]


PROCESS_FILE_PATCH = "onyx.connectors.folder.connector._process_file"


# ===========================================================================
# 1. Full-scan ingestion — load_from_state
# ===========================================================================


class TestLoadFromState:
    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_indexes_all_files_recursively(
        self, mock_pf: MagicMock, connector: LocalFolderConnector, temp_folder: Path
    ) -> None:
        batches = list(connector.load_from_state())
        all_docs = [doc for batch in batches for doc in batch]
        assert len(all_docs) == 5
        identifiers = {doc.semantic_identifier for doc in all_docs}
        assert any("readme.txt" in s for s in identifiers)
        assert any("deep.txt" in s for s in identifiers)

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_non_recursive_mode(self, mock_pf: MagicMock, temp_folder: Path) -> None:
        c = LocalFolderConnector(folder_paths=[str(temp_folder)], recursive=False)
        c.load_credentials({})
        batches = list(c.load_from_state())
        all_docs = [doc for batch in batches for doc in batch]
        # Only root-level files: readme.txt, notes.md
        assert len(all_docs) == 2

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_multiple_folder_paths(self, mock_pf: MagicMock, temp_folder: Path) -> None:
        sub1 = temp_folder / "subdir"
        sub2 = temp_folder / "subdir2"
        c = LocalFolderConnector(folder_paths=[str(sub1), str(sub2)])
        c.load_credentials({})
        batches = list(c.load_from_state())
        all_docs = [doc for batch in batches for doc in batch]
        # subdir has 2 files, subdir2 has 1 file
        assert len(all_docs) == 3

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_source_is_folder(self, mock_pf: MagicMock, connector: LocalFolderConnector) -> None:
        batches = list(connector.load_from_state())
        all_docs = [doc for batch in batches for doc in batch]
        for doc in all_docs:
            assert doc.source == DocumentSource.FOLDER

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_document_has_content(
        self, mock_pf: MagicMock, connector: LocalFolderConnector
    ) -> None:
        batches = list(connector.load_from_state())
        all_docs = [doc for batch in batches for doc in batch]
        for doc in all_docs:
            assert len(doc.sections) > 0
            assert doc.sections[0].text

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_empty_folder(self, mock_pf: MagicMock, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        c = LocalFolderConnector(folder_paths=[str(empty)])
        c.load_credentials({})
        batches = list(c.load_from_state())
        assert batches == []

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_nonexistent_folder(self, mock_pf: MagicMock, tmp_path: Path) -> None:
        c = LocalFolderConnector(folder_paths=[str(tmp_path / "does_not_exist")])
        c.load_credentials({})
        batches = list(c.load_from_state())
        assert batches == []


# ===========================================================================
# 2. Incremental polling — poll_source
# ===========================================================================


class TestPollSource:
    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_poll_returns_only_modified_files(
        self, mock_pf: MagicMock, tmp_path: Path
    ) -> None:
        # Use a fresh tmp_path (not temp_folder) to control file mtimes precisely.
        # Create old file, backdate it, then create new file after recording start_ts.
        old_file = tmp_path / "old.txt"
        old_file.write_text("Old content")
        # Backdate the old file by 1 hour
        old_mtime = time.time() - 3600
        os.utime(str(old_file), (old_mtime, old_mtime))

        # Record start boundary AFTER backdating old file
        start_ts = time.time() - 1  # small buffer

        new_file = tmp_path / "new_file.txt"
        new_file.write_text("Brand new content")

        end_ts = time.time() + 2

        c = LocalFolderConnector(folder_paths=[str(tmp_path)])
        c.load_credentials({})
        batches = list(c.poll_source(start=start_ts, end=end_ts))
        all_docs = [doc for batch in batches for doc in batch]

        assert len(all_docs) == 1
        assert "new_file.txt" in all_docs[0].semantic_identifier

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_poll_no_changes(self, mock_pf: MagicMock, temp_folder: Path) -> None:
        c = LocalFolderConnector(folder_paths=[str(temp_folder)])
        c.load_credentials({})
        future = time.time() + 3600
        batches = list(c.poll_source(start=future, end=future + 3600))
        assert batches == []


# ===========================================================================
# 3. Slim document retrieval — pruning support
# ===========================================================================


class TestRetrieveAllSlimDocs:
    def test_slim_docs_match_full_scan(self, connector: LocalFolderConnector) -> None:
        slim_batches = list(connector.retrieve_all_slim_docs())
        slim_ids = {sd.id for batch in slim_batches for sd in batch}
        assert len(slim_ids) == 5
        for sid in slim_ids:
            assert sid.startswith("FOLDER_CONNECTOR__")

    def test_slim_doc_ids_are_stable(self, temp_folder: Path) -> None:
        c1 = LocalFolderConnector(folder_paths=[str(temp_folder)])
        c1.load_credentials({})
        c2 = LocalFolderConnector(folder_paths=[str(temp_folder)])
        c2.load_credentials({})

        ids1 = {sd.id for batch in c1.retrieve_all_slim_docs() for sd in batch}
        ids2 = {sd.id for batch in c2.retrieve_all_slim_docs() for sd in batch}
        assert ids1 == ids2

    def test_deleted_file_not_in_slim_docs(self, temp_folder: Path) -> None:
        c = LocalFolderConnector(folder_paths=[str(temp_folder)])
        c.load_credentials({})

        ids_before = {sd.id for batch in c.retrieve_all_slim_docs() for sd in batch}
        assert len(ids_before) == 5

        (temp_folder / "readme.txt").unlink()

        ids_after = {sd.id for batch in c.retrieve_all_slim_docs() for sd in batch}
        assert len(ids_after) == 4
        assert ids_after < ids_before


# ===========================================================================
# 4. Access control — OS permission mapping
# ===========================================================================


class TestAccessControl:
    def test_get_file_external_access_returns_access(self, temp_folder: Path) -> None:
        file_path = str(temp_folder / "readme.txt")
        access = _get_file_external_access(file_path)
        assert access is not None
        assert isinstance(access.external_user_emails, set)
        assert isinstance(access.external_user_group_ids, set)
        assert isinstance(access.is_public, bool)

    def test_get_file_external_access_nonexistent_file(self, tmp_path: Path) -> None:
        access = _get_file_external_access(str(tmp_path / "ghost.txt"))
        assert access.is_public is False
        assert len(access.external_user_emails) == 0

    @pytest.mark.skipif(os.name == "nt", reason="Unix permission tests only")
    def test_unix_world_readable_is_public(self, tmp_path: Path) -> None:
        f = tmp_path / "public.txt"
        f.write_text("public content")
        os.chmod(str(f), stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        access = _get_file_external_access(str(f))
        assert access.is_public is True

    @pytest.mark.skipif(os.name == "nt", reason="Unix permission tests only")
    def test_unix_owner_only_is_private(self, tmp_path: Path) -> None:
        f = tmp_path / "private.txt"
        f.write_text("private content")
        os.chmod(str(f), stat.S_IRUSR | stat.S_IWUSR)
        access = _get_file_external_access(str(f))
        assert access.is_public is False
        assert len(access.external_user_emails) >= 1


# ===========================================================================
# 5. Parallel extraction and error handling
# ===========================================================================


class TestParallelAndErrorHandling:
    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_batch_size_controls_yielding(
        self, mock_pf: MagicMock, temp_folder: Path
    ) -> None:
        c = LocalFolderConnector(folder_paths=[str(temp_folder)], batch_size=2)
        c.load_credentials({})
        batches = list(c.load_from_state())
        # 5 files with batch_size=2 -> 3 batches (2+2+1)
        assert len(batches) == 3
        total = sum(len(b) for b in batches)
        assert total == 5

    @patch(PROCESS_FILE_PATCH)
    def test_single_file_failure_does_not_break_batch(
        self, mock_pf: MagicMock, temp_folder: Path
    ) -> None:
        call_count = 0

        def _sometimes_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated extraction failure")
            return _mock_process_file(*args, **kwargs)

        mock_pf.side_effect = _sometimes_fail
        c = LocalFolderConnector(folder_paths=[str(temp_folder)])
        c.load_credentials({})
        batches = list(c.load_from_state())
        all_docs = [doc for batch in batches for doc in batch]
        assert len(all_docs) >= 4

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_large_number_of_files(self, mock_pf: MagicMock, tmp_path: Path) -> None:
        for i in range(50):
            (tmp_path / f"file_{i:03d}.txt").write_text(f"Content {i}")
        c = LocalFolderConnector(folder_paths=[str(tmp_path)], batch_size=10)
        c.load_credentials({})
        batches = list(c.load_from_state())
        total = sum(len(b) for b in batches)
        assert total == 50
        assert len(batches) == 5


# ===========================================================================
# 6. Path security — allowed directories whitelist
# ===========================================================================


class TestPathSecurity:
    def test_is_path_allowed_no_restriction(self) -> None:
        with patch(
            "onyx.connectors.folder.connector.FOLDER_CONNECTOR_ALLOWED_DIRECTORIES", ""
        ):
            assert _is_path_allowed("/any/path") is True

    def test_is_path_allowed_within_whitelist(self) -> None:
        with patch(
            "onyx.connectors.folder.connector.FOLDER_CONNECTOR_ALLOWED_DIRECTORIES",
            "/data/docs,/mnt/shared",
        ):
            assert _is_path_allowed("/data/docs/report.txt") is True
            assert _is_path_allowed("/mnt/shared/file.md") is True

    def test_is_path_allowed_outside_whitelist(self) -> None:
        with patch(
            "onyx.connectors.folder.connector.FOLDER_CONNECTOR_ALLOWED_DIRECTORIES",
            "/data/docs",
        ):
            assert _is_path_allowed("/etc/passwd") is False
            assert _is_path_allowed("/home/user/secret") is False

    def test_validate_connector_settings_rejects_disallowed(self, tmp_path: Path) -> None:
        c = LocalFolderConnector(folder_paths=[str(tmp_path)])
        with patch(
            "onyx.connectors.folder.connector.FOLDER_CONNECTOR_ALLOWED_DIRECTORIES",
            "/only/this/dir",
        ):
            with pytest.raises(ValueError, match="not within allowed"):
                c.validate_connector_settings()

    def test_validate_connector_settings_rejects_nonexistent(self) -> None:
        c = LocalFolderConnector(folder_paths=["/this/path/does/not/exist"])
        with patch(
            "onyx.connectors.folder.connector.FOLDER_CONNECTOR_ALLOWED_DIRECTORIES", ""
        ):
            with pytest.raises(ValueError, match="does not exist"):
                c.validate_connector_settings()


# ===========================================================================
# 7. File filtering
# ===========================================================================


class TestFileFiltering:
    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_extension_filter(self, mock_pf: MagicMock, temp_folder: Path) -> None:
        c = LocalFolderConnector(
            folder_paths=[str(temp_folder)], file_extensions=[".txt"]
        )
        c.load_credentials({})
        batches = list(c.load_from_state())
        all_docs = [doc for batch in batches for doc in batch]
        # Only .txt files: readme.txt, deep.txt, report.txt
        assert len(all_docs) == 3

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_exclude_patterns(self, mock_pf: MagicMock, temp_folder: Path) -> None:
        c = LocalFolderConnector(
            folder_paths=[str(temp_folder)], exclude_patterns=["*.csv", "*.md"]
        )
        c.load_credentials({})
        batches = list(c.load_from_state())
        all_docs = [doc for batch in batches for doc in batch]
        # Excluded: notes.md, data.csv -> remaining: readme.txt, deep.txt, report.txt
        assert len(all_docs) == 3

    @patch(PROCESS_FILE_PATCH, side_effect=_mock_process_file)
    def test_max_file_size_filter(self, mock_pf: MagicMock, tmp_path: Path) -> None:
        (tmp_path / "small.txt").write_text("small")
        (tmp_path / "large.txt").write_bytes(b"x" * (1024 * 1024 + 100))
        c = LocalFolderConnector(folder_paths=[str(tmp_path)], max_file_size_mb=1)
        c.load_credentials({})
        batches = list(c.load_from_state())
        all_docs = [doc for batch in batches for doc in batch]
        assert len(all_docs) == 1


# ===========================================================================
# 8. Document ID stability
# ===========================================================================


class TestDocumentId:
    def test_compute_doc_id_deterministic(self) -> None:
        path = "/data/docs/report.pdf"
        id1 = _compute_doc_id(path)
        id2 = _compute_doc_id(path)
        assert id1 == id2
        assert id1.startswith("FOLDER_CONNECTOR__")

    def test_compute_doc_id_different_paths(self) -> None:
        id1 = _compute_doc_id("/data/a.txt")
        id2 = _compute_doc_id("/data/b.txt")
        assert id1 != id2

    def test_compute_doc_id_format(self) -> None:
        doc_id = _compute_doc_id("/some/path.txt")
        prefix = "FOLDER_CONNECTOR__"
        assert doc_id.startswith(prefix)
        hash_part = doc_id[len(prefix):]
        assert len(hash_part) == 32
        int(hash_part, 16)  # valid hex


# ===========================================================================
# 9. Doc sync (permission sync function)
# ===========================================================================


class TestDocSync:
    def test_folder_doc_sync_yields_permissions(self, temp_folder: Path) -> None:
        cc_pair = MagicMock()
        cc_pair.id = 1
        cc_pair.connector.connector_specific_config = {
            "folder_paths": [str(temp_folder)],
            "recursive": True,
        }
        results = list(
            folder_doc_sync(
                cc_pair=cc_pair,
                fetch_all_existing_docs_fn=None,
                fetch_all_existing_docs_ids_fn=None,
                callback=None,
            )
        )
        assert len(results) == 5
        for result in results:
            assert result.doc_id.startswith("FOLDER_CONNECTOR__")
            assert result.external_access is not None

    def test_folder_doc_sync_respects_callback_stop(self, temp_folder: Path) -> None:
        cc_pair = MagicMock()
        cc_pair.id = 1
        cc_pair.connector.connector_specific_config = {
            "folder_paths": [str(temp_folder)],
            "recursive": True,
        }
        callback = MagicMock()
        callback.should_stop.side_effect = [False, True]

        with pytest.raises(RuntimeError, match="Stop signal"):
            list(
                folder_doc_sync(
                    cc_pair=cc_pair,
                    fetch_all_existing_docs_fn=None,
                    fetch_all_existing_docs_ids_fn=None,
                    callback=callback,
                )
            )

    def test_folder_doc_sync_empty_config(self) -> None:
        cc_pair = MagicMock()
        cc_pair.id = 1
        cc_pair.connector.connector_specific_config = {}
        results = list(
            folder_doc_sync(
                cc_pair=cc_pair,
                fetch_all_existing_docs_fn=None,
                fetch_all_existing_docs_ids_fn=None,
                callback=None,
            )
        )
        assert results == []


# ===========================================================================
# 10. Registry integration
# ===========================================================================


class TestRegistryIntegration:
    def test_folder_source_in_enum(self) -> None:
        assert DocumentSource.FOLDER.value == "folder"
