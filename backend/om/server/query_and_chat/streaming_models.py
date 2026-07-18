from collections.abc import Sequence
from enum import Enum
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from om.context.search.models import InferenceSection
from om.context.search.models import SearchDoc
from om.server.query_and_chat.placement import Placement


class StreamingType(Enum):
    """Enum defining all streaming packet types. This is the single source of truth for type strings."""

    SECTION_END = "section_end"
    STOP = "stop"
    TOP_LEVEL_BRANCHING = "top_level_branching"
    ERROR = "error"

    MESSAGE_START = "message_start"
    MESSAGE_DELTA = "message_delta"
    SEARCH_TOOL_START = "search_tool_start"
    SEARCH_TOOL_QUERIES_DELTA = "search_tool_queries_delta"
    SEARCH_TOOL_DOCUMENTS_DELTA = "search_tool_documents_delta"
    OPEN_URL_START = "open_url_start"
    OPEN_URL_URLS = "open_url_urls"
    OPEN_URL_DOCUMENTS = "open_url_documents"
    IMAGE_GENERATION_START = "image_generation_start"
    IMAGE_GENERATION_HEARTBEAT = "image_generation_heartbeat"
    IMAGE_GENERATION_FINAL = "image_generation_final"
    PYTHON_TOOL_START = "python_tool_start"
    PYTHON_TOOL_DELTA = "python_tool_delta"
    CUSTOM_TOOL_START = "custom_tool_start"
    CUSTOM_TOOL_DELTA = "custom_tool_delta"
    FILE_READER_START = "file_reader_start"
    FILE_READER_RESULT = "file_reader_result"
    REASONING_START = "reasoning_start"
    REASONING_DELTA = "reasoning_delta"
    REASONING_DONE = "reasoning_done"
    CITATION_INFO = "citation_info"
    TOOL_CALL_DEBUG = "tool_call_debug"

    MEMORY_TOOL_START = "memory_tool_start"
    MEMORY_TOOL_DELTA = "memory_tool_delta"
    MEMORY_TOOL_NO_ACCESS = "memory_tool_no_access"

    DEEP_RESEARCH_PLAN_START = "deep_research_plan_start"
    DEEP_RESEARCH_PLAN_DELTA = "deep_research_plan_delta"
    RESEARCH_AGENT_START = "research_agent_start"
    INTERMEDIATE_REPORT_START = "intermediate_report_start"
    INTERMEDIATE_REPORT_DELTA = "intermediate_report_delta"
    INTERMEDIATE_REPORT_CITED_DOCS = "intermediate_report_cited_docs"

    # Workflow Packets
    WORKFLOW_STEP_START = "workflow_step_start"
    WORKFLOW_STEP_DELTA = "workflow_step_delta"
    WORKFLOW_STEP_REASONING_DELTA = "workflow_step_reasoning_delta"
    WORKFLOW_STEP_END = "workflow_step_end"
    WORKFLOW_ORCHESTRATOR_THINKING = "workflow_orchestrator_thinking"
    WORKFLOW_PAUSE_FOR_INPUT = "workflow_pause_for_input"


class BaseObj(BaseModel):
    type: str = ""


################################################
# Control Packets
################################################
# This one isn't strictly necessary, remove in the future
class SectionEnd(BaseObj):
    type: Literal["section_end"] = StreamingType.SECTION_END.value


class OverallStop(BaseObj):
    type: Literal["stop"] = StreamingType.STOP.value
    stop_reason: str | None = None


class TopLevelBranching(BaseObj):
    # This class is used to give advanced heads up to the frontend that the top level flow is branching
    # This is used to avoid having the frontend render the first call then rerendering the other parallel branches
    type: Literal["top_level_branching"] = StreamingType.TOP_LEVEL_BRANCHING.value

    num_parallel_branches: int


class PacketException(BaseObj):
    type: Literal["error"] = StreamingType.ERROR.value

    exception: Exception = Field(exclude=True)
    model_config = {"arbitrary_types_allowed": True}


################################################
# Reasoning Packets
################################################
# Tells the frontend to display the reasoning block
class ReasoningStart(BaseObj):
    type: Literal["reasoning_start"] = StreamingType.REASONING_START.value


# The stream of tokens for the reasoning
class ReasoningDelta(BaseObj):
    type: Literal["reasoning_delta"] = StreamingType.REASONING_DELTA.value

    reasoning: str


class ReasoningDone(BaseObj):
    type: Literal["reasoning_done"] = StreamingType.REASONING_DONE.value


################################################
# Final Agent Response Packets
################################################
# Start of the final answer
class AgentResponseStart(BaseObj):
    type: Literal["message_start"] = StreamingType.MESSAGE_START.value

    final_documents: list[SearchDoc] | None = None
    pre_answer_processing_seconds: float | None = None


