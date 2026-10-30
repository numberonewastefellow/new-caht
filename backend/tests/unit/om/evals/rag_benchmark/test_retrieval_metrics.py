import math

import pytest

from om.evals.rag_benchmark.retrieval_metrics import bootstrap_delta_ci
from om.evals.rag_benchmark.retrieval_metrics import dedupe_ranked_docs
from om.evals.rag_benchmark.retrieval_metrics import gold_ranks
from om.evals.rag_benchmark.retrieval_metrics import hit_at_k
from om.evals.rag_benchmark.retrieval_metrics import ndcg_at_k
from om.evals.rag_benchmark.retrieval_metrics import percentile
from om.evals.rag_benchmark.retrieval_metrics import recall_at_k
from om.evals.rag_benchmark.retrieval_metrics import reciprocal_rank
from om.evals.rag_benchmark.retrieval_metrics import retrieval_metric_set

RANKING = ["d3", "d1", "d7", "d2", "d9"]
GOLD = {"d1", "d2"}


# --- §8a.1 hand-computed reference case ---------------------------------------


def test_reference_ranking_recall() -> None:
    assert recall_at_k(RANKING, GOLD, 3) == 0.5
    assert recall_at_k(RANKING, GOLD, 5) == 1.0


def test_reference_ranking_mrr() -> None:
    assert reciprocal_rank(RANKING, GOLD) == 0.5


def test_reference_ranking_hits() -> None:
    assert hit_at_k(RANKING, GOLD, 1) == 0.0
    assert hit_at_k(RANKING, GOLD, 5) == 1.0


def test_reference_ranking_ndcg() -> None:
    expected = (1 / math.log2(3) + 1 / math.log2(5)) / (1 + 1 / math.log2(3))
    assert ndcg_at_k(RANKING, GOLD, 5) == pytest.approx(expected)
    assert ndcg_at_k(RANKING, GOLD, 5) == pytest.approx(0.6509, abs=1e-4)


def test_gold_at_rank_one_is_perfect() -> None:
    ranking = ["g", "x", "y"]
    assert reciprocal_rank(ranking, {"g"}) == 1.0
    assert ndcg_at_k(ranking, {"g"}, 10) == 1.0
    assert recall_at_k(ranking, {"g"}, 5) == 1.0


def test_no_gold_found_is_all_zero() -> None:
    ranking = ["a", "b", "c"]
    metrics = retrieval_metric_set(ranking, {"z"})
    assert set(metrics.values()) == {0.0}
    assert gold_ranks(ranking, ["z"]) == [None]


def test_empty_ranking_is_all_zero() -> None:
    assert set(retrieval_metric_set([], {"z"}).values()) == {0.0}


def test_multi_gold_partial_recall_and_ideal_dcg() -> None:
    ranking = ["g1", "x", "g2"]
    gold = {"g1", "g2", "g3"}
    assert recall_at_k(ranking, gold, 10) == pytest.approx(2 / 3)
    idcg = 1 + 1 / math.log2(3) + 1 / math.log2(4)
    assert ndcg_at_k(ranking, gold, 10) == pytest.approx((1 + 0.5) / idcg)


def test_ideal_dcg_capped_at_k() -> None:
    # 3 gold docs but k=1: a gold doc at rank 1 is a perfect top-1.
    assert ndcg_at_k(["g1"], {"g1", "g2", "g3"}, 1) == 1.0


def test_empty_gold_raises() -> None:
    with pytest.raises(ValueError):
        recall_at_k(["a"], set(), 5)


def test_dedupe_chunk_hits_counts_doc_once() -> None:
    chunk_hits = ["Doc A.pdf", "doc a.PDF", "Doc B.xlsx", "Doc A.pdf", "doc c.csv"]
    ranked = dedupe_ranked_docs(chunk_hits)
    assert ranked == ["doc a.pdf", "doc b.xlsx", "doc c.csv"]
    # Without dedupe doc c would sit at rank 5; deduped it is rank 3.
    assert gold_ranks(ranked, ["Doc C.CSV"]) == [3]
    assert recall_at_k(ranked, {"doc c.csv"}, 3) == 1.0


def test_percentile_linear_interpolation() -> None:
    values = [float(v) for v in range(1, 101)]
    assert percentile(values, 50) == pytest.approx(50.5)
    assert percentile(values, 95) == pytest.approx(95.05)
    assert percentile([7.0], 95) == 7.0
    assert percentile([1.0, 2.0], 0) == 1.0
    assert percentile([1.0, 2.0], 100) == 2.0


def test_percentile_rejects_empty_and_bad_q() -> None:
    with pytest.raises(ValueError):
        percentile([], 50)
    with pytest.raises(ValueError):
        percentile([1.0], 101)


def test_bootstrap_ci_is_deterministic() -> None:
    before = [0.0, 1.0, 0.5, 1.0, 0.0, 1.0, 0.0, 0.5]
    after = [1.0, 1.0, 0.5, 1.0, 1.0, 1.0, 0.0, 1.0]
    first = bootstrap_delta_ci(before, after)
    second = bootstrap_delta_ci(before, after)
    assert first == second
    delta, low, high = first
    assert delta == pytest.approx(0.3125)
    assert low <= delta <= high


def test_bootstrap_ci_identical_runs_is_zero() -> None:
    values = [0.0, 1.0, 0.5, 1.0]
    assert bootstrap_delta_ci(values, list(values)) == (0.0, 0.0, 0.0)


def test_bootstrap_ci_requires_pairs() -> None:
    with pytest.raises(ValueError):
        bootstrap_delta_ci([1.0], [1.0, 0.0])
