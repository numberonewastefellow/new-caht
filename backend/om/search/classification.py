"""Lightweight LLM classification: is a query a document-search or a chat turn.

Used by ``POST /search/search-flow-classification`` so the UI can route a query
to the search experience vs. a conversational answer. Fails open to "search"
(the safer default for a search-first surface).
"""

from om.llm.factory import get_default_llm
from om.llm.interfaces import LLM
from om.llm.models import ReasoningEffort
from om.llm.models import SystemMessage
from om.llm.models import UserMessage
from om.search.log_events import ACTION_EXECUTE
from om.search.log_events import emit_search_event
from om.search.log_events import STATUS_SUCCESS
from om.utils.logger import setup_logger

logger = setup_logger()

_CLASSIFY_SYSTEM = (
    "You classify a user's message as either a document SEARCH (the user wants to "
    "find documents or look up information) or a CHAT turn (a conversational "
    "question, instruction, or chit-chat). Answer with exactly one word: SEARCH "
    "or CHAT."
)

_CLASSIFY_USER = "Message:\n{query}\n\nClassification (SEARCH or CHAT):"


def classify_search_flow(user_query: str, llm: LLM | None = None) -> bool:
    """Return True if the query should go to the search flow."""
    if not user_query.strip():
        return True
    try:
        llm = llm or get_default_llm(temperature=0.0)
        response = llm.invoke(
            [
                SystemMessage(content=_CLASSIFY_SYSTEM),
                UserMessage(content=_CLASSIFY_USER.format(query=user_query)),
            ],
            max_tokens=8,
            reasoning_effort=ReasoningEffort.LOW,
        )
        content = (response.choice.message.content or "").strip().lower()
        # Default to search unless the model clearly says "chat".
        is_search_flow = "chat" not in content or "search" in content
        emit_search_event(
            event="search.flow_classified",
            action=ACTION_EXECUTE,
            status=STATUS_SUCCESS,
            is_search_flow=is_search_flow,
        )
        return is_search_flow
    except Exception as exc:
        logger.warning("search-flow classification failed, defaulting to search: %s", exc)
        return True
