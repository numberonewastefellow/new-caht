import re

from om.configs.constants import MessageType
from om.llm.interfaces import LLM
from om.llm.models import AssistantMessage
from om.llm.models import ChatCompletionMessage
from om.llm.models import LanguageModelInput
from om.llm.models import ReasoningEffort
from om.llm.models import SystemMessage
from om.llm.models import UserMessage
from om.llm.utils import llm_response_to_string
from om.prompts.prompt_utils import get_current_llm_day_time
from om.prompts.query_expansion import KEYWORD_EXPANSION_PROMPT
from om.prompts.search_prompts import KEYWORD_REPHRASE_SYSTEM_PROMPT
from om.prompts.search_prompts import KEYWORD_REPHRASE_USER_PROMPT
from om.prompts.search_prompts import REPHRASE_CONTEXT_PROMPT
from om.prompts.search_prompts import SEMANTIC_QUERY_REPHRASE_SYSTEM_PROMPT
from om.prompts.search_prompts import SEMANTIC_QUERY_REPHRASE_USER_PROMPT
from om.tools.models import ChatMinimalTextMessage
from om.tracing.llm_utils import llm_generation_span
from om.tracing.llm_utils import record_llm_response
from om.utils.logger import setup_logger

logger = setup_logger()

# Pattern to remove common LLM artifacts: brackets, quotes, list markers, etc.
CLEANUP_PATTERN = re.compile(r'[\[\]"\'`]')


def _clean_keyword_line(line: str) -> str:
    """Clean a keyword line by removing common LLM artifacts.

    Removes brackets, quotes, and other characters that LLMs may accidentally
    include in their output.
    """
    # Remove common artifacts
    cleaned = CLEANUP_PATTERN.sub("", line)
    # Remove leading list markers like "1.", "2.", "-", "*"
    cleaned = re.sub(r"^\s*(?:\d+[\.\)]\s*|[-*]\s*)", "", cleaned)
    return cleaned.strip()


def expand_keywords(
    user_query: str,
    llm: LLM,
) -> list[str]:
    """Expand a user query into multiple keyword-only queries for BM25 search.

    Uses an LLM to generate keyword-based search queries that capture different
    aspects of the user's search intent. Returns only the expanded queries,
    not the original query.

    Args:
        user_query: The original search query from the user
        llm: Language model to use for keyword expansion

    Returns:
        List of expanded keyword queries (excluding the original query).
        Returns empty list if expansion fails or produces no useful expansions.
    """
    messages: LanguageModelInput = [
        UserMessage(content=KEYWORD_EXPANSION_PROMPT.format(user_query=user_query))
    ]

    try:
        response = llm.invoke(
            prompt=messages,
            reasoning_effort=ReasoningEffort.OFF,
            # Limit output - we only expect a few short keyword queries
            max_tokens=150,
        )

        content = llm_response_to_string(response).strip()

        if not content:
            logger.warning("Keyword expansion returned empty response.")
            return []

        # Parse response - each line is a separate keyword query
        # Clean each line to remove LLM artifacts and drop empty lines
        parsed_queries = []
        for line in content.strip().split("\n"):
            cleaned = _clean_keyword_line(line)
            if cleaned:
                parsed_queries.append(cleaned)

        if not parsed_queries:
            logger.warning("Keyword expansion parsing returned no queries.")
            return []

        # Filter out duplicates and queries that match the original
        expanded_queries: list[str] = []
        seen_lower: set[str] = {user_query.lower()}
        for query in parsed_queries:
            query_lower = query.lower()
            if query_lower not in seen_lower:
                seen_lower.add(query_lower)
                expanded_queries.append(query)

        logger.debug(f"Keyword expansion generated {len(expanded_queries)} queries")
        return expanded_queries

    except Exception as e:
        logger.warning(f"Keyword expansion failed: {e}")
        return []


def _build_additional_context(
    user_info: str | None = None,
    memories: list[str] | None = None,
) -> str:
    """Build additional context section for query rephrasing/expansion.

    Returns empty string if both user_info and memories are None/empty.
    Otherwise returns formatted context with "N/A" for missing fields.
    """
    has_user_info = user_info and user_info.strip()
    has_memories = memories and any(m.strip() for m in memories)

    if not has_user_info and not has_memories:
        return ""

    formatted_user_info = user_info if has_user_info else "N/A"
    formatted_memories = (
        "\n".join(f"- {memory}" for memory in memories)
        if has_memories and memories
        else "N/A"
    )

    return REPHRASE_CONTEXT_PROMPT.format(
        user_info=formatted_user_info,
        memories=formatted_memories,
    )


def _build_message_history(
    history: list[ChatMinimalTextMessage],
) -> list[ChatCompletionMessage]:
    """Convert ChatMinimalTextMessage list to ChatCompletionMessage list."""
    messages: list[ChatCompletionMessage] = []

    for msg in history:
        if msg.message_type == MessageType.USER:
            user_msg = UserMessage(content=msg.message)
            messages.append(user_msg)
        elif msg.message_type == MessageType.ASSISTANT:
            assistant_msg = AssistantMessage(content=msg.message)
            messages.append(assistant_msg)

    return messages


