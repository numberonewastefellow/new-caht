"""Behaviour of build_table_file_chunks (overview, all rows, summaries, caps)."""

import pytest

from om.indexing.table_chunking.chunk_builder import build_table_file_chunks
from om.indexing.table_chunking.chunk_builder import ChunkPacker
from om.indexing.table_chunking.chunk_builder import summarize_sheet
from om.indexing.table_chunking.sheet_summary import ChunkBlock
from om.indexing.table_chunking.sheet_summary import ColumnRole
from om.indexing.table_chunking.sheet_summary import SheetKind
from om.indexing.table_chunking.sheet_summary import SheetRows
from om.natural_language_processing.utils import BaseTokenizer
from om.natural_language_processing.utils import count_tokens_safely
from om.natural_language_processing.utils import TiktokenTokenizer
from tests.unit.om.indexing.table_chunking.sample_tables import AAROGYASRI_PREAUTH_CSV
from tests.unit.om.indexing.table_chunking.sample_tables import (
    CID_BANK_STATEMENTS_CSV,
)
from tests.unit.om.indexing.table_chunking.sample_tables import CID_DEPOSITORS_CSV
from tests.unit.om.indexing.table_chunking.sample_tables import csv_sheet
from tests.unit.om.indexing.table_chunking.sample_tables import grievance_rows
from tests.unit.om.indexing.table_chunking.sample_tables import sheet


@pytest.fixture(scope="module")
def tokenizer() -> BaseTokenizer:
    return TiktokenTokenizer("gpt-4")


def _build(
    tokenizer: BaseTokenizer,
    sheets: list[SheetRows],
    max_tokens: int = 512,
    full_rows_max_chunks: int = 3,
    value_chunks_per_sheet: int = 2,
    max_chunks: int = 24,
    file_name: str = "register.xlsx",
) -> list[str]:
    return build_table_file_chunks(
        file_name=file_name,
        sheets=sheets,
        tokenizer=tokenizer,
        max_tokens=max_tokens,
        full_rows_max_chunks=full_rows_max_chunks,
        value_chunks_per_sheet=value_chunks_per_sheet,
        max_chunks=max_chunks,
    )


def test_empty_file_gives_no_chunks(tokenizer: BaseTokenizer) -> None:
    assert _build(tokenizer, []) == []
    assert _build(tokenizer, [sheet("Empty", []), sheet("Blank", [["", " "]])]) == []


def test_small_sheet_keeps_every_row_with_header(tokenizer: BaseTokenizer) -> None:
    chunks = _build(tokenizer, [csv_sheet("Depositors", CID_DEPOSITORS_CSV)])
    assert len(chunks) == 1
    text = chunks[0]
    assert text.startswith("Spreadsheet register.xlsx: 1 sheet (Depositors)")
    assert "Sheet Depositors: 5 rows; Columns: depositor_id" in text
    assert "register.xlsx :: Depositors (all 5 rows)" in text
    for depositor in ["D-1001", "D-1002", "D-1003", "D-1004", "D-1005"]:
        assert f"depositor_id={depositor}" in text
    assert "name=Lakshmi Devi, amount_inr=300000" in text


def test_note_row_is_not_counted_as_a_record(tokenizer: BaseTokenizer) -> None:
    rows = [["Serial#", "Conference", "City"]]
    rows += [[str(i), f"Conference {i}", f"City {i}"] for i in range(1, 17)]
    rows.append(["", "Note: dates are provisional and may change.", ""])
    text = "\n".join(_build(tokenizer, [sheet("Events", rows)]))
    assert "Sheet Events: 17 rows (16 with a Serial# value);" in text
    assert "register.xlsx :: Events (all 17 rows, 16 with a Serial# value)" in text


def test_record_note_absent_when_every_row_is_numbered(
    tokenizer: BaseTokenizer,
) -> None:
    rows = [["Serial#", "Conference"]] + [[str(i), f"C{i}"] for i in range(1, 6)]
    text = "\n".join(_build(tokenizer, [sheet("Events", rows)]))
    assert "Sheet Events: 5 rows;" in text
    assert "with a Serial# value" not in text


