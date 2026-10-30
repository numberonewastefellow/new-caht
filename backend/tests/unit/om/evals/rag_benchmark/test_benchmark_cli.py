"""Runner, judge and CLI tests with a fake stack / fake litellm (no network)."""

import json
from pathlib import Path
from typing import Any

import pytest

from om.evals.rag_benchmark import benchmark_cli
from om.evals.rag_benchmark.answer_judge import build_judge_messages
from om.evals.rag_benchmark.answer_judge import judge_answer
from om.evals.rag_benchmark.answer_judge import JUDGE_PROMPT_SHA256
from om.evals.rag_benchmark.answer_judge import parse_judge_output
from om.evals.rag_benchmark.answer_judge import relevant_excerpt
from om.evals.rag_benchmark.benchmark import run_rag_benchmark
from om.evals.rag_benchmark.benchmark import run_retrieval_mode
from om.evals.rag_benchmark.benchmark import RunConfig
from om.evals.rag_benchmark.benchmark import score_answer
from om.evals.rag_benchmark.benchmark import score_search_result
from om.evals.rag_benchmark.corpus_setup import load_questions
from om.evals.rag_benchmark.models import ExpectedFigure
from om.evals.rag_benchmark.models import RagBenchmarkQuestion
from om.evals.rag_benchmark.models import RagBenchmarkRun
from om.evals.rag_benchmark.models import RetrievedDoc
from tests.rag_benchmark import gen_gov_rag_corpus as gen


class FakeStack:
    api_base = "http://fake"

    def __init__(
        self,
        selection_on: bool = True,
        ranking: list[str] | None = None,
        answer: str = "",
    ) -> None:
        self.settings: dict[str, Any] = {
            "enable_expansion": True,
            "enable_llm_section_selection": selection_on,
        }
        self.puts: list[dict[str, Any]] = []
        self.searches: list[tuple[str, bool]] = []
        self.settings_during_search: list[bool] = []
        self.ranking = ranking or []
        self.answer = answer
        self.fail_with: BaseException | None = None

    def search(
        self,
        query: str,
        run_query_expansion: bool,
        num_hits: int = 50,
        document_sets: list[str] | None = None,
    ) -> Any:
        self.searches.append((query, run_query_expansion))
        self.settings_during_search.append(
            self.settings["enable_llm_section_selection"]
        )
        if self.fail_with is not None:
            raise self.fail_with
        docs = [
            RetrievedDoc(document_id=f"id-{n}", semantic_identifier=n, score=1.0)
            for n in self.ranking
        ]
        return docs, None, 12.5

    def chat(
        self,
        message: str,
        model_provider: str | None,
        model_version: str | None,
        forced_tool_id: int | None,
        agent_id: int = 0,
        temperature: float | None = None,
    ) -> Any:
        top = [
            {"document_id": f"id-{n}", "semantic_identifier": n} for n in self.ranking
        ]
        return {
            "answer": self.answer + " [1]",
            "answer_citationless": self.answer,
            "top_documents": top,
            "citation_info": (
                [{"citation_number": 1, "document_id": top[0]["document_id"]}]
                if top
                else []
            ),
        }, 900.0

    def find_search_tool_id(self) -> int:
        return 4

    def get_expansion_settings(self) -> dict[str, Any]:
        return dict(self.settings)

    def put_expansion_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        self.puts.append(dict(updates))
        self.settings.update(updates)
        return dict(self.settings)

    def get_search_settings(self) -> dict[str, Any]:
        return {"model_name": "fake-embed", "model_dim": 8}


def _q(
    qid: str = "en-001",
    gold: list[str] | None = None,
    figures: list[float] | None = None,
    lang: str = "en",
) -> RagBenchmarkQuestion:
    return RagBenchmarkQuestion(
        id=qid,
        lang=lang,  # type: ignore[arg-type]
        question="What is the fee?",
        category="lookup",
        doc_type="pdf",
        gold_docs=gold or ["land_go_2026_en.pdf"],
        expected_figures=[ExpectedFigure(value=v) for v in (figures or [1250])],
        expected_facts=["the fee is Rs 1,250"],
    )


# --- expansion settings restore ---------------------------------------------------


def test_restores_expansion_settings() -> None:
    stack = FakeStack(selection_on=True, ranking=["land_go_2026_en.pdf"])
    run_retrieval_mode(
        stack, [_q()], RunConfig(label="t", warmup=False), log=lambda _: None
    )
    assert stack.puts == [
        {"enable_llm_section_selection": False},
        {"enable_llm_section_selection": True},
    ]
    assert stack.settings_during_search == [False]
    assert stack.settings["enable_llm_section_selection"] is True
    assert stack.searches == [
        ("What is the fee?", False)
    ]  # no query expansion in raw mode


def test_restores_expansion_settings_after_abort() -> None:
    stack = FakeStack(selection_on=True)
    stack.fail_with = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        run_retrieval_mode(
            stack, [_q()], RunConfig(label="t", warmup=False), log=lambda _: None
        )
    assert stack.settings["enable_llm_section_selection"] is True


