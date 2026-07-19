"""Streaming packet schema for the search flow (SSE / newline-delimited JSON).

Packets form a discriminated union on ``type`` matching the frontend
``SearchStreamPacket`` contract (``web/src/lib/search/interfaces.ts``). Typical
wire order for one flow:

    query_expansions -> search_docs -> [doc_selection_reasoning, llm_selected_docs]
                                    \-> search_error (terminal, on failure)

Each packet is a plain Pydantic model; the transport serializes
``packet.model_dump()`` via ``om.server.utils.get_json_line`` (data-as-JSON-string
per the SSE contract). Keep packets small so the UI renders as they arrive.
"""

from typing import Literal

from pydantic import BaseModel

from om.search.results import SearchDocWithContent


class QueryExpansionsPacket(BaseModel):
    """The full set of queries actually executed (original + expansions)."""

    type: Literal["query_expansions"] = "query_expansions"
    executed_queries: list[str] = []


class SearchDocsPacket(BaseModel):
    type: Literal["search_docs"] = "search_docs"
    search_docs: list[SearchDocWithContent] = []


class DocSelectionReasoningPacket(BaseModel):
    type: Literal["doc_selection_reasoning"] = "doc_selection_reasoning"
    reasoning: str


class LLMSelectedDocsPacket(BaseModel):
    type: Literal["llm_selected_docs"] = "llm_selected_docs"
    llm_selected_doc_ids: list[str] | None = None


class SearchErrorPacket(BaseModel):
    type: Literal["search_error"] = "search_error"
    error: str


SearchStreamPacket = (
    QueryExpansionsPacket
    | SearchDocsPacket
    | DocSelectionReasoningPacket
    | LLMSelectedDocsPacket
    | SearchErrorPacket
)
