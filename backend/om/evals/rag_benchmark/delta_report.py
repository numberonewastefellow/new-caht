"""Before/after markdown tables (paired bootstrap CI per delta) + retrieval gate.

Runs are only comparable on the same dataset, embedding model, answer model
and judge; ``build_delta_report`` refuses otherwise. The retrieval gate (user
decision 2026-10-30): a lane is BLOCKED when a retrieval-mode ranking metric
drops by at least ``GATE_MIN_DROP`` with the whole 95% CI below zero, overall
or in any language. Answer metrics are informational.
"""

from dataclasses import dataclass
from dataclasses import field

from om.evals.rag_benchmark.benchmark import ANSWER_METRICS
from om.evals.rag_benchmark.benchmark import per_question_value
from om.evals.rag_benchmark.benchmark import RETRIEVAL_METRICS
from om.evals.rag_benchmark.models import RagBenchmarkRun
from om.evals.rag_benchmark.retrieval_metrics import bootstrap_delta_ci
from om.evals.rag_benchmark.retrieval_metrics import mean

LANG_GROUPS = ["overall", "lang:en", "lang:te", "lang:hi"]
GATE_METRICS = ["recall@5", "recall@10", "mrr", "ndcg@10"]
GATE_MIN_DROP = 0.02
APPROX = "≈"


class DeltaReportMismatch(ValueError):
    pass


@dataclass
class MetricDelta:
    baseline: float
    value: float
    delta: float
    ci_low: float
    ci_high: float
    n: int

    @property
    def crosses_zero(self) -> bool:
        return self.ci_low <= 0.0 <= self.ci_high


@dataclass
class DeltaReport:
    markdown: str
    blocked: bool
    block_reasons: list[str] = field(default_factory=list)


def check_comparable(baseline: RagBenchmarkRun, other: RagBenchmarkRun) -> None:
    a, b = baseline.env, other.env
    problems = []
    for key in ("dataset_version", "dataset_sha256", "embedding_model"):
        if getattr(a, key) != getattr(b, key):
            problems.append(f"{key}: {getattr(a, key)} != {getattr(b, key)}")
    # Answer-side identity only matters when both runs have answer mode.
    for key in ("answer_model", "judge_model", "judge_prompt_sha256"):
        va, vb = getattr(a, key), getattr(b, key)
        if va is not None and vb is not None and va != vb:
            problems.append(f"{key}: {va} != {vb}")
    if problems:
        raise DeltaReportMismatch(
            f"Runs '{baseline.run.label}' and '{other.run.label}' are not comparable: "
            + "; ".join(problems)
        )


def _values(
    run: RagBenchmarkRun, mode: str, metric: str, group: str
) -> dict[str, float]:
    out: dict[str, float] = {}
    for q in run.per_question:
        if group != "overall":
            kind, _, value = group.partition(":")
            if getattr(q, kind) != value:
                continue
        v = per_question_value(q, mode, metric)
        if v is not None:
            out[q.id] = v
    return out


def metric_delta(
    baseline: RagBenchmarkRun,
    other: RagBenchmarkRun,
    mode: str,
    metric: str,
    group: str,
) -> MetricDelta | None:
    before = _values(baseline, mode, metric, group)
    after = _values(other, mode, metric, group)
    ids = sorted(set(before) & set(after))
    if not ids:
        return None
    b = [before[i] for i in ids]
    a = [after[i] for i in ids]
    delta, low, high = bootstrap_delta_ci(b, a)
    return MetricDelta(
        baseline=mean(b),
        value=mean(a),
        delta=delta,
        ci_low=low,
        ci_high=high,
        n=len(ids),
    )


def _fmt_delta(d: MetricDelta | None) -> str:
    if d is None:
        return "-"
    mark = f"{APPROX} " if d.crosses_zero else ""
    return f"{d.baseline:.3f} → {d.value:.3f} ({mark}{d.delta:+.3f} [{d.ci_low:+.3f}, {d.ci_high:+.3f}])"


def _has_mode(run: RagBenchmarkRun, mode: str) -> bool:
    if mode == "answer":
        return any(q.answers for q in run.per_question)
    return any(mode in q.retrieval for q in run.per_question)


def _group_label(group: str) -> str:
    return group.split(":", 1)[1] if ":" in group else group


