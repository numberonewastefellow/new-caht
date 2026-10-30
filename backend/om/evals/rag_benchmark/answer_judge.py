"""LLM-as-judge for answer completeness and faithfulness.

One JSON-mode call per answer, temperature 0, fixed prompt (its sha256 is
recorded in every run). Called directly through litellm so the judge does
not depend on the stack under test.
"""

import hashlib
import json
import re
from collections.abc import Callable
from typing import Any

from om.evals.rag_benchmark.models import JudgeVerdict

JUDGE_PROMPT = """You are grading an answer produced by a document question-answering system.
The question, the answer and the source text may be in English, Telugu or Hindi.

QUESTION:
{question}

EXPECTED FACTS (numbered):
{facts}

SOURCE TEXT (the only ground truth; excerpts of the gold documents):
<<<
{source}
>>>

ANSWER TO GRADE:
<<<
{answer}
>>>

Tasks:
1. For each expected fact, decide whether the answer states it (same meaning and the
   same figures; number formats such as 1,23,456 / 1.23 lakh / Telugu or Devanagari
   digits count as the same figure).
2. Split the answer into its factual claims (ignore greetings, hedges and citations).
   For each claim decide whether the SOURCE TEXT supports it.

Reply with JSON only, exactly in this shape:
{{"facts_covered": [true, false, ...one boolean per expected fact, in order],
  "claims": [{{"claim": "...", "supported": true}}, ...]}}"""

JUDGE_PROMPT_SHA256 = hashlib.sha256(JUDGE_PROMPT.encode("utf-8")).hexdigest()
SOURCE_CHAR_BUDGET = 16000

CompletionFn = Callable[..., Any]


def _default_completion(**kwargs: Any) -> Any:
    import litellm

    return litellm.completion(**kwargs)


def build_judge_messages(
    question: str, expected_facts: list[str], source_text: str, answer: str
) -> list[dict[str, str]]:
    facts = "\n".join(
        f"{idx}. {fact}" for idx, fact in enumerate(expected_facts, start=1)
    )
    prompt = JUDGE_PROMPT.format(
        question=question,
        facts=facts or "(none)",
        source=source_text[:SOURCE_CHAR_BUDGET],
        answer=answer,
    )
    return [{"role": "user", "content": prompt}]


def _content_of(response: Any) -> str:
    if isinstance(response, dict):
        return response["choices"][0]["message"]["content"]
    return response.choices[0].message.content


def parse_judge_output(content: str, n_facts: int) -> JudgeVerdict:
    text = content.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    data = json.loads(text)
    covered = [bool(v) for v in (data.get("facts_covered") or [])][:n_facts]
    covered += [False] * (n_facts - len(covered))
    claims = [c for c in (data.get("claims") or []) if isinstance(c, dict)]
    supported = [c for c in claims if c.get("supported") is True]
    unsupported = [
        str(c.get("claim", "")) for c in claims if c.get("supported") is not True
    ]
    return JudgeVerdict(
        facts_covered=covered,
        unsupported_claims=unsupported,
        supported_claims=len(supported),
        completeness=(sum(covered) / n_facts) if n_facts else 1.0,
        faithfulness=(len(supported) / len(claims)) if claims else 1.0,
        raw=data,
    )


def judge_answer(
    question: str,
    expected_facts: list[str],
    source_text: str,
    answer: str,
    model: str,
    api_key: str | None = None,
    completion: CompletionFn | None = None,
) -> JudgeVerdict:
    if not answer.strip():
        return JudgeVerdict(
            facts_covered=[False] * len(expected_facts),
            completeness=0.0 if expected_facts else 1.0,
            faithfulness=0.0,  # an empty answer earns nothing
        )
    call = completion or _default_completion
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": build_judge_messages(question, expected_facts, source_text, answer),
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    if api_key:
        kwargs["api_key"] = api_key
    response = call(**kwargs)
    return parse_judge_output(_content_of(response), len(expected_facts))


_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]{2,}")


def relevant_excerpt(text: str, question: str, budget: int = SOURCE_CHAR_BUDGET) -> str:
    """Whole text if it fits; otherwise the first lines (headers) plus the lines
    sharing an identifier-like token with the question (e.g. ``LND-WGL-00042``)."""
    if len(text) <= budget:
        return text
    lines = text.splitlines()
    tokens = {
        t.lower()
        for t in _TOKEN_RE.findall(question)
        if any(ch.isdigit() for ch in t) or "-" in t
    }
    tokens |= {t.lower() for t in _TOKEN_RE.findall(question) if len(t) > 5}
    head = lines[:8]
    hits = [
        line
        for line in lines[8:]
        if tokens and any(tok in line.lower() for tok in tokens)
    ]
    excerpt = "\n".join(head + ["..."] + hits)
    return excerpt[:budget]
