#!/usr/bin/env python3
"""CLI for the RAG benchmark (the counterpart of ``om/evals/eval_cli.py``).

    python -m om.evals.rag_benchmark.benchmark_cli setup  [--api-base URL] [--dry-run]
    python -m om.evals.rag_benchmark.benchmark_cli run    --label baseline --mode all [--dry-run]
    python -m om.evals.rag_benchmark.benchmark_cli compare A.json B.json [C.json ...]

Run it against a SCRATCH stack only (fresh compose project, new volumes). The
API key must be an admin API key of that stack (RAG_BENCHMARK_API_KEY, falls
back to OM_EVAL_API_KEY). ``--dry-run`` uses the in-process offline backend:
no HTTP, no LLM, no stack.
"""

import argparse
import subprocess
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from urllib.parse import urlparse

from om.evals.rag_benchmark.api_client import RagBenchmarkApiClient
from om.evals.rag_benchmark.benchmark import BenchmarkStack
from om.evals.rag_benchmark.benchmark import OfflineStack
from om.evals.rag_benchmark.benchmark import run_rag_benchmark
from om.evals.rag_benchmark.benchmark import RunConfig
from om.evals.rag_benchmark.corpus_setup import build_corpus_zip
from om.evals.rag_benchmark.corpus_setup import CorpusSetupState
from om.evals.rag_benchmark.corpus_setup import document_set_name
from om.evals.rag_benchmark.corpus_setup import load_manifest
from om.evals.rag_benchmark.corpus_setup import load_questions
from om.evals.rag_benchmark.corpus_setup import setup_scratch_corpus
from om.evals.rag_benchmark.corpus_setup import verify_corpus
from om.evals.rag_benchmark.delta_report import build_delta_report
from om.evals.rag_benchmark.delta_report import DeltaReportMismatch
from om.evals.rag_benchmark.delta_report import render_run_summary
from om.evals.rag_benchmark.index_stats import collect_index_stats
from om.evals.rag_benchmark.models import RagBenchmarkRun

_BACKEND_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = _BACKEND_DIR.parent
DEFAULT_DATASET_VERSION = "gov_v1"
DEFAULT_RESULTS_DIR = REPO_ROOT / "docs" / "rag-eval" / "results"
EXIT_GATE_BLOCKED = 2


def default_dataset_dir(version: str) -> Path:
    return _BACKEND_DIR / "tests" / "rag_benchmark" / "datasets" / version


def default_state_file(api_base: str, version: str) -> Path:
    parsed = urlparse(api_base)
    host = f"{parsed.hostname or 'local'}_{parsed.port or ''}".strip("_")
    return Path.home() / ".rag_benchmark" / f"setup_{host}_{version}.json"


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _client(args: argparse.Namespace) -> RagBenchmarkApiClient:
    from om.configs.app_configs import RAG_BENCHMARK_API_BASE
    from om.configs.app_configs import RAG_BENCHMARK_API_KEY

    return RagBenchmarkApiClient(
        args.api_base or RAG_BENCHMARK_API_BASE, args.api_key or RAG_BENCHMARK_API_KEY
    )


def _resolve_dataset(args: argparse.Namespace) -> Path:
    return (
        Path(args.dataset_dir)
        if args.dataset_dir
        else default_dataset_dir(args.dataset)
    )


# --- setup ------------------------------------------------------------------------


def cmd_setup(args: argparse.Namespace) -> int:
    dataset_dir = _resolve_dataset(args)
    manifest = load_manifest(dataset_dir)
    problems = verify_corpus(dataset_dir, manifest)
    if problems:
        print("Corpus does not match manifest:", *problems, sep="\n  ")
        return 1
    if args.dry_run:
        payload = build_corpus_zip(dataset_dir, manifest)
        print(
            f"[dry-run] would upload {len(manifest.files)} files ({len(payload) / 1e6:.2f} MB zip), create file "
            f"connector + document set '{document_set_name(manifest.dataset_version)}', wait for indexing and "
            f"apply {sum(1 for e in manifest.files if e.boost)} boosts. No HTTP calls made."
        )
        return 0
    client = _client(args)
    state = setup_scratch_corpus(
        client, dataset_dir, timeout_s=args.timeout_min * 60.0, poll_s=args.poll_s
    )
    state_file = (
        Path(args.state_file)
        if args.state_file
        else default_state_file(client.api_base, manifest.dataset_version)
    )
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"Indexed {len(state.docs)} docs in {state.indexing_seconds or 0:.0f}s; state -> {state_file}"
    )
    return 0


