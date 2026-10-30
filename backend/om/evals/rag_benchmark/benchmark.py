"""RAG benchmark runner (the counterpart of ``om.evals.eval.run_eval``).

Modes:
  retrieval  search endpoint, no query expansion, LLM section selection switched
             off on the stack for the duration (restored afterwards). No LLM calls.
  product    search endpoint with the stack's own expansion/selection settings.
  answer     chat endpoint (answer LLM pinned via llm_override), repeated
             ``answer_repeats`` times; figures matched deterministically, answers
             graded by the judge.

``OfflineStack`` is a deterministic in-process stand-in (lexical ranking over
the local corpus) used by ``--dry-run`` so the whole pipeline can be verified
without a running stack.
"""

import math
import re
import time
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from typing import Protocol

from pydantic import BaseModel
from pydantic import Field

from om.evals.rag_benchmark.answer_judge import CompletionFn
from om.evals.rag_benchmark.answer_judge import judge_answer
from om.evals.rag_benchmark.answer_judge import JUDGE_PROMPT_SHA256
from om.evals.rag_benchmark.answer_judge import relevant_excerpt
from om.evals.rag_benchmark.corpus_setup import dataset_sha256
from om.evals.rag_benchmark.corpus_setup import load_manifest
from om.evals.rag_benchmark.corpus_setup import read_corpus_text
from om.evals.rag_benchmark.figure_match import match_expected_figures
from om.evals.rag_benchmark.models import AnswerResult
from om.evals.rag_benchmark.models import IndexStats
from om.evals.rag_benchmark.models import MetricAggregate
from om.evals.rag_benchmark.models import QuestionResult
from om.evals.rag_benchmark.models import RagBenchmarkQuestion
from om.evals.rag_benchmark.models import RagBenchmarkRun
from om.evals.rag_benchmark.models import RetrievalMode
from om.evals.rag_benchmark.models import RetrievalResult
from om.evals.rag_benchmark.models import RetrievedDoc
from om.evals.rag_benchmark.models import RunEnv
from om.evals.rag_benchmark.models import RunInfo
from om.evals.rag_benchmark.models import RunMode
from om.evals.rag_benchmark.retrieval_metrics import dedupe_ranked_docs
from om.evals.rag_benchmark.retrieval_metrics import gold_ranks
from om.evals.rag_benchmark.retrieval_metrics import mean
from om.evals.rag_benchmark.retrieval_metrics import percentile
from om.evals.rag_benchmark.retrieval_metrics import recall_at_k
from om.evals.rag_benchmark.retrieval_metrics import retrieval_metric_set

RETRIEVAL_METRICS = ["recall@5", "recall@10", "mrr", "ndcg@10", "hit@5"]
ANSWER_METRICS = [
    "figure_accuracy",
    "figures_all_correct",
    "completeness",
    "faithfulness",
    "chat_recall@10",
]
# Ranked docs kept per question in the result JSON (metrics use the full list).
STORED_RANK_DEPTH = 20
WARMUP_QUERIES = [
    "district wise allocation",
    "standard operating procedure steps",
    "register 2026",
]


class BenchmarkStack(Protocol):
    api_base: str

    def search(
        self,
        query: str,
        run_query_expansion: bool,
        num_hits: int = 50,
        document_sets: list[str] | None = None,
    ) -> tuple[list[RetrievedDoc], list[str] | None, float]: ...

    def chat(
        self,
        message: str,
        model_provider: str | None,
        model_version: str | None,
        forced_tool_id: int | None,
        agent_id: int = 0,
        temperature: float | None = None,
    ) -> tuple[dict[str, Any], float]: ...

    def find_search_tool_id(self) -> int: ...

    def get_expansion_settings(self) -> dict[str, Any]: ...

    def put_expansion_settings(self, updates: dict[str, Any]) -> dict[str, Any]: ...

    def get_search_settings(self) -> dict[str, Any]: ...


class RunConfig(BaseModel):
    label: str
    mode: RunMode = "all"
    lanes: list[str] = Field(default_factory=list)
    num_hits: int = 50
    warmup: bool = True
    answer_provider: str | None = None
    answer_model: str | None = "gpt-4o-mini"
    answer_repeats: int = 2
    answer_temperature: float | None = None
    force_search: bool = True
    judge_model: str | None = "gpt-4.1"  # None disables the judge
    judge_api_key: str | None = None
    document_sets: list[str] | None = None
    git_sha: str | None = None
    branch: str | None = None
    dry_run: bool = False


