from __future__ import annotations

import json
from typing import cast
from typing import Literal

from sqlalchemy.orm import Session

from om.chat.citation_utils import extract_citation_order_from_text
from om.configs.constants import MessageType
from om.context.search.models import SavedSearchDoc
from om.context.search.models import SearchDoc
from om.db.chat import get_db_search_doc_by_id
from om.db.chat import translate_db_search_doc_to_saved_search_doc
from om.db.models import ChatMessage
from om.db.models import ToolCall
from om.db.tools import get_tool_by_id
from om.deep_research.dr_mock_tools import RESEARCH_AGENT_IN_CODE_ID
from om.deep_research.dr_mock_tools import RESEARCH_AGENT_TASK_KEY
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import AgentResponseDelta
from om.server.query_and_chat.streaming_models import AgentResponseStart
from om.server.query_and_chat.streaming_models import CitationInfo
from om.server.query_and_chat.streaming_models import CustomToolDelta
from om.server.query_and_chat.streaming_models import CustomToolStart
from om.server.query_and_chat.streaming_models import FileReaderResult
from om.server.query_and_chat.streaming_models import FileReaderStart
from om.server.query_and_chat.streaming_models import GeneratedImage
from om.server.query_and_chat.streaming_models import ImageGenerationFinal
from om.server.query_and_chat.streaming_models import ImageGenerationToolStart
from om.server.query_and_chat.streaming_models import IntermediateReportDelta
from om.server.query_and_chat.streaming_models import IntermediateReportStart
from om.server.query_and_chat.streaming_models import MemoryToolDelta
from om.server.query_and_chat.streaming_models import MemoryToolStart
from om.server.query_and_chat.streaming_models import OpenUrlDocuments
from om.server.query_and_chat.streaming_models import OpenUrlStart
from om.server.query_and_chat.streaming_models import OpenUrlUrls
from om.server.query_and_chat.streaming_models import OverallStop
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import PythonToolDelta
from om.server.query_and_chat.streaming_models import PythonToolFile
from om.server.query_and_chat.streaming_models import PythonToolStart
from om.server.query_and_chat.streaming_models import ReasoningDelta
from om.server.query_and_chat.streaming_models import ReasoningStart
from om.server.query_and_chat.streaming_models import ResearchAgentStart
from om.server.query_and_chat.streaming_models import SearchToolDocumentsDelta
from om.server.query_and_chat.streaming_models import SearchToolQueriesDelta
from om.server.query_and_chat.streaming_models import SearchToolStart
from om.server.query_and_chat.streaming_models import SectionEnd
from om.server.query_and_chat.streaming_models import TopLevelBranching
from om.tools.tool_implementations.file_reader.file_reader_tool import FileReaderTool
from om.tools.tool_implementations.images.image_generation_tool import (
    ImageGenerationTool,
)
from om.tools.tool_implementations.memory.memory_tool import MemoryTool
from om.tools.tool_implementations.python.python_tool import PythonTool
from om.tools.tool_implementations.open_url.open_url_tool import OpenURLTool
from om.tools.tool_implementations.search.search_tool import SearchTool
from om.tools.tool_implementations.web_search.web_search_tool import WebSearchTool
from om.utils.logger import setup_logger

logger = setup_logger()

# Must match WORKFLOW_STEP_TOOL_ID in message_handler.py
_WORKFLOW_STEP_TOOL_ID = 0


