"""Dataset and result schemas for the RAG benchmark.

Kept free of server imports (no DB / tool registry) so the CLI starts fast on
the host and the unit tests run without a stack.
"""

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

Language = Literal["en", "te", "hi"]
QuestionCategory = Literal[
    "lookup", "aggregate", "multi_part", "recency", "cross_lingual"
]
QuestionDocType = Literal["pdf", "xlsx", "csv", "docx", "multi"]
RetrievalMode = Literal["retrieval", "product"]
RunMode = Literal["retrieval", "product", "answer", "all"]

RESULT_SCHEMA_VERSION = 1


# --- dataset ----------------------------------------------------------------


class ExpectedFigure(BaseModel):
    """A number (or ISO date when ``unit == "date"``) the answer must contain.

    ``unit`` "lakh" / "crore" means ``value`` is expressed in that unit.
    """

    value: float | str
    unit: str | None = None
    # Absolute tolerance. 0 = exact (rounded forms like "1.23 lakh" still match
    # within the precision they state, see figure_match).
    tolerance: float = 0.0
    # True when the figure is computed from the data (aggregates) and therefore
    # does not appear verbatim in the source text.
    computed: bool = False


class AggregateCheck(BaseModel):
    """How a computed figure was derived, so tests can recompute it from the file."""

    file_name: str
    sheet: str | None = None  # None for CSV
    op: Literal["count", "sum"]
    column: str | None = None  # summed column (op == "sum")
    where: dict[str, str] = Field(default_factory=dict)


class RagBenchmarkQuestion(BaseModel):
    id: str
    lang: Language
    question: str
    category: QuestionCategory
    doc_type: QuestionDocType
    # File names, matched case-insensitively against ``semantic_identifier``.
    gold_docs: list[str]
    expected_figures: list[ExpectedFigure] = Field(default_factory=list)
    expected_facts: list[str] = Field(default_factory=list)
    aggregate_check: AggregateCheck | None = None


class ManifestEntry(BaseModel):
    file_name: str
    sha256: str
    size_bytes: int
    lang: Language
    doc_type: Literal["pdf", "xlsx", "csv", "docx"]
    department: str
    doc_updated_at: str  # ISO-8601, UTC
    boost: int = 0
    is_distractor: bool = False
    supersedes: str | None = None  # distractor -> file it is the old version of


class DatasetManifest(BaseModel):
    dataset_version: str
    generator_seed: int
    files: list[ManifestEntry]


# --- per-question results -----------------------------------------------------


class RetrievedDoc(BaseModel):
    document_id: str
    semantic_identifier: str
    score: float | None = None
    chunk_ind: int | None = None


class RetrievalResult(BaseModel):
    mode: RetrievalMode
    ranked_docs: list[str]  # de-duplicated semantic identifiers, rank order
    scores: list[float | None] = Field(default_factory=list)
    gold_ranks: list[int | None] = Field(default_factory=list)  # 1-based
    llm_selected_docs: list[str] | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    latency_ms: float | None = None
    error: str | None = None


class JudgeVerdict(BaseModel):
    facts_covered: list[bool]
    unsupported_claims: list[str] = Field(default_factory=list)
    supported_claims: int = 0
    completeness: float
    faithfulness: float
    raw: dict[str, Any] | None = None


class AnswerResult(BaseModel):
    repeat: int
    answer: str
    retrieved_docs: list[str] = Field(default_factory=list)
    cited_docs: list[str] = Field(default_factory=list)
    figure_hits: list[bool] = Field(default_factory=list)
    judge: JudgeVerdict | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    latency_ms: float | None = None
    error: str | None = None


class QuestionResult(BaseModel):
    id: str
    lang: Language
    category: QuestionCategory
    doc_type: QuestionDocType
    gold_docs: list[str]
    retrieval: dict[str, RetrievalResult] = Field(default_factory=dict)
    answers: list[AnswerResult] = Field(default_factory=list)


# --- run-level --------------------------------------------------------------


class RunInfo(BaseModel):
    label: str
    mode: RunMode
    git_sha: str | None = None
    branch: str | None = None
    lanes: list[str] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None
    dry_run: bool = False
    schema_version: int = RESULT_SCHEMA_VERSION


class RunEnv(BaseModel):
    api_base: str | None = None
    dataset_version: str
    dataset_sha256: str
    embedding_model: str | None = None
    embedding_dim: int | None = None
    search_settings: dict[str, Any] | None = None  # indexing/embedding settings
    expansion_settings: dict[str, Any] | None = None
    answer_model: str | None = None
    answer_provider: str | None = None
    answer_repeats: int = 0
    judge_model: str | None = None
    judge_prompt_sha256: str | None = None
    force_search: bool = True
    document_sets: list[str] | None = None  # search scope filter, None = whole index
    backend: str = "http"  # http | offline


class DocIndexStats(BaseModel):
    semantic_identifier: str
    document_id: str
    doc_type: str
    num_chunks: int | None = None
    num_tokens: int | None = None


class IndexStats(BaseModel):
    docs: list[DocIndexStats] = Field(default_factory=list)
    total_chunks: int = 0
    chunks_by_doc_type: dict[str, dict[str, float]] = Field(default_factory=dict)
    store_size_bytes: int | None = None


class MetricAggregate(BaseModel):
    mode: str  # retrieval | product | answer | latency
    metric: str
    group: str  # "overall" | "lang:te" | "doc_type:pdf" | "category:lookup"
    value: float
    n: int


class RagBenchmarkRun(BaseModel):
    run: RunInfo
    env: RunEnv
    index: IndexStats | None = None
    per_question: list[QuestionResult] = Field(default_factory=list)
    aggregates: list[MetricAggregate] = Field(default_factory=list)