def _modes(mode: RunMode) -> list[str]:
    return ["retrieval", "product", "answer"] if mode == "all" else [mode]


# --- retrieval ------------------------------------------------------------------


def _ranked_with_scores(
    docs: list[RetrievedDoc],
) -> tuple[list[str], list[float | None]]:
    ranked: list[str] = []
    scores: list[float | None] = []
    for doc in docs:
        before = len(ranked)
        ranked = dedupe_ranked_docs([*ranked, doc.semantic_identifier])
        if len(ranked) > before:
            scores.append(doc.score)
    return ranked, scores


def score_search_result(
    question: RagBenchmarkQuestion,
    mode: RetrievalMode,
    docs: list[RetrievedDoc],
    selected_ids: list[str] | None,
    latency_ms: float | None,
) -> RetrievalResult:
    ranked, scores = _ranked_with_scores(docs)
    metrics = retrieval_metric_set(ranked, question.gold_docs)
    selected_docs = None
    if selected_ids is not None:
        selected = set(selected_ids)
        selected_docs = dedupe_ranked_docs(
            d.semantic_identifier for d in docs if d.document_id in selected
        )
        metrics["selected_recall"] = recall_at_k(
            selected_docs, question.gold_docs, len(selected_docs) or 1
        )
    return RetrievalResult(
        mode=mode,
        ranked_docs=ranked[:STORED_RANK_DEPTH],
        scores=scores[:STORED_RANK_DEPTH],
        gold_ranks=gold_ranks(ranked, question.gold_docs),
        llm_selected_docs=selected_docs,
        metrics=metrics,
        latency_ms=latency_ms,
    )


def _run_search_mode(
    stack: BenchmarkStack,
    questions: list[RagBenchmarkQuestion],
    mode: RetrievalMode,
    config: RunConfig,
    log: Callable[[str], None],
) -> dict[str, RetrievalResult]:
    expansion = mode == "product"
    if config.warmup:
        for query in WARMUP_QUERIES:
            try:
                stack.search(query, expansion, config.num_hits, config.document_sets)
            except Exception:  # noqa: BLE001 - warm-up failures are not scored
                pass
    results: dict[str, RetrievalResult] = {}
    for idx, q in enumerate(questions, start=1):
        try:
            docs, selected, latency = stack.search(
                q.question, expansion, config.num_hits, config.document_sets
            )
            results[q.id] = score_search_result(q, mode, docs, selected, latency)
        except Exception as exc:  # noqa: BLE001 - a failed query scores as a miss
            zero = {name: 0.0 for name in RETRIEVAL_METRICS}
            results[q.id] = RetrievalResult(
                mode=mode, ranked_docs=[], metrics=zero, error=str(exc)[:500]
            )
        if idx % 25 == 0:
            log(f"  [{mode}] {idx}/{len(questions)}")
    return results


def run_retrieval_mode(
    stack: BenchmarkStack,
    questions: list[RagBenchmarkQuestion],
    config: RunConfig,
    log: Callable[[str], None] = print,
) -> dict[str, RetrievalResult]:
    """Raw retrieval: LLM section selection is switched off on the (scratch)
    stack for the run and the recorded values are restored afterwards."""
    original = stack.get_expansion_settings()
    changes = (
        {"enable_llm_section_selection": False}
        if original.get("enable_llm_section_selection")
        else {}
    )
    if changes:
        stack.put_expansion_settings(changes)
    try:
        return _run_search_mode(stack, questions, "retrieval", config, log)
    finally:
        if changes:
            stack.put_expansion_settings({key: original[key] for key in changes})


# --- answers ------------------------------------------------------------------------


class GoldTextCache:
    def __init__(self, corpus_dir: Path) -> None:
        self.corpus_dir = corpus_dir
        self._texts: dict[str, str] = {}

    def text(self, file_name: str) -> str:
        if file_name not in self._texts:
            path = self.corpus_dir / file_name
            self._texts[file_name] = read_corpus_text(path) if path.exists() else ""
        return self._texts[file_name]

    def source_for(self, question: RagBenchmarkQuestion) -> str:
        budget = 16000 // max(1, len(question.gold_docs))
        parts = [
            f"### {name}\n{relevant_excerpt(self.text(name), question.question, budget)}"
            for name in question.gold_docs
        ]
        return "\n\n".join(parts)


