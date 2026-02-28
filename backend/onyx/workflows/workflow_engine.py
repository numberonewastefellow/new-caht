"""Multi-Agent Workflow Engine.

Orchestrates multiple personas (agents) in sequence or via LLM-driven routing.
Mirrors the proven Deep Research pattern from dr_loop.py but generalized to
support any number of persona-based sub-agents.
"""

import json
import time
from collections.abc import Callable
from collections.abc import Generator
from queue import Empty
from typing import Any

from sqlalchemy.orm import Session

from onyx.chat.chat_state import ChatStateContainer
from onyx.chat.citation_processor import DynamicCitationProcessor
from onyx.chat.emitter import Emitter
from onyx.chat.llm_loop import construct_message_history
from onyx.chat.llm_step import run_llm_step
from onyx.chat.models import ChatMessageSimple
from onyx.configs.constants import MessageType
from onyx.db.models import AgentWorkflow
from onyx.db.models import AgentWorkflowStep
from onyx.db.models import Persona
from onyx.db.models import User
from onyx.db.workflow import create_workflow_execution
from onyx.db.workflow import update_workflow_execution
from onyx.db.llm import fetch_llm_provider_view
from onyx.llm.factory import get_default_llm
from onyx.llm.factory import get_llm_for_persona
from onyx.llm.factory import get_llm_token_counter
from onyx.llm.factory import llm_from_provider
from onyx.llm.interfaces import LLM
from onyx.llm.models import ToolChoiceOptions
from onyx.server.query_and_chat.placement import Placement
from onyx.server.query_and_chat.streaming_models import AgentResponseDelta
from onyx.server.query_and_chat.streaming_models import AgentResponseStart
from onyx.server.query_and_chat.streaming_models import OverallStop
from onyx.server.query_and_chat.streaming_models import Packet
from onyx.server.query_and_chat.streaming_models import SectionEnd
from onyx.server.query_and_chat.streaming_models import WorkflowOrchestratorThinking
from onyx.server.query_and_chat.streaming_models import WorkflowStepDelta
from onyx.server.query_and_chat.streaming_models import WorkflowStepEnd
from onyx.server.query_and_chat.streaming_models import WorkflowStepStart
from onyx.tools.tool_implementations.agent_tool import AgentTool
from onyx.tools.models import ToolResponse
from onyx.utils.logger import setup_logger
from onyx.utils.threadpool_concurrency import run_in_background
from onyx.utils.threadpool_concurrency import wait_on_background
from onyx.workflows.models import WorkflowContext

logger = setup_logger()

# Maximum words in agent output before truncation for orchestrator context.
# Full output is stored in context.step_outputs; the orchestrator only needs
# a summary to make routing decisions.  (Tier 2.1 — context summarization)
_ORCHESTRATOR_CONTEXT_MAX_WORDS = 250


def _summarize_for_orchestrator(agent_name: str, output: str) -> str:
    """Truncate agent output for the orchestrator's context window.

    The orchestrator only needs enough detail to decide the next step.
    Full output is preserved in context.step_outputs for downstream agents.
    """
    words = output.split()
    if len(words) <= _ORCHESTRATOR_CONTEXT_MAX_WORDS:
        return output
    truncated = " ".join(words[:_ORCHESTRATOR_CONTEXT_MAX_WORDS])
    return (
        f"[{agent_name}: {len(words)} words, showing first "
        f"{_ORCHESTRATOR_CONTEXT_MAX_WORDS}]\n{truncated}..."
    )


# Packet types emitted by run_llm_step that the workflow engine may need to
# suppress to avoid duplicate content in the frontend.
_ANSWER_SUPPRESS_TYPES = frozenset({
    "message_start", "message_delta", "message_end",
})
_REASONING_SUPPRESS_TYPES = frozenset({
    "reasoning_start", "reasoning_delta", "reasoning_done",
})
# For sub-agent streaming: suppress both answer text (engine yields its own
# WorkflowStepDelta) and reasoning (would collide with WorkflowStepStart group).
_AGENT_SUPPRESS_TYPES = _ANSWER_SUPPRESS_TYPES | _REASONING_SUPPRESS_TYPES