def _create_workflow_step_packets(tool_call: ToolCall) -> list[Packet]:
    """Reconstruct workflow step packets from a saved ToolCall.

    Workflow steps are stored with tool_id=0 and a ``_workflow_step`` marker
    in ``tool_call_arguments``.  This recreates the ``WorkflowStepStart``,
    ``WorkflowStepDelta``, ``WorkflowStepEnd`` (and optionally
    ``WorkflowPauseForInput``) packets so the timeline displays correctly
    on session reload.
    """
    from om.server.query_and_chat.streaming_models import (
        WorkflowPauseForInput,
        WorkflowStepDelta,
        WorkflowStepEnd,
        WorkflowStepStart,
    )

    args = tool_call.tool_call_arguments or {}
    turn_idx = tool_call.turn_number
    tab_idx = tool_call.tab_index
    step_name = args.get("step_name", tool_call.tool_call_id or "step")
    agent_name = args.get("agent_name", "Agent")
    step_order = args.get("step_order", 0)
    is_pause = args.get("_workflow_pause", False)

    placement = Placement(turn_index=turn_idx, tab_index=tab_idx)
    packets: list[Packet] = []

    # WorkflowStepStart
    packets.append(
        Packet(
            placement=placement,
            obj=WorkflowStepStart(
                step_name=step_name,
                agent_name=agent_name,
                step_order=step_order,
            ),
        )
    )

    output = tool_call.tool_call_response or ""

    if is_pause:
        # For paused steps, emit WorkflowPauseForInput
        packets.append(
            Packet(
                placement=placement,
                obj=WorkflowPauseForInput(
                    step_name=step_name,
                    agent_name=agent_name,
                    questions=output,
                ),
            )
        )
    else:
        # Normal step — emit delta + end
        if output:
            packets.append(
                Packet(
                    placement=placement,
                    obj=WorkflowStepDelta(content=output),
                )
            )
        # Reconstruct file download links if this step captured files
        file_ids = args.get("_file_ids")
        if file_ids:
            from om.server.query_and_chat.streaming_models import (
                CustomToolDelta,
                CustomToolStart,
            )
            packets.append(
                Packet(
                    placement=placement,
                    obj=CustomToolStart(tool_name="document_files"),
                )
            )
            packets.append(
                Packet(
                    placement=placement,
                    obj=CustomToolDelta(
                        tool_name="document_files",
                        response_type="json",
                        data={"tool_result": "Generated document files", "_file_ids": file_ids},
                        file_ids=file_ids,
                    ),
                )
            )
            packets.append(Packet(placement=placement, obj=SectionEnd()))

        packets.append(
            Packet(
                placement=placement,
                obj=WorkflowStepEnd(
                    step_name=step_name,
                    output_key=args.get("output_key", step_name),
                ),
            )
        )

    # Close the section
    packets.append(Packet(placement=placement, obj=SectionEnd()))

    return packets


def create_message_packets(
    message_text: str,
    final_documents: list[SearchDoc] | None,
    turn_index: int,
) -> list[Packet]:
    packets: list[Packet] = []

    final_search_docs: list[SearchDoc] | None = None
    if final_documents:
        sorted_final_documents = sorted(
            final_documents, key=lambda x: (x.score or 0.0), reverse=True
        )
        final_search_docs = [
            SearchDoc(**doc.model_dump()) for doc in sorted_final_documents
        ]

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index),
            obj=AgentResponseStart(
                final_documents=final_search_docs,
            ),
        )
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index),
            obj=AgentResponseDelta(
                content=message_text,
            ),
        ),
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index),
            obj=SectionEnd(),
        )
    )

    return packets


def create_citation_packets(
    citation_info_list: list[CitationInfo], turn_index: int
) -> list[Packet]:
    packets: list[Packet] = []

    # Emit each citation as a separate CitationInfo packet
    for citation_info in citation_info_list:
        packets.append(
            Packet(
                placement=Placement(turn_index=turn_index),
                obj=citation_info,
            )
        )

    packets.append(Packet(placement=Placement(turn_index=turn_index), obj=SectionEnd()))

    return packets


def create_reasoning_packets(reasoning_text: str, turn_index: int) -> list[Packet]:
    packets: list[Packet] = []

    packets.append(
        Packet(placement=Placement(turn_index=turn_index), obj=ReasoningStart())
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index),
            obj=ReasoningDelta(
                reasoning=reasoning_text,
            ),
        ),
    )

    packets.append(Packet(placement=Placement(turn_index=turn_index), obj=SectionEnd()))

    return packets


def create_image_generation_packets(
    images: list[GeneratedImage], turn_index: int, tab_index: int = 0
) -> list[Packet]:
    packets: list[Packet] = []

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=ImageGenerationToolStart(),
        )
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=ImageGenerationFinal(images=images),
        ),
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=SectionEnd(),
        )
    )

    return packets