def score_answer(
    question: RagBenchmarkQuestion,
    repeat: int,
    response: dict[str, Any],
    latency_ms: float | None,
) -> AnswerResult:
    answer = response.get("answer_citationless") or response.get("answer") or ""
    top_docs = response.get("top_documents") or []
    retrieved = dedupe_ranked_docs(
        str(d.get("semantic_identifier") or "") for d in top_docs
    )
    id_to_name = {
        d.get("document_id"): str(d.get("semantic_identifier") or "") for d in top_docs
    }
    cited = dedupe_ranked_docs(
        id_to_name[c.get("document_id")]
        for c in response.get("citation_info") or []
        if c.get("document_id") in id_to_name
    )
    hits = match_expected_figures(answer, question.expected_figures)
    metrics = {
        "figure_accuracy": mean([1.0 if h else 0.0 for h in hits]) if hits else 0.0,
        "figures_all_correct": 1.0 if hits and all(hits) else 0.0,
        "chat_recall@10": recall_at_k(retrieved, question.gold_docs, 10),
    }
    return AnswerResult(
        repeat=repeat,
        answer=answer,
        retrieved_docs=retrieved,
        cited_docs=cited,
        figure_hits=hits,
        metrics=metrics,
        latency_ms=latency_ms,
        error=response.get("error_msg"),
    )


def run_answer_mode(
    stack: BenchmarkStack,
    questions: list[RagBenchmarkQuestion],
    config: RunConfig,
    gold_texts: GoldTextCache,
    judge_completion: CompletionFn | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, list[AnswerResult]]:
    tool_id = stack.find_search_tool_id() if config.force_search else None
    results: dict[str, list[AnswerResult]] = {q.id: [] for q in questions}
    for repeat in range(1, config.answer_repeats + 1):
        for idx, q in enumerate(questions, start=1):
            try:
                response, latency = stack.chat(
                    q.question,
                    config.answer_provider,
                    config.answer_model,
                    tool_id,
                    temperature=config.answer_temperature,
                )
                result = score_answer(q, repeat, response, latency)
            except Exception as exc:  # noqa: BLE001 - a failed turn scores as zero
                result = AnswerResult(
                    repeat=repeat,
                    answer="",
                    figure_hits=[False] * len(q.expected_figures),
                    metrics={name: 0.0 for name in ANSWER_METRICS},
                    error=str(exc)[:500],
                )
            if config.judge_model:
                try:
                    verdict = judge_answer(
                        q.question,
                        q.expected_facts,
                        gold_texts.source_for(q),
                        result.answer,
                        model=config.judge_model,
                        api_key=config.judge_api_key,
                        completion=judge_completion,
                    )
                    result.judge = verdict
                    result.metrics["completeness"] = verdict.completeness
                    result.metrics["faithfulness"] = verdict.faithfulness
                except (
                    Exception
                ) as exc:  # noqa: BLE001 - judge failure is recorded, not scored
                    result.error = (result.error or "") + f" | judge: {str(exc)[:300]}"
            results[q.id].append(result)
            if idx % 25 == 0:
                log(f"  [answer r{repeat}] {idx}/{len(questions)}")
    return results


# --- aggregation ----------------------------------------------------------------


def question_groups(q: QuestionResult) -> list[str]:
    return [
        "overall",
        f"lang:{q.lang}",
        f"doc_type:{q.doc_type}",
        f"category:{q.category}",
    ]


def per_question_value(q: QuestionResult, mode: str, metric: str) -> float | None:
    """One value per question; answer metrics are averaged over repeats."""
    if mode in ("retrieval", "product"):
        result = q.retrieval.get(mode)
        if result is None:
            return None
        return result.metrics.get(metric)
    if mode == "answer":
        values = [a.metrics[metric] for a in q.answers if metric in a.metrics]
        return mean(values) if values else None
    raise ValueError(mode)


def _latencies(q: QuestionResult, mode: str) -> list[float]:
    if mode == "answer":
        return [a.latency_ms for a in q.answers if a.latency_ms is not None]
    result = q.retrieval.get(mode)
    return [result.latency_ms] if result and result.latency_ms is not None else []


