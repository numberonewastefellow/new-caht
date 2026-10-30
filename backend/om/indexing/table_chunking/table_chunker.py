"""Chunking of spreadsheets and CSV files.

All sheets of one file are chunked together, once, so the chunks can describe
the whole file and their number stays bounded. See ``chunk_builder.py`` for
what the chunks hold.
"""

import io
from collections.abc import Iterator
from functools import partial

from om.configs.app_configs import TABLE_FULL_ROWS_MAX_CHUNKS
from om.configs.app_configs import TABLE_MAX_CHUNKS_PER_FILE
from om.configs.app_configs import TABLE_VALUE_CHUNKS_PER_SHEET
from om.connectors.models import TableSection
from om.indexing.table_chunking.chunk_builder import build_table_file_chunks
from om.indexing.table_chunking.sheet_summary import SheetRows
from om.natural_language_processing.utils import BaseTokenizer
from om.utils.csv_parsing import read_csv_rows
from om.utils.logger import setup_logger

logger = setup_logger()


def _open_csv_rows(csv_text: str) -> Iterator[list[str]]:
    """A fresh row iterator over inline CSV text."""
    return read_csv_rows(io.StringIO(csv_text, newline=""))


class TableChunker:
    def __init__(self, tokenizer: BaseTokenizer) -> None:
        self.tokenizer = tokenizer

    def chunk_table_file(
        self,
        sections: list[TableSection],
        content_token_limit: int,
        file_name: str,
    ) -> list[str]:
        """Chunk texts for one file: every TableSection (sheet) of it at once."""
        if not sections:
            return []
        sheets = [
            SheetRows(
                name=section.sheet_name or "",
                open_rows=partial(_open_csv_rows, section.text),
            )
            for section in sections
        ]
        chunk_texts = build_table_file_chunks(
            file_name=file_name,
            sheets=sheets,
            tokenizer=self.tokenizer,
            max_tokens=content_token_limit,
            full_rows_max_chunks=TABLE_FULL_ROWS_MAX_CHUNKS,
            value_chunks_per_sheet=TABLE_VALUE_CHUNKS_PER_SHEET,
            max_chunks=TABLE_MAX_CHUNKS_PER_FILE,
        )
        if not chunk_texts:
            logger.warning(
                "Table file %r (%s sheet(s)) produced no chunks; only its title "
                "and metadata are searchable.",
                file_name,
                len(sections),
            )
        return chunk_texts
