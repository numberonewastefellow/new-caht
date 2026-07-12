"""Deterministic Vespa retrieval baseline tests.

Each test runs a real search against the seeded corpus and:
  (a) asserts exact, computable filter behavior (KB / source_type / time_cutoff), and
  (b) snapshots the ranked result list as a golden file (see snapshot.py).

IMPORTANT — isolation: the target Vespa index is shared with whatever else has been
ingested into the app, so every query here is scoped to the corpus' own document
sets (``corpus.ALL_KBS``). That keeps results deterministic and reproducible
regardless of ambient data, and makes the snapshots portable across environments.

Generate goldens the first time with:  BASELINE_MODE=record pytest tests/search_baseline/test_vespa_baseline.py
Then run plain `pytest` to assert against them.

The same harness is engine-agnostic, so after the OpenSearch migration the
identical cases can be replayed against OpenSearch and diffed (see compare_engines.py).
"""

import pytest
from sqlalchemy.orm import Session

from om.configs.constants import DocumentSource
from tests.search_baseline import corpus
from tests.search_baseline.harness import BaselineHit
from tests.search_baseline.harness import get_index
from tests.search_baseline.harness import hit_doc_ids
from tests.search_baseline.harness import KEYWORD_ALPHA
from tests.search_baseline.harness import run_search
from tests.search_baseline.harness import SEMANTIC_ALPHA
from tests.search_baseline.snapshot import assert_matches

pytestmark = pytest.mark.usefixtures("seeded_corpus")

ALL_CORPUS_IDS = set(corpus.CORPUS_BY_ID)


def _corpus_search(db_session: Session, **kwargs) -> list[BaselineHit]:
    """Run a search scoped to the corpus' knowledge bases (unless already scoped).

    Scoping to the corpus document sets isolates the baseline from any other
    documents present in the shared index.
    """
    index = get_index("vespa", db_session)
    kwargs.setdefault("document_sets", corpus.ALL_KBS)
    return run_search(index, db_session=db_session, **kwargs)


def _returned_ids(hits: list[BaselineHit]) -> set[str]:
    return {h.document_id for h in hits}


def _assert_corpus_only(hits: list[BaselineHit]) -> None:
    """All results must be corpus docs (proves KB scoping isolates ambient data)."""
    foreign = _returned_ids(hits) - ALL_CORPUS_IDS
    assert not foreign, f"Non-corpus documents leaked into a KB-scoped query: {foreign}"


# --------------------------------------------------------------------------- #
# Plain term queries (semantic ranking profile, default alpha)
# --------------------------------------------------------------------------- #


def test_query_kubernetes_deploy(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="how do I deploy containers to a kubernetes cluster"
    )
    _assert_corpus_only(hits)
    assert hits[0].document_id == "eng-k8s-deploy", (
        f"Expected the kubernetes runbook to rank first, got {hit_doc_ids(hits)[:3]}"
    )
    assert_matches("query_kubernetes_deploy", hits)


def test_query_parental_leave(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="how much paid parental leave do new parents get"
    )
    _assert_corpus_only(hits)
    assert hits[0].document_id == "hr-parental-leave", hit_doc_ids(hits)[:3]
    assert_matches("query_parental_leave", hits)


def test_query_expense_report(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="how to submit an expense report for reimbursement"
    )
    _assert_corpus_only(hits)
    assert hits[0].document_id == "fin-expense-report", hit_doc_ids(hits)[:3]
    assert_matches("query_expense_report", hits)


# --------------------------------------------------------------------------- #
# Keyword vs semantic ranking profile (the live "rerank" knob)
# --------------------------------------------------------------------------- #


def test_keyword_vs_semantic_profile(db_session: Session) -> None:
    query = "asyncio event loop coroutines"

    keyword_hits = _corpus_search(db_session, query=query, hybrid_alpha=KEYWORD_ALPHA)
    semantic_hits = _corpus_search(db_session, query=query, hybrid_alpha=SEMANTIC_ALPHA)

    _assert_corpus_only(keyword_hits)
    _assert_corpus_only(semantic_hits)
    assert keyword_hits, "keyword profile returned no results"
    assert semantic_hits, "semantic profile returned no results"
    # Both profiles should surface the async guide for this query.
    assert "eng-python-async" in hit_doc_ids(keyword_hits)
    assert "eng-python-async" in hit_doc_ids(semantic_hits)

    assert_matches("profile_keyword_async", keyword_hits)
    assert_matches("profile_semantic_async", semantic_hits)


