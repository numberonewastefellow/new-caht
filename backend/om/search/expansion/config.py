"""Typed, ORM-decoupled views over the per-tenant search-expansion settings.

The expander (Phase 1) depends only on ``QueryExpansionConfig``; the orchestrator
(Phase 2) additionally consumes ``FusionConfig``. Both are projected from the
``SearchExpansionSettings`` row (with hard-coded defaults when the table is
unavailable), so nothing downstream touches SQLAlchemy directly.
"""

from pydantic import BaseModel
from sqlalchemy.orm import Session

from om.db.models import SearchExpansionSettings
from om.db.search_expansion_settings import get_expansion_settings


class QueryExpansionConfig(BaseModel):
    enable_expansion: bool = True
    enable_keyword_expansion: bool = True
    enable_semantic_rephrase: bool = True
    enable_keyword_history_expansion: bool = True
    max_variants: int = 3

    @classmethod
    def from_db(cls, settings: SearchExpansionSettings) -> "QueryExpansionConfig":
        return cls(
            enable_expansion=settings.enable_expansion,
            enable_keyword_expansion=settings.enable_keyword_expansion,
            enable_semantic_rephrase=settings.enable_semantic_rephrase,
            enable_keyword_history_expansion=settings.enable_keyword_history_expansion,
            max_variants=max(1, settings.max_variants),
        )


class FusionConfig(BaseModel):
    rrf_k: int = 60
    original_query_weight: float = 2.0
    semantic_variant_weight: float = 1.0
    keyword_variant_weight: float = 1.0
    num_results: int = 25
    num_retrieved_per_query: int = 30
    enable_llm_section_selection: bool = False
    # Max docs fed to the LLM relevance pass (request-overridable; not persisted).
    llm_selection_num_docs: int = 25

    @classmethod
    def from_db(cls, settings: SearchExpansionSettings) -> "FusionConfig":
        return cls(
            rrf_k=max(1, settings.rrf_k),
            original_query_weight=settings.original_query_weight,
            semantic_variant_weight=settings.semantic_variant_weight,
            keyword_variant_weight=settings.keyword_variant_weight,
            num_results=max(1, settings.num_results),
            num_retrieved_per_query=max(1, settings.num_retrieved_per_query),
            enable_llm_section_selection=settings.enable_llm_section_selection,
            llm_selection_num_docs=max(1, settings.num_results),
        )


class SearchFlowConfig(BaseModel):
    """Fully-resolved config for one search flow."""

    expansion: QueryExpansionConfig
    fusion: FusionConfig

    @classmethod
    def from_db(cls, settings: SearchExpansionSettings) -> "SearchFlowConfig":
        return cls(
            expansion=QueryExpansionConfig.from_db(settings),
            fusion=FusionConfig.from_db(settings),
        )

    @classmethod
    def load(cls, db_session: Session) -> "SearchFlowConfig":
        """Load the tenant's config, falling back to defaults on any error."""
        try:
            return cls.from_db(get_expansion_settings(db_session))
        except Exception:
            return cls(expansion=QueryExpansionConfig(), fusion=FusionConfig())