def _drain_emitter_to_list(
    emitter: Emitter,
    suppress_types: frozenset[str] | None = None,
) -> list[Packet]:
    """Non-blocking drain of all pending packets from the emitter queue.

    Returns the packets as a list so callers can inspect placement values
    (e.g. to track the max turn_index) before yielding.

    Args:
        emitter: The emitter whose bus to drain.
        suppress_types: If provided, packet types in this set are dropped
            to avoid duplicating content that the workflow engine yields
            separately (e.g. WorkflowStepDelta, WorkflowOrchestratorThinking).
    """
    packets: list[Packet] = []
    while True:
        try:
            packet = emitter.bus.get_nowait()
            if suppress_types and packet.obj.type in suppress_types:
                continue
            packets.append(packet)
        except Empty:
            break
    return packets


def _max_turn_index(packets: list[Packet], current_max: int) -> int:
    """Return the highest turn_index seen across packets and current_max."""
    for pkt in packets:
        if hasattr(pkt, "placement") and pkt.placement.turn_index > current_max:
            current_max = pkt.placement.turn_index
    return current_max


class _StreamingAgentResult:
    """Mutable container to capture ToolResponse + max turn_index from streaming."""

    def __init__(self, start_turn_index: int) -> None:
        self.response: ToolResponse | None = None
        self.exception: Exception | None = None
        self.max_turn_index: int = start_turn_index
        self.cancelled: bool = False


def _stream_agent_packets(
    agent_tool: AgentTool,
    placement: Placement,
    emitter: Emitter,
    result: _StreamingAgentResult,
    is_connected: Callable[[], bool] | None = None,
    suppress_types: frozenset[str] | None = _AGENT_SUPPRESS_TYPES,
    **agent_kwargs: Any,
) -> Generator[Packet, None, None]:
    """Run agent in a background thread, yielding emitter packets in real-time.

    This mirrors the pattern from run_chat_loop_with_state_containers: the
    agent runs in a background thread emitting packets to emitter.bus, while
    the main (generator) thread polls the bus every 50ms and yields each
    packet immediately to the SSE endpoint for real-time streaming.

    The ToolResponse and max_turn_index are stored in `result` for the caller.
    If is_connected returns False, sets result.cancelled and returns early.
    """

    def _run_agent() -> None:
        try:
            result.response = agent_tool.run(placement, None, **agent_kwargs)
        except Exception as e:
            result.exception = e

    thread = run_in_background(_run_agent)

    cancelled = False
    last_cancel_check = time.monotonic()

    # Poll emitter bus in real-time while agent runs in background
    while True:
        try:
            pkt = emitter.bus.get(timeout=0.05)
        except Empty:
            # Queue empty — check if thread has finished
            if not thread.is_alive():
                break
            # Check stop signal during idle polling
            if is_connected is not None and not is_connected():
                logger.info("Workflow agent cancelled by user")
                cancelled = True
                break
            last_cancel_check = time.monotonic()
            continue

        if suppress_types and pkt.obj.type in suppress_types:
            continue
        if pkt.placement.turn_index > result.max_turn_index:
            result.max_turn_index = pkt.placement.turn_index
        yield pkt

        # Check stop signal periodically even when packets are flowing,
        # matching the pattern from chat_state.py (lines 253-264).
        current_time = time.monotonic()
        if current_time - last_cancel_check >= 0.1:
            if is_connected is not None and not is_connected():
                logger.info("Workflow agent cancelled by user during streaming")
                cancelled = True
                break
            last_cancel_check = current_time

    if cancelled:
        # Don't wait for the background thread — exit fast like chat_state.py
        result.cancelled = True
        return

    # Drain any packets that arrived between the last get() and thread exit
    while True:
        try:
            pkt = emitter.bus.get_nowait()
            if suppress_types and pkt.obj.type in suppress_types:
                continue
            if pkt.placement.turn_index > result.max_turn_index:
                result.max_turn_index = pkt.placement.turn_index
            yield pkt
        except Empty:
            break

    # Propagate any exception from the agent thread
    wait_on_background(thread)
    if result.exception:
        raise result.exception