def _delta_table(
    baseline: RagBenchmarkRun,
    other: RagBenchmarkRun,
    mode: str,
    metrics: list[str],
    groups: list[str],
) -> list[str]:
    lines = ["| metric | " + " | ".join(_group_label(g) for g in groups) + " |"]
    lines.append("|---" * (len(groups) + 1) + "|")
    for metric in metrics:
        cells = [
            _fmt_delta(metric_delta(baseline, other, mode, metric, g)) for g in groups
        ]
        if all(c == "-" for c in cells):
            continue
        lines.append(f"| {metric} | " + " | ".join(cells) + " |")
    return lines


def retrieval_gate(baseline: RagBenchmarkRun, other: RagBenchmarkRun) -> list[str]:
    reasons: list[str] = []
    if not (_has_mode(baseline, "retrieval") and _has_mode(other, "retrieval")):
        return reasons
    for metric in GATE_METRICS:
        for group in LANG_GROUPS:
            d = metric_delta(baseline, other, "retrieval", metric, group)
            if d is not None and d.delta <= -GATE_MIN_DROP and d.ci_high < 0:
                reasons.append(
                    f"{metric} [{_group_label(group)}] {d.delta:+.3f} (CI {d.ci_low:+.3f}..{d.ci_high:+.3f})"
                )
    return reasons


def _aggregate(
    run: RagBenchmarkRun, mode: str, metric: str, group: str
) -> float | None:
    for agg in run.aggregates:
        if agg.mode == mode and agg.metric == metric and agg.group == group:
            return agg.value
    return None


def _run_meta(run: RagBenchmarkRun) -> str:
    return (
        f"`{run.run.label}` (sha `{(run.run.git_sha or '?')[:10]}`, branch `{run.run.branch or '?'}`, "
        f"lanes {', '.join(run.run.lanes) or '-'}, mode {run.run.mode}"
        f"{', DRY RUN (offline backend)' if run.run.dry_run else ''})"
    )


def _env_lines(run: RagBenchmarkRun) -> list[str]:
    env = run.env
    return [
        f"- Dataset: `{env.dataset_version}` sha256 `{env.dataset_sha256[:12]}`",
        f"- Embedding: `{env.embedding_model}` (dim {env.embedding_dim}); backend `{env.backend}`",
        f"- Answer model: `{env.answer_model}` x{env.answer_repeats}; judge `{env.judge_model}`"
        f" (prompt `{(env.judge_prompt_sha256 or '-')[:12]}`); force search {env.force_search}",
    ]


def _latency_lines(runs: list[RagBenchmarkRun]) -> list[str]:
    metrics = sorted(
        {a.metric for r in runs for a in r.aggregates if a.mode == "latency"}
    )
    if not metrics:
        return []
    lines = [
        "",
        "### Latency (ms, informational)",
        "",
        "| metric | group | " + " | ".join(f"`{r.run.label}`" for r in runs) + " |",
    ]
    lines.append("|---|---|" + "---|" * len(runs))
    for metric in metrics:
        for group in LANG_GROUPS:
            values = [_aggregate(r, "latency", metric, group) for r in runs]
            if all(v is None for v in values):
                continue
            lines.append(
                f"| {metric} | {_group_label(group)} | "
                + " | ".join("-" if v is None else f"{v:.0f}" for v in values)
                + " |"
            )
    return lines


def _index_lines(runs: list[RagBenchmarkRun]) -> list[str]:
    if not any(r.index for r in runs):
        return []
    lines = [
        "",
        "### Index",
        "",
        "| | " + " | ".join(f"`{r.run.label}`" for r in runs) + " |",
        "|---|" + "---|" * len(runs),
    ]
    lines.append(
        "| total chunks | "
        + " | ".join(str(r.index.total_chunks) if r.index else "-" for r in runs)
        + " |"
    )
    doc_types = sorted({t for r in runs if r.index for t in r.index.chunks_by_doc_type})
    for doc_type in doc_types:
        cells = []
        for r in runs:
            s = r.index.chunks_by_doc_type.get(doc_type) if r.index else None
            cells.append(
                f"{s['min']:.0f} / {s['median']:.0f} / {s['max']:.0f}" if s else "-"
            )
        lines.append(
            f"| chunks/doc {doc_type} (min/median/max) | " + " | ".join(cells) + " |"
        )
    lines.append(
        "| store size (MB) | "
        + " | ".join(
            (
                f"{r.index.store_size_bytes / 1e6:.1f}"
                if r.index and r.index.store_size_bytes
                else "-"
            )
            for r in runs
        )
        + " |"
    )
    return lines