def test_leaves_settings_alone_when_selection_already_off() -> None:
    stack = FakeStack(selection_on=False, ranking=["x"])
    run_retrieval_mode(
        stack, [_q()], RunConfig(label="t", warmup=False), log=lambda _: None
    )
    assert stack.puts == []


def test_failed_query_scores_as_miss() -> None:
    stack = FakeStack(selection_on=False)
    stack.fail_with = RuntimeError("boom")
    results = run_retrieval_mode(
        stack, [_q()], RunConfig(label="t", warmup=False), log=lambda _: None
    )
    assert results["en-001"].error == "boom"
    assert set(results["en-001"].metrics.values()) == {0.0}


# --- scoring --------------------------------------------------------------------


def test_score_search_result_dedupes_chunks_and_selected_recall() -> None:
    docs = [
        RetrievedDoc(document_id="a", semantic_identifier="X.pdf", score=0.9),
        RetrievedDoc(document_id="a", semantic_identifier="x.pdf", score=0.8),
        RetrievedDoc(document_id="b", semantic_identifier="gold.pdf", score=0.7),
    ]
    result = score_search_result(_q(gold=["GOLD.pdf"]), "product", docs, ["b"], 5.0)
    assert result.ranked_docs == ["x.pdf", "gold.pdf"]
    assert result.scores == [0.9, 0.7]
    assert result.gold_ranks == [2]
    assert result.metrics["mrr"] == 0.5
    assert result.metrics["selected_recall"] == 1.0
    assert result.llm_selected_docs == ["gold.pdf"]


def test_score_answer_uses_citationless_text_and_maps_citations() -> None:
    response = {
        "answer": "Fee is Rs 1,250 [2]",
        "answer_citationless": "Fee is Rs 1,250",
        "top_documents": [
            {"document_id": "d1", "semantic_identifier": "other.pdf"},
            {"document_id": "d2", "semantic_identifier": "land_go_2026_en.pdf"},
        ],
        "citation_info": [{"citation_number": 2, "document_id": "d2"}],
    }
    result = score_answer(_q(figures=[1250, 2]), 1, response, 100.0)
    # "[2]" in the raw answer must not count as the figure 2.
    assert result.figure_hits == [True, False]
    assert result.cited_docs == ["land_go_2026_en.pdf"]
    assert result.metrics["figure_accuracy"] == 0.5
    assert result.metrics["figures_all_correct"] == 0.0
    assert result.metrics["chat_recall@10"] == 1.0


# --- judge --------------------------------------------------------------------------


def test_parse_judge_output_with_fences_and_padding() -> None:
    content = '```json\n{"facts_covered": [true], "claims": [{"claim": "a", "supported": true}, {"claim": "b", "supported": false}]}\n```'
    verdict = parse_judge_output(content, n_facts=2)
    assert verdict.facts_covered == [True, False]
    assert verdict.completeness == 0.5
    assert verdict.faithfulness == 0.5
    assert verdict.unsupported_claims == ["b"]


def test_parse_judge_output_no_claims_is_faithful() -> None:
    verdict = parse_judge_output(
        '{"facts_covered": [true, true, true], "claims": []}', n_facts=2
    )
    assert verdict.facts_covered == [True, True]
    assert verdict.faithfulness == 1.0


def test_judge_answer_calls_litellm_in_json_mode() -> None:
    calls: list[dict[str, Any]] = []

    def fake_completion(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"facts_covered": [true], "claims": [{"claim": "fee 1250", "supported": true}]}'
                    }
                }
            ]
        }

    verdict = judge_answer(
        "q?",
        ["fact"],
        "source",
        "answer",
        model="gpt-4.1",
        api_key="k",
        completion=fake_completion,
    )
    assert verdict.completeness == 1.0 and verdict.faithfulness == 1.0
    assert calls[0]["temperature"] == 0
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["model"] == "gpt-4.1" and calls[0]["api_key"] == "k"


def test_judge_empty_answer_needs_no_llm() -> None:
    def explode(**_: Any) -> Any:
        raise AssertionError("must not be called")

    verdict = judge_answer("q", ["f1", "f2"], "s", "  ", model="m", completion=explode)
    assert verdict.completeness == 0.0 and verdict.faithfulness == 0.0


def test_judge_prompt_is_fixed() -> None:
    messages = build_judge_messages("Q", ["a", "b"], "SRC", "ANS")
    assert "1. a\n2. b" in messages[0]["content"]
    assert len(JUDGE_PROMPT_SHA256) == 64


def test_relevant_excerpt_keeps_rows_with_question_ids() -> None:
    text = "\n".join(
        ["header"] * 8 + [f"LND-WGL-{i:05d},Warangal,{i}" for i in range(3000)]
    )
    excerpt = relevant_excerpt(text, "fee for LND-WGL-01234?", budget=2000)
    assert "LND-WGL-01234,Warangal,1234" in excerpt
    assert len(excerpt) <= 2000


# --- runner end to end (fake stack + fake judge) -----------------------------------------


