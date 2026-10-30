"""PDF text extraction via pypdfium2 (PDFium, the C engine Chrome uses).

Kept in its own module with no heavy imports: it runs inside the isolated child
process (see om/utils/process_isolation.py), which imports this module before
calling it, so a small import surface keeps each PDF's child start-up cheap.
"""


def extract_pdf_text_pdfium(
    file_bytes: bytes, password: str | None, page_separator: str
) -> str:
    """Extract the text of every page and join the pages with ``page_separator``.

    PDFium releases the GIL while parsing, so a large or complex PDF can't pin a
    worker thread or stall the indexing heartbeat during text extraction.
    """
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(file_bytes, password=password)
    try:
        page_texts: list[str] = []
        for page in pdf:
            # Per-page try/finally so a get_textpage() failure still closes the
            # native page handle instead of leaking it until GC.
            try:
                textpage = page.get_textpage()
                try:
                    # PDFium ends lines with "\r\n"; keep "\n" like other extractors.
                    page_texts.append(
                        textpage.get_text_range()
                        .replace("\r\n", "\n")
                        .replace("\r", "\n")
                    )
                finally:
                    textpage.close()
            finally:
                page.close()
        return page_separator.join(page_texts)
    finally:
        pdf.close()