def build_delta_report(runs: list[RagBenchmarkRun]) -> DeltaReport:
    if len(runs) < 2:
        raise ValueError("compare needs a baseline and at least one other run")
    baseline = runs[0]
    for other in runs[1:]:
        check_comparable(baseline, other)

    lines = [f"# RAG benchmark delta vs baseline {_run_meta(baseline)}", ""]
    lines.extend(_env_lines(baseline))
    lines.append("")
    lines.append(
        "Cells: `baseline → run (Δ [95% paired-bootstrap CI])`; "
        f"`{APPROX}` = CI crosses 0 (no significant change). Retrieval metrics are doc-level."
    )
    all_reasons: list[str] = []
    for other in runs[1:]:
        reasons = retrieval_gate(baseline, other)
        all_reasons.extend(f"{other.run.label}: {r}" for r in reasons)
        lines += ["", f"## {_run_meta(other)}", ""]
        verdict = "BLOCK" if reasons else "PASS"
        lines.append(
            f"**Retrieval gate: {verdict}**"
            + (" - " + "; ".join(reasons) if reasons else "")
        )
        for mode, metrics in (
            ("retrieval", RETRIEVAL_METRICS),
            ("product", RETRIEVAL_METRICS + ["selected_recall"]),
            ("answer", ANSWER_METRICS),
        ):
            if not (_has_mode(baseline, mode) and _has_mode(other, mode)):
                continue
            note = " (informational)" if mode == "answer" else ""
            lines += ["", f"### {mode} mode{note}", ""]
            lines += _delta_table(baseline, other, mode, metrics, LANG_GROUPS)
        if _has_mode(baseline, "retrieval") and _has_mode(other, "retrieval"):
            breakdown = sorted(
                {f"doc_type:{q.doc_type}" for q in baseline.per_question}
                | {f"category:{q.category}" for q in baseline.per_question}
            )
            lines += ["", "### retrieval recall@10 by doc type / category", ""]
            lines += ["| group | recall@10 |", "|---|---|"]
            for group in breakdown:
                lines.append(
                    f"| {group} | {_fmt_delta(metric_delta(baseline, other, 'retrieval', 'recall@10', group))} |"
                )
    lines += _latency_lines(runs)
    lines += _index_lines(runs)
    return DeltaReport(
        markdown="\n".join(lines) + "\n",
        blocked=bool(all_reasons),
        block_reasons=all_reasons,
    )


def render_run_summary(run: RagBenchmarkRun) -> str:
    """Single-run markdown (written next to the run JSON)."""
    lines = [f"# RAG benchmark run {_run_meta(run)}", ""]
    lines.extend(_env_lines(run))
    for mode, metrics in (
        ("retrieval", RETRIEVAL_METRICS),
        ("product", RETRIEVAL_METRICS + ["selected_recall"]),
        ("answer", ANSWER_METRICS),
    ):
        if not _has_mode(run, mode):
            continue
        lines += [
            "",
            f"## {mode} mode",
            "",
            "| metric | " + " | ".join(_group_label(g) for g in LANG_GROUPS) + " |",
        ]
        lines.append("|---" * (len(LANG_GROUPS) + 1) + "|")
        for metric in metrics:
            values = [_aggregate(run, mode, metric, g) for g in LANG_GROUPS]
            if all(v is None for v in values):
                continue
            lines.append(
                f"| {metric} | "
                + " | ".join("-" if v is None else f"{v:.3f}" for v in values)
                + " |"
            )
    groups = sorted(
        {
            a.group
            for a in run.aggregates
            if a.group.startswith(("doc_type:", "category:"))
        }
    )
    if groups:
        lines += [
            "",
            "## Breakdown",
            "",
            "| group | retrieval recall@10 | retrieval mrr | answer figure_accuracy |",
            "|---|---|---|---|",
        ]
        for group in groups:
            cells = [
                _aggregate(run, "retrieval", "recall@10", group),
                _aggregate(run, "retrieval", "mrr", group),
                _aggregate(run, "answer", "figure_accuracy", group),
            ]
            lines.append(
                f"| {group} | "
                + " | ".join("-" if v is None else f"{v:.3f}" for v in cells)
                + " |"
            )
    lines += _latency_lines([run])
    lines += _index_lines([run])
    errors = sum(
        1 for q in run.per_question for r in q.retrieval.values() if r.error
    ) + sum(1 for q in run.per_question for a in q.answers if a.error)
    lines += ["", f"Errors: {errors} failed calls (scored as misses)."]
    return "\n".join(lines) + "\n"
