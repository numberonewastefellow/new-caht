"""Chunker._chunk_table_sections: TableSections of one file become one bounded
set of chunks, placed in document order among the text chunks."""

import pytest

from om.configs.constants import DocumentSource
from om.connectors.models import Document
from om.connectors.models import IndexingDocument
from om.connectors.models import TableSection
from om.connectors.models import TextSection
from om.indexing.chunker import Chunker
from om.indexing.embedder import DefaultIndexingEmbedder
from om.indexing.indexing_pipeline import process_image_sections
from om.indexing.table_chunking import table_chunker as table_chunker_module
from tests.unit.om.indexing.table_chunking.sample_tables import CID_DEPOSITORS_CSV
from tests.unit.om.indexing.table_chunking.sample_tables import grievance_rows
from tests.unit.om.indexing.table_chunking.sample_tables import rows_to_csv

_LARGE_CSV = rows_to_csv(grievance_rows(3000))


def _doc(
    sections: list[TextSection | TableSection],
    semantic_identifier: str = "register.xlsx",
    metadata: dict[str, str | list[str]] | None = None,
) -> IndexingDocument:
    document = Document(
        id="table_doc",
        source=DocumentSource.FILE,
        semantic_identifier=semantic_identifier,
        metadata=metadata or {},
        sections=list(sections),
    )
    return process_image_sections([document])[0]


def _chunker(embedder: DefaultIndexingEmbedder, **kwargs: bool) -> Chunker:
    return Chunker(tokenizer=embedder.embedding_model.tokenizer, **kwargs)


def test_table_only_document(embedder: DefaultIndexingEmbedder) -> None:
    doc = _doc(
        [
            TableSection(text=_LARGE_CSV, link=None, sheet_name="Register"),
            TableSection(text=CID_DEPOSITORS_CSV, link=None, sheet_name="Depositors"),
        ],
        metadata={"department": "revenue"},
    )
    chunks = _chunker(embedder).chunk([doc])
    assert 1 < len(chunks) <= 24
    assert [c.chunk_id for c in chunks] == list(range(len(chunks)))
    assert chunks[0].content.startswith(
        "Spreadsheet register.xlsx: 2 sheets (Register, Depositors)"
    )
    assert [c.section_continuation for c in chunks] == [False] + [True] * (
        len(chunks) - 1
    )
    for chunk in chunks:
        assert chunk.source_links == {0: ""}
        assert chunk.title_prefix.startswith("register.xlsx")
        assert "revenue" in chunk.metadata_suffix_keyword
        assert chunk.blurb
    joined = "\n".join(c.content for c in chunks)
    assert "register.xlsx :: Depositors (all 5 rows)" in joined
    assert "register.xlsx :: Register: 3000 rows x 6 columns (summary" in joined


def test_mixed_text_and_table_keeps_order(embedder: DefaultIndexingEmbedder) -> None:
    doc = _doc(
        [
            TextSection(text="Text before the table.", link="t1"),
            TableSection(text=CID_DEPOSITORS_CSV, link="f1", sheet_name="Depositors"),
            TextSection(text="Text after the table.", link="t2"),
        ]
    )
    chunks = _chunker(embedder).chunk([doc])
    assert len(chunks) == 3
    assert chunks[0].content == "Text before the table."
    assert chunks[0].source_links == {0: "t1"}
    assert chunks[1].content.startswith("Spreadsheet register.xlsx")
    assert chunks[1].source_links == {0: "f1"}
    assert not chunks[1].section_continuation
    assert chunks[2].content == "Text after the table."
    assert chunks[2].source_links == {0: "t2"}


def test_two_files_grouped_by_link(embedder: DefaultIndexingEmbedder) -> None:
    doc = _doc(
        [
            TableSection(text=CID_DEPOSITORS_CSV, link="a.xlsx", sheet_name="A1"),
            TableSection(text=CID_DEPOSITORS_CSV, link="b.xlsx", sheet_name="B1"),
            TableSection(text=_LARGE_CSV, link="a.xlsx", sheet_name="A2"),
        ]
    )
    chunks = _chunker(embedder).chunk([doc])
    file_a = [c for c in chunks if c.source_links == {0: "a.xlsx"}]
    file_b = [c for c in chunks if c.source_links == {0: "b.xlsx"}]
    assert len(file_a) + len(file_b) == len(chunks)
    # File a (both of its sheets) comes first, at its first sheet.
    assert chunks[: len(file_a)] == file_a
    assert file_a[0].content.startswith("Spreadsheet register.xlsx: 2 sheets (A1, A2)")
    assert file_b[0].content.startswith("Spreadsheet register.xlsx: 1 sheet (B1)")
    assert not file_a[0].section_continuation
    assert not file_b[0].section_continuation
    assert all(c.section_continuation for c in file_a[1:] + file_b[1:])
    assert [c.chunk_id for c in chunks] == list(range(len(chunks)))


def test_file_cap(
    embedder: DefaultIndexingEmbedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(table_chunker_module, "TABLE_MAX_CHUNKS_PER_FILE", 2)
    doc = _doc([TableSection(text=_LARGE_CSV, link=None, sheet_name="Register")])
    chunks = _chunker(embedder).chunk([doc])
    assert len(chunks) == 2


def test_empty_sheet_gives_one_empty_chunk(embedder: DefaultIndexingEmbedder) -> None:
    doc = _doc([TableSection(text="", link=None, sheet_name="Empty")])
    chunks = _chunker(embedder).chunk([doc])
    assert len(chunks) == 1
    assert chunks[0].content == ""


def test_multipass_on(embedder: DefaultIndexingEmbedder) -> None:
    doc = _doc([TableSection(text=_LARGE_CSV, link=None, sheet_name="Register")])
    chunks = _chunker(embedder, enable_multipass=True, enable_large_chunks=True).chunk(
        [doc]
    )
    normal = [c for c in chunks if c.large_chunk_id is None]
    large = [c for c in chunks if c.large_chunk_id is not None]
    assert normal and large
    assert all(c.mini_chunk_texts for c in normal)


def test_contextual_rag_on(embedder: DefaultIndexingEmbedder) -> None:
    doc = _doc([TableSection(text=_LARGE_CSV, link=None, sheet_name="Register")])
    plain = _chunker(embedder).chunk([doc])
    with_rag = _chunker(embedder, enable_contextual_rag=True).chunk([doc])
    assert with_rag
    assert all(c.contextual_rag_reserved_tokens > 0 for c in with_rag)
    # Less room per chunk can only mean the same or more chunks.
    assert len(with_rag) >= len(plain)
