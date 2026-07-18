"""Deterministic OpenSearch retrieval baseline tests.

Runs against the OpenSearch engine (`get_index("opensearch")`) and snapshots
under `baselines/opensearch/`. The retrieval path is the production one
(`search_chunks → hybrid_retrieval`), so these goldens pin ranking behavior for
the sole document-index backend.

All queries are scoped to the corpus' document sets for isolation from ambient data.

Record goldens:  BASELINE_MODE=record pytest tests/search_baseline/test_opensearch_baseline.py
Assert:          pytest tests/search_baseline/test_opensearch_baseline.py
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

ENGINE = "opensearch"
pytestmark = pytest.mark.usefixtures("seeded_corpus_opensearch")

ALL_CORPUS_IDS = set(corpus.CORPUS_BY_ID)


def _corpus_search(db_session: Session, **kwargs) -> list[BaselineHit]:
    """Search OpenSearch scoped to the corpus' knowledge bases (unless already scoped)."""
    index = get_index(ENGINE, db_session)
    kwargs.setdefault("document_sets", corpus.ALL_KBS)
    return run_search(index, db_session=db_session, **kwargs)


def _returned_ids(hits: list[BaselineHit]) -> set[str]:
    return {h.document_id for h in hits}


def _assert_corpus_only(hits: list[BaselineHit]) -> None:
    foreign = _returned_ids(hits) - ALL_CORPUS_IDS
    assert not foreign, f"Non-corpus documents leaked into a KB-scoped query: {foreign}"


def _snap(name: str, hits: list[BaselineHit]) -> None:
    assert_matches(name, hits, engine=ENGINE)


# ----- Plain term queries -------------------------------------------------- #


def test_query_kubernetes_deploy(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="how do I deploy containers to a kubernetes cluster"
    )
    _assert_corpus_only(hits)
    assert hits[0].document_id == "eng-k8s-deploy", hit_doc_ids(hits)[:3]
    _snap("query_kubernetes_deploy", hits)


def test_query_parental_leave(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="how much paid parental leave do new parents get"
    )
    _assert_corpus_only(hits)
    assert hits[0].document_id == "hr-parental-leave", hit_doc_ids(hits)[:3]
    _snap("query_parental_leave", hits)


def test_query_expense_report(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="how to submit an expense report for reimbursement"
    )
    _assert_corpus_only(hits)
    assert hits[0].document_id == "fin-expense-report", hit_doc_ids(hits)[:3]
    _snap("query_expense_report", hits)


# ----- Keyword vs semantic ranking profile --------------------------------- #


def test_keyword_vs_semantic_profile(db_session: Session) -> None:
    query = "asyncio event loop coroutines"
    keyword_hits = _corpus_search(db_session, query=query, hybrid_alpha=KEYWORD_ALPHA)
    semantic_hits = _corpus_search(db_session, query=query, hybrid_alpha=SEMANTIC_ALPHA)

    _assert_corpus_only(keyword_hits)
    _assert_corpus_only(semantic_hits)
    assert "eng-python-async" in hit_doc_ids(keyword_hits)
    assert "eng-python-async" in hit_doc_ids(semantic_hits)

    _snap("profile_keyword_async", keyword_hits)
    _snap("profile_semantic_async", semantic_hits)


# ----- document_set (knowledge base) filter -------------------------------- #


def test_filter_document_set_engineering(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="technical guide", document_sets=[corpus.KB_ENGINEERING]
    )
    _assert_corpus_only(hits)
    assert _returned_ids(hits) == corpus.doc_ids_in_kb(corpus.KB_ENGINEERING)
    _snap("filter_kb_engineering", hits)


def test_filter_document_set_hr(db_session: Session) -> None:
    hits = _corpus_search(db_session, query="company policy", document_sets=[corpus.KB_HR])
    _assert_corpus_only(hits)
    assert _returned_ids(hits) == corpus.doc_ids_in_kb(corpus.KB_HR)
    _snap("filter_kb_hr", hits)


def test_filter_document_set_finance(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="budget and costs", document_sets=[corpus.KB_FINANCE]
    )
    _assert_corpus_only(hits)
    assert "shared-saas-cost" in _returned_ids(hits)
    assert _returned_ids(hits) == corpus.doc_ids_in_kb(corpus.KB_FINANCE)
    _snap("filter_kb_finance", hits)


# ----- source_type filter -------------------------------------------------- #


def test_filter_source_type_file(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="guide policy report", source_types=[DocumentSource.FILE]
    )
    _assert_corpus_only(hits)
    assert _returned_ids(hits) == corpus.doc_ids_with_source(DocumentSource.FILE)
    _snap("filter_source_file", hits)


def test_filter_source_type_web(db_session: Session) -> None:
    hits = _corpus_search(
        db_session, query="guide policy process", source_types=[DocumentSource.WEB]
    )
    _assert_corpus_only(hits)
    assert _returned_ids(hits) == corpus.doc_ids_with_source(DocumentSource.WEB)
    _snap("filter_source_web", hits)


# ----- time_cutoff (date) filter ------------------------------------------- #


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
    _snap("filter_time_cutoff_recent", hits)


# ----- Combined filters ---------------------------------------------------- #


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
    _snap("filter_combined_eng_file_recent", hits)


# ----- Keyword expansion --------------------------------------------------- #


def test_keyword_expansion(db_session: Session) -> None:
    hits = _corpus_search(
        db_session,
        query="how do I make my database queries faster",
        query_keywords=["database", "index", "query", "performance"],
    )
    _assert_corpus_only(hits)
    assert "eng-db-indexing" in hit_doc_ids(hits)[:3], hit_doc_ids(hits)[:3]
    _snap("keyword_expansion_db", hits)