def create_python_tool_packets(
    code: str,
    stdout: str,
    stderr: str,
    files: list[PythonToolFile],
    turn_index: int,
    tab_index: int = 0,
) -> list[Packet]:
    """Reconstruct PythonTool packets from stored ToolCall data for history reload."""
    packets: list[Packet] = []

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=PythonToolStart(code=code),
        )
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=PythonToolDelta(
                stdout=stdout,
                stderr=stderr,
                file_ids=[f.file_id for f in files],
                files=files,
            ),
        )
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=SectionEnd(),
        )
    )

    return packets


def create_custom_tool_packets(
    tool_name: str,
    response_type: str,
    turn_index: int,
    tab_index: int = 0,
    data: dict | list | str | int | float | bool | None = None,
    file_ids: list[str] | None = None,
) -> list[Packet]:
    packets: list[Packet] = []

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=CustomToolStart(tool_name=tool_name),
        )
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=CustomToolDelta(
                tool_name=tool_name,
                response_type=response_type,
                data=data,
                file_ids=file_ids,
            ),
        ),
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=SectionEnd(),
        )
    )

    return packets


def create_file_reader_packets(
    summary_json: str,
    turn_index: int,
    tab_index: int = 0,
) -> list[Packet]:
    """Recreate FileReaderStart + FileReaderResult + SectionEnd from the stored
    JSON summary so that the FileReaderToolRenderer can display the result on
    page reload."""
    import json

    packets: list[Packet] = []
    placement = Placement(turn_index=turn_index, tab_index=tab_index)

    packets.append(Packet(placement=placement, obj=FileReaderStart()))

    try:
        data = json.loads(summary_json)
        packets.append(
            Packet(
                placement=placement,
                obj=FileReaderResult(
                    file_name=data["file_name"],
                    file_id=data["file_id"],
                    start_char=data["start_char"],
                    end_char=data["end_char"],
                    total_chars=data["total_chars"],
                    preview_start=data.get("preview_start", ""),
                    preview_end=data.get("preview_end", ""),
                ),
            )
        )
    except (json.JSONDecodeError, KeyError):
        # Gracefully degrade for old data that wasn't saved as JSON summary
        pass

    packets.append(Packet(placement=placement, obj=SectionEnd()))
    return packets


def create_research_agent_packets(
    research_task: str,
    report_content: str | None,
    turn_index: int,
    tab_index: int = 0,
) -> list[Packet]:
    """Create packets for research agent tool calls.
    This recreates the packet structure that ResearchAgentRenderer expects:
    - ResearchAgentStart with the research task
    - IntermediateReportStart to signal report begins
    - IntermediateReportDelta with the report content (if available)
    - SectionEnd to mark completion
    """
    packets: list[Packet] = []

    # Emit research agent start
    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=ResearchAgentStart(research_task=research_task),
        )
    )

    # Emit report content if available
    if report_content:
        # Emit IntermediateReportStart before delta
        packets.append(
            Packet(
                placement=Placement(turn_index=turn_index, tab_index=tab_index),
                obj=IntermediateReportStart(),
            )
        )

        packets.append(
            Packet(
                placement=Placement(turn_index=turn_index, tab_index=tab_index),
                obj=IntermediateReportDelta(content=report_content),
            )
        )

    # Emit section end
    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=SectionEnd(),
        )
    )

    return packets


def create_fetch_packets(
    fetch_docs: list[SavedSearchDoc],
    urls: list[str],
    turn_index: int,
    tab_index: int = 0,
) -> list[Packet]:
    packets: list[Packet] = []
    # Emit start packet
    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=OpenUrlStart(),
        )
    )
    # Emit URLs packet
    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=OpenUrlUrls(urls=urls),
        )
    )
    # Emit documents packet
    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=OpenUrlDocuments(
                documents=[SearchDoc(**doc.model_dump()) for doc in fetch_docs]
            ),
        )
    )
    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=SectionEnd(),
        )
    )
    return packets


def create_memory_packets(
    memory_text: str,
    operation: Literal["add", "update"],
    memory_id: int | None,
    turn_index: int,
    tab_index: int = 0,
    index: int | None = None,
) -> list[Packet]:
    packets: list[Packet] = []

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=MemoryToolStart(),
        )
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=MemoryToolDelta(
                memory_text=memory_text,
                operation=operation,
                memory_id=memory_id,
                index=index,
            ),
        ),
    )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=SectionEnd(),
        )
    )

    return packets


