"""Spreadsheet and CSV files as TableSections, for any connector that has the
file bytes and its name.

- ``.xlsx``: one TableSection per non-empty sheet.
- ``.csv`` / ``.tsv``: one TableSection for the whole file (TSV is rewritten
  as CSV, so every TableSection holds excel-dialect CSV).
- empty input: ``[]``.

The CSV text is kept inline in the section, as the old TextSection did.
"""

import csv
import io
from typing import Any
from typing import IO
from typing import NamedTuple

from om.connectors.models import TableSection
from om.file_processing.extract_file_text import extract_result_from_text_file
from om.file_processing.extract_file_text import get_file_ext
from om.file_processing.extract_file_text import xlsx_sheets_to_csv
from om.utils.csv_parsing import read_csv_rows

TABLE_FILE_EXTENSIONS = {".xlsx", ".csv", ".tsv"}
SPREADSHEET_FILE_EXTENSIONS = {".xlsx"}


class TableFileExtraction(NamedTuple):
    sections: list[TableSection]
    # Metadata from an ``#OM_METADATA=`` first line of a csv/tsv file, as the
    # plain-text extraction reads it; always empty for xlsx.
    metadata: dict[str, Any]


def is_table_file(file_name: str) -> bool:
    return get_file_ext(file_name) in TABLE_FILE_EXTENSIONS


def _tsv_to_csv(tsv_text: str) -> str:
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(
        read_csv_rows(io.StringIO(tsv_text, newline=""), dialect="excel-tab")
    )
    return out.getvalue().rstrip("\n")


def extract_table_file(
    file: IO[Any], file_name: str, link: str | None = None
) -> TableFileExtraction:
    """TableSections of a table file, plus any metadata its first line holds.

    Raises ValueError for a file that is not a table file. An unreadable
    workbook gives no sections, so the caller can fall back to plain text.
    """
    extension = get_file_ext(file_name)
    if extension not in TABLE_FILE_EXTENSIONS:
        raise ValueError(f"{file_name!r} is not a table file")

    file.seek(0)
    if extension in SPREADSHEET_FILE_EXTENSIONS:
        sections = [
            TableSection(text=csv_text, link=link, sheet_name=sheet_name)
            for sheet_name, csv_text in xlsx_sheets_to_csv(file, file_name=file_name)
        ]
        return TableFileExtraction(sections=sections, metadata={})

    extraction = extract_result_from_text_file(file)
    text = extraction.text_content.strip()
    if not text:
        return TableFileExtraction(sections=[], metadata=extraction.metadata)
    if extension == ".tsv":
        text = _tsv_to_csv(text)
    return TableFileExtraction(
        sections=[TableSection(text=text, link=link)],
        metadata=extraction.metadata,
    )


def table_file_to_sections(
    file: IO[Any], file_name: str, link: str | None = None
) -> list[TableSection]:
    return extract_table_file(file, file_name, link).sections