def semantic_query_rephrase(
    history: list[ChatMinimalTextMessage],
    llm: LLM,
    user_info: str | None = None,
    memories: list[str] | None = None,
) -> str:
    """Rephrase a query into a standalone query using chat history context.

    Converts the user's query into a self-contained search query that incorporates
    relevant context from the chat history and optional user information/memories.

    Args:
        history: Chat message history. Must contain at least one user message.
        llm: Language model to use for rephrasing
        user_info: Optional user information for personalization
        memories: Optional user memories for personalization

    Returns:
        Rephrased standalone query string

    Raises:
        ValueError: If history is empty or contains no user messages
        RuntimeError: If LLM fails to generate a rephrased query
    """
    if not history:
        raise ValueError("History cannot be empty for query rephrasing")

    # Find the last user message in the history
    last_user_message_idx = None
    for i in range(len(history) - 1, -1, -1):
        if history[i].message_type == MessageType.USER:
            last_user_message_idx = i
            break

    if last_user_message_idx is None:
        raise ValueError("History must contain at least one user message")

    # Extract the last user query
    user_query = history[last_user_message_idx].message

    # Build additional context section
    additional_context = _build_additional_context(user_info, memories)

    current_datetime_str = get_current_llm_day_time(
        include_day_of_week=True, full_sentence=False
    )

    # Build system message with current date
    system_msg = SystemMessage(
        content=SEMANTIC_QUERY_REPHRASE_SYSTEM_PROMPT.format(
            current_date=current_datetime_str
        )
    )

    # Convert chat history to message format (excluding the last user message and everything after it)
    messages: list[ChatCompletionMessage] = [system_msg]
    messages.extend(_build_message_history(history[:last_user_message_idx]))

    # Add the last message as the user prompt with instructions
    final_user_msg = UserMessage(
        content=SEMANTIC_QUERY_REPHRASE_USER_PROMPT.format(
            additional_context=additional_context, user_query=user_query
        )
    )
    messages.append(final_user_msg)

    # Call LLM and return result with Braintrust tracing
    with llm_generation_span(
        llm=llm, flow="semantic_query_rephrase", input_messages=messages
    ) as span_generation:
        response = llm.invoke(prompt=messages, reasoning_effort=ReasoningEffort.OFF)
        record_llm_response(span_generation, response)
        final_query = response.choice.message.content

    if not final_query:
        # It's ok if some other queries fail, this one is likely the best one
        # It also can't fail in parsing so we should be able to guarantee a valid query here.
        raise RuntimeError("LLM failed to generate a rephrased query")

    return final_query


def keyword_query_expansion(
    history: list[ChatMinimalTextMessage],
    llm: LLM,
    user_info: str | None = None,
    memories: list[str] | None = None,
) -> list[str] | None:
    """Expand a query into multiple keyword-only queries using chat history context.

    Converts the user's query into a set of keyword-based search queries (max 3)
    that incorporate relevant context from the chat history and optional user
    information/memories. Returns a list of keyword queries.

    Args:
        history: Chat message history. Must contain at least one user message.
        llm: Language model to use for keyword expansion
        user_info: Optional user information for personalization
        memories: Optional user memories for personalization

    Returns:
        List of keyword-only query strings (max 3), or empty list if generation fails

    Raises:
        ValueError: If history is empty or contains no user messages
    """
    if not history:
        raise ValueError("History cannot be empty for keyword query expansion")

    # Find the last user message in the history
    last_user_message_idx = None
    for i in range(len(history) - 1, -1, -1):
        if history[i].message_type == MessageType.USER:
            last_user_message_idx = i
            break

    if last_user_message_idx is None:
        raise ValueError("History must contain at least one user message")

    # Extract the last user query
    user_query = history[last_user_message_idx].message

    # Build additional context section
    additional_context = _build_additional_context(user_info, memories)

    current_datetime_str = get_current_llm_day_time(
        include_day_of_week=True, full_sentence=False
    )

    # Build system message with current date
    system_msg = SystemMessage(
        content=KEYWORD_REPHRASE_SYSTEM_PROMPT.format(current_date=current_datetime_str)
    )

    # Convert chat history to message format (excluding the last user message and everything after it)
    messages: list[ChatCompletionMessage] = [system_msg]
    messages.extend(_build_message_history(history[:last_user_message_idx]))

    # Add the last message as the user prompt with instructions
    final_user_msg = UserMessage(
        content=KEYWORD_REPHRASE_USER_PROMPT.format(
            additional_context=additional_context, user_query=user_query
        )
    )
    messages.append(final_user_msg)

    # Call LLM and return result with Braintrust tracing
    with llm_generation_span(
        llm=llm, flow="keyword_query_expansion", input_messages=messages
    ) as span_generation:
        response = llm.invoke(prompt=messages, reasoning_effort=ReasoningEffort.OFF)
        record_llm_response(span_generation, response)
        content = response.choice.message.content

    # Parse the response - each line is a separate keyword query
    if not content:
        return []

    queries = [line.strip() for line in content.strip().split("\n") if line.strip()]
    return queries