# --------------------------------------------------------------------------- #
# Filter: document_set (knowledge base)
# --------------------------------------------------------------------------- #


def test_filter_document_set_engineering(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="technical guide", document_sets=[corpus.KB_ENGINEERING]
    )
    _assert_corpus_only(hits)
    assert _returned_ids(hits) == corpus.doc_ids_in_kb(corpus.KB_ENGINEERING)
    assert_matches("filter_kb_engineering", hits)


def test_filter_document_set_hr(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="company policy", document_sets=[corpus.KB_HR]
    )
    _assert_corpus_only(hits)
    assert _returned_ids(hits) == corpus.doc_ids_in_kb(corpus.KB_HR)
    assert_matches("filter_kb_hr", hits)


def test_filter_document_set_finance(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="budget and costs", document_sets=[corpus.KB_FINANCE]
    )
    _assert_corpus_only(hits)
    # The shared engineering+finance doc must be retrievable under Finance too.
    assert "shared-saas-cost" in _returned_ids(hits)
    assert _returned_ids(hits) == corpus.doc_ids_in_kb(corpus.KB_FINANCE)
    assert_matches("filter_kb_finance", hits)


# --------------------------------------------------------------------------- #
# Filter: source_type (scoped to the corpus KBs for isolation)
# --------------------------------------------------------------------------- #


def test_filter_source_type_file(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="guide policy report", source_types=[DocumentSource.FILE]
    )
    _assert_corpus_only(hits)
    assert _returned_ids(hits) == corpus.doc_ids_with_source(DocumentSource.FILE)
    assert_matches("filter_source_file", hits)


def test_filter_source_type_web(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="guide policy process", source_types=[DocumentSource.WEB]
    )
    _assert_corpus_only(hits)
    assert _returned_ids(hits) == corpus.doc_ids_with_source(DocumentSource.WEB)
    assert_matches("filter_source_web", hits)


# --------------------------------------------------------------------------- #
# Filter: time_cutoff (date), scoped to the corpus KBs
# --------------------------------------------------------------------------- #


def test_filter_time_cutoff_recent_only(db_session: Session) -> None:
    hits = _corpus_search(
        db_session,
        query="guide policy report process",
        time_cutoff=corpus.TIME_CUTOFF_BETWEEN,
    )
    _assert_corpus_only(hits)
    returned = _returned_ids(hits)
    assert returned == corpus.recent_doc_ids()
    old_ids = ALL_CORPUS_IDS - corpus.recent_doc_ids()
    assert not (returned & old_ids), "Old docs leaked past the time cutoff"
    assert_matches("filter_time_cutoff_recent", hits)


# --------------------------------------------------------------------------- #
# Combined filters
# --------------------------------------------------------------------------- #


def test_combined_filters(db_session: Session) -> None:
    hits = _corpus_search(
        db_session,
        query="engineering guide",
        document_sets=[corpus.KB_ENGINEERING],
        source_types=[DocumentSource.FILE],
        time_cutoff=corpus.TIME_CUTOFF_BETWEEN,
    )
    _assert_corpus_only(hits)
    expected = (
        corpus.doc_ids_in_kb(corpus.KB_ENGINEERING)
        & corpus.doc_ids_with_source(DocumentSource.FILE)
        & corpus.recent_doc_ids()
    )
    assert _returned_ids(hits) == expected
    assert_matches("filter_combined_eng_file_recent", hits)


# --------------------------------------------------------------------------- #
# Keyword expansion (explicit final_keywords)
# --------------------------------------------------------------------------- #


def test_keyword_expansion(db_session: Session) -> None:
    hits = _corpus_search(
        db_session,
        query="how do I make my database queries faster",
        query_keywords=["database", "index", "query", "performance"],
    )
    _assert_corpus_only(hits)
    assert "eng-db-indexing" in hit_doc_ids(hits)[:3], hit_doc_ids(hits)[:3]
    assert_matches("keyword_expansion_db", hits)
