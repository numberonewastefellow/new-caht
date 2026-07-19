"""Clean-room prompt templates for query expansion.

These strings are authored for WS-E from the behavior spec + the query-expansion
research cited in the README. They intentionally request a strict, minimal output
shape (a JSON array of strings, or a single line) so parsing is robust and cheap.
"""

# --- keyword expansion (history-independent) --------------------------------

KEYWORD_EXPANSION_SYSTEM = (
    "You rewrite a search query into alternative keyword-style queries for a "
    "keyword (BM25) search engine. Each alternative should use synonyms, related "
    "terminology, acronyms/expansions, or a differently-phrased set of keywords "
    "that a relevant document might contain. Preserve the user's intent. Do NOT "
    "answer the query. Do NOT add explanations."
)

KEYWORD_EXPANSION_USER = (
    "Search query:\n{query}\n\n"
    "Return up to {max_variants} alternative keyword queries as a JSON array of "
    'strings, e.g. ["...", "..."]. Return only the JSON array.'
)


# --- history-aware semantic rephrase (single standalone question) -----------

SEMANTIC_REPHRASE_SYSTEM = (
    "You rewrite the user's latest message into a single standalone search "
    "question. Resolve pronouns and references using the conversation history so "
    "the question is fully self-contained and understandable without the history. "
    "Keep it concise and faithful to the user's intent. Do NOT answer it. Return "
    "only the rewritten question as plain text, with no preamble or quotes."
)

SEMANTIC_REPHRASE_USER = (
    "Conversation history (oldest first):\n{history}\n\n"
    "Latest user message:\n{query}\n\n"
    "Standalone search question:"
)


# --- history-aware keyword expansion ----------------------------------------

KEYWORD_HISTORY_SYSTEM = (
    "You rewrite the user's latest message into alternative keyword-style queries "
    "for a keyword (BM25) search engine, using the conversation history to resolve "
    "references and fold in relevant context. Each alternative should use "
    "synonyms, related terminology, or a differently-phrased set of keywords. Do "
    "NOT answer the query. Do NOT add explanations."
)

KEYWORD_HISTORY_USER = (
    "Conversation history (oldest first):\n{history}\n\n"
    "Latest user message:\n{query}\n\n"
    "Return up to {max_variants} context-aware keyword queries as a JSON array of "
    'strings, e.g. ["...", "..."]. Return only the JSON array.'
)


def format_history(turns: list[tuple[str, str]]) -> str:
    """Render (role, content) turns into a compact transcript block."""
    lines: list[str] = []
    for role, content in turns:
        speaker = "User" if role == "user" else "Assistant"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines) if lines else "(no prior messages)"
