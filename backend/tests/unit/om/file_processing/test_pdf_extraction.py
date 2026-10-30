"""PDF text extraction: PDFium (isolated child process) with pypdf fallback.

Fixture PDFs live in ./fixtures/ and are pre-built so the tests don't depend on
any PDF-writing library.
"""

from io import BytesIO
from pathlib import Path

import pytest
from pypdfium2 import PdfiumError

from om.file_processing import extract_file_text
from om.file_processing.extract_file_text import pdf_to_text
from om.file_processing.extract_file_text import read_pdf_file
from om.file_processing.pdfium_text import extract_pdf_text_pdfium
from om.utils.process_isolation import IsolatedProcessCrashed
from om.utils.process_isolation import IsolatedProcessTimeout

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> BytesIO:
    return BytesIO((FIXTURES / name).read_bytes())


class TestReadPdfFile:
    def test_basic_text_extraction(self) -> None:
        text, _, images = read_pdf_file(_load("simple.pdf"))
        assert "Hello World" in text
        assert images == []

    def test_multi_page_text_extraction(self) -> None:
        text, _, _ = read_pdf_file(_load("multipage.pdf"))
        assert "Page one content" in text
        assert "Page two content" in text

    def test_in_process_extraction_matches_isolated(self) -> None:
        isolated, _, _ = read_pdf_file(_load("multipage.pdf"))
        in_process, _, _ = read_pdf_file(_load("multipage.pdf"), isolate_pdfium=False)
        assert isolated == in_process

    def test_text_extraction_uses_pdfium(self) -> None:
        text = extract_pdf_text_pdfium(
            (FIXTURES / "multipage.pdf").read_bytes(),
            None,
            extract_file_text.TEXT_SECTION_SEPARATOR,
        )
        assert "Page one content" in text
        assert "Page two content" in text

    def test_pdfium_line_endings_are_normalized(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PDFium returns "\\r\\n" line breaks; chunks should only carry "\\n"."""

        class _TextPage:
            def get_text_range(self) -> str:
                return "line one\r\nline two\rline three"

            def close(self) -> None:
                pass

        class _Page:
            def get_textpage(self) -> _TextPage:
                return _TextPage()

            def close(self) -> None:
                pass

        class _Doc:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def __iter__(self):  # type: ignore[no-untyped-def]
                return iter([_Page(), _Page()])

            def close(self) -> None:
                pass

        import pypdfium2

        monkeypatch.setattr(pypdfium2, "PdfDocument", _Doc)
        text = extract_pdf_text_pdfium(b"", None, "\n\n")
        assert "\r" not in text
        assert (
            text == "line one\nline two\nline three\n\nline one\nline two\nline three"
        )

    @pytest.mark.parametrize(
        "isolation_failure",
        [
            # pypdf is more lenient than PDFium and reads some PDFs it rejects.
            PdfiumError("Failed to load document (PDFium: Data format error)."),
            # A malformed PDF can hard-abort PDFium (SIGABRT).
            IsolatedProcessCrashed(6),
            # ...or hang it until the deadline.
            IsolatedProcessTimeout(120),
        ],
        ids=["pdfium_error", "native_crash", "timeout"],
    )
    def test_falls_back_to_pypdf_on_isolation_failure(
        self, monkeypatch: pytest.MonkeyPatch, isolation_failure: Exception
    ) -> None:
        def _fail(*_args: object, **_kwargs: object) -> str:
            raise isolation_failure

        monkeypatch.setattr(extract_file_text, "run_in_isolated_process", _fail)
        text, _, _ = read_pdf_file(_load("multipage.pdf"))
        assert "Page one content" in text
        assert "Page two content" in text

    def test_image_extraction_survives_isolation_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _crash(*_args: object, **_kwargs: object) -> str:
            raise IsolatedProcessCrashed(6)

        monkeypatch.setattr(extract_file_text, "run_in_isolated_process", _crash)
        _, _, images = read_pdf_file(_load("with_image.pdf"), extract_images=True)
        assert len(images) >= 1

    def test_metadata_extraction(self) -> None:
        _, pdf_metadata, _ = read_pdf_file(_load("with_metadata.pdf"))
        assert pdf_metadata.get("Title") == "My Title"
        assert pdf_metadata.get("Author") == "Jane Doe"

    def test_encrypted_pdf_with_correct_password(self) -> None:
        text, _, _ = read_pdf_file(_load("encrypted.pdf"), pdf_pass="pass123")
        assert "Secret Content" in text

    def test_encrypted_pdf_without_password(self) -> None:
        text, _, _ = read_pdf_file(_load("encrypted.pdf"))
        assert text == ""

    def test_encrypted_pdf_with_wrong_password(self) -> None:
        text, _, _ = read_pdf_file(_load("encrypted.pdf"), pdf_pass="wrong")
        assert text == ""

    def test_owner_password_only_pdf_extracts_text(self) -> None:
        # Only an owner password (edit/print restrictions): opens with "".
        text, _, _ = read_pdf_file(_load("owner_protected.pdf"))
        assert "Hello World" in text

    def test_empty_pdf(self) -> None:
        text, _, _ = read_pdf_file(_load("empty.pdf"))
        assert text.strip() == ""

    def test_invalid_pdf_returns_empty(self) -> None:
        text, _, images = read_pdf_file(BytesIO(b"this is not a pdf"))
        assert text == ""
        assert images == []

    def test_image_extraction_disabled_by_default(self) -> None:
        _, _, images = read_pdf_file(_load("with_image.pdf"))
        assert images == []

    def test_image_callback_streams_instead_of_collecting(self) -> None:
        collected: list[tuple[bytes, str]] = []

        def callback(data: bytes, name: str) -> None:
            collected.append((data, name))

        _, _, images = read_pdf_file(
            _load("with_image.pdf"), extract_images=True, image_callback=callback
        )
        assert len(collected) == 1
        assert len(collected[0][0]) > 0
        assert images == []


class TestPdfToText:
    def test_returns_text(self) -> None:
        assert "Hello World" in pdf_to_text(_load("simple.pdf"))

    def test_with_password(self) -> None:
        assert "Secret Content" in pdf_to_text(
            _load("encrypted.pdf"), pdf_pass="pass123"
        )