def create_search_packets(
    search_queries: list[str],
    search_docs: list[SavedSearchDoc],
    is_internet_search: bool,
    turn_index: int,
    tab_index: int = 0,
) -> list[Packet]:
    packets: list[Packet] = []

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=SearchToolStart(
                is_internet_search=is_internet_search,
            ),
        )
    )

    # Emit queries if present
    if search_queries:
        packets.append(
            Packet(
                placement=Placement(turn_index=turn_index, tab_index=tab_index),
                obj=SearchToolQueriesDelta(queries=search_queries),
            ),
        )

    # Emit documents if present
    if search_docs:
        sorted_search_docs = sorted(
            search_docs, key=lambda x: (x.score or 0.0), reverse=True
        )
        packets.append(
            Packet(
                placement=Placement(turn_index=turn_index, tab_index=tab_index),
                obj=SearchToolDocumentsDelta(
                    documents=[
                        SearchDoc(**doc.model_dump()) for doc in sorted_search_docs
                    ]
                ),
            ),
        )

    packets.append(
        Packet(
            placement=Placement(turn_index=turn_index, tab_index=tab_index),
            obj=SectionEnd(),
        )
    )

    return packets


def translate_assistant_message_to_packets(
    chat_message: ChatMessage,
    db_session: Session,
) -> list[Packet]:
    """
    Translates an assistant message and tool calls to packet format.
    It needs to be a list of list of packets combined into indices for "steps".
    The final answer and citations are also a "step".
    """
    packet_list: list[Packet] = []

    if chat_message.message_type != MessageType.ASSISTANT:
        raise ValueError(f"Chat message {chat_message.id} is not an assistant message")

    if chat_message.tool_calls:
        # Group tool calls by turn_number
        tool_calls_by_turn: dict[int, list] = {}
        for tool_call in chat_message.tool_calls:
            turn_num = tool_call.turn_number
            if turn_num not in tool_calls_by_turn:
                tool_calls_by_turn[turn_num] = []
            tool_calls_by_turn[turn_num].append(tool_call)

        tool_call_turns = set(tool_calls_by_turn.keys())
        # Process each turn in order
        for turn_num in sorted(tool_calls_by_turn.keys()):
            tool_calls_in_turn = tool_calls_by_turn[turn_num]

            # Insert pre-tool reasoning once per turn (if available)
            turn_reasoning = next(
                (
                    tool_call.reasoning_tokens
                    for tool_call in tool_calls_in_turn
                    if tool_call.reasoning_tokens
                ),
                None,
            )
            if turn_reasoning:
                # Use the previous turn slot when free to preserve reasoning-before-tool ordering.
                reasoning_turn_index = turn_num
                if turn_num > 0 and (turn_num - 1) not in tool_call_turns:
                    reasoning_turn_index = turn_num - 1
                packet_list.extend(
                    create_reasoning_packets(
                        reasoning_text=turn_reasoning,
                        turn_index=reasoning_turn_index,
                    )
                )

            # Process each tool call in this turn (single pass).
            # We buffer packets for the turn so we can conditionally prepend a TopLevelBranching
            # packet (which must appear before any tool output in the turn).
            research_agent_count = 0
            turn_tool_packets: list[Packet] = []
            for tool_call in tool_calls_in_turn:
                # Workflow step tool calls use sentinel tool_id=0
                if tool_call.tool_id == _WORKFLOW_STEP_TOOL_ID:
                    turn_tool_packets.extend(
                        _create_workflow_step_packets(tool_call)
                    )
                    continue

                # Here we do a try because some tools may get deleted before the session is reloaded.
                try:
                    tool = get_tool_by_id(tool_call.tool_id, db_session)
                    if tool.in_code_tool_id == RESEARCH_AGENT_IN_CODE_ID:
                        research_agent_count += 1

                    # Handle different tool types
                    if tool.in_code_tool_id in [
                        SearchTool.__name__,
                        WebSearchTool.__name__,
                    ]:
                        queries = cast(
                            list[str], tool_call.tool_call_arguments.get("queries", [])
                        )
                        search_docs: list[SavedSearchDoc] = [
                            translate_db_search_doc_to_saved_search_doc(doc)
                            for doc in tool_call.search_docs
                        ]
                        turn_tool_packets.extend(
                            create_search_packets(
                                search_queries=queries,
                                search_docs=search_docs,
                                is_internet_search=tool.in_code_tool_id
                                == WebSearchTool.__name__,
                                turn_index=turn_num,
                                tab_index=tool_call.tab_index,
                            )
                        )

                    elif tool.in_code_tool_id == OpenURLTool.__name__:
                        fetch_docs: list[SavedSearchDoc] = [
                            translate_db_search_doc_to_saved_search_doc(doc)
                            for doc in tool_call.search_docs
                        ]
                        # Get URLs from tool_call_arguments
                        urls = cast(
                            list[str], tool_call.tool_call_arguments.get("urls", [])
                        )
                        turn_tool_packets.extend(
                            create_fetch_packets(
                                fetch_docs,
                                urls,
                                turn_num,
                                tab_index=tool_call.tab_index,
                            )
                        )

                    elif tool.in_code_tool_id == ImageGenerationTool.__name__:
                        if tool_call.generated_images:
                            images = [
                                GeneratedImage(**img)
                                for img in tool_call.generated_images
                            ]
                            turn_tool_packets.extend(
                                create_image_generation_packets(
                                    images, turn_num, tab_index=tool_call.tab_index
                                )
                            )

                    elif tool.in_code_tool_id == FileReaderTool.__name__:
                        turn_tool_packets.extend(
                            create_file_reader_packets(
                                summary_json=tool_call.tool_call_response or "",
                                turn_index=turn_num,
                                tab_index=tool_call.tab_index,
                            )
                        )

                    elif tool.in_code_tool_id == RESEARCH_AGENT_IN_CODE_ID:
                        # Not ideal but not a huge issue if the research task is lost.
                        research_task = cast(
                            str,
                            tool_call.tool_call_arguments.get(RESEARCH_AGENT_TASK_KEY)
                            or "Could not fetch saved research task.",
                        )
                        turn_tool_packets.extend(
                            create_research_agent_packets(
                                research_task=research_task,
                                report_content=tool_call.tool_call_response,
                                turn_index=turn_num,
                                tab_index=tool_call.tab_index,
                            )
                        )

                    elif tool.in_code_tool_id == MemoryTool.__name__:
                        if tool_call.tool_call_response:
                            memory_data = json.loads(tool_call.tool_call_response)
                            turn_tool_packets.extend(
                                create_memory_packets(
                                    memory_text=memory_data["memory_text"],
                                    operation=cast(
                                        Literal["add", "update"],
                                        memory_data["operation"],
                                    ),
                                    memory_id=memory_data.get("memory_id"),
                                    turn_index=turn_num,
                                    tab_index=tool_call.tab_index,
                                    index=memory_data.get("index"),
                                )
                            )

                    elif tool.in_code_tool_id == PythonTool.__name__:
                        # Reconstruct PythonTool packets from stored data
                        code = tool_call.tool_call_arguments.get("code", "")
                        stdout = ""
                        stderr = ""
                        python_files: list[PythonToolFile] = []

                        if tool_call.tool_call_response:
                            try:
                                result_data = json.loads(
                                    tool_call.tool_call_response
                                )
                                stdout = result_data.get("stdout", "")
                                stderr = result_data.get("stderr", "")
                                # Extract file_ids from file_link URLs
                                # file_link format: {WEB_DOMAIN}/api/converse/file/{file_id}
                                for gen_file in result_data.get(
                                    "generated_files", []
                                ):
                                    file_link = gen_file.get("file_link", "")
                                    filename = gen_file.get("filename", "")
                                    # Extract file_id from the URL
                                    file_id = file_link.rsplit("/", 1)[-1]
                                    if file_id:
                                        python_files.append(
                                            PythonToolFile(
                                                file_id=file_id,
                                                filename=filename,
                                            )
                                        )
                            except (json.JSONDecodeError, KeyError):
                                logger.warning(
                                    f"Failed to parse PythonTool response for tool_call {tool_call.id}"
                                )

                        turn_tool_packets.extend(
                            create_python_tool_packets(
                                code=code,
                                stdout=stdout,
                                stderr=stderr,
                                files=python_files,
                                turn_index=turn_num,
                                tab_index=tool_call.tab_index,
                            )
                        )

                    else:
                        # Custom tool or MCP tool — parse stored JSON
                        # for file_ids persisted by MCP file download flow
                        response_type = "text"
                        data: dict | list | str | int | float | bool | None = (
                            tool_call.tool_call_response
                        )
                        file_ids: list[str] | None = None

                        if tool_call.tool_call_response:
                            try:
                                parsed = json.loads(
                                    tool_call.tool_call_response
                                )
                                if isinstance(parsed, dict):
                                    file_ids = parsed.pop("_file_ids", None)
                                    data = parsed
                                    response_type = "json"
                            except (json.JSONDecodeError, ValueError):
                                pass

                        turn_tool_packets.extend(
                            create_custom_tool_packets(
                                tool_name=tool.display_name or tool.name,
                                response_type=response_type,
                                turn_index=turn_num,
                                tab_index=tool_call.tab_index,
                                data=data,
                                file_ids=file_ids,
                            )
                        )

                except Exception as e:
                    logger.warning(f"Error processing tool call {tool_call.id}: {e}")
                    continue

            if research_agent_count > 1:
                # Emit TopLevelBranching before processing any tool output in the turn.
                packet_list.append(
                    Packet(
                        placement=Placement(turn_index=turn_num),
                        obj=TopLevelBranching(
                            num_parallel_branches=research_agent_count
                        ),
                    )
                )
            packet_list.extend(turn_tool_packets)

    # Determine the next turn_index for the final message
    # It should come after all tool calls
    max_tool_turn = 0
    if chat_message.tool_calls:
        max_tool_turn = max(tc.turn_number for tc in chat_message.tool_calls)

    citations = chat_message.citations
    citation_info_list: list[CitationInfo] = []

    if citations:
        for citation_num, search_doc_id in citations.items():
            search_doc = get_db_search_doc_by_id(search_doc_id, db_session)
            if search_doc:
                citation_info_list.append(
                    CitationInfo(
                        citation_number=citation_num,
                        document_id=search_doc.document_id,
                    )
                )

        # Sort citations by order of appearance in message text
        citation_order = extract_citation_order_from_text(chat_message.message or "")
        order_map = {num: idx for idx, num in enumerate(citation_order)}
        citation_info_list.sort(
            key=lambda c: order_map.get(c.citation_number, float("inf"))
        )

    # Message comes after tool calls, with optional reasoning step beforehand
    message_turn_index = max_tool_turn + 1
    if chat_message.reasoning_tokens:
        packet_list.extend(
            create_reasoning_packets(
                reasoning_text=chat_message.reasoning_tokens,
                turn_index=message_turn_index,
            )
        )
        message_turn_index += 1

    if chat_message.message:
        packet_list.extend(
            create_message_packets(
                message_text=chat_message.message,
                final_documents=[
                    translate_db_search_doc_to_saved_search_doc(doc)
                    for doc in chat_message.search_docs
                ],
                turn_index=message_turn_index,
            )
        )

    # Citations come after the message
    citation_turn_index = (
        message_turn_index + 1 if citation_info_list else message_turn_index
    )

    if len(citation_info_list) > 0:
        packet_list.extend(
            create_citation_packets(citation_info_list, citation_turn_index)
        )

    # Return the highest turn_index used
    final_turn_index = 0
    if chat_message.message_type == MessageType.ASSISTANT:
        max_tool_turn = 0
        if chat_message.tool_calls:
            max_tool_turn = max(tc.turn_number for tc in chat_message.tool_calls)

        final_turn_index = max_tool_turn
        if chat_message.reasoning_tokens:
            final_turn_index = max(final_turn_index, max_tool_turn + 1)
        if chat_message.message:
            final_turn_index = max(final_turn_index, message_turn_index)
        if citation_info_list:
            final_turn_index = max(final_turn_index, citation_turn_index)

    # Determine stop reason - check if message indicates user cancelled
    stop_reason: str | None = None
    if chat_message.message:
        if "generation was stopped" in chat_message.message.lower():
            stop_reason = "user_cancelled"

    # Add overall stop packet at the end
    packet_list.append(
        Packet(
            placement=Placement(turn_index=final_turn_index),
            obj=OverallStop(stop_reason=stop_reason),
        )
    )

    return packet_list