def _get_orchestrator_llm(
    workflow: AgentWorkflow,
    db_session: Session,
) -> LLM:
    """Get the LLM for the orchestrator based on workflow config."""
    if workflow.orchestrator_llm_provider and workflow.orchestrator_llm_model:
        provider_view = fetch_llm_provider_view(
            db_session=db_session,
            provider_name=workflow.orchestrator_llm_provider,
        )
        if provider_view is None:
            logger.warning(
                f"Orchestrator LLM provider '{workflow.orchestrator_llm_provider}' "
                f"not found, falling back to default"
            )
            return get_default_llm()
        return llm_from_provider(
            model_name=workflow.orchestrator_llm_model,
            llm_provider=provider_view,
        )
    return get_default_llm()


def _build_agent_tools(
    steps: list[AgentWorkflowStep],
    emitter: Emitter,
    db_session: Session,
    user: User | None = None,
) -> list[AgentTool]:
    """Build AgentTool instances for each workflow step's persona.

    Performance: pre-resolves user and caches LLM instances to avoid
    redundant DB lookups per agent call (Tier 1.5).
    Also checks persona.tools on the main thread to avoid lazy-loading
    in background agent threads (Tier 1.1).
    """
    agent_tools = []
    llm_cache: dict[int, LLM] = {}

    for step in steps:
        persona = step.persona if step.persona else db_session.get(Persona, step.persona_id)
        if persona is None or persona.deleted:
            logger.warning(
                f"Persona {step.persona_id} not found for workflow step {step.id}"
            )
            continue

        # Cache LLM per persona (avoids re-creating for same persona)
        if persona.id not in llm_cache:
            llm_cache[persona.id] = get_llm_for_persona(persona, user) if user else get_default_llm()

        # Check has_tools on main thread (eager-loaded, thread-safe)
        has_tools = bool(persona.tools)

        agent_tools.append(
            AgentTool(
                persona=persona,
                emitter=emitter,
                db_session=db_session,
                step_name=step.step_name,
                step_order=step.step_order,
                step_id=step.id,
                output_key=step.output_key,
                user=user,
                llm=llm_cache[persona.id],
                has_tools=has_tools,
            )
        )
    return agent_tools


def _build_orchestrator_system_prompt(
    workflow: AgentWorkflow,
    agent_tools: list[AgentTool],
) -> str:
    """Build the system prompt for the orchestrator LLM."""
    custom_prompt = workflow.orchestrator_prompt or ""

    agents_description = "\n".join(
        f"- **{tool.display_name}** (`{tool.name}`): {tool.description}"
        for tool in agent_tools
    )

    return f"""You are a workflow orchestrator that coordinates multiple AI agents to complete tasks.

Your job is to:
1. Analyze the user's request
2. Decide which agent(s) to delegate to and in what order
3. Provide clear, specific task descriptions when delegating
4. Synthesize the results into a final answer

Available agents:
{agents_description}

RULES:
- You MUST delegate to at least one agent before providing a final answer — never answer the user directly without consulting a specialist first
- Call ONE agent at a time with a clear, specific task description
- After receiving an agent's output, decide whether to call another agent or provide the final answer
- When you have enough information from the agents, synthesize their outputs into a concise final answer
- Do NOT ask the user clarifying questions — work with the information provided and make reasonable assumptions

{custom_prompt}"""


def _apply_input_mapping(
    mapping: dict[str, Any] | None,
    context: WorkflowContext,
) -> str:
    """Apply input mapping to resolve context references into a task string."""
    if not mapping:
        # Default: pass user input + all previous outputs
        parts = [f"User request: {context.user_input}"]
        for key, output in context.step_outputs.items():
            parts.append(f"\nOutput from '{key}':\n{output}")
        return "\n".join(parts)

    result_parts = []
    for key, template in mapping.items():
        if isinstance(template, str):
            # Replace $user_input with actual user input
            resolved = template.replace("$user_input", context.user_input)
            # Replace step output references — support both $key.output and $key
            # Do longer pattern first to avoid partial matches
            for output_key, output in context.step_outputs.items():
                resolved = resolved.replace(f"${output_key}.output", output)
            for output_key, output in context.step_outputs.items():
                resolved = resolved.replace(f"${output_key}", output)
            result_parts.append(f"{key}: {resolved}")
        else:
            result_parts.append(f"{key}: {template}")
    return "\n".join(result_parts)


