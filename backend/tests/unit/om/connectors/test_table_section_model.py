"""TableSection and the SectionKind discriminator survive JSON round-trips."""

import json
import sys
from datetime import datetime
from datetime import timezone
from unittest.mock import MagicMock

from om.background.indexing.run_docfetching import strip_null_characters
from om.configs.constants import DocumentSource
from om.connectors.models import Document
from om.connectors.models import ImageSection
from om.connectors.models import IndexingDocument
from om.connectors.models import SectionKind
from om.connectors.models import TableSection
from om.connectors.models import TextSection
from om.file_store.document_batch_storage import FileStoreDocumentBatchStorage


def _document() -> Document:
    return Document(
        id="doc1",
        source=DocumentSource.FILE,
        semantic_identifier="register.xlsx",
        metadata={},
        doc_updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        sections=[
            TextSection(text="intro", link="t"),
            ImageSection(image_file_id="img", link=None),
            TableSection(text="a,b\n1,2", link=None, sheet_name="Sheet1"),
            TableSection(text="c,d\n3,4", link=None),
        ],
    )


def test_kind_defaults() -> None:
    assert TextSection(text="x").kind is SectionKind.TEXT
    assert ImageSection(image_file_id="i").kind is SectionKind.IMAGE
    assert TableSection(text="a,b").kind is SectionKind.TABLE
    assert TableSection(text="a,b").sheet_name is None


def test_table_section_roundtrip() -> None:
    document = _document()
    dumped = document.model_dump(mode="json")
    assert [s["kind"] for s in dumped["sections"]] == [
        "text",
        "image",
        "table",
        "table",
    ]
    restored = Document.model_validate(json.loads(json.dumps(dumped)))
    assert [type(s) for s in restored.sections] == [
        TextSection,
        ImageSection,
        TableSection,
        TableSection,
    ]
    assert restored == document
    # The pipeline rebuilds documents from a python-mode dump too.
    rebuilt = IndexingDocument(**document.model_dump(), processed_sections=[])
    assert [type(s) for s in rebuilt.sections] == [
        TextSection,
        ImageSection,
        TableSection,
        TableSection,
    ]


def test_old_json_without_kind_still_parses() -> None:
    old = {
        "id": "doc1",
        "source": "file",
        "semantic_identifier": "notes.txt",
        "metadata": {},
        "sections": [
            {"text": "hello", "link": "l", "image_file_id": None},
            {"text": None, "link": None, "image_file_id": "img"},
            {"text": "summary", "link": None, "image_file_id": "img2"},
        ],
    }
    restored = Document.model_validate(old)
    assert [type(s) for s in restored.sections] == [
        TextSection,
        ImageSection,
        TextSection,
    ]


def test_ingestion_payload_may_send_table_kind() -> None:
    payload = {
        "id": "doc1",
        "source": "ingestion_api",
        "semantic_identifier": "data.csv",
        "metadata": {},
        "sections": [{"kind": "table", "text": "a,b\n1,2", "link": "https://x"}],
    }
    restored = Document.model_validate(payload)
    assert isinstance(restored.sections[0], TableSection)


def test_batch_storage_serialize_roundtrip() -> None:
    storage = FileStoreDocumentBatchStorage(
        cc_pair_id=1, index_attempt_id=1, file_store=MagicMock()
    )
    document = _document()
    restored = storage._deserialize_documents(storage._serialize_documents([document]))
    assert restored == [document]
    assert isinstance(restored[0].sections[2], TableSection)
    assert restored[0].sections[2].sheet_name == "Sheet1"


def test_sizeof() -> None:
    section = TableSection(text="a,b\n1,2" * 100, link="l", sheet_name="S")
    assert sys.getsizeof(section) >= sys.getsizeof(section.text)


def test_char_length_counts_table_text() -> None:
    document = _document()
    indexing_doc = IndexingDocument(**document.model_dump(), processed_sections=[])
    assert indexing_doc.get_total_char_length() == len("register.xlsx") + len(
        "intro"
    ) + len("a,b\n1,2") + len("c,d\n3,4")
    assert "a,b" in document.get_text_content()


def test_strip_null_characters_cleans_table_text() -> None:
    document = Document(
        id="doc1",
        source=DocumentSource.FILE,
        semantic_identifier="register.csv",
        metadata={},
        sections=[TableSection(text="a,b\n1\x00,2", link="l\x00")],
    )
    cleaned = strip_null_characters([document])
    assert cleaned[0].sections[0].text == "a,b\n1,2"
    assert cleaned[0].sections[0].link == "l"
    assert isinstance(cleaned[0].sections[0], TableSection)
