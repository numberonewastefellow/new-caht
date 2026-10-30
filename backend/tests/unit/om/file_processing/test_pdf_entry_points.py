"""Regression tests for the existing features that read PDFs, after the switch to
PDFium. They go through the same public entry points the callers use:

- extract_file_text: chat uploads, workspace files, airtable/confluence/dropbox/
  egnyte/highspot/google-drive connectors
- extract_text_and_images: file/blob/sharepoint/drupal connectors, agent tool
- web_content.extract_pdf_text: web search / open-URL on PDF pages
"""

from io import BytesIO
from pathlib import Path

import pytest

from om.file_processing import extract_file_text as eft
from om.utils import web_content

FIXTURES = Path(__file__).parent / "fixtures"


def _bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture(autouse=True)
def _no_unstructured(monkeypatch: pytest.MonkeyPatch) -> None:
    # The Unstructured API path takes over when a key is set; keep it local.
    monkeypatch.setattr(eft, "get_unstructured_api_key", lambda: None)


def test_extract_file_text_reads_pdf_by_extension() -> None:
    text = eft.extract_file_text(BytesIO(_bytes("multipage.pdf")), "report.pdf")
    assert "Page one content" in text
    assert "Page two content" in text


def test_extract_file_text_with_explicit_extension() -> None:
    text = eft.extract_file_text(
        BytesIO(_bytes("simple.pdf")), "download", extension=".pdf"
    )
    assert "Hello World" in text


def test_extract_text_and_images_returns_text_and_metadata() -> None:
    result = eft.extract_text_and_images(
        BytesIO(_bytes("with_metadata.pdf")), "with_metadata.pdf"
    )
    assert result.metadata.get("Title") == "My Title"


def test_extract_text_and_images_with_password() -> None:
    result = eft.extract_text_and_images(
        BytesIO(_bytes("encrypted.pdf")), "encrypted.pdf", pdf_pass="pass123"
    )
    assert "Secret Content" in result.text_content


def test_extract_text_and_images_owner_protected_pdf() -> None:
    # Previously returned "" (no password given); now indexes the text.
    result = eft.extract_text_and_images(
        BytesIO(_bytes("owner_protected.pdf")), "owner_protected.pdf"
    )
    assert "Hello World" in result.text_content


def test_extract_text_and_images_collects_images_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(eft, "get_image_extraction_and_analysis_enabled", lambda: True)
    result = eft.extract_text_and_images(
        BytesIO(_bytes("with_image.pdf")), "with_image.pdf"
    )
    assert len(result.embedded_images) == 1


def test_read_pdf_file_ignores_caller_stream_position() -> None:
    # Callers sometimes sniff the header first; pypdf always read from byte 0.
    stream = BytesIO(_bytes("simple.pdf"))
    stream.read(5)
    text, _, _ = eft.read_pdf_file(stream)
    assert "Hello World" in text


def test_web_content_pdf_text_and_title() -> None:
    text, metadata = web_content.extract_pdf_text(_bytes("with_metadata.pdf"))
    assert web_content.title_from_pdf_metadata(metadata) == "My Title"
    assert isinstance(text, str)


def test_web_content_invalid_pdf_returns_empty() -> None:
    text, metadata = web_content.extract_pdf_text(b"<html>not a pdf</html>")
    assert text == ""
    assert metadata == {}