def compute_aggregates(per_question: list[QuestionResult]) -> list[MetricAggregate]:
    aggregates: list[MetricAggregate] = []
    modes_present = {
        "retrieval": any("retrieval" in q.retrieval for q in per_question),
        "product": any("product" in q.retrieval for q in per_question),
        "answer": any(q.answers for q in per_question),
    }
    groups = sorted(
        {g for q in per_question for g in question_groups(q)}, key=_group_order
    )
    for mode, present in modes_present.items():
        if not present:
            continue
        if mode == "answer":
            metrics = ANSWER_METRICS
        elif mode == "product":
            metrics = RETRIEVAL_METRICS + ["selected_recall"]
        else:
            metrics = RETRIEVAL_METRICS
        for metric in metrics:
            for group in groups:
                values = [
                    v
                    for q in per_question
                    if group in question_groups(q)
                    for v in [per_question_value(q, mode, metric)]
                    if v is not None
                ]
                if values:
                    aggregates.append(
                        MetricAggregate(
                            mode=mode,
                            metric=metric,
                            group=group,
                            value=mean(values),
                            n=len(values),
                        )
                    )
        for group in [g for g in groups if g == "overall" or g.startswith("lang:")]:
            latencies = [
                lat
                for q in per_question
                if group in question_groups(q)
                for lat in _latencies(q, mode)
            ]
            if latencies:
                for pct in (50, 95):
                    aggregates.append(
                        MetricAggregate(
                            mode="latency",
                            metric=f"{mode}_p{pct}_ms",
                            group=group,
                            value=percentile(latencies, pct),
                            n=len(latencies),
                        )
                    )
    return aggregates


def _group_order(group: str) -> tuple[int, str]:
    order = {"overall": 0, "lang:en": 1, "lang:te": 2, "lang:hi": 3}
    return (order.get(group, 10), group)


# --- runner ---------------------------------------------------------------------


def run_rag_benchmark(
    stack: BenchmarkStack,
    dataset_dir: Path,
    questions: list[RagBenchmarkQuestion],
    config: RunConfig,
    index_stats: IndexStats | None = None,
    judge_completion: CompletionFn | None = None,
    log: Callable[[str], None] = print,
    backend: str = "http",
) -> RagBenchmarkRun:
    manifest = load_manifest(dataset_dir)
    started = datetime.now(timezone.utc)
    modes = _modes(config.mode)
    try:
        search_settings = stack.get_search_settings()
    except Exception:  # noqa: BLE001 - informational only
        search_settings = None
    try:
        expansion_settings = stack.get_expansion_settings()
    except Exception:  # noqa: BLE001 - informational only
        expansion_settings = None

    per_question = {
        q.id: QuestionResult(
            id=q.id,
            lang=q.lang,
            category=q.category,
            doc_type=q.doc_type,
            gold_docs=q.gold_docs,
        )
        for q in questions
    }
    if "retrieval" in modes:
        log("Retrieval mode ...")
        for qid, result in run_retrieval_mode(stack, questions, config, log).items():
            per_question[qid].retrieval["retrieval"] = result
    if "product" in modes:
        log("Product mode ...")
        for qid, result in _run_search_mode(
            stack, questions, "product", config, log
        ).items():
            per_question[qid].retrieval["product"] = result
    if "answer" in modes:
        log(f"Answer mode ({config.answer_repeats} repeats) ...")
        gold_texts = GoldTextCache(dataset_dir / "corpus")
        for qid, answers in run_answer_mode(
            stack, questions, config, gold_texts, judge_completion, log
        ).items():
            per_question[qid].answers = answers

    results = list(per_question.values())
    answer_mode = "answer" in modes
    env = RunEnv(
        api_base=stack.api_base,
        dataset_version=manifest.dataset_version,
        dataset_sha256=dataset_sha256(dataset_dir),
        embedding_model=(search_settings or {}).get("model_name"),
        embedding_dim=(search_settings or {}).get("model_dim"),
        search_settings=search_settings,
        expansion_settings=expansion_settings,
        answer_model=config.answer_model if answer_mode else None,
        answer_provider=config.answer_provider if answer_mode else None,
        answer_repeats=config.answer_repeats if answer_mode else 0,
        judge_model=config.judge_model if answer_mode else None,
        judge_prompt_sha256=(
            JUDGE_PROMPT_SHA256 if answer_mode and config.judge_model else None
        ),
        force_search=config.force_search,
        document_sets=config.document_sets,
        backend=backend,
    )
    return RagBenchmarkRun(
        run=RunInfo(
            label=config.label,
            mode=config.mode,
            git_sha=config.git_sha,
            branch=config.branch,
            lanes=config.lanes,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            dry_run=config.dry_run,
        ),
        env=env,
        index=index_stats,
        per_question=results,
        aggregates=compute_aggregates(results),
    )