def test_csv_file_without_sheet_name(tokenizer: BaseTokenizer) -> None:
    chunks = _build(
        tokenizer,
        [csv_sheet("", CID_BANK_STATEMENTS_CSV)],
        file_name="bank_statements.csv",
    )
    assert chunks[0].startswith("Spreadsheet bank_statements.csv\n")
    assert "Sheet Data: 4 rows" in chunks[0]
    assert "bank_statements.csv (all 4 rows)" in chunks[0]


def test_two_column_key_value_sheet(tokenizer: BaseTokenizer) -> None:
    chunks = _build(tokenizer, [csv_sheet("Preauth", AAROGYASRI_PREAUTH_CSV)])
    assert len(chunks) == 1
    assert "field=cost_estimate, value=90000" in chunks[0]


def test_large_sheet_gets_summary(tokenizer: BaseTokenizer) -> None:
    rows = grievance_rows(5000)
    chunks = _build(tokenizer, [sheet("Register", rows)])
    assert 1 < len(chunks) <= 24
    text = "\n".join(chunks)
    assert "Sheet Register: 5000 rows" in text
    assert "register.xlsx :: Register: 5000 rows x 6 columns (summary" in text
    assert "Time range: filed_on 2025-01-01 to 2025-06-28" in text
    assert (
        "Identifiers: case_id (case id) GRV-00000 ... GRV-04999 (5000 distinct)" in text
    )
    assert "district values (count): Hyderabad (1000)" in text
    assert "Totals across all rows:" in text
    assert "amount: total " in text and "count 5000" in text
    assert "Total amount by district (highest first):" in text
    assert "Total amount by month: 2025-01 " in text
    assert "Sample row: case_id=GRV-00000, district=Hyderabad" in text
    assert "register.xlsx :: Register: more values" in text
    # Rows are not all copied: a late row id is absent.
    assert "GRV-04321" not in text


def test_chunks_respect_token_limit(tokenizer: BaseTokenizer) -> None:
    for max_tokens in (128, 512, 2048):
        chunks = _build(
            tokenizer, [sheet("Register", grievance_rows(3000))], max_tokens=max_tokens
        )
        for chunk in chunks:
            # Lines are joined with newlines; allow a few tokens of BPE drift.
            assert count_tokens_safely(chunk, tokenizer) <= max_tokens + 5


def test_small_sheet_that_needs_several_chunks_repeats_heading(
    tokenizer: BaseTokenizer,
) -> None:
    rows = grievance_rows(12)
    chunks = _build(tokenizer, [sheet("Small", rows)], max_tokens=256)
    row_chunks = [c for c in chunks if "(all 12 rows)" in c]
    assert len(row_chunks) >= 2
    for chunk in row_chunks:
        assert chunk.startswith("register.xlsx :: Small (all 12 rows)\nColumns: ")
    joined = "\n".join(row_chunks)
    for i in range(12):
        assert f"case_id=GRV-{i:05d}," in joined


def test_same_header_sheets_merge(tokenizer: BaseTokenizer) -> None:
    sheets = [
        sheet("Jan", grievance_rows(1500, start=0)),
        sheet("Feb", grievance_rows(1500, start=1500)),
        sheet("Mar", grievance_rows(1500, start=3000)),
    ]
    text = "\n".join(_build(tokenizer, sheets))
    assert "sheets Jan, Feb, Mar (same columns): 4500 rows" in text
    assert "Sheet Jan, Feb, Mar: 4500 rows" in text


def test_small_same_header_sheets_do_not_merge(tokenizer: BaseTokenizer) -> None:
    sheets = [
        csv_sheet("A", CID_DEPOSITORS_CSV),
        csv_sheet("B", CID_DEPOSITORS_CSV),
    ]
    text = "\n".join(_build(tokenizer, sheets))
    assert "register.xlsx :: A (all 5 rows)" in text
    assert "register.xlsx :: B (all 5 rows)" in text


def test_text_sheet_goes_into_overview(tokenizer: BaseTokenizer) -> None:
    readme = [["About this register"], ["Maintained by the district office."]]
    chunks = _build(
        tokenizer,
        [sheet("Readme", readme), csv_sheet("Depositors", CID_DEPOSITORS_CSV)],
    )
    text = "\n".join(chunks)
    assert "About: About this register Maintained by the district office." in chunks[0]
    # No separate block repeats the readme.
    assert text.count("Maintained by the district office.") == 1