# The stream of tokens for the final response
# There is no end packet for this as the stream is over and a final OverallStop packet is emitted
class AgentResponseDelta(BaseObj):
    type: Literal["message_delta"] = StreamingType.MESSAGE_DELTA.value

    content: str
    file_ids: list[str] | None = None
    file_names: list[str] | None = None


# Citation info for the sidebar and inline citations
class CitationInfo(BaseObj):
    type: Literal["citation_info"] = StreamingType.CITATION_INFO.value

    # The numerical number of the citation as provided by the LLM
    citation_number: int
    # The document id of the SearchDoc (same as the field stored in the DB)
    # This is the actual document id from the connector, not the int id
    document_id: str


class ToolCallDebug(BaseObj):
    type: Literal["tool_call_debug"] = StreamingType.TOOL_CALL_DEBUG.value

    tool_call_id: str
    tool_name: str
    tool_args: dict[str, Any]


################################################
# Tool Packets
################################################
# Search tool is called and the UI block needs to start
class SearchToolStart(BaseObj):
    type: Literal["search_tool_start"] = StreamingType.SEARCH_TOOL_START.value

    is_internet_search: bool = False


# Queries coming through as the LLM determines what to search
# Mostly for query expansions and advanced search strategies
class SearchToolQueriesDelta(BaseObj):
    type: Literal["search_tool_queries_delta"] = (
        StreamingType.SEARCH_TOOL_QUERIES_DELTA.value
    )

    queries: list[str]


# Documents coming through as the system knows what to add to the context
class SearchToolDocumentsDelta(BaseObj):
    type: Literal["search_tool_documents_delta"] = (
        StreamingType.SEARCH_TOOL_DOCUMENTS_DELTA.value
    )

    # This cannot be the SavedSearchDoc as this is yielded by the SearchTool directly
    # which does not save documents to the DB.
    documents: list[SearchDoc]


# OpenURL tool packets - 3-stage sequence
class OpenUrlStart(BaseObj):
    """Signal that OpenURL tool has started."""

    type: Literal["open_url_start"] = StreamingType.OPEN_URL_START.value


class OpenUrlUrls(BaseObj):
    """URLs to be fetched (sent before crawling begins)."""

    type: Literal["open_url_urls"] = StreamingType.OPEN_URL_URLS.value

    urls: list[str]


class OpenUrlDocuments(BaseObj):
    """Final documents after crawling completes."""

    type: Literal["open_url_documents"] = StreamingType.OPEN_URL_DOCUMENTS.value

    documents: list[SearchDoc]


# Image generation starting, needs to allocate a placeholder block for it on the UI
class ImageGenerationToolStart(BaseObj):
    type: Literal["image_generation_start"] = StreamingType.IMAGE_GENERATION_START.value


# Since image generation can take a while
# we send a heartbeat to the frontend to keep the UI/connection alive
class ImageGenerationToolHeartbeat(BaseObj):
    type: Literal["image_generation_heartbeat"] = (
        StreamingType.IMAGE_GENERATION_HEARTBEAT.value
    )


# Represents an image generated by an image generation tool
class GeneratedImage(BaseModel):
    """Represents an image generated by an image generation tool."""

    file_id: str
    url: str
    revised_prompt: str
    shape: str | None = None


# The final generated images all at once at the end of image generation
class ImageGenerationFinal(BaseObj):
    type: Literal["image_generation_final"] = StreamingType.IMAGE_GENERATION_FINAL.value

    images: list[GeneratedImage]


class PythonToolStart(BaseObj):
    type: Literal["python_tool_start"] = StreamingType.PYTHON_TOOL_START.value
    code: str


class PythonToolFile(BaseModel):
    """Enriched file metadata for PythonTool-generated files (charts, CSVs, etc.)."""

    file_id: str
    filename: str


class PythonToolDelta(BaseObj):
    type: Literal["python_tool_delta"] = StreamingType.PYTHON_TOOL_DELTA.value

    stdout: str = ""
    stderr: str = ""
    file_ids: list[str] = []  # Kept for backward compatibility
    files: list[PythonToolFile] = []  # Enriched file metadata

    # --- Live-streaming metadata (all optional; older clients ignore them) ---
    # Set only on the TERMINAL delta so the renderer can show accurate status and
    # elapsed time without inferring failure from stderr presence.
    exit_code: int | None = None
    timed_out: bool = False
    duration_ms: int | None = None
    # Non-timeout failure mode when set: "oom", "kernel_died", "timeout".
    error_kind: str | None = None
    # Self-heal attempt boundary: when True, the renderer archives the failed
    # attempt's live output as a collapsed block and clears the live pane so the
    # next attempt streams into a clean surface.
    reset: bool = False


