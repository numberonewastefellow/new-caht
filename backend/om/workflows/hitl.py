"""Human-in-the-loop helpers: detect clarification requests and resume them.

Shared by the sequential and llm_decision orchestration modes.
"""

from __future__ import annotations

# Deterministic signal: if the agent output starts with this prefix,
# the engine treats it as an explicit pause request. The prefix is
# stripped before showing the questions to the user.
NEEDS_INPUT_PREFIX = "[NEEDS_INPUT]"

_INPUT_SIGNAL_PATTERNS = [
    "what", "which", "how many", "when", "where",
    "could you", "can you", "please provide", "please specify",
    "i need", "i'll need", "more information", "more details",
]

# Maximum clarification rounds before truncating older entries
MAX_CLARIFICATION_ROUNDS = 5


def agent_requests_input(output: str) -> bool:
    """Detect whether the agent is asking the user for information.

    Three detection modes (checked for steps with can_request_input=True):
    1. Deterministic positive: output starts with "[NEEDS_INPUT]" prefix.
    2. Deterministic negative: output contains "STATUS: COMPLETE" — agent
       explicitly signals it has enough info, so never pause.
    3. Heuristic fallback: at least one line contains BOTH a "?" AND a
       signal pattern. Per-line scoping avoids false positives where a
       signal word (e.g. "what") appears in a template field on one line
       and "?" appears in echoed code on a completely different line.

    Only checked for steps with can_request_input=True.
    """
    stripped = output.strip()

    # Mode 1: explicit structured signal — agent is asking for input
    if stripped.upper().startswith(NEEDS_INPUT_PREFIX):
        return True

    # Mode 2: negative signal — agent says it's done, don't pause
    if "STATUS: COMPLETE" in stripped.upper():
        return False

    # Mode 3: heuristic — require "?" and signal pattern on the SAME line
    for line in stripped.split("\n"):
        lower_line = line.lower()
        if "?" not in lower_line:
            continue
        if any(p in lower_line for p in _INPUT_SIGNAL_PATTERNS):
            return True
    return False


def strip_needs_input_prefix(output: str) -> str:
    """Strip the [NEEDS_INPUT] prefix if present, returning clean question text."""
    stripped = output.strip()
    if stripped.upper().startswith(NEEDS_INPUT_PREFIX):
        return stripped[len(NEEDS_INPUT_PREFIX):].strip()
    return stripped


def build_clarification_task(
    original_task: str,
    clarification_conversation: list[dict[str, str]],
) -> str:
    """Build a structured prompt for an agent resuming from clarification.

    Enterprise pattern (LangGraph/CrewAI): the agent is re-run with accumulated
    context rather than relying on the orchestrator LLM to re-delegate.

    The agent sees: TASK + CLARIFICATION HISTORY + INSTRUCTIONS.
    """
    parts = [f"TASK:\n{original_task}"]

    if clarification_conversation:
        # Truncate to last N rounds if conversation is very long
        conv = clarification_conversation
        if len(conv) > MAX_CLARIFICATION_ROUNDS * 2:
            conv = conv[-(MAX_CLARIFICATION_ROUNDS * 2):]

        conv_lines = []
        for entry in conv:
            if entry.get("role") == "agent":
                conv_lines.append(f"You previously asked:\n{entry['content']}")
            elif entry.get("role") == "user":
                conv_lines.append(f"The user responded:\n{entry['content']}")
        parts.append("CLARIFICATION HISTORY:\n" + "\n\n".join(conv_lines))

    parts.append(
        "INSTRUCTIONS: You now have the user's responses above. "
        "If you have all the information you need, produce your complete "
        "final output. If you still need more details, ask your follow-up "
        "questions."
    )
    return "\n\n".join(parts)
