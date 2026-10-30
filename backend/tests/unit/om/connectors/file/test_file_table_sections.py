"""File and blob connectors emit TableSections for xlsx/csv/tsv files."""

import io
from datetime import datetime
from datetime import timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from om.configs.constants import BlobType
from om.connectors.blob import connector as blob_module
from om.connectors.blob.connector import BlobStorageConnector
from om.connectors.file import utils as file_utils
from om.connectors.file.utils import _process_file
from om.connectors.models import Document
from om.connectors.models import TableSection
from om.connectors.models import TextSection
from om.file_processing import extract_file_text
from tests.unit.om.indexing.table_chunking.sample_tables import build_sample_xlsx

_CSV = b"case_id,district,amount\nGRV-1,Hyderabad,0\nGRV-2,Warangal,4500\n"


@pytest.fixture(autouse=True)
def _no_unstructured(monkeypatch: pytest.MonkeyPatch) -> None:
    # The text path asks the key-value store for an Unstructured key (a DB
    # call); unit tests run without a DB.
    monkeypatch.setattr(extract_file_text, "get_unstructured_api_key", lambda: None)


def test_table_files_bypass_unstructured(monkeypatch: pytest.MonkeyPatch) -> None:
    def _must_not_run(*_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("Unstructured must not see table files")

    monkeypatch.setattr(extract_file_text, "get_unstructured_api_key", lambda: "key")
    monkeypatch.setattr(extract_file_text, "unstructured_to_text", _must_not_run)
    docs = _process("register.csv", _CSV, "text/csv")
    assert isinstance(docs[0].sections[0], TableSection)
    docs = _process("register.xlsx", build_sample_xlsx(), "application/octet-stream")
    assert isinstance(docs[0].sections[0], TableSection)


def _process(name: str, data: bytes, file_type: str | None = None) -> list[Document]:
    return _process_file(
        file_id="file-1",
        file_name=name,
        file=io.BytesIO(data),
        metadata=None,
        pdf_pass=None,
        file_type=file_type,
    )


def test_xlsx_gives_one_table_section_per_sheet() -> None:
    docs = _process("register.xlsx", build_sample_xlsx(), "application/octet-stream")
    assert len(docs) == 1
    sections = docs[0].sections
    assert all(isinstance(s, TableSection) for s in sections)
    assert [s.sheet_name for s in sections] == ["Readme", "Register"]  # type: ignore[union-attr]
    assert all(s.link is None for s in sections)
    assert docs[0].semantic_identifier == "register.xlsx"


def test_csv_gives_one_table_section() -> None:
    docs = _process("register.csv", _CSV, "text/csv")
    (section,) = docs[0].sections
    assert isinstance(section, TableSection)
    assert section.text == _CSV.decode().strip()


def test_csv_metadata_line_still_applies() -> None:
    data = b'#OM_METADATA={"link": "https://example.com/r"}\n' + _CSV
    docs = _process("register.csv", data, "text/csv")
    (section,) = docs[0].sections
    assert isinstance(section, TableSection)
    assert section.link == "https://example.com/r"
    assert "OM_METADATA" not in section.text


def test_kill_switch_gives_text_section(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(file_utils, "TABLE_CHUNKING_ENABLED", False)
    docs = _process("register.csv", _CSV, "text/csv")
    (section,) = docs[0].sections
    assert type(section) is TextSection
    assert section.text == _CSV.decode().strip()


def test_extraction_failure_falls_back_to_text(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(file_utils, "extract_table_file", _boom)
    docs = _process("register.csv", _CSV, "text/csv")
    (section,) = docs[0].sections
    assert type(section) is TextSection


def test_corrupt_xlsx_falls_back_to_text_path() -> None:
    docs = _process("broken.xlsx", b"not a zip", "application/octet-stream")
    # Same as before this change: nothing readable, no sections.
    assert docs[0].sections == []


def test_non_table_files_unchanged() -> None:
    docs = _process("notes.txt", b"hello world", "text/plain")
    (section,) = docs[0].sections
    assert type(section) is TextSection
    assert section.text == "hello world"


def _blob_connector(files: dict[str, bytes]) -> BlobStorageConnector:
    connector = BlobStorageConnector(
        bucket_type=BlobType.S3.value, bucket_name="bucket", prefix=""
    )
    s3_client = MagicMock()
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {
            "Contents": [
                {
                    "Key": key,
                    "LastModified": datetime(2025, 1, 1, tzinfo=timezone.utc),
                    "Size": len(data),
                }
                for key, data in files.items()
            ]
        }
    ]
    s3_client.get_paginator.return_value = paginator
    connector.s3_client = s3_client
    connector._download_object = lambda key: files[key]  # type: ignore[method-assign]
    connector._get_blob_link = lambda key: f"https://bucket/{key}"  # type: ignore[method-assign]
    return connector


def _blob_documents(connector: BlobStorageConnector) -> list[Document]:
    return [
        doc
        for batch in connector.load_from_state()
        for doc in batch
        if isinstance(doc, Document)
    ]


def test_blob_table_files() -> None:
    connector = _blob_connector(
        {
            "dir/register.xlsx": build_sample_xlsx(),
            "dir/data.csv": _CSV,
            "dir/notes.txt": b"hello",
        }
    )
    docs = {doc.semantic_identifier: doc for doc in _blob_documents(connector)}
    xlsx_sections = docs["register.xlsx"].sections
    assert [type(s) for s in xlsx_sections] == [TableSection, TableSection]
    assert all(s.link == "https://bucket/dir/register.xlsx" for s in xlsx_sections)
    (csv_section,) = docs["data.csv"].sections
    assert isinstance(csv_section, TableSection)
    (text_section,) = docs["notes.txt"].sections
    assert type(text_section) is TextSection


def test_blob_kill_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(blob_module, "TABLE_CHUNKING_ENABLED", False)
    connector = _blob_connector({"data.csv": _CSV})
    (doc,) = _blob_documents(connector)
    (section,) = doc.sections
    assert type(section) is TextSection
