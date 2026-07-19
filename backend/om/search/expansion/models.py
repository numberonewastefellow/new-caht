"""Domain models for LLM-backed query expansion.

Three complementary transforms (see README for the research basis):
  * KEYWORD           - keyword-only reformulations (synonyms / related terms) to
                        widen BM25 vocabulary coverage. History-independent.
  * SEMANTIC_REPHRASE - history-aware rewrite of the latest query into a single
                        standalone, context-resolved question.
  * KEYWORD_HISTORY   - history-aware keyword reformulations that fold in relevant
                        conversation context.

Every LLM call is traced (tokens, latency, raw output, parsed variants, errors)
for explainability and cost accounting.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class ExpansionStrategy(str, Enum):
    KEYWORD = "keyword"
    SEMANTIC_REPHRASE = "semantic_rephrase"
    KEYWORD_HISTORY = "keyword_history"


class HistoryTurn(BaseModel):
    """One prior conversation turn used for history-aware expansion."""

    role: Literal["user", "assistant"]
    content: str


class ExpandedQuery(BaseModel):
    """A single expanded/rephrased query variant to run against the index."""

    text: str
    strategy: ExpansionStrategy
    # True  -> retrieve this variant with a keyword (BM25) leaning.
    # False -> retrieve with a semantic leaning.
    is_keyword: bool


class StrategyTrace(BaseModel):
    """Per-strategy LLM tracing for explainability + cost accounting."""

    strategy: ExpansionStrategy
    status: Literal["success", "error", "skipped"]
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    duration_ms: float | None = None
    raw_output: str | None = None
    variants: list[str] = Field(default_factory=list)
    error: str | None = None
    # True when the conversation history was truncated to fit the token budget.
    truncated_history: bool = False


class ExpansionTrace(BaseModel):
    """Aggregate trace across every expansion strategy that ran."""

    llm_model: str | None = None
    total_duration_ms: float | None = None
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    strategy_traces: list[StrategyTrace] = Field(default_factory=list)

    def add(self, trace: StrategyTrace) -> None:
        self.strategy_traces.append(trace)
        if trace.prompt_tokens:
            self.total_prompt_tokens += trace.prompt_tokens
        if trace.completion_tokens:
            self.total_completion_tokens += trace.completion_tokens


class QueryExpansionResult(BaseModel):
    """Outcome of expanding a single query."""

    original_query: str
    # Standalone, context-resolved rewrite (semantic). None if disabled/failed or
    # no history was supplied.
    rephrased_query: str | None = None
    # Keyword-only variants (union of KEYWORD and KEYWORD_HISTORY strategies),
    # de-duplicated and order-preserving.
    keyword_variants: list[str] = Field(default_factory=list)
    trace: ExpansionTrace = Field(default_factory=ExpansionTrace)

    @property
    def effective_query(self) -> str:
        """Best single query for display / history: the standalone rephrase when
        available, otherwise the original."""
        return self.rephrased_query or self.original_query

    @property
    def expansion_texts(self) -> list[str]:
        """Flat list of the produced expansion strings (no original)."""
        texts = list(self.keyword_variants)
        if self.rephrased_query and self.rephrased_query != self.original_query:
            texts.insert(0, self.rephrased_query)
        return texts

    def retrieval_variants(self) -> list[ExpandedQuery]:
        """Ordered, de-duplicated expansion variants to run in addition to the
        original query. The original itself is run by the orchestrator."""
        seen: set[str] = {self.original_query.strip().lower()}
        variants: list[ExpandedQuery] = []

        if self.rephrased_query:
            key = self.rephrased_query.strip().lower()
            if key and key not in seen:
                seen.add(key)
                variants.append(
                    ExpandedQuery(
                        text=self.rephrased_query,
                        strategy=ExpansionStrategy.SEMANTIC_REPHRASE,
                        is_keyword=False,
                    )
                )

        for kw in self.keyword_variants:
            key = kw.strip().lower()
            if key and key not in seen:
                seen.add(key)
                variants.append(
                    ExpandedQuery(
                        text=kw,
                        strategy=ExpansionStrategy.KEYWORD,
                        is_keyword=True,
                    )
                )
        return variants