# Custom tool being called, first allocate a placeholder block for it on the UI
class CustomToolStart(BaseObj):
    type: Literal["custom_tool_start"] = StreamingType.CUSTOM_TOOL_START.value

    tool_name: str


# The allowed streamed packets for a custom tool
class CustomToolDelta(BaseObj):
    type: Literal["custom_tool_delta"] = StreamingType.CUSTOM_TOOL_DELTA.value

    tool_name: str
    response_type: str
    # For non-file responses
    data: dict | list | str | int | float | bool | None = None
    # For file-based responses like image/csv
    file_ids: list[str] | None = None


################################################
# File Reader Packets
################################################
class FileReaderStart(BaseObj):
    type: Literal["file_reader_start"] = StreamingType.FILE_READER_START.value


class FileReaderResult(BaseObj):
    type: Literal["file_reader_result"] = StreamingType.FILE_READER_RESULT.value

    file_name: str
    file_id: str
    start_char: int
    end_char: int
    total_chars: int
    # Short previews of the retrieved text for the collapsed/expanded UI
    preview_start: str = ""
    preview_end: str = ""


# Memory Tool Packets
################################################
class MemoryToolStart(BaseObj):
    type: Literal["memory_tool_start"] = StreamingType.MEMORY_TOOL_START.value


class MemoryToolDelta(BaseObj):
    type: Literal["memory_tool_delta"] = StreamingType.MEMORY_TOOL_DELTA.value

    memory_text: str
    operation: Literal["add", "update"]
    memory_id: int | None = None
    index: int | None = None


class MemoryToolNoAccess(BaseObj):
    type: Literal["memory_tool_no_access"] = StreamingType.MEMORY_TOOL_NO_ACCESS.value


################################################
# Deep Research Packets
################################################
class DeepResearchPlanStart(BaseObj):
    type: Literal["deep_research_plan_start"] = (
        StreamingType.DEEP_RESEARCH_PLAN_START.value
    )


class DeepResearchPlanDelta(BaseObj):
    type: Literal["deep_research_plan_delta"] = (
        StreamingType.DEEP_RESEARCH_PLAN_DELTA.value
    )

    content: str


class ResearchAgentStart(BaseObj):
    type: Literal["research_agent_start"] = StreamingType.RESEARCH_AGENT_START.value
    research_task: str


class IntermediateReportStart(BaseObj):
    type: Literal["intermediate_report_start"] = (
        StreamingType.INTERMEDIATE_REPORT_START.value
    )


class IntermediateReportDelta(BaseObj):
    type: Literal["intermediate_report_delta"] = (
        StreamingType.INTERMEDIATE_REPORT_DELTA.value
    )
    content: str


class IntermediateReportCitedDocs(BaseObj):
    type: Literal["intermediate_report_cited_docs"] = (
        StreamingType.INTERMEDIATE_REPORT_CITED_DOCS.value
    )
    cited_docs: list[SearchDoc] | None = None


################################################
# Workflow Packets
################################################
class WorkflowStepStart(BaseObj):
    type: Literal["workflow_step_start"] = StreamingType.WORKFLOW_STEP_START.value
    step_name: str
    agent_name: str | None = None
    step_order: int
    step_type: str = "agent"
    promote_output: bool = False


class WorkflowStepDelta(BaseObj):
    type: Literal["workflow_step_delta"] = StreamingType.WORKFLOW_STEP_DELTA.value
    content: str
    # When True, consumers replace the step's accumulated live-streamed text with
    # `content` (the authoritative agent_output) instead of appending. Live
    # sub-agent prose chunks stream with replace=False; the final block reconciles
    # with replace=True. NOTE: a consumer that ignores `replace` and appends every
    # delta will DOUBLE the output (streamed chunks + the authoritative block),
    # since the accumulated chunks already equal agent_output. This is safe here
    # only because the frontend renderer, the persistence writer
    # (message_handler._run_workflow_and_save), and the backend ship together and
    # all honor `replace`.
    replace: bool = False


class WorkflowStepReasoningDelta(BaseObj):
    # Live sub-agent reasoning ("thinking") chunk, tagged to the current workflow
    # step's placement so it renders in a collapsible block under the step. Ephemeral
    # (not persisted / not reconstructed on reload).
    type: Literal["workflow_step_reasoning_delta"] = (
        StreamingType.WORKFLOW_STEP_REASONING_DELTA.value
    )
    content: str


class WorkflowStepEnd(BaseObj):
    type: Literal["workflow_step_end"] = StreamingType.WORKFLOW_STEP_END.value
    step_name: str
    output_key: str


