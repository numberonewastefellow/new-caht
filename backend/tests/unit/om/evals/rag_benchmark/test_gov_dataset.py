"""Integrity of the committed gov_v1 RAG benchmark dataset (no stack needed)."""

import codecs
import csv
import hashlib
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pytest
from openpyxl import load_workbook

from om.evals.rag_benchmark.models import DatasetManifest
from om.evals.rag_benchmark.models import RagBenchmarkQuestion
from tests.rag_benchmark import gen_gov_rag_corpus as gen

# Upstream product names, stored obfuscated so this file never contains them.
_UPSTREAM_NAMES = [codecs.decode(n, "rot13") for n in ("balk", "qnafjre")]


@lru_cache(maxsize=1)
def _questions() -> list[RagBenchmarkQuestion]:
    lines = gen.QUESTIONS_PATH.read_text(encoding="utf-8").splitlines()
    return [
        RagBenchmarkQuestion.model_validate_json(line) for line in lines if line.strip()
    ]


@lru_cache(maxsize=1)
def _manifest() -> DatasetManifest:
    return DatasetManifest.model_validate_json(
        gen.MANIFEST_PATH.read_text(encoding="utf-8")
    )


def test_question_ids_unique_and_schema_valid() -> None:
    questions = _questions()
    assert len(questions) == 150
    assert len({q.id for q in questions}) == 150
    for q in questions:
        assert q.gold_docs, q.id
        assert q.expected_figures, q.id
        assert q.expected_facts, q.id


def test_language_quotas() -> None:
    assert Counter(q.lang for q in _questions()) == {"en": 60, "te": 45, "hi": 45}


def test_doc_type_and_category_quotas() -> None:
    questions = _questions()
    doc_types = Counter(q.doc_type for q in questions)
    assert doc_types["pdf"] == 40
    assert doc_types["xlsx"] + doc_types["csv"] == 60
    assert doc_types["docx"] == 30
    assert doc_types["multi"] == 20
    categories = Counter(q.category for q in questions)
    assert categories["aggregate"] == 20
    assert categories["recency"] == 10
    assert categories["multi_part"] == 20
    assert categories["cross_lingual"] == 15
    assert all(q.lang != "en" for q in questions if q.category == "cross_lingual")


def test_multi_doc_questions_have_two_gold_docs_or_two_parts() -> None:
    for q in _questions():
        if q.doc_type == "multi":
            assert len(q.expected_figures) >= 2, q.id


def test_gold_docs_exist_in_manifest() -> None:
    names = {e.file_name for e in _manifest().files}
    for q in _questions():
        for gold in q.gold_docs:
            assert gold in names, f"{q.id}: {gold}"


def test_manifest_matches_files_on_disk() -> None:
    manifest = _manifest()
    assert manifest.dataset_version == gen.DATASET_VERSION
    on_disk = {p.name for p in gen.CORPUS_DIR.iterdir() if p.is_file()}
    assert on_disk == {e.file_name for e in manifest.files}
    for entry in manifest.files:
        payload = (gen.CORPUS_DIR / entry.file_name).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == entry.sha256, entry.file_name
        assert len(payload) == entry.size_bytes


def test_corpus_shape() -> None:
    files = _manifest().files
    assert Counter(e.doc_type for e in files)["pdf"] == 16
    assert {e.lang for e in files} == {"en", "te", "hi"}
    distractors = [e for e in files if e.is_distractor]
    assert len(distractors) == 8
    by_name = {e.file_name: e for e in files}
    for old in distractors:
        current = by_name[old.supersedes or ""]
        assert old.doc_updated_at < current.doc_updated_at
        assert old.lang == current.lang
    assert any(e.boost for e in files)


def test_recency_gold_is_the_current_version() -> None:
    files = {e.file_name: e for e in _manifest().files}
    superseded = {e.supersedes for e in files.values() if e.is_distractor}
    for q in _questions():
        assert all(not files[g].is_distractor for g in q.gold_docs), q.id
        if q.category == "recency":
            assert any(g in superseded for g in q.gold_docs), q.id


def test_no_upstream_names_in_dataset_text() -> None:
    texts = [
        gen.QUESTIONS_PATH.read_text(encoding="utf-8"),
        gen.MANIFEST_PATH.read_text(encoding="utf-8"),
    ]
    texts.extend(
        gen.extract_text(gen.CORPUS_DIR / e.file_name) for e in _manifest().files
    )
    for text in texts:
        lowered = text.lower()
        for name in _UPSTREAM_NAMES:
            assert name not in lowered


def test_no_upstream_names_in_binaries() -> None:
    for entry in _manifest().files:
        raw = (gen.CORPUS_DIR / entry.file_name).read_bytes().lower()
        for name in _UPSTREAM_NAMES:
            assert name.encode() not in raw, entry.file_name


def test_expected_figures_appear_in_extracted_gold_text() -> None:
    """Generator self-check: gold answers are stated by our own extracted text,
    and recency figures are not stated by the superseded distractor."""
    assert gen.self_check(gen.CORPUS_DIR, _questions(), _manifest()) == []


def _tabular_rows(file_name: str, sheet: str | None) -> list[dict[str, str]]:
    path = gen.CORPUS_DIR / file_name
    if sheet is None:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    workbook = load_workbook(path, read_only=True)
    rows = list(workbook[sheet].iter_rows(values_only=True))
    header = [str(h) for h in rows[0]]
    return [dict(zip(header, (str(v) for v in row))) for row in rows[1:]]


def test_computed_aggregates_match_the_files() -> None:
    checked = 0
    for q in _questions():
        if q.category != "aggregate":
            continue
        check = q.aggregate_check
        assert check is not None, q.id
        rows = [
            r
            for r in _tabular_rows(check.file_name, check.sheet)
            if all(r[k] == v for k, v in check.where.items())
        ]
        expected: float = (
            float(len(rows))
            if check.op == "count"
            else sum(float(r[check.column or ""]) for r in rows)
        )
        assert [f.value for f in q.expected_figures] == [expected], q.id
        assert all(f.computed for f in q.expected_figures)
        checked += 1
    assert checked == 20


@pytest.mark.parametrize("suffix", [".xlsx", ".docx", ".csv"])
def test_generator_reproduces_committed_files(tmp_path: Path, suffix: str) -> None:
    data = {dept.key: gen.build_dept_data(dept) for dept in gen.DEPTS}
    gen.write_corpus(tmp_path, data, pdf_source_dir=None)
    generated = sorted(p for p in tmp_path.iterdir() if p.suffix == suffix)
    assert generated
    for path in generated:
        committed = gen.CORPUS_DIR / path.name
        if suffix == ".csv":
            assert path.read_bytes() == committed.read_bytes(), path.name
        else:
            assert gen.zip_content_digest(path) == gen.zip_content_digest(
                committed
            ), path.name


def test_generator_reproduces_questions() -> None:
    data = {dept.key: gen.build_dept_data(dept) for dept in gen.DEPTS}
    regenerated = gen.questions_jsonl(gen.build_questions(data))
    assert regenerated == gen.QUESTIONS_PATH.read_text(encoding="utf-8")
    # And it parses back to the same objects.
    assert [json.loads(line)["id"] for line in regenerated.splitlines()] == [
        q.id for q in _questions()
    ]