def run_workflow_sequential(
    workflow: AgentWorkflow,
    user_message: str,
    emitter: Emitter,
    db_session: Session,
    user: User,
    is_connected: Callable[[], bool] | None = None,
) -> Generator[Packet, None, None]:
    """Run a workflow in sequential mode — fixed order, no LLM routing.

    Each step's output becomes the next step's input.
    """
    context = WorkflowContext(user_input=user_message)
    steps = sorted(workflow.steps, key=lambda s: s.step_order)
    execution = create_workflow_execution(
        db_session, workflow.id, user.id
    )

    steps_executed = []
    total_tokens = 0
    start_time = time.monotonic()
    turn_index = 0  # Running counter — incremented based on drained packet turn_indices
    cancelled = False

    # Pre-build agent tools with cached LLMs + user (Tier 1.5 performance)
    agent_tools_by_step: dict[int, AgentTool] = {}
    llm_cache: dict[int, LLM] = {}
    for step in steps:
        persona = step.persona if step.persona else db_session.get(Persona, step.persona_id)
        if persona is None or persona.deleted:
            continue
        if persona.id not in llm_cache:
            llm_cache[persona.id] = get_llm_for_persona(persona, user)
        has_tools = bool(persona.tools)
        agent_tools_by_step[step.id] = AgentTool(
            persona=persona,
            emitter=emitter,
            db_session=db_session,
            step_name=step.step_name,
            step_order=step.step_order,
            step_id=step.id,
            output_key=step.output_key,
            user=user,
            llm=llm_cache[persona.id],
            has_tools=has_tools,
        )

    try:
        for step in steps:
            # Check stop signal before starting each step
            if is_connected is not None and not is_connected():
                logger.info("Workflow cancelled by user before step %s", step.step_name)
                cancelled = True
                break

            agent_tool = agent_tools_by_step.get(step.id)
            if agent_tool is None:
                logger.warning(f"Skipping step {step.step_name}: no agent tool")
                continue

            step_start_time = time.monotonic()
            persona = agent_tool._persona

            placement = Placement(turn_index=turn_index)

            # Emit step start
            yield Packet(
                placement=placement,
                obj=WorkflowStepStart(
                    step_name=step.step_name,
                    persona_name=persona.name,
                    step_order=step.step_order,
                ),
            )

            # Build the task input from context
            task_input = _apply_input_mapping(step.input_mapping, context)

            streaming_result = _StreamingAgentResult(start_turn_index=turn_index)
            yield from _stream_agent_packets(
                agent_tool=agent_tool,
                placement=placement,
                emitter=emitter,
                result=streaming_result,
                is_connected=is_connected,
                task=task_input,
            )

            # Check if agent was cancelled mid-execution
            if streaming_result.cancelled:
                # Close the open step so the frontend can show it as stopped
                yield Packet(
                    placement=placement,
                    obj=WorkflowStepEnd(
                        step_name=step.step_name,
                        output_key=step.output_key,
                    ),
                )
                yield Packet(placement=placement, obj=SectionEnd())
                cancelled = True
                turn_index = streaming_result.max_turn_index + 1
                break

            result = streaming_result.response
            # Track the highest turn_index from streamed packets so the next
            # step doesn't collide with internal agent turn_indices.
            turn_index = streaming_result.max_turn_index

            # Extract output from result
            try:
                result_data = json.loads(
                    result.llm_facing_response if result else ""
                )
                agent_output = result_data.get("agent_output", "")
            except (json.JSONDecodeError, AttributeError):
                agent_output = (
                    result.llm_facing_response if result else ""
                ) or ""

            # Yield the agent output as a WorkflowStepDelta (C1 fix)
            yield Packet(
                placement=placement,
                obj=WorkflowStepDelta(content=agent_output),
            )

            # Store output in context
            context.step_outputs[step.output_key] = agent_output
            context.current_step = step.step_name

            step_duration_ms = int((time.monotonic() - step_start_time) * 1000)

            # Estimate token usage (M1 fix)
            step_tokens = len(task_input.split()) + len(agent_output.split())
            total_tokens += step_tokens

            steps_executed.append({
                "step_id": step.id,
                "persona_id": step.persona_id,
                "step_name": step.step_name,
                "input_text": task_input[:500],  # Truncate for storage
                "output_text": agent_output[:2000],
                "duration_ms": step_duration_ms,
                "tokens_used": step_tokens,
            })

            # Emit step end
            yield Packet(
                placement=placement,
                obj=WorkflowStepEnd(
                    step_name=step.step_name,
                    output_key=step.output_key,
                ),
            )
            yield Packet(placement=placement, obj=SectionEnd())

            # Advance turn_index past all indices used by this step
            turn_index += 1

            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed > workflow.timeout_seconds:
                logger.warning(f"Workflow timeout after {elapsed:.1f}s")
                break

            if step.is_terminal:
                break

        total_duration_ms = int((time.monotonic() - start_time) * 1000)
        update_workflow_execution(
            db_session,
            execution.id,
            status="cancelled" if cancelled else "completed",
            steps_executed=steps_executed,
            total_tokens=total_tokens,
            total_duration_ms=total_duration_ms,
        )

    except Exception as e:
        logger.exception("Workflow execution failed")
        total_duration_ms = int((time.monotonic() - start_time) * 1000)
        update_workflow_execution(
            db_session,
            execution.id,
            status="failed",
            steps_executed=steps_executed,
            total_tokens=total_tokens,
            total_duration_ms=total_duration_ms,
            error_message=str(e),
        )
        raise

    # Emit overall stop
    yield Packet(
        placement=Placement(turn_index=turn_index),
        obj=OverallStop(
            type="stop",
            stop_reason="user_cancelled" if cancelled else None,
        ),
    )


