from datetime import datetime
from datetime import timezone

import pytest

from om.evals.rag_benchmark.benchmark import compute_aggregates
from om.evals.rag_benchmark.delta_report import build_delta_report
from om.evals.rag_benchmark.delta_report import DeltaReportMismatch
from om.evals.rag_benchmark.delta_report import metric_delta
from om.evals.rag_benchmark.delta_report import render_run_summary
from om.evals.rag_benchmark.models import AnswerResult
from om.evals.rag_benchmark.models import QuestionResult
from om.evals.rag_benchmark.models import RagBenchmarkRun
from om.evals.rag_benchmark.models import RetrievalResult
from om.evals.rag_benchmark.models import RunEnv
from om.evals.rag_benchmark.models import RunInfo
from om.evals.rag_benchmark.retrieval_metrics import retrieval_metric_set

LANGS = ["en"] * 4 + ["te"] * 4 + ["hi"] * 4


def _run(
    label: str,
    hits: list[bool],
    answer_acc: list[float] | None = None,
    env: dict[str, str] | None = None,
) -> RagBenchmarkRun:
    """One gold doc per question; hit -> gold at rank 1, miss -> not retrieved."""
    per_question = []
    for idx, (lang, hit) in enumerate(zip(LANGS, hits)):
        ranked = ["gold.pdf", "x.pdf"] if hit else ["x.pdf", "y.pdf"]
        q = QuestionResult(
            id=f"{lang}-{idx:03d}",
            lang=lang,  # type: ignore[arg-type]
            category="lookup",
            doc_type="pdf",
            gold_docs=["gold.pdf"],
            retrieval={
                "retrieval": RetrievalResult(
                    mode="retrieval",
                    ranked_docs=ranked,
                    metrics=retrieval_metric_set(ranked, ["gold.pdf"]),
                    latency_ms=100.0 + idx,
                )
            },
        )
        if answer_acc is not None:
            q.answers = [
                AnswerResult(
                    repeat=r,
                    answer="a",
                    metrics={"figure_accuracy": answer_acc[idx]},
                    latency_ms=1000.0,
                )
                for r in (1, 2)
            ]
        per_question.append(q)
    env_fields: dict[str, object] = {
        "dataset_version": "gov_v1",
        "dataset_sha256": "a" * 64,
        "embedding_model": "embed-x",
        "answer_model": "gpt-4o-mini" if answer_acc is not None else None,
        "judge_model": "gpt-4.1" if answer_acc is not None else None,
    }
    env_fields.update(env or {})
    return RagBenchmarkRun(
        run=RunInfo(
            label=label,
            mode="all",
            started_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
        ),
        env=RunEnv(**env_fields),  # type: ignore[arg-type]
        per_question=per_question,
        aggregates=compute_aggregates(per_question),
    )


ALL_HIT = [True] * 12
BASE_HITS = [True, True, False, True, True, False, True, True, True, True, False, True]


def test_result_json_round_trip() -> None:
    run = _run("baseline", BASE_HITS, answer_acc=[1.0] * 12)
    assert RagBenchmarkRun.model_validate_json(run.model_dump_json()) == run


def test_baseline_vs_baseline_is_zero_with_ci_containing_zero() -> None:
    base = _run("baseline", BASE_HITS, answer_acc=[0.5] * 12)
    same = _run("baseline2", BASE_HITS, answer_acc=[0.5] * 12)
    for group in ["overall", "lang:en", "lang:te", "lang:hi"]:
        for metric in ["recall@5", "recall@10", "mrr", "ndcg@10", "hit@5"]:
            d = metric_delta(base, same, "retrieval", metric, group)
            assert d is not None and d.delta == 0.0 and d.ci_low <= 0.0 <= d.ci_high
        d = metric_delta(base, same, "answer", "figure_accuracy", group)
        assert d is not None and d.delta == 0.0
    report = build_delta_report([base, same])
    assert not report.blocked
    assert "Retrieval gate: PASS" in report.markdown


def test_language_split_is_independent() -> None:
    base = _run("baseline", BASE_HITS)
    # Only Telugu changes: te-006 (a miss) becomes a hit.
    hits = list(BASE_HITS)
    hits[5] = True
    lane = _run("l1", hits)
    assert metric_delta(base, lane, "retrieval", "recall@5", "lang:en").delta == 0.0  # type: ignore[union-attr]
    assert metric_delta(base, lane, "retrieval", "recall@5", "lang:hi").delta == 0.0  # type: ignore[union-attr]
    te = metric_delta(base, lane, "retrieval", "recall@5", "lang:te")
    assert (
        te is not None and te.baseline == 0.75 and te.value == 1.0 and te.delta == 0.25
    )
    overall = metric_delta(base, lane, "retrieval", "recall@5", "overall")
    assert overall is not None and overall.delta == pytest.approx(1 / 12)


