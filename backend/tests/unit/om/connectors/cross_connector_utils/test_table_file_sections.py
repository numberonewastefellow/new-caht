import io

import pytest

from om.connectors.cross_connector_utils.table_file_sections import (
    extract_table_file,
)
from om.connectors.cross_connector_utils.table_file_sections import is_table_file
from om.connectors.cross_connector_utils.table_file_sections import (
    table_file_to_sections,
)
from om.connectors.models import TableSection
from om.file_processing.extract_file_text import xlsx_sheets_to_csv
from om.file_processing.extract_file_text import xlsx_to_text
from om.utils.csv_parsing import read_csv_rows
from tests.unit.om.indexing.table_chunking.sample_tables import build_sample_xlsx


def test_is_table_file() -> None:
    assert is_table_file("a.xlsx")
    assert is_table_file("A.CSV")
    assert is_table_file("dir/b.tsv")
    assert not is_table_file("a.xls")
    assert not is_table_file("a.txt")
    assert not is_table_file("csv")


def test_xlsx_one_section_per_non_empty_sheet() -> None:
    sections = table_file_to_sections(
        io.BytesIO(build_sample_xlsx()), "register.xlsx", link="https://x"
    )
    assert [s.sheet_name for s in sections] == ["Readme", "Register"]
    assert all(isinstance(s, TableSection) for s in sections)
    assert all(s.link == "https://x" for s in sections)
    register_rows = list(read_csv_rows(io.StringIO(sections[1].text, newline="")))
    assert register_rows == [
        ["case_id", "district", "amount", "note"],
        ["GRV-1", "Hyderabad", "0", 'said "urgent", twice'],
        ["GRV-2", "Warangal", "4500", "line one\nline two"],
    ]


def test_xlsx_to_text_is_unchanged() -> None:
    # The old text extraction (chat uploads, read_file, Google Drive...) must
    # keep its exact output, including its known quirks (0 -> "", no quoting).
    text = xlsx_to_text(io.BytesIO(build_sample_xlsx()), file_name="register.xlsx")
    assert text == (
        "Grievance register, mock data\n"
        "Maintained by the district office."
        "\n\n"
        "case_id,district,amount,note\n"
        'GRV-1,Hyderabad,,said "urgent", twice\n'
        "GRV-2,Warangal,4500,line one\nline two"
        "\n\n"
    )


def test_corrupt_xlsx_gives_no_sections() -> None:
    assert xlsx_sheets_to_csv(io.BytesIO(b"not a zip"), "broken.xlsx") == []
    assert table_file_to_sections(io.BytesIO(b"not a zip"), "broken.xlsx") == []


def test_csv_one_section() -> None:
    data = b'id,note\nA-1,"a, b"\nA-2,0\n'
    sections = table_file_to_sections(io.BytesIO(data), "data.csv")
    assert len(sections) == 1
    assert sections[0].sheet_name is None
    assert sections[0].link is None
    assert sections[0].text == 'id,note\nA-1,"a, b"\nA-2,0'


def test_tsv_is_rewritten_as_csv() -> None:
    data = "id\tnote\nA-1\ta, b\nA-2\tplain\n".encode("utf-8")
    sections = table_file_to_sections(io.BytesIO(data), "data.tsv")
    assert sections[0].text == 'id,note\nA-1,"a, b"\nA-2,plain'


def test_csv_metadata_line_is_returned() -> None:
    data = b'#OM_METADATA={"link": "https://example.com/a"}\nid,v\n1,2\n'
    extraction = extract_table_file(io.BytesIO(data), "data.csv")
    assert extraction.metadata == {"link": "https://example.com/a"}
    assert extraction.sections[0].text == "id,v\n1,2"


def test_non_utf8_csv_is_decoded() -> None:
    data = "id,place\n1,Montréal\n".encode("latin-1")
    sections = table_file_to_sections(io.BytesIO(data), "data.csv")
    assert "Montr" in sections[0].text


def test_empty_inputs() -> None:
    assert table_file_to_sections(io.BytesIO(b""), "empty.csv") == []
    assert table_file_to_sections(io.BytesIO(b"  \n \n"), "blank.tsv") == []


def test_not_a_table_file() -> None:
    with pytest.raises(ValueError):
        table_file_to_sections(io.BytesIO(b"x"), "notes.txt")


def test_big_cell_has_no_field_limit_error() -> None:
    big = "x" * (200 * 1024)
    data = f"id,blob\n1,{big}\n".encode("utf-8")
    sections = table_file_to_sections(io.BytesIO(data), "big.csv")
    rows = list(read_csv_rows(io.StringIO(sections[0].text, newline="")))
    assert rows[1][1] == big
    # TSV goes through the csv reader itself.
    tsv = f"id\tblob\n1\t{big}\n".encode("utf-8")
    assert big in table_file_to_sections(io.BytesIO(tsv), "big.tsv")[0].text
