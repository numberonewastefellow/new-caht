"""Optional LLM relevance selection over fused search results.

Given the query and the fused documents, ask the LLM which are actually relevant.
This is a best-effort enhancement gated by config; any failure returns an empty
selection and never breaks the search flow.
"""

import json
import re
from collections.abc import Sequence

from om.context.search.models import SearchDoc
from om.llm.interfaces import LLM
from om.llm.models import ReasoningEffort
from om.llm.models import SystemMessage
from om.llm.models import UserMessage
from om.utils.logger import setup_logger

logger = setup_logger()

_MAX_BLURB_CHARS = 300
_OUTPUT_MAX_TOKENS = 256

_SELECTION_SYSTEM = (
    "You judge which candidate documents are relevant to a search query. Consider "
    "a document relevant if it would help answer or address the query. Be strict: "
    "exclude documents that are only loosely related."
)

_SELECTION_USER = (
    "Query:\n{query}\n\n"
    "Candidate documents (index: title: snippet):\n{documents}\n\n"
    "Return the indices of the relevant documents as a JSON array of integers, "
    'e.g. [0, 2, 3]. Return an empty array [] if none are relevant. Return only '
    "the JSON array."
)


def select_relevant_documents(
    query: str,
    documents: Sequence[SearchDoc],
    llm: LLM,
    max_to_judge: int = 25,
) -> list[str]:
    """Return the document ids the LLM judged relevant. Empty on any failure."""
    if not documents:
        return []
    judged = documents[:max_to_judge]
    lines: list[str] = []
    for index, doc in enumerate(judged):
        snippet = (doc.blurb or "").strip().replace("\n", " ")[:_MAX_BLURB_CHARS]
        lines.append(f"[{index}] {doc.semantic_identifier}: {snippet}")

    try:
        response = llm.invoke(
            [
                SystemMessage(content=_SELECTION_SYSTEM),
                UserMessage(
                    content=_SELECTION_USER.format(
                        query=query, documents="\n".join(lines)
                    )
                ),
            ],
            max_tokens=_OUTPUT_MAX_TOKENS,
            reasoning_effort=ReasoningEffort.LOW,
        )
        content = response.choice.message.content or ""
        indices = _parse_int_list(content)
        return [
            judged[i].document_id for i in indices if 0 <= i < len(judged)
        ]
    except Exception as exc:
        logger.warning("LLM section selection failed: %s", exc)
        return []


def _parse_int_list(text: str) -> list[int]:
    """Extract a JSON array of ints, tolerating surrounding prose / fences."""
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                out: list[int] = []
                seen: set[int] = set()
                for element in parsed:
                    if isinstance(element, bool):
                        continue
                    if isinstance(element, int) and element not in seen:
                        seen.add(element)
                        out.append(element)
                return out
        except Exception:
            pass
    # Fallback: pull bare integers out of the text, order-preserving + unique.
    out2: list[int] = []
    seen2: set[int] = set()
    for match in re.findall(r"\d+", text):
        value = int(match)
        if value not in seen2:
            seen2.add(value)
            out2.append(value)
    return out2
