"""Built-in node type ``agent`` v1: run one Agent as a workflow step.

v1 predates the ``config`` column: its settings live in the legacy step columns
(``agent_id`` and the ``*_override`` columns) and are read by
``load_agent_config_v1``.

The runner reproduces the legacy sequential engine's agent step exactly
(packets, placements, checkpoints, trace calls); the golden harness in
``tests/unit/om/workflows/engine_golden`` guards this.
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import model_serializer
from pydantic import SerializerFunctionWrapHandler

from om.configs.constants import DEFAULT_AGENT_ID
from om.db.models import Agent
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import AgentResponseDelta
from om.server.query_and_chat.streaming_models import AgentResponseStart
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import SectionEnd
from om.server.query_and_chat.streaming_models import WorkflowPauseForInput
from om.server.query_and_chat.streaming_models import WorkflowStepDelta
from om.server.query_and_chat.streaming_models import WorkflowStepEnd
from om.server.query_and_chat.streaming_models import WorkflowStepStart
from om.utils.logger import setup_logger
from om.workflows.agent_streaming import stream_agent_packets
from om.workflows.agent_streaming import StreamingAgentResult
from om.workflows.hitl import agent_requests_input
from om.workflows.hitl import strip_needs_input_prefix
from om.workflows.inputs import apply_input_mapping
from om.workflows.inputs import apply_safe_input_mapping
from om.workflows.inputs import SAFE_REFERENCES_SCHEMA_VERSION
from om.workflows.inputs import UnresolvedReferenceError
from om.workflows.output_contract import check_schema
from om.workflows.output_contract import format_instruction
from om.workflows.output_contract import OutputContractError
from om.workflows.output_contract import read_output
from om.workflows.output_contract import retry_task
from om.workflows.nodes.base import SaveContext
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepSaveError
from om.workflows.nodes.base import StepStatus

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from om.db.models import AgentWorkflowStep
    from om.tools.models import ToolResponse
    from om.tools.tool_implementations.agent_tool import AgentTool
    from om.workflows.graph import WorkflowNode
    from om.workflows.models import WorkflowStepCreate
    from om.workflows.state import RunContext

logger = setup_logger()

AGENT_NODE_TYPE = "agent"


OUTPUT_SCHEMA_FIELD = "output_schema"
SEQUENTIAL_MODE = "sequential"
MAX_REPLY_IN_ERROR = 300


class AgentStepConfigV1(BaseModel):
    """Settings of an ``agent`` v1 step.

    ``agent_id`` is optional here only to keep legacy rows loadable; the save API
    requires it and a run fails on a step without one (``load_step_agent``).
    The ``*_override`` fields override the agent's own settings for this step.
    """

    agent_id: int | None = None
    llm_provider_override: str | None = None
    llm_model_override: str | None = None
    max_output_tokens_override: int | None = None
    system_prompt_override: str | None = None
    task_prompt_override: str | None = None
    tool_ids_override: list[int] | None = None
    document_set_ids_override: list[int] | None = None
    replace_base_system_prompt_override: bool | None = None
    # What the agent must return, as a JSON schema (see output_contract.py).
    output_schema: dict[str, Any] | None = None

    @model_serializer(mode="wrap")
    def _omit_empty_schema(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # Absent unless set, so existing definitions keep their content hash.
        data = handler(self)
        if data.get(OUTPUT_SCHEMA_FIELD) is None:
            data.pop(OUTPUT_SCHEMA_FIELD, None)
        return data


def load_agent_config_v1(step: AgentWorkflowStep) -> dict[str, Any]:
    """Read an ``agent`` v1 config: the legacy step columns, plus the ``config`` column."""
    config: dict[str, Any] = {
        field: getattr(step, field)
        for field in AgentStepConfigV1.model_fields
        if field != OUTPUT_SCHEMA_FIELD
    }
    stored = getattr(step, "config", None)
    if isinstance(stored, dict) and stored.get(OUTPUT_SCHEMA_FIELD):
        config[OUTPUT_SCHEMA_FIELD] = stored[OUTPUT_SCHEMA_FIELD]
    return config


def store_agent_config_v1(config: dict[str, Any]) -> dict[str, Any]:
    """The step payload fields for an ``agent`` v1 config (same names)."""
    fields = AgentStepConfigV1.model_validate(config).model_dump()
    schema = fields.pop(OUTPUT_SCHEMA_FIELD, None)
    return {**fields, "config": {OUTPUT_SCHEMA_FIELD: schema}} if schema else fields


class UnusableStepAgentError(Exception):
    """A step's agent can't run workflow steps. The message completes "<step> ..."."""


def load_step_agent(db_session: Session, agent_id: int | None) -> Agent:
    """The agent a step runs, checked at save time and again at run time.

    Steps run dedicated agents. The default Assistant is excluded because admins
    change its tools and prompt globally for chat, which would silently change
    every workflow using it. A workflow's wrapper agent is excluded because it has
    no tools or prompt of its own: as a step it is an empty LLM call, not its
    workflow.

    Raises:
        UnusableStepAgentError: the agent is missing, deleted, or not dedicated.
    """
    agent = db_session.get(Agent, agent_id) if agent_id is not None else None
    if agent is None or agent.deleted:
        raise UnusableStepAgentError(
            f"uses agent {agent_id}, which was not found or deleted"
        )
    if agent.id == DEFAULT_AGENT_ID:
        raise UnusableStepAgentError(
            "uses the default Assistant; choose a dedicated agent"
        )
    if agent.workflow_id is not None:
        raise UnusableStepAgentError(
            "uses a workflow's own agent; choose a dedicated agent"
        )
    return agent


def prepare_agent_step_v1(
    step: WorkflowStepCreate, ctx: SaveContext
) -> WorkflowStepCreate:
    """The step must use a dedicated agent; settings stay in the legacy fields."""
    try:
        load_step_agent(ctx.db_session, step.agent_id)
    except UnusableStepAgentError as e:
        raise StepSaveError(f'"{step.step_name}" {e}') from e
    schema = (step.config or {}).get(OUTPUT_SCHEMA_FIELD)
    if not schema:
        return step.model_copy(update={"config": None})
    try:
        check_schema(schema)
    except ValueError as e:
        raise StepSaveError(f'"{step.step_name}": {e}') from e
    if step.can_request_input:
        raise StepSaveError(
            f'"{step.step_name}" can\'t both ask the user questions and have an '
            "expected output: a question isn't JSON"
        )
    if ctx.orchestration_mode != SEQUENTIAL_MODE:
        raise StepSaveError(
            f'"{step.step_name}" has an expected output, which only Sequential '
            "workflows support"
        )
    return step.model_copy(update={"config": {OUTPUT_SCHEMA_FIELD: schema}})


@dataclass(frozen=True)
class _AgentResult:
    """What an agent produced, parsed from its ToolResponse."""

    output: str
    file_ids: list[str]
    file_details: list[dict[str, Any]]


def _parse_agent_response(response: ToolResponse | None) -> _AgentResult:
    raw = response.llm_facing_response if response else ""
    try:
        data = json.loads(raw)
        return _AgentResult(
            output=data.get("agent_output", ""),
            file_ids=data.get("_file_ids", []),
            file_details=data.get("_file_details", []),
        )
    except (json.JSONDecodeError, AttributeError):
        return _AgentResult(output=raw or "", file_ids=[], file_details=[])


class AgentRunnerV1:
    """Runs an ``agent`` v1 node: stream the agent, then complete or pause."""

    def run(
        self, node: WorkflowNode, ctx: RunContext
    ) -> Generator[Packet, None, StepOutcome]:
        config = AgentStepConfigV1.model_validate(node.config)
        try:
            agent_tool = ctx.agent_tools.get(node, config)
        except UnusableStepAgentError as e:
            return StepOutcome(status=StepStatus.FAILED, error=f'"{node.name}" {e}')

        try:
            task_input = self._task_input(node, ctx)
        except UnresolvedReferenceError as e:
            return StepOutcome(status=StepStatus.FAILED, error=f'"{node.name}" {e}')

        state = ctx.state
        agent_name = agent_tool._agent.name
        step_start = time.monotonic()
        logger.info(
            "[Sequential] STEP START step=%d/%d name='%s' agent='%s' "
            "can_request_input=%s",
            node.step_order + 1,
            len(ctx.graph.nodes),
            node.name,
            agent_name,
            node.can_request_input,
        )

        placement = Placement(turn_index=state.turn.value)
        yield Packet(
            placement=placement,
            obj=WorkflowStepStart(
                step_name=node.name,
                agent_name=agent_name,
                step_order=node.step_order,
                promote_output=node.promote_output,
            ),
        )

        trace_node_id = self._trace_start(node, ctx, config, task_input)

        # A model that can't enforce the schema is told it in the task.
        agent_input = task_input
        if config.output_schema and not agent_tool.enforces_response_format:
            agent_input = f"{task_input}\n\n{format_instruction(config.output_schema)}"

        streaming = StreamingAgentResult(start_turn_index=state.turn.value)
        # HITL (can_request_input) steps: don't stream sub-agent prose/reasoning
        # live. Their output is a clarification (may carry the [NEEDS_INPUT]
        # marker) surfaced via the pause packet + main message, and reload shows
        # an empty step row — streaming would leak the raw marker / chain-of-
        # thought and diverge from the reloaded view.
        stream_step = not node.can_request_input
        yield from stream_agent_packets(
            agent_tool=agent_tool,
            placement=placement,
            emitter=ctx.emitter,
            result=streaming,
            is_connected=ctx.is_connected,
            stream_answer_as_step=stream_step,
            stream_reasoning_as_step=stream_step,
            task=agent_input,
        )

        if streaming.cancelled:
            # Close the open step so the frontend can show it as stopped
            yield from _close_step(node, placement)
            state.turn.observe(streaming.max_turn_index)
            state.turn.advance()
            return StepOutcome(status=StepStatus.CANCELLED)

        # Move past the turn indices the sub-agent used so the next step
        # doesn't collide with them.
        state.turn.observe(streaming.max_turn_index)
        result = _parse_agent_response(streaming.response)
        if result.file_details:
            state.context.shared_data.setdefault("step_files", {})[node.output_key] = {
                "file_ids": result.file_ids,
                "files": result.file_details,
            }

        output = result.output
        logger.info(
            "[Sequential] AGENT DONE step='%s' agent='%s' "
            "llm_time=%.2fs output_len=%d words=%d",
            node.name,
            agent_name,
            time.monotonic() - step_start,
            len(output),
            len(output.split()),
        )

        if node.can_request_input and agent_requests_input(output):
            yield from self._pause(
                node, ctx, placement, agent_name, task_input, output, trace_node_id
            )
            return StepOutcome(status=StepStatus.PAUSED, output=output)

        if config.output_schema:
            checked = yield from self._expected_output(
                node, ctx, placement, agent_tool, config.output_schema, agent_input,
                output, trace_node_id, step_start,
            )
            if isinstance(checked, StepOutcome):
                return checked
            output = checked

        yield from self._complete(
            node, ctx, placement, config, agent_name, task_input, output,
            trace_node_id, step_start,
        )
        status = StepStatus.TERMINAL if node.is_terminal else StepStatus.COMPLETED
        return StepOutcome(status=status, output=output)

    # ── Steps of the run ──────────────────────────────────────────────────

    def _expected_output(
        self,
        node: WorkflowNode,
        ctx: RunContext,
        placement: Placement,
        agent_tool: AgentTool,
        schema: dict[str, Any],
        task: str,
        reply: str,
        trace_node_id: str | None,
        step_start: float,
    ) -> Generator[Packet, None, str | StepOutcome]:
        """The reply as the declared JSON, asking the agent once more if it isn't."""
        try:
            return read_output(reply, schema)
        except OutputContractError as e:
            problem = str(e)
        logger.warning(
            "[Sequential] Step '%s': output doesn't match its schema (%s); retrying",
            node.name,
            problem,
        )

        state = ctx.state
        retry = StreamingAgentResult(start_turn_index=state.turn.value)
        yield from stream_agent_packets(
            agent_tool=agent_tool,
            placement=placement,
            emitter=ctx.emitter,
            result=retry,
            is_connected=ctx.is_connected,
            stream_answer_as_step=True,
            stream_reasoning_as_step=True,
            task=retry_task(task, reply, problem, schema),
        )
        if retry.cancelled:
            yield from _close_step(node, placement)
            state.turn.observe(retry.max_turn_index)
            state.turn.advance()
            return StepOutcome(status=StepStatus.CANCELLED)

        state.turn.observe(retry.max_turn_index)
        second = _parse_agent_response(retry.response).output
        try:
            return read_output(second, schema)
        except OutputContractError as e:
            message = (
                f'"{node.name}" (agent {agent_tool._agent.name}) didn\'t return its '
                f"expected output, even after a retry: {e}. It replied: "
                f"{second[:MAX_REPLY_IN_ERROR]}"
            )
        yield Packet(placement=placement, obj=WorkflowStepDelta(content=message, replace=True))
        yield from _close_step(node, placement)
        state.turn.advance()
        try:
            ctx.trace.finish_agent(
                trace_node_id,
                message,
                status="failed",
                duration_ms=int((time.monotonic() - step_start) * 1000),
            )
            ctx.persist_trace()
        except Exception:
            logger.debug("[Trace] finish_agent failed", exc_info=True)
        return StepOutcome(status=StepStatus.FAILED, error=message)

    @staticmethod
    def _task_input(node: WorkflowNode, ctx: RunContext) -> str:
        """The paused node resumes with its clarification task; others use the mapping."""
        resume = ctx.state.resume
        if resume and resume.task_override and resume.node_key == node.node_key:
            return resume.task_override
        if ctx.graph.schema_version < SAFE_REFERENCES_SCHEMA_VERSION:
            return apply_input_mapping(node.input_mapping, ctx.state.context)
        return apply_safe_input_mapping(
            node.input_mapping, ctx.state.context, ctx.reference_variables()
        )

    @staticmethod
    def _trace_start(
        node: WorkflowNode,
        ctx: RunContext,
        config: AgentStepConfigV1,
        task_input: str,
    ) -> str | None:
        """Open the agent node in the running state (best-effort)."""
        try:
            trace_node_id = ctx.trace.start_agent(
                step_id=node.step_id,
                name=node.name,
                agent_id=config.agent_id,
                input_text=task_input,
                file_names=ctx.trace_file_names,
            )
            ctx.persist_trace()
            return trace_node_id
        except Exception:
            logger.debug("[Trace] start_agent failed", exc_info=True)
            return None

    def _pause(
        self,
        node: WorkflowNode,
        ctx: RunContext,
        placement: Placement,
        agent_name: str,
        task_input: str,
        output: str,
        trace_node_id: str | None,
    ) -> Generator[Packet, None, None]:
        """Save a pause checkpoint and ask the user the agent's questions."""
        state = ctx.state
        logger.info(
            "[Sequential] PAUSE DETECTED step='%s' agent='%s' — "
            "agent is requesting user input, saving checkpoint",
            node.name,
            agent_name,
        )
        questions = strip_needs_input_prefix(output)
        resume = state.resume
        conversation = list(resume.conversation) if resume and resume.conversation else []
        conversation.append({"role": "agent", "content": questions})

        ctx.save_checkpoint(
            paused_node=node,
            paused_agent_original_task=(
                resume.original_task if resume and resume.original_task else task_input
            ),
            clarification_conversation=conversation,
        )
        ctx.persist_progress()

        # Trace: mark the agent paused + persist (per-message key) so this
        # turn's message resolves to a graph (best-effort).
        try:
            ctx.trace.finish_agent(trace_node_id, questions, status="paused")
            ctx.trace.finalize("paused", state.total_tokens, state.elapsed_ms())
            ctx.persist_trace(include_message_key=True)
            logger.info(
                "[Trace] SEQ-PAUSE step='%s' execution_id=%d",
                node.name,
                ctx.execution.id,
            )
        except Exception:
            logger.debug("[Trace] seq pause persist failed", exc_info=True)

        yield from _close_step(node, placement)
        # Pause packet with the questions (inside the timeline)...
        pause_placement = Placement(turn_index=state.turn.value + 1)
        yield Packet(
            placement=pause_placement,
            obj=WorkflowPauseForInput(
                step_name=node.name,
                agent_name=agent_name,
                questions=questions,
            ),
        )
        yield Packet(placement=pause_placement, obj=SectionEnd())
        # ...and the same questions as the main message, so the user sees them
        # prominently outside the timeline panel.
        message_placement = Placement(turn_index=state.turn.value + 2)
        yield Packet(placement=message_placement, obj=AgentResponseStart())
        yield Packet(
            placement=message_placement, obj=AgentResponseDelta(content=questions)
        )
        yield Packet(placement=message_placement, obj=SectionEnd())
        # The coordinator emits the final stop packet at the cursor.
        state.turn.advance(3)

    def _complete(
        self,
        node: WorkflowNode,
        ctx: RunContext,
        placement: Placement,
        config: AgentStepConfigV1,
        agent_name: str,
        task_input: str,
        output: str,
        trace_node_id: str | None,
        step_start: float,
    ) -> Generator[Packet, None, None]:
        """Emit the final output, record it, and optionally promote it."""
        state = ctx.state
        # The authoritative output reconciles (replace=True) any live-streamed
        # prose chunks. Empty output uses replace=False so it can't wipe
        # streamed content.
        yield Packet(
            placement=placement,
            obj=WorkflowStepDelta(content=output, replace=bool(output)),
        )
        # Step end comes BEFORE promote_output so no tool packet follows the
        # promoted message_start (which would reset finalAnswerComing in the
        # frontend).
        yield from _close_step(node, placement)

        state.context.current_step = node.name
        ctx.complete_node(node, output)

        duration_ms = int((time.monotonic() - step_start) * 1000)
        # Rough token estimate (no tokenizer on this path).
        tokens = len(task_input.split()) + len(output.split())
        state.total_tokens += tokens
        logger.info(
            "[Sequential] STEP DONE step=%d/%d name='%s' agent='%s' "
            "duration=%dms tokens=%d output_words=%d",
            node.step_order + 1,
            len(ctx.graph.nodes),
            node.name,
            agent_name,
            duration_ms,
            tokens,
            len(output.split()),
        )
        state.steps_executed.append({
            "step_id": node.step_id,
            "agent_id": config.agent_id,
            "step_name": node.name,
            "input_text": task_input[:500],  # Truncate for storage
            "output_text": output[:2000],
            "duration_ms": duration_ms,
            "tokens_used": tokens,
        })

        try:
            ctx.trace.finish_agent(
                trace_node_id,
                output,
                status="completed",
                duration_ms=duration_ms,
                tokens=tokens,
            )
            ctx.persist_trace()
        except Exception:
            logger.debug("[Trace] finish_agent failed", exc_info=True)

        # Output promotion: emit as MESSAGE packets so the frontend renders it
        # as main content outside the timeline.
        if node.promote_output and output:
            promoted = Placement(turn_index=state.turn.value + 1)
            yield Packet(placement=promoted, obj=AgentResponseStart())
            yield Packet(placement=promoted, obj=AgentResponseDelta(content=output))
            yield Packet(placement=promoted, obj=SectionEnd())
            state.turn.advance()

        # Advance past all indices used by this step
        state.turn.advance()


def _close_step(node: WorkflowNode, placement: Placement) -> Generator[Packet, None, None]:
    yield Packet(
        placement=placement,
        obj=WorkflowStepEnd(step_name=node.name, output_key=node.output_key),
    )
    yield Packet(placement=placement, obj=SectionEnd())