def test_long_text_sheet_gets_its_own_block(tokenizer: BaseTokenizer) -> None:
    readme = [
        [f"Line {i} of a long readme with several words in it."] for i in range(60)
    ]
    text = "\n".join(_build(tokenizer, [sheet("Readme", readme)]))
    assert "register.xlsx :: Readme\nLine 0 of" in text
    assert "Line 59 of a long readme" in text


def test_preamble_rows_above_header(tokenizer: BaseTokenizer) -> None:
    rows = [["Grievance register 2025"], [""], ["Amounts in INR"]] + grievance_rows(10)
    summary = summarize_sheet("R", iter(rows), tokenizer, 3 * 512)
    assert summary.kind == SheetKind.TABLE
    assert summary.header[0] == "case_id"
    assert summary.preamble == ["Grievance register 2025", "Amounts in INR"]
    chunks = _build(tokenizer, [sheet("R", rows)])
    assert "About: Grievance register 2025 Amounts in INR" in chunks[0]


def test_no_header_gives_unnamed_columns(tokenizer: BaseTokenizer) -> None:
    rows = [[str(i), str(i * 2), str(i * 3)] for i in range(30)]
    summary = summarize_sheet("N", iter(rows), tokenizer, 3 * 512)
    assert summary.synthetic_header
    assert summary.header == ["Column 1", "Column 2", "Column 3"]
    assert summary.row_count == 30
    text = "\n".join(_build(tokenizer, [sheet("N", rows)]))
    assert "Columns: 3 unnamed columns" in text
    assert "0, 0, 0" in text  # values without names, 0 kept


def test_repeated_header_rows_are_skipped(tokenizer: BaseTokenizer) -> None:
    rows = grievance_rows(5)
    rows = rows + [rows[0]] + grievance_rows(5, start=5)[1:]
    summary = summarize_sheet("R", iter(rows), tokenizer, 3 * 512)
    assert summary.row_count == 10


def test_column_roles(tokenizer: BaseTokenizer) -> None:
    rows = [["case_id", "district", "amount", "filed_on", "email", "remark"]]
    for i in range(300):
        rows.append(
            [
                f"GRV-{i}",
                ["North", "South"][i % 2],
                str(i),
                "2025-01-0" + str(1 + i % 9),
                f"user{i}@example.com",
                f"free text {i}",
            ]
        )
    summary = summarize_sheet("R", iter(rows), tokenizer, 10)
    assert not summary.is_small
    roles = [col.role() for col in summary.columns]
    assert roles == [
        ColumnRole.IDENTIFIER,
        ColumnRole.CATEGORY,
        ColumnRole.NUMERIC,
        ColumnRole.DATE,
        ColumnRole.CONTACT,
        ColumnRole.TEXT,
    ]


def test_dates_day_first_detected(tokenizer: BaseTokenizer) -> None:
    rows = [["filed_on", "amount", "district"]]
    for i in range(300):
        day = 1 + i % 28
        month = 1 + i % 3
        rows.append([f"{day:02d}/{month:02d}/2025", "10", ["A", "B"][i % 2]])
    text = "\n".join(_build(tokenizer, [sheet("R", rows)], full_rows_max_chunks=0))
    assert "Time range: filed_on 2025-01-01 to 2025-03-28" in text
    assert "Total amount by month: 2025-01 1000; 2025-02 1000; 2025-03 1000" in text


def test_ambiguous_dates_get_no_month_totals(tokenizer: BaseTokenizer) -> None:
    rows = [["filed_on", "amount"]]
    for i in range(100):
        rows.append([f"0{1 + i % 9}/0{1 + i % 5}/2025", "10"])
    text = "\n".join(_build(tokenizer, [sheet("R", rows)], full_rows_max_chunks=0))
    assert "Time range" not in text
    assert "by month" not in text


def test_numbers_units_and_percentages(tokenizer: BaseTokenizer) -> None:
    rows = [["ward", "fee", "share", "balance"]]
    for i in range(200):
        rows.append([["A", "B"][i % 2], "₹4,500", "45%", "-1,234.50"])
    text = "\n".join(_build(tokenizer, [sheet("R", rows)], full_rows_max_chunks=0))
    assert "fee: total 900000₹; average 4500₹" in text
    # Percentages are averaged, never summed.
    assert "share: average 45%" in text
    assert "share: total" not in text
    assert "balance: total -246900; average -1234.50" in text
    assert "Average share by ward (highest first): A 45%; B 45%" in text


