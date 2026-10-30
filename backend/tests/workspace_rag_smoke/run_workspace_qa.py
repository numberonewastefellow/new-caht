"""Workspace RAG smoke test: ask fixed questions in a workspace chat and score the answers.

Each question runs in a fresh chat session scoped to one workspace, through the
same `/converse/send-chat-message` endpoint the web app uses (non-streaming).
Scoring is deterministic: every `expect_all` group must have one alternative
present in the answer; `expect_absent` questions must say the info is missing.

Auth (never written to disk by this script):
  OM_SESSION_COOKIE   value of the `fastapiusersauth` cookie (for web base :3000/api), or
  VIRTUALAI_API_KEY   bearer API key (for api base :8080)

Usage:
  python run_workspace_qa.py --workspace-id 4 --label before --out d:/tmp/batch1-live
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import requests

HERE = Path(__file__).resolve().parent

MISSING_INFO_PATTERNS = [
    r"\bnot (?:be )?(?:found|mentioned|provided|available|included|listed|present|contain)",
    r"\bno (?:information|mention|details|data|record)",
    r"\b(?:does|do|did)n'?t (?:contain|mention|include|provide|have|list)",
    r"\b(?:does|do|did) not (?:contain|mention|include|provide|have|list)",
    r"\bunable to find\b",
    r"\bcould(?: not|n'?t) find\b",
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def score_answer(answer: str, case: dict[str, Any]) -> tuple[bool, list[str]]:
    norm = _norm(answer)
    if case.get("expect_absent"):
        ok = any(re.search(p, norm) for p in MISSING_INFO_PATTERNS)
        return ok, [] if ok else ["no 'not in the documents' statement"]
    missing = [
        "/".join(group)
        for group in case["expect_all"]
        if not any(_norm(alt) in norm for alt in group)
    ]
    return not missing, missing


class ChatClient:
    def __init__(self, api_base: str, cookie: str | None, api_key: str | None) -> None:
        self.api_base = api_base.rstrip("/")
        self.session = requests.Session()
        if cookie:
            self.session.cookies.set("fastapiusersauth", cookie)
        elif api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        else:
            raise SystemExit("Set OM_SESSION_COOKIE or VIRTUALAI_API_KEY")

    def ask(
        self,
        question: str,
        workspace_id: int,
        model_provider: str,
        model_version: str,
        timeout_s: float,
    ) -> tuple[dict[str, Any], float]:
        body = {
            "message": question,
            "stream": False,
            "chat_session_info": {
                "agent_id": 0,
                "description": "workspace-rag-smoke",
                "workspace_id": workspace_id,
            },
            "llm_override": {
                "model_provider": model_provider,
                "model_version": model_version,
                "temperature": 0.0,
            },
            "origin": "webapp",
        }
        started = time.perf_counter()
        resp = self.session.post(
            f"{self.api_base}/converse/send-chat-message", json=body, timeout=timeout_s
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        resp.raise_for_status()
        return resp.json(), latency_ms


def _cited_files(data: dict[str, Any]) -> list[str]:
    by_id = {
        d.get("document_id"): d.get("semantic_identifier") or d.get("document_id")
        for d in data.get("top_documents") or []
    }
    cited = []
    for c in data.get("citation_info") or []:
        name = by_id.get(c.get("document_id"), c.get("document_id"))
        if name not in cited:
            cited.append(name)
    return cited


def _file_ok(case: dict[str, Any], cited: list[str]) -> bool | None:
    kind = case.get("file")
    if kind == "xlsx":
        return any(str(c).lower().endswith(".xlsx") for c in cited)
    if kind == "pdf":
        return any(str(c).lower().endswith(".pdf") for c in cited)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-id", type=int, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", default="d:/tmp/batch1-live")
    ap.add_argument("--questions", default=str(HERE / "questions_workspace4.json"))
    ap.add_argument("--api-base", default=os.environ.get("OM_API_BASE", "http://localhost:3000/api"))
    ap.add_argument("--model-provider", default="gpt")
    ap.add_argument("--model-version", default="gpt-4o-mini")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--timeout", type=float, default=240.0)
    args = ap.parse_args()

    client = ChatClient(
        args.api_base,
        os.environ.get("OM_SESSION_COOKIE"),
        os.environ.get("VIRTUALAI_API_KEY"),
    )
    cases = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    out_dir = Path(args.out) / args.label
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for case in cases:
        for rep in range(args.repeats):
            try:
                data, latency = client.ask(
                    case["question"],
                    args.workspace_id,
                    args.model_provider,
                    args.model_version,
                    args.timeout,
                )
                answer = data.get("answer_citationless") or data.get("answer") or ""
                error = data.get("error_msg")
            except Exception as exc:  # record and keep going
                data, latency, answer, error = {}, 0.0, "", str(exc)
            ok, missing = score_answer(answer, case) if answer else (False, ["no answer"])
            cited = _cited_files(data)
            row = {
                "id": case["id"],
                "kind": case["kind"],
                "rep": rep,
                "correct": ok,
                "missing": missing,
                "cited_files": cited,
                "cited_right_file": _file_ok(case, cited),
                "latency_ms": round(latency),
                "answer_chars": len(answer),
                "error": error,
                "answer": answer,
            }
            results.append(row)
            mark = "PASS" if ok else "FAIL"
            print(f"[{mark}] {case['id']} rep{rep} {round(latency)}ms cited={cited} missing={missing}", flush=True)

    n = len(results)
    correct = sum(r["correct"] for r in results)
    lat = [r["latency_ms"] for r in results if r["latency_ms"]]
    summary = {
        "label": args.label,
        "workspace_id": args.workspace_id,
        "model": f"{args.model_provider}/{args.model_version}",
        "runs": n,
        "correct": correct,
        "accuracy": round(correct / n, 3) if n else 0,
        "p50_latency_ms": round(statistics.median(lat)) if lat else None,
        "mean_answer_chars": round(statistics.mean(r["answer_chars"] for r in results)) if n else 0,
        "errors": sum(1 for r in results if r["error"]),
    }
    (out_dir / "results.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