# --- run --------------------------------------------------------------------------


def _upload_braintrust(run: RagBenchmarkRun) -> None:
    import braintrust

    from om.configs.app_configs import BRAINTRUST_API_KEY
    from om.configs.app_configs import BRAINTRUST_PROJECT

    experiment = braintrust.init(
        project=BRAINTRUST_PROJECT,
        experiment=f"rag-benchmark-{run.run.label}",
        api_key=BRAINTRUST_API_KEY or None,
    )
    for q in run.per_question:
        scores: dict[str, float] = {}
        for mode, result in q.retrieval.items():
            scores.update({f"{mode}.{k}": v for k, v in result.metrics.items()})
        for answer in q.answers:
            scores.update(
                {f"answer.r{answer.repeat}.{k}": v for k, v in answer.metrics.items()}
            )
        experiment.log(
            input=q.id,
            output={
                "retrieval": {m: r.ranked_docs[:10] for m, r in q.retrieval.items()},
                "answers": [a.answer for a in q.answers],
            },
            scores=scores,
            metadata={
                "lang": q.lang,
                "category": q.category,
                "doc_type": q.doc_type,
                "gold_docs": q.gold_docs,
            },
        )
    experiment.flush()


def write_run(run: RagBenchmarkRun, results_dir: Path) -> tuple[Path, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{run.run.started_at:%Y-%m-%d}_{run.run.label}"
    json_path = results_dir / f"{stem}.json"
    md_path = results_dir / f"{stem}.md"
    json_path.write_text(run.model_dump_json(indent=1), encoding="utf-8")
    md_path.write_text(render_run_summary(run), encoding="utf-8")
    return json_path, md_path


def cmd_run(args: argparse.Namespace) -> int:
    dataset_dir = _resolve_dataset(args)
    manifest = load_manifest(dataset_dir)
    questions = load_questions(
        Path(args.questions) if args.questions else dataset_dir / "questions.jsonl"
    )
    if args.ids:
        wanted = set(args.ids.split(","))
        questions = [q for q in questions if q.id in wanted]
    if args.limit:
        questions = questions[: args.limit]

    from om.configs.app_configs import RAG_BENCHMARK_JUDGE_API_KEY
    from om.configs.app_configs import RAG_BENCHMARK_JUDGE_MODEL

    judge_model = (
        None if args.no_judge else (args.judge_model or RAG_BENCHMARK_JUDGE_MODEL)
    )
    if args.dry_run and not args.judge_in_dry_run:
        judge_model = None
    config = RunConfig(
        label=args.label,
        mode=args.mode,
        lanes=[lane for lane in (args.lanes or "").split(",") if lane],
        num_hits=args.num_hits,
        answer_provider=args.answer_provider,
        answer_model=args.answer_model,
        answer_repeats=args.repeats,
        force_search=not args.no_force_search,
        judge_model=judge_model,
        judge_api_key=RAG_BENCHMARK_JUDGE_API_KEY or None,
        document_sets=[args.scope_document_set] if args.scope_document_set else None,
        git_sha=args.git_sha or _git("rev-parse", "HEAD"),
        branch=args.branch or _git("rev-parse", "--abbrev-ref", "HEAD"),
        dry_run=args.dry_run,
    )

    stack: BenchmarkStack
    index_stats = None
    if args.dry_run:
        stack = OfflineStack(dataset_dir)
        backend = "offline"
    else:
        client = _client(args)
        stack = client
        backend = "http"
        state_file = (
            Path(args.state_file)
            if args.state_file
            else default_state_file(client.api_base, manifest.dataset_version)
        )
        if state_file.exists():
            state = CorpusSetupState.model_validate_json(
                state_file.read_text(encoding="utf-8")
            )
            auth = (
                tuple(args.opensearch_auth.split(":", 1))
                if args.opensearch_auth
                else None
            )
            index_stats = collect_index_stats(
                client, manifest, state.docs, args.opensearch_url, auth
            )
        else:
            print(
                f"No setup state at {state_file}; index stats skipped (run `setup` first)."
            )

    run = run_rag_benchmark(
        stack, dataset_dir, questions, config, index_stats=index_stats, backend=backend
    )
    results_dir = (
        Path(args.results_dir)
        if args.results_dir
        else (
            Path.cwd() / "rag-benchmark-dry-run"
            if args.dry_run
            else DEFAULT_RESULTS_DIR
        )
    )
    json_path, md_path = write_run(run, results_dir)
    print(f"Wrote {json_path}\nWrote {md_path}")
    if args.braintrust:
        _upload_braintrust(run)
    return 0


# --- compare --------------------------------------------------------------------


def load_run(path: Path) -> RagBenchmarkRun:
    return RagBenchmarkRun.model_validate_json(path.read_text(encoding="utf-8"))


def cmd_compare(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.runs]
    runs = [load_run(p) for p in paths]
    try:
        report = build_delta_report(runs)
    except DeltaReportMismatch as exc:
        print(f"REFUSED: {exc}")
        return 1
    if args.out:
        out = Path(args.out)
    else:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        others = "-".join(r.run.label for r in runs[1:])
        out = paths[-1].parent / f"{date}_{others}_vs_{runs[0].run.label}.md"
    out.write_text(report.markdown, encoding="utf-8")
    print(f"Wrote {out}")
    if report.blocked:
        print("Retrieval gate: BLOCK", *report.block_reasons, sep="\n  ")
        return EXIT_GATE_BLOCKED
    print("Retrieval gate: PASS")
    return 0


# --- parser -----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--api-base",
            help="API server root, e.g. http://localhost:18080 (or http://host:3000/api)",
        )
        p.add_argument("--api-key", help="admin API key of the scratch stack")
        p.add_argument("--dataset", default=DEFAULT_DATASET_VERSION)
        p.add_argument("--dataset-dir", help="override the dataset directory")
        p.add_argument(
            "--state-file",
            help="setup state JSON (default ~/.rag_benchmark/setup_<host>_<port>_<dataset>.json)",
        )
        p.add_argument(
            "--dry-run", action="store_true", help="offline backend: no HTTP, no LLM"
        )

    p_setup = sub.add_parser(
        "setup", help="upload the corpus to the scratch stack and wait for indexing"
    )
    common(p_setup)
    p_setup.add_argument("--timeout-min", type=float, default=60.0)
    p_setup.add_argument("--poll-s", type=float, default=15.0)
    p_setup.set_defaults(func=cmd_setup)

    p_run = sub.add_parser(
        "run", help="run the benchmark and write results JSON + markdown"
    )
    common(p_run)
    p_run.add_argument(
        "--label", required=True, help="run label, e.g. baseline / l1 / combined"
    )
    p_run.add_argument(
        "--mode", choices=["retrieval", "product", "answer", "all"], default="all"
    )
    p_run.add_argument("--lanes", help="comma-separated lane list, e.g. l1,l2")
    p_run.add_argument("--num-hits", type=int, default=50)
    p_run.add_argument("--answer-model", default="gpt-4o-mini")
    p_run.add_argument(
        "--answer-provider",
        help="LLM provider name on the stack (llm_override.model_provider)",
    )
    p_run.add_argument(
        "--repeats", type=int, default=2, help="answer-mode repeats (averaged)"
    )
    p_run.add_argument(
        "--judge-model", help="default RAG_BENCHMARK_JUDGE_MODEL (gpt-4.1)"
    )
    p_run.add_argument("--no-judge", action="store_true")
    p_run.add_argument(
        "--judge-in-dry-run",
        action="store_true",
        help="call the real judge even with --dry-run",
    )
    p_run.add_argument(
        "--no-force-search",
        action="store_true",
        help="let the model choose whether to search",
    )
    p_run.add_argument(
        "--scope-document-set",
        help="filter search to this document set (dev-stack fallback only)",
    )
    p_run.add_argument(
        "--questions", help="alternative questions.jsonl (e.g. a mini set)"
    )
    p_run.add_argument("--ids", help="comma-separated question ids")
    p_run.add_argument("--limit", type=int)
    p_run.add_argument("--results-dir")
    p_run.add_argument(
        "--opensearch-url", help="scratch OpenSearch URL for index store size"
    )
    p_run.add_argument("--opensearch-auth", help="user:password for --opensearch-url")
    p_run.add_argument("--git-sha")
    p_run.add_argument("--branch")
    p_run.add_argument(
        "--braintrust",
        action="store_true",
        help="also log per-question rows to Braintrust",
    )
    p_run.set_defaults(func=cmd_run)

    p_cmp = sub.add_parser("compare", help="delta table: first run is the baseline")
    p_cmp.add_argument("runs", nargs="+")
    p_cmp.add_argument("--out")
    p_cmp.set_defaults(func=cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