def test_unicode_values_and_blank_or_duplicate_headers(
    tokenizer: BaseTokenizer,
) -> None:
    rows = [["జిల్లా", "", "स्थिति", "स्थिति"]]
    for i in range(5):
        rows.append(["హైదరాబాద్", "x", "लंबित", "हल"])
    text = "\n".join(_build(tokenizer, [sheet("తెలుగు", rows)]))
    assert "Columns: జిల్లా, स्थिति, स्थिति" in text
    assert "జిల్లా=హైదరాబాద్, x, स्थिति=लंबित, स्थिति=हल" in text


def test_cells_with_commas_quotes_and_newlines(tokenizer: BaseTokenizer) -> None:
    rows = [
        ["id", "note"],
        ["A-1", 'He said "pending", then left'],
        ["A-2", "line one\nline two"],
    ]
    text = "\n".join(_build(tokenizer, [sheet("R", rows)]))
    assert 'note=He said "pending", then left' in text
    assert "note=line one\nline two" in text


def test_huge_cell_is_trimmed_not_fatal(tokenizer: BaseTokenizer) -> None:
    rows = [["id", "blob"], ["A-1", "word " * 40_000], ["A-2", "short"]]
    chunks = _build(tokenizer, [sheet("R", rows)], max_tokens=512)
    assert chunks
    for chunk in chunks:
        assert count_tokens_safely(chunk, tokenizer) <= 512 + 5


def test_file_cap_and_fair_truncation(tokenizer: BaseTokenizer) -> None:
    sheets = [
        sheet(
            f"S{i}",
            [[f"col_{i}_a", f"col_{i}_b"]]
            + [[f"v{i}-{j}", f"w{i}-{j}"] for j in range(300)],
        )
        for i in range(40)
    ]
    chunks = _build(tokenizer, sheets, max_chunks=24)
    assert len(chunks) == 24
    overview = "\n".join(c for c in chunks if c.startswith("Spreadsheet"))
    assert "40 sheets" in overview


def test_tight_caps(tokenizer: BaseTokenizer) -> None:
    sheets = [
        sheet("Register", grievance_rows(2000)),
        sheet("Other", grievance_rows(50)),
    ]
    chunks = _build(
        tokenizer,
        sheets,
        full_rows_max_chunks=1,
        value_chunks_per_sheet=0,
        max_chunks=5,
    )
    assert 1 <= len(chunks) <= 5
    assert "more values" not in "\n".join(chunks)


def test_redundant_columns_get_no_value_lists(tokenizer: BaseTokenizer) -> None:
    rows = [["first_name", "full_name", "amount"]]
    for i in range(300):
        rows.append([f"Name{i}", f"Name{i} Surname{i}", str(i)])
    summary = summarize_sheet("R", iter(rows), tokenizer, 10)
    assert summary.redundant_columns == {0}
    text = "\n".join(_build(tokenizer, [sheet("R", rows)], full_rows_max_chunks=0))
    assert "first_name (first name) (300 distinct" not in text
    assert "full_name (full name) (300 distinct; most common first)" in text


def test_wide_sheet(tokenizer: BaseTokenizer) -> None:
    header = [f"c{i}" for i in range(60)]
    rows = [header] + [[f"t{j} {i}" for i in range(60)] for j in range(250)]
    chunks = _build(tokenizer, [sheet("Wide", rows)])
    assert 1 <= len(chunks) <= 24
    assert "Wide: 250 rows x 60 columns" in "\n".join(chunks)


def test_packer_merges_small_blocks_and_caps(tokenizer: BaseTokenizer) -> None:
    packer = ChunkPacker(tokenizer=tokenizer, max_tokens=50, max_chunks=2)
    packer.add(ChunkBlock(lines=["a b c"], label="one"))
    packer.add(ChunkBlock(lines=["d e f"], label="two"))
    packer.add(ChunkBlock(lines=["word " * 45], label="three"))
    packer.add(ChunkBlock(lines=["word " * 45], label="four"))
    chunks = packer.finish()
    assert len(chunks) == 2
    assert chunks[0] == "a b c\nd e f"