# --- offline backend (--dry-run) ---------------------------------------------------

_WORD_RE = re.compile(r"\w+", flags=re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [t.casefold() for t in _WORD_RE.findall(text)]


class OfflineStack:
    """Deterministic stand-in for the stack: BM25 over whole local corpus files,
    and an "answer" that quotes the best-matching line of the top document."""

    api_base = "offline://local-corpus"

    def __init__(self, dataset_dir: Path, k1: float = 1.2, b: float = 0.75) -> None:
        manifest = load_manifest(dataset_dir)
        corpus_dir = dataset_dir / "corpus"
        self.texts = {
            e.file_name: read_corpus_text(corpus_dir / e.file_name)
            for e in manifest.files
        }
        self.doc_tokens = {
            name: Counter(_tokens(text)) for name, text in self.texts.items()
        }
        self.doc_len = {name: sum(c.values()) for name, c in self.doc_tokens.items()}
        self.avg_len = mean(list(self.doc_len.values())) or 1.0
        df: Counter[str] = Counter()
        for counts in self.doc_tokens.values():
            df.update(counts.keys())
        n = len(self.doc_tokens)
        self.idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }
        self.k1, self.b = k1, b
        self.expansion_settings: dict[str, Any] = {
            "enable_expansion": False,
            "enable_llm_section_selection": False,
        }

    def _rank(self, query: str) -> list[tuple[str, float]]:
        terms = set(_tokens(query))
        scored = []
        for name, counts in self.doc_tokens.items():
            norm = self.k1 * (1 - self.b + self.b * self.doc_len[name] / self.avg_len)
            score = sum(
                self.idf.get(t, 0.0) * counts[t] * (self.k1 + 1) / (counts[t] + norm)
                for t in terms
                if counts[t]
            )
            if score > 0:
                scored.append((name, score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored

    def search(
        self,
        query: str,
        run_query_expansion: bool,
        num_hits: int = 50,
        document_sets: list[str] | None = None,
    ) -> tuple[list[RetrievedDoc], list[str] | None, float]:
        started = time.perf_counter()
        docs = [
            RetrievedDoc(
                document_id=f"offline__{name}",
                semantic_identifier=name,
                score=score,
                chunk_ind=0,
            )
            for name, score in self._rank(query)[:num_hits]
        ]
        return docs, None, (time.perf_counter() - started) * 1000.0

    def chat(
        self,
        message: str,
        model_provider: str | None,
        model_version: str | None,
        forced_tool_id: int | None,
        agent_id: int = 0,
        temperature: float | None = None,
    ) -> tuple[dict[str, Any], float]:
        started = time.perf_counter()
        ranked = self._rank(message)[:5]
        answer = ""
        if ranked:
            terms = set(_tokens(message))
            lines = [
                line for line in self.texts[ranked[0][0]].splitlines() if line.strip()
            ]
            answer = max(
                lines,
                key=lambda line: (len(terms & set(_tokens(line))), -len(line)),
                default="",
            )
        top = [
            {"document_id": f"offline__{name}", "semantic_identifier": name}
            for name, _ in ranked
        ]
        response = {
            "answer": answer,
            "answer_citationless": answer,
            "top_documents": top,
            "citation_info": (
                [{"citation_number": 1, "document_id": top[0]["document_id"]}]
                if top
                else []
            ),
            "tool_calls": [],
            "message_id": 0,
        }
        return response, (time.perf_counter() - started) * 1000.0

    def find_search_tool_id(self) -> int:
        return 0

    def get_expansion_settings(self) -> dict[str, Any]:
        return dict(self.expansion_settings)

    def put_expansion_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        self.expansion_settings.update(updates)
        return dict(self.expansion_settings)

    def get_search_settings(self) -> dict[str, Any]:
        return {"model_name": "offline-bm25", "model_dim": 0}