def test_run_rag_benchmark_all_modes_with_fake_judge() -> None:
    questions = [_q("en-001"), _q("te-001", gold=["missing.pdf"], lang="te")]
    stack = FakeStack(
        selection_on=True,
        ranking=["land_go_2026_en.pdf", "x.pdf"],
        answer="The fee is ₹1,250.",
    )

    def fake_completion(**_: Any) -> dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"facts_covered": [true], "claims": [{"claim": "c", "supported": true}]}'
                    }
                }
            ]
        }

    config = RunConfig(
        label="unit", mode="all", answer_repeats=2, warmup=False, judge_model="gpt-4.1"
    )
    run = run_rag_benchmark(
        stack,
        gen.DATASET_DIR,
        questions,
        config,
        judge_completion=fake_completion,
        log=lambda _: None,
    )
    by_id = {q.id: q for q in run.per_question}
    assert by_id["en-001"].retrieval["retrieval"].metrics["recall@5"] == 1.0
    assert by_id["te-001"].retrieval["retrieval"].metrics["recall@5"] == 0.0
    assert len(by_id["en-001"].answers) == 2
    assert by_id["en-001"].answers[0].figure_hits == [True]
    agg = {(a.mode, a.metric, a.group): a.value for a in run.aggregates}
    assert agg[("retrieval", "recall@5", "overall")] == 0.5
    assert agg[("retrieval", "recall@5", "lang:te")] == 0.0
    assert agg[("answer", "completeness", "overall")] == 1.0
    assert ("latency", "answer_p95_ms", "overall") in agg
    assert run.env.embedding_model == "fake-embed"
    assert run.env.judge_prompt_sha256 == JUDGE_PROMPT_SHA256
    assert run.env.answer_model == "gpt-4o-mini" and run.env.answer_repeats == 2
    assert stack.settings["enable_llm_section_selection"] is True
    assert RagBenchmarkRun.model_validate_json(run.model_dump_json()) == run


# --- CLI -------------------------------------------------------------------------


def test_cli_dry_run_then_compare_baseline_vs_itself(tmp_path: Path) -> None:
    out = tmp_path / "results"
    code = benchmark_cli.main(
        [
            "run",
            "--dry-run",
            "--label",
            "base",
            "--mode",
            "all",
            "--limit",
            "12",
            "--repeats",
            "1",
            "--results-dir",
            str(out),
        ]
    )
    assert code == 0
    json_files = sorted(out.glob("*_base.json"))
    assert len(json_files) == 1 and json_files[0].with_suffix(".md").exists()
    run = RagBenchmarkRun.model_validate_json(json_files[0].read_text(encoding="utf-8"))
    assert (
        run.run.dry_run and run.env.backend == "offline" and run.env.judge_model is None
    )
    assert len(run.per_question) == 12

    report = tmp_path / "self.md"
    assert (
        benchmark_cli.main(
            ["compare", str(json_files[0]), str(json_files[0]), "--out", str(report)]
        )
        == 0
    )
    assert "Retrieval gate: PASS" in report.read_text(encoding="utf-8")


def test_cli_compare_refuses_other_dataset(tmp_path: Path) -> None:
    out = tmp_path / "results"
    benchmark_cli.main(
        [
            "run",
            "--dry-run",
            "--label",
            "a",
            "--mode",
            "retrieval",
            "--limit",
            "3",
            "--results-dir",
            str(out),
        ]
    )
    path = next(out.glob("*_a.json"))
    data = json.loads(path.read_text(encoding="utf-8"))
    data["env"]["dataset_sha256"] = "0" * 64
    data["run"]["label"] = "b"
    other = out / "other.json"
    other.write_text(json.dumps(data), encoding="utf-8")
    assert (
        benchmark_cli.main(
            ["compare", str(path), str(other), "--out", str(tmp_path / "x.md")]
        )
        == 1
    )
    assert not (tmp_path / "x.md").exists()


def test_cli_setup_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    assert benchmark_cli.main(["setup", "--dry-run"]) == 0
    assert "No HTTP calls made" in capsys.readouterr().out


def test_dataset_questions_load_via_runner_loader() -> None:
    assert len(load_questions(gen.QUESTIONS_PATH)) == 150


def test_braintrust_upload_logs_one_row_per_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import braintrust

    logged: list[dict[str, Any]] = []

    class FakeExperiment:
        def log(self, **kwargs: Any) -> None:
            logged.append(kwargs)

        def flush(self) -> None:
            pass

    monkeypatch.setattr(braintrust, "init", lambda **_: FakeExperiment())
    stack = FakeStack(
        selection_on=False, ranking=["land_go_2026_en.pdf"], answer="Rs 1,250"
    )
    run = run_rag_benchmark(
        stack,
        gen.DATASET_DIR,
        [_q()],
        RunConfig(label="bt", mode="retrieval", warmup=False),
        log=lambda _: None,
    )
    benchmark_cli._upload_braintrust(run)
    assert len(logged) == 1
    assert logged[0]["scores"]["retrieval.recall@5"] == 1.0
