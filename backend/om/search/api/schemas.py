"""Request/response schemas for the search API.

Authored clean-room from the frontend wire contract
(``web/src/lib/search/interfaces.ts``) so the existing UI keeps working. Field
names/types match that contract exactly.
"""

import datetime

from pydantic import BaseModel

from om.context.search.models import BaseFilters
from om.db.models import SearchExpansionSettings
from om.db.models import SearchQuery
from om.search.expansion.models import HistoryTurn
from om.search.results import SearchDocWithContent


# --- classification ---------------------------------------------------------


class SearchFlowClassificationRequest(BaseModel):
    user_query: str


class SearchFlowClassificationResponse(BaseModel):
    is_search_flow: bool


# --- search -----------------------------------------------------------------


class SendSearchQueryRequest(BaseModel):
    search_query: str
    filters: BaseFilters | None = None
    num_docs_fed_to_llm_selection: int | None = None
    run_query_expansion: bool = True
    num_hits: int = 50
    include_content: bool = False
    stream: bool = False
    # Optional prior conversation turns; when provided, history-aware expansion
    # (standalone rephrase + context-aware keyword variants) is applied.
    history: list[HistoryTurn] | None = None


class SearchFullResponse(BaseModel):
    all_executed_queries: list[str] = []
    search_docs: list[SearchDocWithContent] = []
    doc_selection_reasoning: str | None = None
    llm_selected_doc_ids: list[str] | None = None
    error: str | None = None


# --- history ----------------------------------------------------------------


class SearchQueryResponse(BaseModel):
    query: str
    query_expansions: list[str] | None = None
    created_at: datetime.datetime

    @classmethod
    def from_row(cls, row: SearchQuery) -> "SearchQueryResponse":
        return cls(
            query=row.query,
            query_expansions=row.query_expansions,
            created_at=row.created_at,
        )


class SearchHistoryResponse(BaseModel):
    search_queries: list[SearchQueryResponse] = []


# --- expansion settings (config UI) -----------------------------------------


class ExpansionSettingsResponse(BaseModel):
    enable_expansion: bool
    enable_keyword_expansion: bool
    enable_semantic_rephrase: bool
    enable_keyword_history_expansion: bool
    max_variants: int
    num_results: int
    num_retrieved_per_query: int
    rrf_k: int
    original_query_weight: float
    semantic_variant_weight: float
    keyword_variant_weight: float
    enable_llm_section_selection: bool

    @classmethod
    def from_row(
        cls, row: SearchExpansionSettings
    ) -> "ExpansionSettingsResponse":
        return cls(
            enable_expansion=row.enable_expansion,
            enable_keyword_expansion=row.enable_keyword_expansion,
            enable_semantic_rephrase=row.enable_semantic_rephrase,
            enable_keyword_history_expansion=row.enable_keyword_history_expansion,
            max_variants=row.max_variants,
            num_results=row.num_results,
            num_retrieved_per_query=row.num_retrieved_per_query,
            rrf_k=row.rrf_k,
            original_query_weight=row.original_query_weight,
            semantic_variant_weight=row.semantic_variant_weight,
            keyword_variant_weight=row.keyword_variant_weight,
            enable_llm_section_selection=row.enable_llm_section_selection,
        )


class ExpansionSettingsUpdateRequest(BaseModel):
    """Partial update; only provided (non-None) fields are applied."""

    enable_expansion: bool | None = None
    enable_keyword_expansion: bool | None = None
    enable_semantic_rephrase: bool | None = None
    enable_keyword_history_expansion: bool | None = None
    max_variants: int | None = None
    num_results: int | None = None
    num_retrieved_per_query: int | None = None
    rrf_k: int | None = None
    original_query_weight: float | None = None
    semantic_variant_weight: float | None = None
    keyword_variant_weight: float | None = None
    enable_llm_section_selection: bool | None = None
