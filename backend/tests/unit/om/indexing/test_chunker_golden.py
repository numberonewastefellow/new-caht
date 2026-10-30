"""Golden test: the chunks of non-table documents must not change.

The fixture was captured from the Chunker *before* the table-chunking branch
was added. Text and image sections must keep producing byte-identical chunks.

Regenerate only on purpose:
    REGENERATE_GOLDEN_TEXT_CHUNKS=1 python -m pytest \
        tests/unit/om/indexing/test_chunker_golden.py
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest

from om.configs.constants import DocumentSource
from om.connectors.models import Document
from om.connectors.models import IndexingDocument
from om.connectors.models import Section
from om.connectors.models import TextSection
from om.indexing import chunker as chunker_module
from om.indexing.chunker import Chunker
from om.indexing.embedder import DefaultIndexingEmbedder
from om.indexing.indexing_pipeline import process_image_sections
from om.indexing.models import DocAwareChunk

_FIXTURE = Path(__file__).parent / "fixtures" / "golden_text_chunks.json"

_LONG_PARAGRAPH = (
    "The district office records every grievance in a register. Each entry has a "
    "date, a ward, a category and a status. Officers review pending entries every "
    "Monday and close the resolved ones. "
)


def _doc(
    doc_id: str,
    sections: list[TextSection],
    title: str | None = None,
    semantic_identifier: str = "Golden Doc",
    metadata: dict[str, str | list[str]] | None = None,
) -> Document:
    return Document(
        id=doc_id,
        source=DocumentSource.WEB,
        semantic_identifier=semantic_identifier,
        title=title,
        metadata=metadata or {},
        doc_updated_at=None,
        sections=list(sections),
    )


def _indexing_doc(document: Document, processed: list[Section]) -> IndexingDocument:
    return IndexingDocument(**document.model_dump(), processed_sections=processed)


def _cases() -> list[tuple[str, dict[str, Any], list[IndexingDocument]]]:
    """(case name, Chunker kwargs, documents)."""
    cases: list[tuple[str, dict[str, Any], list[IndexingDocument]]] = []

    long_doc = _doc(
        "long_text",
        [TextSection(text=_LONG_PARAGRAPH * 60, link="https://example.com/long")],
        metadata={"tags": ["a", "b"], "owner": "ops"},
    )
    cases.append(("long_text", {}, process_image_sections([long_doc])))

    many_small = _doc(
        "many_small",
        [
            TextSection(text=f"Short section number {i}.", link=f"link{i}")
            for i in range(40)
        ],
        title="Many small sections",
    )
    cases.append(("many_small_sections", {}, process_image_sections([many_small])))

    mixed = _doc(
        "mixed",
        [
            TextSection(text="Intro text before the image.", link="l1"),
            TextSection(text="Outro text after the image.", link="l3"),
        ],
    )
    cases.append(
        (
            "image_section",
            {},
            [
                _indexing_doc(
                    mixed,
                    [
                        Section(text="Intro text before the image.", link="l1"),
                        Section(
                            text="A chart of grievances by ward.",
                            link="l2",
                            image_file_id="img_1",
                        ),
                        Section(text="Outro text after the image.", link="l3"),
                    ],
                )
            ],
        )
    )

    oversized = _doc(
        "oversized",
        [
            TextSection(text="Lead in.", link="a"),
            TextSection(text=("word " * 3000).strip(), link="b"),
            TextSection(text="Tail text.", link="c"),
        ],
    )
    cases.append(("oversized_section", {}, process_image_sections([oversized])))
    cases.append(
        (
            "oversized_strict",
            {"_strict": True},
            process_image_sections([oversized]),
        )
    )

    multipass_doc = _doc(
        "multipass",
        [TextSection(text=_LONG_PARAGRAPH * 30, link="m")],
        title="Multipass",
    )
    cases.append(
        (
            "multipass_large_chunks",
            {"enable_multipass": True, "enable_large_chunks": True},
            process_image_sections([multipass_doc]),
        )
    )

    rag_doc = _doc("rag", [TextSection(text=_LONG_PARAGRAPH * 40, link="r")])
    cases.append(
        (
            "contextual_rag",
            {"enable_contextual_rag": True},
            process_image_sections([rag_doc]),
        )
    )

    empty_with_title = _doc(
        "empty_titled", [TextSection(text="", link="e")], title="Only a title"
    )
    cases.append(("empty_with_title", {}, process_image_sections([empty_with_title])))

    unicode_doc = _doc(
        "unicode",
        [
            TextSection(
                text="ఫిర్యాదుల రిజిస్టర్ జిల్లా వారీగా. शिकायत रजिस्टर। " * 80,
                link="u",
            )
        ],
        title="Telugu and Hindi",
    )
    cases.append(("unicode_text", {}, process_image_sections([unicode_doc])))

    csv_lines = ["case_id,district,status,amount"] + [
        f"TS-HYD-{i:04d},District {i % 7},Pending,{i * 10}" for i in range(400)
    ]
    csv_doc = _doc(
        "csv_as_text",
        [TextSection(text="\n".join(csv_lines), link=None)],
        semantic_identifier="register.csv",
        metadata={"source": "upload"},
    )
    cases.append(("csv_as_text", {}, process_image_sections([csv_doc])))

    big_metadata = _doc(
        "big_metadata",
        [TextSection(text=_LONG_PARAGRAPH * 5, link="x")],
        metadata={f"key{i}": f"value number {i} " * 5 for i in range(30)},
    )
    cases.append(("big_metadata", {}, process_image_sections([big_metadata])))

    two_docs = [
        _doc("two_a", [TextSection(text="First doc text.", link="1")]),
        _doc("two_b", [TextSection(text=_LONG_PARAGRAPH * 10, link="2")]),
    ]
    cases.append(("two_documents", {}, process_image_sections(two_docs)))
    return cases


def _serialize(chunk: DocAwareChunk) -> dict[str, Any]:
    return {
        "doc_id": chunk.source_document.id,
        "chunk_id": chunk.chunk_id,
        "content": chunk.content,
        "blurb": chunk.blurb,
        "source_links": (
            {str(k): v for k, v in chunk.source_links.items()}
            if chunk.source_links is not None
            else None
        ),
        "image_file_id": chunk.image_file_id,
        "section_continuation": chunk.section_continuation,
        "title_prefix": chunk.title_prefix,
        "metadata_suffix_semantic": chunk.metadata_suffix_semantic,
        "metadata_suffix_keyword": chunk.metadata_suffix_keyword,
        "mini_chunk_texts": chunk.mini_chunk_texts,
        "large_chunk_id": chunk.large_chunk_id,
        "large_chunk_reference_ids": chunk.large_chunk_reference_ids,
        "contextual_rag_reserved_tokens": chunk.contextual_rag_reserved_tokens,
    }


def _run_all(
    embedder: DefaultIndexingEmbedder, monkeypatch: pytest.MonkeyPatch
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for name, kwargs, documents in _cases():
        kwargs = dict(kwargs)
        strict = kwargs.pop("_strict", False)
        monkeypatch.setattr(chunker_module, "STRICT_CHUNK_TOKEN_LIMIT", strict)
        chunker = Chunker(tokenizer=embedder.embedding_model.tokenizer, **kwargs)
        result[name] = [_serialize(c) for c in chunker.chunk(documents)]
    return result


def test_text_chunks_match_golden(
    embedder: DefaultIndexingEmbedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    actual = _run_all(embedder, monkeypatch)
    if os.environ.get("REGENERATE_GOLDEN_TEXT_CHUNKS") == "1":
        _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        _FIXTURE.write_text(
            json.dumps(actual, ensure_ascii=False, indent=1, sort_keys=True),
            encoding="utf-8",
        )
    expected = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert sorted(actual) == sorted(expected)
    for name in expected:
        assert actual[name] == expected[name], f"golden case {name!r} changed"