def test_delta_table_golden_row() -> None:
    base = _run("baseline", BASE_HITS)
    lane = _run("l1", ALL_HIT)
    md = build_delta_report([base, lane]).markdown
    row = next(line for line in md.splitlines() if line.startswith("| recall@5 |"))
    # 3 of 12 misses fixed (one per language). Small n: every CI touches 0 -> "≈".
    assert row == (
        "| recall@5 | 0.750 → 1.000 (≈ +0.250 [+0.000, +0.500]) "
        "| 0.750 → 1.000 (≈ +0.250 [+0.000, +0.750]) "
        "| 0.750 → 1.000 (≈ +0.250 [+0.000, +0.750]) "
        "| 0.750 → 1.000 (≈ +0.250 [+0.000, +0.750]) |"
    )
    te_lost = _run("l2", [True] * 4 + [False] * 4 + [True] * 4)
    md2 = build_delta_report([lane, te_lost]).markdown
    row2 = next(line for line in md2.splitlines() if line.startswith("| recall@5 |"))
    assert (
        "| 1.000 → 0.000 (-1.000 [-1.000, -1.000]) |" in row2
    )  # te: significant, no "≈"
    assert "### retrieval mode" in md and "| recall@10 |" in md


def test_gate_blocks_on_significant_retrieval_drop() -> None:
    base = _run("baseline", ALL_HIT)
    worse = [True] * 4 + [False] * 4 + [True] * 4  # all Telugu lost
    lane = _run("l2", worse)
    report = build_delta_report([base, lane])
    assert report.blocked
    assert any("[te]" in reason for reason in report.block_reasons)
    assert "Retrieval gate: BLOCK" in report.markdown


def test_answer_drop_does_not_block() -> None:
    base = _run("baseline", ALL_HIT, answer_acc=[1.0] * 12)
    lane = _run("l2", ALL_HIT, answer_acc=[0.0] * 12)
    report = build_delta_report([base, lane])
    assert not report.blocked
    assert "answer mode (informational)" in report.markdown


@pytest.mark.parametrize(
    "env",
    [
        {"dataset_sha256": "b" * 64},
        {"dataset_version": "gov_v2"},
        {"embedding_model": "embed-y"},
    ],
)
def test_refuses_mismatched_runs(env: dict[str, str]) -> None:
    with pytest.raises(DeltaReportMismatch):
        build_delta_report([_run("baseline", ALL_HIT), _run("other", ALL_HIT, env=env)])


@pytest.mark.parametrize(
    "env", [{"answer_model": "gpt-4.1-mini"}, {"judge_model": "gpt-4o"}]
)
def test_refuses_mismatched_answer_or_judge_model(env: dict[str, str]) -> None:
    base = _run("baseline", ALL_HIT, answer_acc=[1.0] * 12)
    other = _run("other", ALL_HIT, [1.0] * 12, env=env)
    with pytest.raises(DeltaReportMismatch):
        build_delta_report([base, other])


def test_retrieval_only_run_compares_with_full_run() -> None:
    base = _run("baseline", ALL_HIT, answer_acc=[1.0] * 12)
    lane = _run("l3", ALL_HIT)  # no answer mode -> answer model None, not a mismatch
    report = build_delta_report([base, lane])
    assert "### answer mode" not in report.markdown


def test_multi_run_compare_has_one_section_per_lane() -> None:
    runs = [
        _run("baseline", BASE_HITS),
        _run("l1", ALL_HIT),
        _run("l2", BASE_HITS),
        _run("combined", ALL_HIT),
    ]
    md = build_delta_report(runs).markdown
    assert md.count("**Retrieval gate:") == 3
    assert "| retrieval_p50_ms | overall |" in md


def test_needs_two_runs() -> None:
    with pytest.raises(ValueError):
        build_delta_report([_run("baseline", ALL_HIT)])


def test_run_summary_has_language_columns() -> None:
    md = render_run_summary(_run("baseline", BASE_HITS, answer_acc=[1.0] * 12))
    assert "| metric | overall | en | te | hi |" in md
    assert "| recall@5 | 0.750 | 0.750 | 0.750 | 0.750 |" in md
    assert "## answer mode" in md