class WorkflowOrchestratorThinking(BaseObj):
    type: Literal["workflow_orchestrator_thinking"] = (
        StreamingType.WORKFLOW_ORCHESTRATOR_THINKING.value
    )
    content: str


class WorkflowPauseForInput(BaseObj):
    """Emitted when an agent requests user input (human-in-the-loop).

    The workflow engine saves a checkpoint and stops execution.
    The frontend renders the questions and the user responds
    via normal chat input. The engine detects the paused execution
    and resumes from the checkpoint.
    """

    type: Literal["workflow_pause_for_input"] = (
        StreamingType.WORKFLOW_PAUSE_FOR_INPUT.value
    )
    step_name: str
    agent_name: str
    questions: str  # The agent's clarification text


################################################
# Packet Object
################################################
# Discriminated union of all possible packet object types
PacketObj = Union[
    # Control Packets
    OverallStop,
    SectionEnd,
    TopLevelBranching,
    PacketException,
    # Agent Response Packets
    AgentResponseStart,
    AgentResponseDelta,
    # Tool Packets
    SearchToolStart,
    SearchToolQueriesDelta,
    SearchToolDocumentsDelta,
    ImageGenerationToolStart,
    ImageGenerationToolHeartbeat,
    ImageGenerationFinal,
    OpenUrlStart,
    OpenUrlUrls,
    OpenUrlDocuments,
    PythonToolStart,
    PythonToolDelta,
    CustomToolStart,
    CustomToolDelta,
    FileReaderStart,
    FileReaderResult,
    MemoryToolStart,
    MemoryToolDelta,
    MemoryToolNoAccess,
    # Reasoning Packets
    ReasoningStart,
    ReasoningDelta,
    ReasoningDone,
    # Citation Packets
    CitationInfo,
    ToolCallDebug,
    # Deep Research Packets
    DeepResearchPlanStart,
    DeepResearchPlanDelta,
    ResearchAgentStart,
    IntermediateReportStart,
    IntermediateReportDelta,
    IntermediateReportCitedDocs,
    # Workflow Packets
    WorkflowStepStart,
    WorkflowStepDelta,
    WorkflowStepReasoningDelta,
    WorkflowStepEnd,
    WorkflowOrchestratorThinking,
    WorkflowPauseForInput,
]


class Packet(BaseModel):
    placement: Placement

    obj: Annotated[PacketObj, Field(discriminator="type")]


################################################
# Search API Packets
################################################
# NOTE: SearchDocWithContent is defined here (rather than in
# om.server.query_and_chat.models) because the search packets below need it and
# `models` already imports from this module. It is re-exported from
# `om.server.query_and_chat.models` for convenience.
class SearchDocWithContent(SearchDoc):
    # Allows None because this is determined by a flag but the object used in code
    # of the search path uses this type
    content: str | None

    @classmethod
    def from_inference_sections(
        cls,
        sections: Sequence[InferenceSection],
        include_content: bool = False,
        is_internet: bool = False,
    ) -> list["SearchDocWithContent"]:
        """Convert InferenceSections to SearchDocWithContent objects.

        Args:
            sections: Sequence of InferenceSection objects
            include_content: If True, populate content field with combined_content
            is_internet: Whether these are internet search results

        Returns:
            List of SearchDocWithContent with optional content
        """
        if not sections:
            return []

        return [
            cls(
                document_id=(chunk := section.center_chunk).document_id,
                chunk_ind=chunk.chunk_id,
                semantic_identifier=chunk.semantic_identifier or "Unknown",
                link=chunk.source_links[0] if chunk.source_links else None,
                blurb=chunk.blurb,
                source_type=chunk.source_type,
                boost=chunk.boost,
                hidden=chunk.hidden,
                metadata=chunk.metadata,
                score=chunk.score,
                match_highlights=chunk.match_highlights,
                updated_at=chunk.updated_at,
                primary_owners=chunk.primary_owners,
                secondary_owners=chunk.secondary_owners,
                is_internet=is_internet,
                content=section.combined_content if include_content else None,
            )
            for section in sections
        ]


class SearchQueriesPacket(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["search_queries"] = "search_queries"
    all_executed_queries: list[str]


class SearchDocsPacket(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["search_docs"] = "search_docs"
    search_docs: list[SearchDocWithContent]


class SearchErrorPacket(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["search_error"] = "search_error"
    error: str


class LLMSelectedDocsPacket(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["llm_selected_docs"] = "llm_selected_docs"
    # None if LLM selection failed, empty list if no docs selected, list of IDs otherwise
    llm_selected_doc_ids: list[str] | None