def run_workflow_llm_decision(
    workflow: AgentWorkflow,
    user_message: str,
    emitter: Emitter,
    db_session: Session,
    user: User,
    is_connected: Callable[[], bool] | None = None,
) -> Generator[Packet, None, None]:
    """Run a workflow in LLM-decision mode — orchestrator LLM decides which agent to call.

    Mirrors the Deep Research dr_loop.py pattern:
    - Orchestrator LLM sees all agents as callable tools
    - Decides which agent to call and with what task
    - Collects results and decides next step
    - Generates final answer when done
    """
    context = WorkflowContext(user_input=user_message)
    steps = sorted(workflow.steps, key=lambda s: s.step_order)
    execution = create_workflow_execution(
        db_session, workflow.id, user.id
    )

    # Build agent tools (with cached LLMs + user — Tier 1.5)
    agent_tools = _build_agent_tools(steps, emitter, db_session, user=user)
    if not agent_tools:
        raise ValueError("No valid agent tools found for workflow")

    # Get orchestrator LLM
    orchestrator_llm = _get_orchestrator_llm(workflow, db_session)
    token_counter = get_llm_token_counter(orchestrator_llm)

    # Build orchestrator system prompt
    system_prompt_text = _build_orchestrator_system_prompt(workflow, agent_tools)
    system_prompt = ChatMessageSimple(
        message=system_prompt_text,
        token_count=token_counter(system_prompt_text),
        message_type=MessageType.SYSTEM,
    )

    # Pre-compute tool definitions once (they don't change — Tier 1.2)
    tool_defs = [tool.tool_definition() for tool in agent_tools]

    # Initial user message
    user_msg = ChatMessageSimple(
        message=user_message,
        token_count=token_counter(user_message),
        message_type=MessageType.USER,
    )
    msg_history: list[ChatMessageSimple] = [user_msg]

    steps_executed = []
    total_tokens = 0
    start_time = time.monotonic()
    tools_by_name = {tool.name: tool for tool in agent_tools}
    state_container = ChatStateContainer()
    turn_index = 0
    agent_call_counts: dict[str, int] = {}  # prevent calling same agent too many times
    max_calls_per_agent = workflow.max_calls_per_agent
    cancelled = False
    final_answer_emitted = False

    try:
        for cycle in range(workflow.max_steps):
            # Check stop signal at the start of each orchestrator cycle
            if is_connected is not None and not is_connected():
                logger.info("Workflow orchestrator cancelled by user at cycle %d", cycle)
                cancelled = True
                break

            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed > workflow.timeout_seconds:
                logger.warning(
                    f"Workflow orchestrator timeout after {elapsed:.1f}s"
                )
                break

            placement = Placement(turn_index=turn_index)

            # Build message history for orchestrator
            truncated_history = construct_message_history(
                system_prompt=system_prompt,
                custom_agent_prompt=None,
                simple_chat_history=msg_history,
                reminder_message=None,
                project_files=None,
                available_tokens=orchestrator_llm.config.max_input_tokens,
            )

            # Filter tool_defs to exclude agents that have reached their call
            # limit. This prevents the model from repeatedly selecting a blocked
            # agent (which smaller models are prone to doing even when given an
            # error message in the conversation).
            if max_calls_per_agent:
                available_defs = [
                    td for td in tool_defs
                    if agent_call_counts.get(td["function"]["name"], 0) < max_calls_per_agent
                ]
            else:
                available_defs = tool_defs

            tool_choice = ToolChoiceOptions.AUTO
            citation_processor = DynamicCitationProcessor()

            llm_step_result, has_reasoned = run_llm_step(
                emitter=emitter,
                history=truncated_history,
                tool_definitions=available_defs,
                tool_choice=tool_choice,
                llm=orchestrator_llm,
                placement=placement,
                citation_processor=citation_processor,
                state_container=state_container,
                final_documents=None,
                user_identity=None,
            )

            # Drain emitter: captures orchestrator reasoning/thinking packets.
            # Suppress answer types — the engine yields them separately as
            # WorkflowOrchestratorThinking or explicit AgentResponseStart/Delta.
            orchestrator_drained = _drain_emitter_to_list(
                emitter, suppress_types=_AGENT_SUPPRESS_TYPES
            )
            yield from orchestrator_drained
            turn_index = _max_turn_index(orchestrator_drained, turn_index)

            if has_reasoned:
                turn_index += 1

            # Debug: log orchestrator decision for each cycle
            logger.info(
                "Workflow orchestrator cycle %d: answer=%s, tool_calls=%s, "
                "has_reasoned=%s, drained=%d packets",
                cycle,
                repr(llm_step_result.answer[:200] if llm_step_result.answer else None),
                [tc.tool_name for tc in llm_step_result.tool_calls] if llm_step_result.tool_calls else None,
                has_reasoned,
                len(orchestrator_drained),
            )

            # If orchestrator produced a final answer (no tool calls)
            if llm_step_result.answer and not llm_step_result.tool_calls:
                # Yield the final synthesis answer so the frontend can display it
                final_placement = Placement(turn_index=turn_index)
                yield Packet(
                    placement=final_placement,
                    obj=AgentResponseStart(),
                )
                yield Packet(
                    placement=final_placement,
                    obj=AgentResponseDelta(content=llm_step_result.answer),
                )
                yield Packet(placement=final_placement, obj=SectionEnd())
                turn_index += 1
                final_answer_emitted = True
                break

            # Emit orchestrator thinking if there's text alongside tool calls (H1)
            # Use current turn_index (after reasoning increment) to avoid
            # grouping with reasoning packets from the drain.
            if llm_step_result.answer and llm_step_result.tool_calls:
                orch_placement = Placement(turn_index=turn_index)
                yield Packet(
                    placement=orch_placement,
                    obj=WorkflowOrchestratorThinking(
                        content=llm_step_result.answer,
                    ),
                )
                yield Packet(placement=orch_placement, obj=SectionEnd())
                turn_index += 1

            # Process tool calls (agent delegations)
            if llm_step_result.tool_calls:
                for tool_call in llm_step_result.tool_calls:
                    # Check stop signal before each agent delegation
                    if is_connected is not None and not is_connected():
                        logger.info("Workflow cancelled before agent %s", tool_call.tool_name)
                        cancelled = True
                        break

                    agent_tool = tools_by_name.get(tool_call.tool_name)
                    if agent_tool is None:
                        logger.warning(
                            f"Unknown agent tool: {tool_call.tool_name}"
                        )
                        continue

                    # Guard: prevent calling the same agent too many times
                    call_count = agent_call_counts.get(tool_call.tool_name, 0)
                    if call_count >= max_calls_per_agent:
                        logger.warning(
                            f"Agent '{tool_call.tool_name}' already called "
                            f"{call_count} times, skipping"
                        )
                        # Tell the orchestrator to use a different agent
                        refuse_msg = ChatMessageSimple(
                            message=json.dumps({
                                "tool_call_id": tool_call.tool_call_id,
                                "name": tool_call.tool_name,
                                "arguments": tool_call.tool_args,
                            }),
                            token_count=50,
                            message_type=MessageType.ASSISTANT,
                        )
                        msg_history.append(refuse_msg)
                        error_response = (
                            f"ERROR: Agent '{agent_tool.display_name}' has "
                            f"already been called {call_count} times. "
                            f"Do NOT call this agent again. "
                            f"Use a DIFFERENT agent or provide the final answer."
                        )
                        msg_history.append(ChatMessageSimple(
                            message=error_response,
                            token_count=token_counter(error_response),
                            message_type=MessageType.TOOL_CALL_RESPONSE,
                        ))
                        continue
                    agent_call_counts[tool_call.tool_name] = call_count + 1

                    step_start_time = time.monotonic()
                    turn_index += 1
                    agent_placement = Placement(turn_index=turn_index)

                    # Yield WorkflowStepStart directly (C1 fix — don't rely on emitter bus)
                    yield Packet(
                        placement=agent_placement,
                        obj=WorkflowStepStart(
                            step_name=agent_tool._step_name,
                            persona_name=agent_tool._persona.name,
                            step_order=agent_tool._step_order,
                        ),
                    )

                    # Run the agent with real-time streaming
                    streaming_result = _StreamingAgentResult(
                        start_turn_index=turn_index
                    )
                    yield from _stream_agent_packets(
                        agent_tool=agent_tool,
                        placement=agent_placement,
                        emitter=emitter,
                        result=streaming_result,
                        is_connected=is_connected,
                        **tool_call.tool_args,
                    )

                    # Check if agent was cancelled mid-execution
                    if streaming_result.cancelled:
                        # Close the open step so the frontend shows it as stopped
                        yield Packet(
                            placement=agent_placement,
                            obj=WorkflowStepEnd(
                                step_name=agent_tool.display_name,
                                output_key=agent_tool.output_key,
                            ),
                        )
                        yield Packet(placement=agent_placement, obj=SectionEnd())
                        cancelled = True
                        turn_index = streaming_result.max_turn_index + 1
                        break

                    result = streaming_result.response
                    turn_index = streaming_result.max_turn_index

                    # Extract output
                    try:
                        result_data = json.loads(
                            result.llm_facing_response if result else ""
                        )
                        agent_output = result_data.get("agent_output", "")
                    except (json.JSONDecodeError, AttributeError):
                        agent_output = (
                            result.llm_facing_response if result else ""
                        ) or ""

                    # Yield the agent output as a WorkflowStepDelta (C1 fix)
                    yield Packet(
                        placement=agent_placement,
                        obj=WorkflowStepDelta(content=agent_output),
                    )

                    # Store in context using output_key (M2 fix)
                    context.step_outputs[agent_tool.output_key] = agent_output

                    task_input = json.dumps(tool_call.tool_args)
                    step_tokens = token_counter(task_input) + token_counter(agent_output)
                    total_tokens += step_tokens

                    step_duration_ms = int(
                        (time.monotonic() - step_start_time) * 1000
                    )
                    steps_executed.append({
                        "step_id": agent_tool.step_id,
                        "persona_id": agent_tool.id,
                        "step_name": agent_tool.display_name,
                        "input_text": task_input[:500],
                        "output_text": agent_output[:2000],
                        "duration_ms": step_duration_ms,
                        "tokens_used": step_tokens,
                    })

                    # Add tool result to orchestrator history
                    tool_call_msg = ChatMessageSimple(
                        message=json.dumps({
                            "tool_call_id": tool_call.tool_call_id,
                            "name": tool_call.tool_name,
                            "arguments": tool_call.tool_args,
                        }),
                        token_count=50,
                        message_type=MessageType.ASSISTANT,
                    )
                    msg_history.append(tool_call_msg)

                    # Summarize agent output for orchestrator context (Tier 2.1)
                    # Full output is in context.step_outputs for downstream agents.
                    summarized = _summarize_for_orchestrator(
                        agent_tool.display_name,
                        result.llm_facing_response or "",
                    )
                    tool_response_msg = ChatMessageSimple(
                        message=summarized,
                        token_count=token_counter(summarized),
                        message_type=MessageType.TOOL_CALL_RESPONSE,
                    )
                    msg_history.append(tool_response_msg)

                    yield Packet(
                        placement=agent_placement,
                        obj=WorkflowStepEnd(
                            step_name=agent_tool.display_name,
                            output_key=agent_tool.output_key,
                        ),
                    )
                    yield Packet(placement=agent_placement, obj=SectionEnd())

                if cancelled:
                    break
                turn_index += 1
            else:
                # No answer and no tool calls — unusual, break
                logger.warning("Orchestrator produced no answer and no tool calls")
                break

        total_duration_ms = int((time.monotonic() - start_time) * 1000)
        update_workflow_execution(
            db_session,
            execution.id,
            status="cancelled" if cancelled else "completed",
            steps_executed=steps_executed,
            total_tokens=total_tokens,
            total_duration_ms=total_duration_ms,
        )

    except Exception as e:
        logger.exception("Workflow LLM-decision execution failed")
        total_duration_ms = int((time.monotonic() - start_time) * 1000)
        update_workflow_execution(
            db_session,
            execution.id,
            status="failed",
            steps_executed=steps_executed,
            total_tokens=total_tokens,
            total_duration_ms=total_duration_ms,
            error_message=str(e),
        )
        raise

    # Fallback: if the orchestrator loop ended without producing a final
    # answer (e.g. max_steps exhausted, timeout, or model kept calling
    # blocked agents), synthesize a basic answer from available outputs
    # so the user isn't left with nothing.
    if not cancelled and not final_answer_emitted and context.step_outputs:
        logger.info(
            "Workflow loop ended without final answer; "
            "emitting fallback from %d agent output(s)",
            len(context.step_outputs),
        )
        fallback_parts = []
        for key, output in context.step_outputs.items():
            fallback_parts.append(f"**{key}**:\n{output}")
        fallback_text = "\n\n---\n\n".join(fallback_parts)

        fallback_placement = Placement(turn_index=turn_index)
        yield Packet(
            placement=fallback_placement,
            obj=AgentResponseStart(),
        )
        yield Packet(
            placement=fallback_placement,
            obj=AgentResponseDelta(content=fallback_text),
        )
        yield Packet(placement=fallback_placement, obj=SectionEnd())
        turn_index += 1

    # Emit overall stop
    yield Packet(
        placement=Placement(turn_index=turn_index + 1),
        obj=OverallStop(
            type="stop",
            stop_reason="user_cancelled" if cancelled else None,
        ),
    )


def run_workflow(
    workflow: AgentWorkflow,
    user_message: str,
    emitter: Emitter,
    db_session: Session,
    user: User,
    is_connected: Callable[[], bool] | None = None,
) -> Generator[Packet, None, None]:
    """Main entry point — dispatches to the appropriate orchestration mode."""
    mode = workflow.orchestration_mode

    if mode == "sequential":
        yield from run_workflow_sequential(
            workflow, user_message, emitter, db_session, user,
            is_connected=is_connected,
        )
    elif mode == "llm_decision":
        yield from run_workflow_llm_decision(
            workflow, user_message, emitter, db_session, user,
            is_connected=is_connected,
        )
    else:
        raise ValueError(f"Unsupported orchestration mode: {mode}")
