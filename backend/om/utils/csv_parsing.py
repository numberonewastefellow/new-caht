"""CSV reading that survives large cells.

Python's csv module refuses fields over 128 KiB by default ("field larger than
field limit"), which real spreadsheets hit with long descriptions or pasted
documents. The limit is process-global state, so it is raised here, at the
point of use, rather than once at import time.
"""

import csv
from collections.abc import Iterable
from collections.abc import Iterator

CSV_FIELD_SIZE_LIMIT_BYTES = 128 * 1024 * 1024


def read_csv_rows(source: Iterable[str], dialect: str = "excel") -> Iterator[list[str]]:
    """Rows of ``source`` (a text stream or any iterable of lines)."""
    csv.field_size_limit(CSV_FIELD_SIZE_LIMIT_BYTES)
    return csv.reader(source, dialect=dialect)
