"""Multi-Agent Workflow Engine.

Orchestrates multiple agents (agents) in sequence or via LLM-driven routing.
Mirrors the proven Deep Research pattern from dr_loop.py but generalized to
support any number of agent-based sub-agents.
"""

import datetime
import json
import time
from collections.abc import Callable
from collections.abc import Generator
from queue import Empty
from uuid import UUID

from sqlalchemy.orm import Session

from om.chat.chat_state import ChatStateContainer
from om.chat.citation_processor import DynamicCitationProcessor
from om.chat.emitter import Emitter
from om.chat.llm_loop import construct_message_history
from om.chat.llm_step import run_llm_step
from om.chat.models import ChatMessageSimple
from om.configs.app_configs import WORKFLOW_ENGINE_V2
from om.configs.constants import MessageType
from om.db.models import AgentWorkflow
from om.db.models import AgentWorkflowStep
from om.db.models import Agent
from om.db.models import User
from om.db.models import WorkflowExecution
from om.db.workflow import create_workflow_execution
from om.workflows.trace_models import load_workflow_trace
from om.workflows.trace_models import persist_workflow_trace
from om.workflows.trace_models import WorkflowTraceBuilder
from om.db.workflow import get_paused_execution
from om.db.workflow import load_checkpoint
from om.db.workflow import save_checkpoint
from om.db.workflow import update_workflow_execution
from om.db.llm import fetch_llm_provider_view
from om.llm.factory import get_default_llm
from om.llm.factory import get_llm_for_agent
from om.llm.factory import get_llm_token_counter
from om.llm.factory import llm_from_provider
from om.llm.interfaces import LLM
from om.llm.models import ToolChoiceOptions
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import AgentResponseDelta
from om.server.query_and_chat.streaming_models import AgentResponseStart
from om.server.query_and_chat.streaming_models import OverallStop
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import SectionEnd
from om.server.query_and_chat.streaming_models import WorkflowOrchestratorThinking
from om.server.query_and_chat.streaming_models import WorkflowStepDelta
from om.server.query_and_chat.streaming_models import WorkflowStepEnd
from om.server.query_and_chat.streaming_models import WorkflowPauseForInput
from om.server.query_and_chat.streaming_models import WorkflowStepStart
from om.tools.tool_implementations.agent_tool import AgentTool
from om.tools.models import ChatFile
from om.utils.logger import setup_logger
from om.workflows.agent_streaming import AGENT_SUPPRESS_TYPES as _AGENT_SUPPRESS_TYPES
from om.workflows.agent_streaming import stream_agent_packets as _stream_agent_packets
from om.workflows.agent_streaming import StreamingAgentResult as _StreamingAgentResult
from om.workflows.hitl import agent_requests_input as _agent_requests_input
from om.workflows.hitl import build_clarification_task as _build_clarification_task
from om.workflows.hitl import strip_needs_input_prefix as _strip_needs_input_prefix
from om.workflows.inputs import apply_input_mapping as _apply_input_mapping
from om.workflows.inputs import collect_workflow_files as _collect_workflow_files
from om.workflows.graph import graph_from_workflow
from om.workflows.models import WorkflowCheckpoint
from om.workflows.models import WorkflowContext
from om.workflows.nodes.agent import load_step_agent
from om.workflows.nodes.agent import UnusableStepAgentError
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.orchestrator_history import agent_call
from om.workflows.orchestrator_history import agent_result
from om.workflows.orchestrator_history import restore_history
from om.workflows.orchestrator_history import serialize_history
from om.workflows.sequential import run_workflow_sequential_v2
from om.workflows.step_runners.conditional_router import evaluate_condition
from om.workflows.versioning import pin_workflow_version

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
    chat_files: list[ChatFile] | None = None,
    sandbox_session_id: str | None = None,
) -> list[AgentTool]:
    """Build AgentTool instances for each workflow step's agent.

    Performance: pre-resolves user and caches LLM instances to avoid
    redundant DB lookups per agent call (Tier 1.5).
    Also checks agent.tools on the main thread to avoid lazy-loading
    in background agent threads (Tier 1.1).
    """
    agent_tools = []
    llm_cache: dict[str, LLM] = {}

    for step in steps:
        try:
            agent = load_step_agent(db_session, step.agent_id)
        except UnusableStepAgentError as e:
            logger.warning(f"Not offering workflow step {step.id}: it {e}")
            continue

        # Resolve effective LLM: step override > agent override > default
        effective_provider = step.llm_provider_override or agent.llm_model_provider_override
        effective_model = step.llm_model_override or agent.llm_model_version_override

        # Cache LLM per (provider, model) pair
        llm_key = f"{effective_provider}:{effective_model}"
        if llm_key not in llm_cache:
            if step.llm_provider_override and user:
                # Step has its own LLM override — build a temporary agent-like
                # object isn't needed; just override via LLMOverride
                from om.llm.override_models import LLMOverride

                llm_cache[llm_key] = get_llm_for_agent(
                    agent,
                    user,
                    llm_override=LLMOverride(
                        model_provider=step.llm_provider_override,
                        model_version=step.llm_model_override,
                    ),
                )
            elif user:
                llm_cache[llm_key] = get_llm_for_agent(agent, user)
            else:
                llm_cache[llm_key] = get_default_llm()

        # Check has_tools on main thread (eager-loaded, thread-safe)
        # If tool_ids_override is set, override the has_tools check
        has_tools = (
            bool(step.tool_ids_override)
            if step.tool_ids_override is not None
            else bool(agent.tools)
        )

        agent_tools.append(
            AgentTool(
                agent=agent,
                emitter=emitter,
                db_session=db_session,
                step_name=step.step_name,
                step_order=step.step_order,
                step_id=step.id,
                output_key=step.output_key,
                user=user,
                llm=llm_cache[llm_key],
                has_tools=has_tools,
                promote_output=step.promote_output,
                chat_files=chat_files,
                sandbox_session_id=sandbox_session_id,
                # Step-level overrides (applied in AgentTool.run())
                max_output_tokens_override=step.max_output_tokens_override,
                system_prompt_override=step.system_prompt_override,
                task_prompt_override=step.task_prompt_override,
                tool_ids_override=step.tool_ids_override,
                document_set_ids_override=step.document_set_ids_override,
                replace_base_system_prompt_override=step.replace_base_system_prompt_override,
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
- Follow the custom instructions below carefully — they specify which agents to call and in what order
- Do NOT provide a final answer until you have called all agents specified in the custom instructions
- If the custom instructions specify a sequence of agents, you MUST call EVERY agent in that sequence before providing a final answer
- Do NOT ask the user clarifying questions — work with the information provided and make reasonable assumptions

{custom_prompt}"""


def run_workflow_sequential(
    workflow: AgentWorkflow,
    user_message: str,
    emitter: Emitter,
    db_session: Session,
    user: User,
    is_connected: Callable[[], bool] | None = None,
    chat_session_id: UUID | None = None,
    paused_execution: WorkflowExecution | None = None,
    chat_files: list[ChatFile] | None = None,
    sandbox_session_id: str | None = None,
    assistant_message_id: int | None = None,
) -> Generator[Packet, None, None]:
    """Run a workflow in sequential mode — fixed order, no LLM routing.

    Each step's output becomes the next step's input.
    Supports pause/resume via checkpoints (human-in-the-loop).

    Legacy engine, used only when WORKFLOW_ENGINE_V2 is off; the default is
    the node-registry coordinator in om/workflows/sequential.py. Kept for one
    release as a fallback, then removed.
    """
    steps = sorted(workflow.steps, key=lambda s: s.step_order)
    completed_step_ids: set[int] = set()

    logger.info(
        "[Sequential] Starting with %d steps, resume=%s",
        len(steps),
        paused_execution is not None,
    )

    # Variables for conversation-aware resume (accessible in step loop)
    resume_task_override: str | None = None
    resume_conversation: list[dict[str, str]] | None = None
    paused_step_id: int | None = None
    checkpoint: WorkflowCheckpoint | None = None

    # Resume from paused execution or start fresh
    if paused_execution:
        paused_step_id = paused_execution.paused_at_step_id
        checkpoint = load_checkpoint(paused_execution)
        if checkpoint:
            original_input = checkpoint.shared_data.get(
                "_original_user_input", user_message
            )

            # Enterprise conversation-aware resume
            if (
                checkpoint.clarification_conversation
                and checkpoint.paused_agent_original_task
            ):
                conversation = list(checkpoint.clarification_conversation)
                conversation.append({"role": "user", "content": user_message})

                resume_task_override = _build_clarification_task(
                    checkpoint.paused_agent_original_task,
                    conversation,
                )
                resume_conversation = conversation

                context = WorkflowContext(
                    user_input=original_input,
                    step_outputs=checkpoint.step_outputs,
                    shared_data=checkpoint.shared_data,
                )
                logger.info(
                    "[Sequential] CONVERSATION-AWARE RESUME "
                    "clarification_rounds=%d",
                    len(conversation),
                )
            else:
                # Fallback for old checkpoints: flat-string approach
                prev_clarifications: list[str] = list(
                    checkpoint.shared_data.get("_clarifications", [])
                )
                prev_clarifications.append(user_message)
                all_user_inputs = [original_input] + prev_clarifications
                full_context = "\n".join(
                    f"- {inp}" for inp in all_user_inputs
                )
                context = WorkflowContext(
                    user_input=(
                        f"Everything the user has said:\n{full_context}"
                    ),
                    step_outputs=checkpoint.step_outputs,
                    shared_data={
                        **checkpoint.shared_data,
                        "_clarifications": prev_clarifications,
                    },
                )
                logger.info(
                    "[Sequential] FALLBACK RESUME (no clarification "
                    "conversation in checkpoint)"
                )

            completed_step_ids = set(checkpoint.completed_step_ids)
            turn_index = checkpoint.turn_index
            execution = paused_execution
            execution.status = "running"
            execution.paused_at_step_id = None
            db_session.commit()
            steps_executed = list(execution.steps_executed or [])
            logger.info(
                "[Sequential] Resumed execution_id=%d, completed_steps=%s, "
                "step_outputs_keys=%s direct_resume=%s",
                execution.id,
                list(completed_step_ids),
                list(checkpoint.step_outputs.keys()),
                resume_task_override is not None,
            )
        else:
            # Checkpoint corrupted — mark old execution as failed
            logger.warning(
                "[Sequential] Checkpoint corrupted for execution_id=%d, "
                "starting fresh",
                paused_execution.id,
            )
            paused_execution.status = "failed"
            paused_execution.error_message = "Checkpoint data corrupted"
            paused_execution.completed_at = datetime.datetime.now(
                datetime.timezone.utc
            )
            db_session.commit()
            context = WorkflowContext(user_input=user_message)
            execution = create_workflow_execution(
                db_session, workflow.id, user.id, chat_session_id
            )
            steps_executed = []
            turn_index = 0
    else:
        context = WorkflowContext(user_input=user_message)
        execution = create_workflow_execution(
            db_session, workflow.id, user.id, chat_session_id
        )
        steps_executed = []
        turn_index = 0

    total_tokens = 0
    start_time = time.monotonic()
    cancelled = False

    # Trace graph (best-effort; never breaks a run). Same builder as
    # llm_decision — sequential has no orchestrator, so decisions show up as
    # conditional_router nodes instead.
    _trace_file_names = [f.filename for f in (chat_files or [])]
    trace_builder = WorkflowTraceBuilder(
        execution.id,
        workflow.id,
        workflow.name,
        str(chat_session_id) if chat_session_id else None,
        mode="sequential",
        message_id=assistant_message_id,
    )
    try:
        if paused_execution:
            _prior_trace = load_workflow_trace(execution.id)
            if _prior_trace:
                trace_builder.restore(_prior_trace)
        else:
            trace_builder.set_start(user_message, _trace_file_names)
    except Exception:
        logger.debug("[Trace] sequential init failed", exc_info=True)

    # Pre-build agent tools with cached LLMs + user (Tier 1.5 performance)
    # Skip non-agent steps (e.g. conditional_router has no agent)
    agent_tools_by_step: dict[int, AgentTool] = {}
    llm_cache: dict[int, LLM] = {}
    skip_step_orders: set[int] = set()  # Branch-skip for conditional router
    for step in steps:
        if step.step_type == "conditional_router":
            continue
        if step.agent_id is None:
            continue
        agent = step.agent if step.agent else db_session.get(Agent, step.agent_id)
        if agent is None or agent.deleted:
            continue
        if agent.id not in llm_cache:
            llm_cache[agent.id] = get_llm_for_agent(agent, user)
        has_tools = bool(agent.tools)
        agent_tools_by_step[step.id] = AgentTool(
            agent=agent,
            emitter=emitter,
            db_session=db_session,
            step_name=step.step_name,
            step_order=step.step_order,
            step_id=step.id,
            output_key=step.output_key,
            user=user,
            llm=llm_cache[agent.id],
            has_tools=has_tools,
            promote_output=step.promote_output,
            chat_files=chat_files,
            sandbox_session_id=sandbox_session_id,
            max_output_tokens_override=step.max_output_tokens_override,
            system_prompt_override=step.system_prompt_override,
            task_prompt_override=step.task_prompt_override,
            tool_ids_override=step.tool_ids_override,
            document_set_ids_override=step.document_set_ids_override,
            replace_base_system_prompt_override=step.replace_base_system_prompt_override,
        )

    try:
        for step in steps:
            # Check stop signal before starting each step
            if is_connected is not None and not is_connected():
                logger.info("Workflow cancelled by user before step %s", step.step_name)
                cancelled = True
                break

            # Skip completed steps on resume
            if step.id in completed_step_ids:
                logger.debug(
                    "[Sequential] Skipping completed step '%s' (id=%d)",
                    step.step_name, step.id,
                )
                continue

            # Skip steps that are in the inactive branch of a conditional router
            if step.step_order in skip_step_orders:
                logger.info(
                    "[Sequential] Skipping step '%s' (order=%d) — "
                    "inactive conditional branch",
                    step.step_name, step.step_order,
                )
                continue

            # ── Conditional Router step: evaluate and set branch skips ──
            if step.step_type == "conditional_router":
                condition_config = step.condition or {}
                result, explanation = evaluate_condition(
                    condition_config, context
                )
                # Store result in context
                context.step_outputs[step.output_key] = (
                    "true" if result else "false"
                )

                # Determine which branch to skip
                if result:
                    false_steps = condition_config.get("false_steps", [])
                    skip_step_orders.update(int(s) for s in false_steps)
                else:
                    true_steps = condition_config.get("true_steps", [])
                    skip_step_orders.update(int(s) for s in true_steps)

                # Trace: record the branch decision (best-effort)
                try:
                    trace_builder.add_router(
                        step.step_name,
                        explanation,
                        "true" if result else "false",
                    )
                    persist_workflow_trace(trace_builder.trace)
                except Exception:
                    logger.debug("[Trace] router node failed", exc_info=True)

                placement = Placement(turn_index=turn_index)

                # Emit step lifecycle so the UI shows the evaluation
                yield Packet(
                    placement=placement,
                    obj=WorkflowStepStart(
                        step_name=step.step_name,
                        agent_name=None,
                        step_order=step.step_order,
                        step_type="conditional_router",
                    ),
                )
                yield Packet(
                    placement=placement,
                    obj=WorkflowStepDelta(content=explanation),
                )
                yield Packet(
                    placement=placement,
                    obj=WorkflowStepEnd(
                        step_name=step.step_name,
                        output_key=step.output_key,
                    ),
                )
                yield Packet(placement=placement, obj=SectionEnd())

                # Save checkpoint
                step_checkpoint = WorkflowCheckpoint(
                    step_outputs=dict(context.step_outputs),
                    shared_data={
                        **context.shared_data,
                        "_original_user_input": context.shared_data.get(
                            "_original_user_input", context.user_input
                        ),
                    },
                    completed_step_ids=[
                        s.id for s in steps
                        if s.output_key in context.step_outputs
                    ],
                    turn_index=turn_index,
                )
                save_checkpoint(db_session, execution.id, step_checkpoint)

                steps_executed.append({
                    "step_id": step.id,
                    "agent_id": None,
                    "step_name": step.step_name,
                    "input_text": str(condition_config)[:500],
                    "output_text": explanation,
                    "duration_ms": 0,
                    "tokens_used": 0,
                })

                turn_index += 1
                continue

            agent_tool = agent_tools_by_step.get(step.id)
            if agent_tool is None:
                logger.warning(f"Skipping step {step.step_name}: no agent tool")
                continue

            step_start_time = time.monotonic()
            agent = agent_tool._agent
            logger.info(
                "[Sequential] STEP START step=%d/%d name='%s' agent='%s' "
                "can_request_input=%s",
                step.step_order + 1,
                len(steps),
                step.step_name,
                agent.name,
                step.can_request_input,
            )

            placement = Placement(turn_index=turn_index)

            # Emit step start
            yield Packet(
                placement=placement,
                obj=WorkflowStepStart(
                    step_name=step.step_name,
                    agent_name=agent.name,
                    step_order=step.step_order,
                    promote_output=step.promote_output,
                ),
            )

            # Build the task input: use conversation-aware override for
            # the paused step, normal input mapping for all others
            if resume_task_override and step.id == paused_step_id:
                task_input = resume_task_override
            else:
                task_input = _apply_input_mapping(step.input_mapping, context)

            # Trace: open the agent node in the running state (best-effort)
            trace_node_id: str | None = None
            try:
                trace_node_id = trace_builder.start_agent(
                    step_id=step.id,
                    name=step.step_name,
                    agent_id=step.agent_id,
                    input_text=task_input,
                    file_names=_trace_file_names,
                )
                persist_workflow_trace(trace_builder.trace)
            except Exception:
                logger.debug("[Trace] start_agent failed", exc_info=True)

            streaming_result = _StreamingAgentResult(start_turn_index=turn_index)
            # HITL (can_request_input) steps: don't stream sub-agent prose/reasoning
            # live. Their output is a clarification (may carry the [NEEDS_INPUT]
            # marker) surfaced via the pause packet + main message, and reload shows
            # an empty step row — streaming would leak the raw marker / chain-of-
            # thought and diverge from the reloaded view.
            _stream_step = not step.can_request_input
            yield from _stream_agent_packets(
                agent_tool=agent_tool,
                placement=placement,
                emitter=emitter,
                result=streaming_result,
                is_connected=is_connected,
                stream_answer_as_step=_stream_step,
                stream_reasoning_as_step=_stream_step,
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
                # Capture file metadata for downstream workflow steps
                _file_details = result_data.get("_file_details", [])
                _file_ids = result_data.get("_file_ids", [])
                if _file_details:
                    step_files = context.shared_data.setdefault(
                        "step_files", {}
                    )
                    step_files[step.output_key] = {
                        "file_ids": _file_ids,
                        "files": _file_details,
                    }
            except (json.JSONDecodeError, AttributeError):
                agent_output = (
                    result.llm_facing_response if result else ""
                ) or ""

            agent_elapsed = time.monotonic() - step_start_time
            output_len = len(agent_output)
            logger.info(
                "[Sequential] AGENT DONE step='%s' agent='%s' "
                "llm_time=%.2fs output_len=%d words=%d",
                step.step_name,
                agent.name,
                agent_elapsed,
                output_len,
                len(agent_output.split()),
            )

            # Check if agent is requesting user input (human-in-the-loop)
            if step.can_request_input and _agent_requests_input(agent_output):
                logger.info(
                    "[Sequential] PAUSE DETECTED step='%s' agent='%s' — "
                    "agent is requesting user input, saving checkpoint",
                    step.step_name,
                    agent.name,
                )
                # Build accumulated clarification conversation
                accumulated_conv: list[dict[str, str]] = list(
                    resume_conversation
                ) if resume_conversation else []
                accumulated_conv.append({
                    "role": "agent",
                    "content": _strip_needs_input_prefix(agent_output),
                })

                pause_checkpoint = WorkflowCheckpoint(
                    step_outputs=dict(context.step_outputs),
                    shared_data={
                        **context.shared_data,
                        "_original_user_input": context.shared_data.get(
                            "_original_user_input", context.user_input
                        ),
                    },
                    completed_step_ids=[
                        s.id for s in steps
                        if s.output_key in context.step_outputs
                    ],
                    turn_index=turn_index,
                    # Enterprise: save original task and conversation
                    paused_agent_original_task=(
                        checkpoint.paused_agent_original_task
                        if (checkpoint and checkpoint.paused_agent_original_task)
                        else task_input
                    ),
                    clarification_conversation=accumulated_conv,
                )
                save_checkpoint(
                    db_session, execution.id, pause_checkpoint,
                    paused_at_step_id=step.id,
                )
                total_duration_ms = int(
                    (time.monotonic() - start_time) * 1000
                )
                update_workflow_execution(
                    db_session, execution.id,
                    steps_executed=steps_executed,
                    total_tokens=total_tokens,
                    total_duration_ms=total_duration_ms,
                )
                # Trace: mark the agent paused + persist (per-message key) so
                # this turn's message resolves to a graph (best-effort).
                try:
                    trace_builder.finish_agent(
                        trace_node_id,
                        _strip_needs_input_prefix(agent_output),
                        status="paused",
                    )
                    trace_builder.finalize(
                        "paused", total_tokens, total_duration_ms
                    )
                    persist_workflow_trace(
                        trace_builder.trace, include_message_key=True
                    )
                    logger.info(
                        "[Trace] SEQ-PAUSE step='%s' execution_id=%d msg_id=%s",
                        step.step_name,
                        execution.id,
                        assistant_message_id,
                    )
                except Exception:
                    logger.debug("[Trace] seq pause persist failed", exc_info=True)
                # Close the step
                yield Packet(
                    placement=placement,
                    obj=WorkflowStepEnd(
                        step_name=step.step_name,
                        output_key=step.output_key,
                    ),
                )
                yield Packet(placement=placement, obj=SectionEnd())
                # Emit pause packet with questions (inside timeline)
                pause_placement = Placement(turn_index=turn_index + 1)
                pause_questions = _strip_needs_input_prefix(agent_output)
                yield Packet(
                    placement=pause_placement,
                    obj=WorkflowPauseForInput(
                        step_name=step.step_name,
                        agent_name=agent.name,
                        questions=pause_questions,
                    ),
                )
                yield Packet(placement=pause_placement, obj=SectionEnd())
                # Also emit as main message content so the user sees
                # the questions prominently outside the timeline panel.
                msg_placement = Placement(turn_index=turn_index + 2)
                yield Packet(
                    placement=msg_placement,
                    obj=AgentResponseStart(),
                )
                yield Packet(
                    placement=msg_placement,
                    obj=AgentResponseDelta(content=pause_questions),
                )
                yield Packet(
                    placement=msg_placement, obj=SectionEnd(),
                )
                yield Packet(
                    placement=Placement(turn_index=turn_index + 3),
                    obj=OverallStop(type="stop"),
                )
                return  # Stop execution, free thread

            # Yield the authoritative agent output as a WorkflowStepDelta,
            # reconciling (replace=True) any live-streamed prose chunks. Empty
            # output uses replace=False so it can't wipe streamed content.
            yield Packet(
                placement=placement,
                obj=WorkflowStepDelta(
                    content=agent_output, replace=bool(agent_output)
                ),
            )

            # Emit step end BEFORE promote_output so no tool packet
            # follows the promoted message_start (which would reset
            # finalAnswerComing in the frontend).
            yield Packet(
                placement=placement,
                obj=WorkflowStepEnd(
                    step_name=step.step_name,
                    output_key=step.output_key,
                ),
            )
            yield Packet(placement=placement, obj=SectionEnd())

            # Store output in context
            context.step_outputs[step.output_key] = agent_output
            context.current_step = step.step_name

            # Save checkpoint after step completion (crash recovery)
            step_checkpoint = WorkflowCheckpoint(
                step_outputs=dict(context.step_outputs),
                shared_data={
                    **context.shared_data,
                    "_original_user_input": context.shared_data.get(
                        "_original_user_input", context.user_input
                    ),
                },
                completed_step_ids=[
                    s.id for s in steps
                    if s.output_key in context.step_outputs
                ],
                turn_index=turn_index,
            )
            save_checkpoint(db_session, execution.id, step_checkpoint)

            step_duration_ms = int((time.monotonic() - step_start_time) * 1000)

            # Estimate token usage (M1 fix)
            step_tokens = len(task_input.split()) + len(agent_output.split())
            total_tokens += step_tokens

            logger.info(
                "[Sequential] STEP DONE step=%d/%d name='%s' agent='%s' "
                "duration=%dms tokens=%d output_words=%d",
                step.step_order + 1,
                len(steps),
                step.step_name,
                agent.name,
                step_duration_ms,
                step_tokens,
                len(agent_output.split()),
            )

            steps_executed.append({
                "step_id": step.id,
                "agent_id": step.agent_id,
                "step_name": step.step_name,
                "input_text": task_input[:500],  # Truncate for storage
                "output_text": agent_output[:2000],
                "duration_ms": step_duration_ms,
                "tokens_used": step_tokens,
            })

            # Trace: close the running agent node (best-effort)
            try:
                trace_builder.finish_agent(
                    trace_node_id,
                    agent_output,
                    status="completed",
                    duration_ms=step_duration_ms,
                    tokens=step_tokens,
                )
                persist_workflow_trace(trace_builder.trace)
            except Exception:
                logger.debug("[Trace] finish_agent failed", exc_info=True)

            # Output promotion: emit as MESSAGE packets so the frontend
            # renders it as main content outside the timeline.
            # Emitted AFTER step end so no trailing tool packet resets
            # the frontend's finalAnswerComing flag.
            if step.promote_output and agent_output:
                promoted_placement = Placement(turn_index=turn_index + 1)
                yield Packet(
                    placement=promoted_placement,
                    obj=AgentResponseStart(),
                )
                yield Packet(
                    placement=promoted_placement,
                    obj=AgentResponseDelta(content=agent_output),
                )
                yield Packet(
                    placement=promoted_placement,
                    obj=SectionEnd(),
                )
                turn_index += 1

            # Advance turn_index past all indices used by this step
            turn_index += 1

            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed > workflow.timeout_seconds:
                logger.warning(f"Workflow timeout after {elapsed:.1f}s")
                break

            if step.is_terminal:
                break

        # ── Final summary emission ──────────────────────────────────────
        # After all steps complete, emit a final message for the user.
        # Uses the last step's output plus file download links from
        # shared_data["step_files"] (structured file metadata).
        if not cancelled and context.step_outputs:
            # Check if any step already promoted output
            any_promoted = any(
                s.promote_output
                for s in steps
                if s.output_key in context.step_outputs
            )

            # Collect file_ids and file_names from structured metadata,
            # de-duplicated by filename (last writer wins) so a document
            # touched by more than one step yields a single download link.
            step_files = context.shared_data.get("step_files", {})
            all_file_ids, all_file_names = _collect_workflow_files(step_files)

            # Emit final summary if no step promoted its output
            if not any_promoted:
                last_key = list(context.step_outputs.keys())[-1]
                last_output = context.step_outputs[last_key]

                final_placement = Placement(turn_index=turn_index)
                yield Packet(
                    placement=final_placement,
                    obj=AgentResponseStart(),
                )
                yield Packet(
                    placement=final_placement,
                    obj=AgentResponseDelta(
                        content=last_output,
                        file_ids=all_file_ids or None,
                        file_names=all_file_names or None,
                    ),
                )
                yield Packet(
                    placement=final_placement,
                    obj=SectionEnd(),
                )
                turn_index += 1
            elif all_file_ids:
                # A step promoted output but we still have files to
                # show — emit a brief file summary with download links
                file_placement = Placement(turn_index=turn_index)
                yield Packet(
                    placement=file_placement,
                    obj=AgentResponseStart(),
                )
                yield Packet(
                    placement=file_placement,
                    obj=AgentResponseDelta(
                        content="",
                        file_ids=all_file_ids,
                        file_names=all_file_names or None,
                    ),
                )
                yield Packet(
                    placement=file_placement,
                    obj=SectionEnd(),
                )
                turn_index += 1

        total_duration_ms = int((time.monotonic() - start_time) * 1000)
        final_status = "cancelled" if cancelled else "completed"
        logger.info(
            "[Sequential] COMPLETE execution_id=%d status=%s "
            "steps_ran=%d total_tokens=%d total_time=%dms "
            "per_step_times=[%s]",
            execution.id,
            final_status,
            len(steps_executed),
            total_tokens,
            total_duration_ms,
            ", ".join(
                f"{s['step_name']}={s['duration_ms']}ms"
                for s in steps_executed
            ),
        )
        update_workflow_execution(
            db_session,
            execution.id,
            status=final_status,
            steps_executed=steps_executed,
            total_tokens=total_tokens,
            total_duration_ms=total_duration_ms,
        )

        # Trace: record final answer + persist the completed graph (best-effort)
        try:
            if not cancelled and context.step_outputs:
                _final_text = list(context.step_outputs.values())[-1]
                trace_builder.add_finish(_final_text)
            trace_builder.finalize(
                final_status, total_tokens, total_duration_ms
            )
            persist_workflow_trace(
                trace_builder.trace, include_message_key=True
            )
        except Exception:
            logger.debug("[Trace] sequential complete persist failed", exc_info=True)

    except Exception as e:
        logger.exception("[Sequential] Workflow execution failed")
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
        try:
            trace_builder.finalize("failed", total_tokens, total_duration_ms)
            persist_workflow_trace(
                trace_builder.trace, include_message_key=True
            )
        except Exception:
            logger.debug("[Trace] sequential failed persist failed", exc_info=True)
        raise

    # Emit overall stop
    yield Packet(
        placement=Placement(turn_index=turn_index),
        obj=OverallStop(
            type="stop",
            stop_reason="user_cancelled" if cancelled else None,
        ),
    )



def _pinned_version_id(
    db_session: Session, workflow: AgentWorkflow, user: User
) -> int:
    """The version an ``llm_decision`` run starts on, recorded in its history."""
    graph = graph_from_workflow(workflow, get_node_registry())
    return pin_workflow_version(db_session, workflow, graph, user.id).id


def run_workflow_llm_decision(
    workflow: AgentWorkflow,
    user_message: str,
    emitter: Emitter,
    db_session: Session,
    user: User,
    is_connected: Callable[[], bool] | None = None,
    chat_session_id: UUID | None = None,
    paused_execution: WorkflowExecution | None = None,
    chat_files: list[ChatFile] | None = None,
    sandbox_session_id: str | None = None,
    assistant_message_id: int | None = None,
) -> Generator[Packet, None, None]:
    """Run a workflow in LLM-decision mode — orchestrator LLM decides which agent to call.

    Mirrors the Deep Research dr_loop.py pattern:
    - Orchestrator LLM sees all agents as callable tools
    - Decides which agent to call and with what task
    - Collects results and decides next step
    - Generates final answer when done

    Supports pause/resume via checkpoints (human-in-the-loop).
    """
    steps = sorted(workflow.steps, key=lambda s: s.step_order)
    steps_by_id = {step.id: step for step in steps}

    logger.info(
        "[LLM-Decision] Starting with %d steps, resume=%s",
        len(steps),
        paused_execution is not None,
    )

    # Build agent tools (with cached LLMs + user — Tier 1.5)
    agent_tools = _build_agent_tools(steps, emitter, db_session, user=user, chat_files=chat_files, sandbox_session_id=sandbox_session_id)
    if not agent_tools:
        raise ValueError("No valid agent tools found for workflow")

    # Get orchestrator LLM
    orchestrator_llm = _get_orchestrator_llm(workflow, db_session)
    token_counter = get_llm_token_counter(orchestrator_llm)
    logger.info(
        "[LLM-Decision] Orchestrator LLM: provider=%s model=%s agents=[%s]",
        workflow.orchestrator_llm_provider or "default",
        workflow.orchestrator_llm_model or "default",
        ", ".join(t.display_name for t in agent_tools),
    )

    # Build orchestrator system prompt
    system_prompt_text = _build_orchestrator_system_prompt(workflow, agent_tools)
    system_prompt = ChatMessageSimple(
        message=system_prompt_text,
        token_count=token_counter(system_prompt_text),
        message_type=MessageType.SYSTEM,
    )

    # Pre-compute tool definitions once (they don't change — Tier 1.2)
    tool_defs = [tool.tool_definition() for tool in agent_tools]
    tools_by_name = {tool.name: tool for tool in agent_tools}
    tools_by_step_id = {tool.step_id: tool for tool in agent_tools}

    cycle_start = 0

    # Resume from paused execution or start fresh
    # These are set during resume and used for direct agent re-call
    _direct_resume_task: str | None = None
    _direct_resume_conversation: list[dict[str, str]] | None = None
    _direct_resume_tool: AgentTool | None = None
    _direct_resume_step: AgentWorkflowStep | None = None
    checkpoint: WorkflowCheckpoint | None = None

    if paused_execution:
        paused_step_id = paused_execution.paused_at_step_id
        checkpoint = load_checkpoint(paused_execution)
        if checkpoint:
            original_input = checkpoint.shared_data.get(
                "_original_user_input", user_message
            )
            context = WorkflowContext(
                user_input=original_input,
                step_outputs=checkpoint.step_outputs,
                shared_data=checkpoint.shared_data,
            )
            msg_history = restore_history(
                checkpoint.orchestrator_history
            )
            agent_call_counts = dict(checkpoint.agent_call_counts)
            # Decrement the paused agent's call count so it can be
            # re-called within max_calls_per_agent.
            if paused_step_id:
                paused_tool = tools_by_step_id.get(paused_step_id)
                if paused_tool and paused_tool.name in agent_call_counts:
                    agent_call_counts[paused_tool.name] = max(
                        0, agent_call_counts[paused_tool.name] - 1
                    )
            cycle_start = checkpoint.cycle_count
            turn_index = checkpoint.turn_index
            execution = paused_execution
            execution.status = "running"
            execution.paused_at_step_id = None
            db_session.commit()
            steps_executed = list(execution.steps_executed or [])

            # Enterprise resume: if we have a clarification conversation,
            # prepare for DIRECT agent re-call (bypass orchestrator)
            if (
                checkpoint.clarification_conversation
                and checkpoint.paused_agent_original_task
                and paused_step_id
            ):
                conversation = list(checkpoint.clarification_conversation)
                conversation.append({"role": "user", "content": user_message})

                _direct_resume_task = _build_clarification_task(
                    checkpoint.paused_agent_original_task,
                    conversation,
                )
                _direct_resume_conversation = conversation
                _direct_resume_tool = tools_by_step_id.get(paused_step_id)
                _direct_resume_step = steps_by_id.get(paused_step_id)

                logger.info(
                    "[LLM-Decision] DIRECT RESUME execution_id=%d "
                    "agent='%s' clarification_rounds=%d",
                    execution.id,
                    _direct_resume_tool.display_name if _direct_resume_tool else "?",
                    len(conversation),
                )
            else:
                # Fallback: no clarification conversation saved (old checkpoint
                # format or crash recovery). Pass on the user's reply and let the
                # orchestrator decide.
                user_clarification = (
                    f"The agent requested more information from the user. "
                    f"The user responded:\n\n{user_message}\n\n"
                    f"Please call the same agent again with this additional "
                    f"information included in the task."
                )
                msg_history.append(ChatMessageSimple(
                    message=user_clarification,
                    token_count=token_counter(user_clarification),
                    message_type=MessageType.USER,
                ))
                logger.info(
                    "[LLM-Decision] FALLBACK RESUME execution_id=%d "
                    "(no clarification_conversation in checkpoint)",
                    execution.id,
                )

            logger.info(
                "[LLM-Decision] Resumed execution_id=%d cycle_start=%d "
                "history_len=%d agent_call_counts=%s step_outputs=%s "
                "direct_resume=%s",
                execution.id,
                cycle_start,
                len(msg_history),
                dict(agent_call_counts),
                list(checkpoint.step_outputs.keys()),
                _direct_resume_task is not None,
            )
        else:
            # Checkpoint corrupted — mark old execution as failed
            logger.warning(
                "[LLM-Decision] Checkpoint corrupted for execution_id=%d, "
                "starting fresh",
                paused_execution.id,
            )
            paused_execution.status = "failed"
            paused_execution.error_message = "Checkpoint data corrupted"
            paused_execution.completed_at = datetime.datetime.now(
                datetime.timezone.utc
            )
            db_session.commit()
            context = WorkflowContext(user_input=user_message)
            user_msg = ChatMessageSimple(
                message=user_message,
                token_count=token_counter(user_message),
                message_type=MessageType.USER,
            )
            msg_history = [user_msg]
            execution = create_workflow_execution(
                db_session, workflow.id, user.id, chat_session_id,
                workflow_version_id=_pinned_version_id(db_session, workflow, user),
            )
            steps_executed = []
            turn_index = 0
            agent_call_counts = {}
    else:
        context = WorkflowContext(user_input=user_message)
        user_msg = ChatMessageSimple(
            message=user_message,
            token_count=token_counter(user_message),
            message_type=MessageType.USER,
        )
        msg_history = [user_msg]
        execution = create_workflow_execution(
            db_session, workflow.id, user.id, chat_session_id,
            workflow_version_id=_pinned_version_id(db_session, workflow, user),
        )
        steps_executed = []
        turn_index = 0
        agent_call_counts = {}

    total_tokens = 0
    start_time = time.monotonic()
    state_container = ChatStateContainer()
    max_calls_per_agent = workflow.max_calls_per_agent
    cancelled = False
    final_answer_emitted = False
    promoted_output_emitted = False
    final_answer_text = ""

    # --- Execution trace graph (best-effort observability) ---
    _trace_file_names = [f.filename for f in (chat_files or [])]
    trace_builder = WorkflowTraceBuilder(
        execution_id=execution.id,
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        chat_session_id=str(chat_session_id) if chat_session_id else None,
        mode="llm_decision",
        message_id=assistant_message_id,
    )
    if paused_execution is not None:
        _prior_trace = load_workflow_trace(execution.id)
        if _prior_trace is not None:
            trace_builder.restore(_prior_trace)
    else:
        trace_builder.set_start(user_message, _trace_file_names)
    logger.info(
        "[Trace] workflow start execution_id=%d chat_files=%d names=%s resume=%s",
        execution.id,
        len(_trace_file_names),
        _trace_file_names,
        paused_execution is not None,
    )

    try:
        # ================================================================
        # Enterprise Direct Agent Re-call (bypass orchestrator on resume)
        # ================================================================
        # If resuming from a clarification pause, run the paused agent
        # DIRECTLY before entering the orchestrator loop. This is the
        # enterprise pattern (LangGraph/CrewAI): the orchestrator is
        # bypassed during resume; it regains control only after the
        # agent finishes.
        if _direct_resume_task and _direct_resume_tool and _direct_resume_step:
            direct_start_time = time.monotonic()
            turn_index += 1
            agent_placement = Placement(turn_index=turn_index)

            logger.info(
                "[LLM-Decision] DIRECT RE-CALL START agent='%s' "
                "task_len=%d conversation_rounds=%d",
                _direct_resume_tool.display_name,
                len(_direct_resume_task),
                len(_direct_resume_conversation) if _direct_resume_conversation else 0,
            )

            # Emit step start
            yield Packet(
                placement=agent_placement,
                obj=WorkflowStepStart(
                    step_name=_direct_resume_tool._step_name,
                    agent_name=_direct_resume_tool._agent.name,
                    step_order=_direct_resume_tool._step_order,
                    promote_output=_direct_resume_tool.promote_output,
                ),
            )

            # Trace: open the resumed agent node in the running state
            resume_node_id: str | None = None
            try:
                resume_node_id = trace_builder.start_agent(
                    step_id=_direct_resume_tool.step_id,
                    name=_direct_resume_tool.display_name,
                    agent_id=_direct_resume_tool.id,
                    input_text=_direct_resume_task,
                    file_names=_trace_file_names,
                    call_index=agent_call_counts.get(_direct_resume_tool.name),
                )
                persist_workflow_trace(trace_builder.trace)
            except Exception:
                logger.debug("[Trace] resume start_agent failed", exc_info=True)

            # Run the agent directly with the clarification task
            streaming_result = _StreamingAgentResult(
                start_turn_index=turn_index
            )
            # Resuming a paused step is definitionally HITL, so don't stream its
            # prose/reasoning live (keep the row clean, consistent with reload).
            _stream_step = not _direct_resume_step.can_request_input
            yield from _stream_agent_packets(
                agent_tool=_direct_resume_tool,
                placement=agent_placement,
                emitter=emitter,
                result=streaming_result,
                is_connected=is_connected,
                stream_answer_as_step=_stream_step,
                stream_reasoning_as_step=_stream_step,
                task=_direct_resume_task,
            )

            if streaming_result.cancelled:
                yield Packet(
                    placement=agent_placement,
                    obj=WorkflowStepEnd(
                        step_name=_direct_resume_tool.display_name,
                        output_key=_direct_resume_tool.output_key,
                    ),
                )
                yield Packet(placement=agent_placement, obj=SectionEnd())
                # Trace: don't leave the node stuck in "running"
                try:
                    trace_builder.finish_agent(
                        resume_node_id, "", status="failed"
                    )
                    persist_workflow_trace(trace_builder.trace)
                except Exception:
                    logger.debug("[Trace] resume cancel close failed", exc_info=True)
                cancelled = True
                turn_index = streaming_result.max_turn_index + 1
            else:
                result = streaming_result.response
                turn_index = streaming_result.max_turn_index

                # Extract agent output
                try:
                    result_data = json.loads(
                        result.llm_facing_response if result else ""
                    )
                    agent_output = result_data.get("agent_output", "")
                except (json.JSONDecodeError, AttributeError):
                    agent_output = (
                        result.llm_facing_response if result else ""
                    ) or ""

                direct_elapsed_ms = int(
                    (time.monotonic() - direct_start_time) * 1000
                )
                logger.info(
                    "[LLM-Decision] DIRECT RE-CALL DONE agent='%s' "
                    "time=%dms output_len=%d words=%d",
                    _direct_resume_tool.display_name,
                    direct_elapsed_ms,
                    len(agent_output),
                    len(agent_output.split()),
                )

                # Check if agent STILL needs more input → re-pause
                if (
                    _direct_resume_step.can_request_input
                    and _agent_requests_input(agent_output)
                ):
                    logger.info(
                        "[LLM-Decision] DIRECT RE-CALL RE-PAUSE "
                        "agent='%s' — still needs user input",
                        _direct_resume_tool.display_name,
                    )
                    conversation = list(
                        _direct_resume_conversation or []
                    )
                    conversation.append({
                        "role": "agent",
                        "content": _strip_needs_input_prefix(agent_output),
                    })

                    # Save tool_call to msg_history for continuity
                    synthetic_id = (
                        f"resume_{_direct_resume_step.id}_{cycle_start}"
                    )
                    msg_history.append(agent_call(
                    synthetic_id, _direct_resume_tool.name,
                    {"task": _direct_resume_task}, token_counter,
                ))

                    pause_checkpoint = WorkflowCheckpoint(
                        step_outputs=dict(context.step_outputs),
                        shared_data={
                            **context.shared_data,
                            "_original_user_input": context.shared_data.get(
                                "_original_user_input", context.user_input
                            ),
                        },
                        completed_step_ids=[
                            s.id for s in steps
                            if s.output_key in context.step_outputs
                        ],
                        orchestrator_history=serialize_history(
                            msg_history
                        ),
                        cycle_count=cycle_start,
                        agent_call_counts=dict(agent_call_counts),
                        turn_index=turn_index,
                        paused_agent_original_task=(
                            checkpoint.paused_agent_original_task
                            if checkpoint else ""
                        ),
                        clarification_conversation=conversation,
                    )
                    save_checkpoint(
                        db_session, execution.id, pause_checkpoint,
                        paused_at_step_id=_direct_resume_step.id,
                    )
                    total_duration_ms = int(
                        (time.monotonic() - start_time) * 1000
                    )
                    update_workflow_execution(
                        db_session, execution.id,
                        steps_executed=steps_executed,
                        total_tokens=total_tokens,
                        total_duration_ms=total_duration_ms,
                    )
                    # Trace: close the running node as paused + persist (per-message
                    # key) so this resume turn's message resolves to a graph.
                    try:
                        trace_builder.finish_agent(
                            resume_node_id,
                            _strip_needs_input_prefix(agent_output),
                            status="paused",
                        )
                        trace_builder.finalize(
                            "paused", total_tokens, total_duration_ms
                        )
                        persist_workflow_trace(
                            trace_builder.trace, include_message_key=True
                        )
                    except Exception:
                        logger.debug("[Trace] resume re-pause persist failed", exc_info=True)
                    logger.info(
                        "[Trace] RESUME-PAUSE agent='%s' execution_id=%d "
                        "msg_id=%s",
                        _direct_resume_tool.display_name,
                        execution.id,
                        assistant_message_id,
                    )

                    # Close step + emit pause
                    yield Packet(
                        placement=agent_placement,
                        obj=WorkflowStepEnd(
                            step_name=_direct_resume_tool.display_name,
                            output_key=_direct_resume_tool.output_key,
                        ),
                    )
                    yield Packet(
                        placement=agent_placement, obj=SectionEnd()
                    )
                    pause_placement = Placement(
                        turn_index=turn_index + 1
                    )
                    pause_questions = _strip_needs_input_prefix(
                        agent_output
                    )
                    yield Packet(
                        placement=pause_placement,
                        obj=WorkflowPauseForInput(
                            step_name=_direct_resume_tool._step_name,
                            agent_name=_direct_resume_tool._agent.name,
                            questions=pause_questions,
                        ),
                    )
                    yield Packet(
                        placement=pause_placement, obj=SectionEnd()
                    )
                    # Also emit as main message content
                    msg_placement = Placement(
                        turn_index=turn_index + 2
                    )
                    yield Packet(
                        placement=msg_placement,
                        obj=AgentResponseStart(),
                    )
                    yield Packet(
                        placement=msg_placement,
                        obj=AgentResponseDelta(
                            content=pause_questions
                        ),
                    )
                    yield Packet(
                        placement=msg_placement, obj=SectionEnd()
                    )
                    yield Packet(
                        placement=Placement(turn_index=turn_index + 3),
                        obj=OverallStop(type="stop"),
                    )
                    return  # Stop execution — wait for next resume

                # === Agent finished — inject into orchestrator history ===
                context.step_outputs[
                    _direct_resume_tool.output_key
                ] = agent_output

                # Synthesize tool_call + response so orchestrator sees it
                synthetic_id = (
                    f"resume_{_direct_resume_step.id}_{cycle_start}"
                )
                msg_history.append(agent_call(
                    synthetic_id, _direct_resume_tool.name,
                    {"task": _direct_resume_task}, token_counter,
                ))
                summarized = _summarize_for_orchestrator(
                    _direct_resume_tool.display_name, agent_output
                )
                msg_history.append(agent_result(synthetic_id, summarized, token_counter))

                # Track execution
                step_tokens = (
                    token_counter(_direct_resume_task)
                    + token_counter(agent_output)
                )
                total_tokens += step_tokens
                steps_executed.append({
                    "step_id": _direct_resume_tool.step_id,
                    "agent_id": _direct_resume_tool.id,
                    "step_name": _direct_resume_tool.display_name,
                    "input_text": _direct_resume_task[:500],
                    "output_text": agent_output[:2000],
                    "duration_ms": direct_elapsed_ms,
                    "tokens_used": step_tokens,
                })

                # Trace: close the resumed agent node as completed. Previously
                # this path recorded nothing, so a resumed agent that finished
                # was missing from the graph entirely.
                try:
                    trace_builder.finish_agent(
                        resume_node_id,
                        agent_output,
                        status="completed",
                        duration_ms=direct_elapsed_ms,
                        tokens=step_tokens,
                    )
                    persist_workflow_trace(trace_builder.trace)
                except Exception:
                    logger.debug("[Trace] resume finish_agent failed", exc_info=True)

                # Emit step content and close; reconcile live-streamed prose
                # with the authoritative output (replace=True when non-empty).
                yield Packet(
                    placement=agent_placement,
                    obj=WorkflowStepDelta(
                        content=agent_output, replace=bool(agent_output)
                    ),
                )

                # Emit step end BEFORE promote_output so no tool
                # packet follows the promoted message_start.
                yield Packet(
                    placement=agent_placement,
                    obj=WorkflowStepEnd(
                        step_name=_direct_resume_tool.display_name,
                        output_key=_direct_resume_tool.output_key,
                    ),
                )
                yield Packet(
                    placement=agent_placement, obj=SectionEnd()
                )

                # Output promotion for direct resume path
                if _direct_resume_tool.promote_output and agent_output:
                    promoted_placement = Placement(
                        turn_index=turn_index + 1
                    )
                    yield Packet(
                        placement=promoted_placement,
                        obj=AgentResponseStart(),
                    )
                    yield Packet(
                        placement=promoted_placement,
                        obj=AgentResponseDelta(content=agent_output),
                    )
                    yield Packet(
                        placement=promoted_placement,
                        obj=SectionEnd(),
                    )
                    turn_index += 1
                    promoted_output_emitted = True

                turn_index += 1

                # Increment call count for the resumed agent
                agent_call_counts[_direct_resume_tool.name] = (
                    agent_call_counts.get(_direct_resume_tool.name, 0) + 1
                )

                logger.info(
                    "[LLM-Decision] DIRECT RE-CALL COMPLETE — "
                    "agent='%s' output stored as '%s', "
                    "falling through to orchestrator loop",
                    _direct_resume_tool.display_name,
                    _direct_resume_tool.output_key,
                )

            # Clear direct resume state
            _direct_resume_task = None
            _direct_resume_tool = None
            _direct_resume_step = None
            _direct_resume_conversation = None

        for cycle in range(cycle_start, workflow.max_steps):
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
                workspace_files=None,
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

            orchestrator_call_start = time.monotonic()
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

            orchestrator_call_ms = int(
                (time.monotonic() - orchestrator_call_start) * 1000
            )
            tool_call_names = (
                [tc.tool_name for tc in llm_step_result.tool_calls]
                if llm_step_result.tool_calls else []
            )
            logger.info(
                "[LLM-Decision] ORCHESTRATOR cycle=%d/%d llm_time=%dms "
                "tool_calls=%s has_answer=%s has_reasoned=%s "
                "elapsed=%.1fs agent_calls=%s",
                cycle + 1,
                workflow.max_steps,
                orchestrator_call_ms,
                tool_call_names or "none",
                bool(llm_step_result.answer and not llm_step_result.tool_calls),
                has_reasoned,
                time.monotonic() - start_time,
                dict(agent_call_counts),
            )

            # Trace: record the orchestrator decision for this cycle and
            # persist immediately so the live graph shows the routing choice
            # before the delegated agent finishes (best-effort).
            if llm_step_result.tool_calls:
                try:
                    trace_builder.add_orchestrator(cycle + 1, llm_step_result.answer)
                    persist_workflow_trace(trace_builder.trace)
                except Exception:
                    logger.debug("[Trace] orchestrator persist failed", exc_info=True)

            # If orchestrator produced a final answer (no tool calls)
            if llm_step_result.answer and not llm_step_result.tool_calls:
                final_answer_text = llm_step_result.answer
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
                        refuse_msg = agent_call(
                            tool_call.tool_call_id, tool_call.tool_name,
                            tool_call.tool_args, token_counter,
                        )
                        msg_history.append(refuse_msg)
                        error_response = (
                            f"ERROR: Agent '{agent_tool.display_name}' has "
                            f"already been called {call_count} times. "
                            f"Do NOT call this agent again. "
                            f"Use a DIFFERENT agent or provide the final answer."
                        )
                        msg_history.append(
                            agent_result(tool_call.tool_call_id, error_response, token_counter)
                        )
                        continue
                    agent_call_counts[tool_call.tool_name] = call_count + 1

                    step_start_time = time.monotonic()
                    turn_index += 1
                    agent_placement = Placement(turn_index=turn_index)

                    task_preview = str(tool_call.tool_args.get("task", ""))[:100]
                    logger.info(
                        "[LLM-Decision] AGENT START agent='%s' call=%d/%d "
                        "task='%s...'",
                        agent_tool.display_name,
                        call_count + 1,
                        max_calls_per_agent,
                        task_preview,
                    )

                    # Yield WorkflowStepStart directly (C1 fix — don't rely on emitter bus)
                    yield Packet(
                        placement=agent_placement,
                        obj=WorkflowStepStart(
                            step_name=agent_tool._step_name,
                            agent_name=agent_tool._agent.name,
                            step_order=agent_tool._step_order,
                            promote_output=agent_tool.promote_output,
                        ),
                    )

                    # Trace: open the agent node in the running state so the
                    # live graph shows it while it works (best-effort).
                    agent_node_id: str | None = None
                    try:
                        agent_node_id = trace_builder.start_agent(
                            step_id=agent_tool.step_id,
                            name=agent_tool.display_name,
                            agent_id=agent_tool.id,
                            input_text=json.dumps(tool_call.tool_args),
                            file_names=_trace_file_names,
                            call_index=agent_call_counts.get(tool_call.tool_name),
                        )
                        persist_workflow_trace(trace_builder.trace)
                    except Exception:
                        logger.debug("[Trace] start_agent failed", exc_info=True)

                    # Run the agent with real-time streaming
                    streaming_result = _StreamingAgentResult(
                        start_turn_index=turn_index
                    )
                    # HITL steps: don't stream prose/reasoning live (see sequential
                    # path). The step's can_request_input comes from its WorkflowStep.
                    _step_obj = steps_by_id.get(agent_tool.step_id)
                    _stream_step = not (_step_obj and _step_obj.can_request_input)
                    yield from _stream_agent_packets(
                        agent_tool=agent_tool,
                        placement=agent_placement,
                        emitter=emitter,
                        result=streaming_result,
                        stream_answer_as_step=_stream_step,
                        stream_reasoning_as_step=_stream_step,
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
                        # Trace: don't leave the node stuck in "running"
                        try:
                            trace_builder.finish_agent(
                                agent_node_id, "", status="failed"
                            )
                            persist_workflow_trace(trace_builder.trace)
                        except Exception:
                            logger.debug("[Trace] cancel close failed", exc_info=True)
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

                    agent_elapsed_ms = int(
                        (time.monotonic() - step_start_time) * 1000
                    )
                    logger.info(
                        "[LLM-Decision] AGENT DONE agent='%s' "
                        "llm_time=%dms output_len=%d words=%d",
                        agent_tool.display_name,
                        agent_elapsed_ms,
                        len(agent_output),
                        len(agent_output.split()),
                    )

                    # Check if agent is requesting user input (human-in-the-loop)
                    step_obj = steps_by_id.get(agent_tool.step_id)
                    if (
                        step_obj
                        and step_obj.can_request_input
                        and _agent_requests_input(agent_output)
                    ):
                        logger.info(
                            "[LLM-Decision] PAUSE DETECTED agent='%s' — "
                            "requesting user input, saving checkpoint "
                            "(cycle=%d, elapsed=%.1fs)",
                            agent_tool.display_name,
                            cycle,
                            time.monotonic() - start_time,
                        )
                        # Save the tool_call to msg_history so resume has it
                        tool_call_msg = agent_call(
                            tool_call.tool_call_id, tool_call.tool_name,
                            tool_call.tool_args, token_counter,
                        )
                        msg_history.append(tool_call_msg)

                        # Build clarification conversation: if we already
                        # have one from a previous resume, extend it;
                        # otherwise start fresh with the agent's questions.
                        prev_conversation: list[dict[str, str]] = list(
                            checkpoint.clarification_conversation
                        ) if (checkpoint and checkpoint.clarification_conversation) else []
                        prev_conversation.append({
                            "role": "agent",
                            "content": _strip_needs_input_prefix(agent_output),
                        })

                        pause_checkpoint = WorkflowCheckpoint(
                            step_outputs=dict(context.step_outputs),
                            shared_data={
                                **context.shared_data,
                                "_original_user_input": context.shared_data.get(
                                    "_original_user_input", context.user_input
                                ),
                            },
                            completed_step_ids=[
                                s.id for s in steps
                                if s.output_key in context.step_outputs
                            ],
                            orchestrator_history=serialize_history(
                                msg_history
                            ),
                            cycle_count=cycle + 1,
                            agent_call_counts=dict(agent_call_counts),
                            turn_index=turn_index,
                            # Enterprise pause/resume: save original task
                            # and accumulated clarification conversation
                            paused_agent_original_task=(
                                checkpoint.paused_agent_original_task
                                if (checkpoint and checkpoint.paused_agent_original_task)
                                else tool_call.tool_args.get("task", "")
                            ),
                            clarification_conversation=prev_conversation,
                        )
                        save_checkpoint(
                            db_session, execution.id, pause_checkpoint,
                            paused_at_step_id=step_obj.id,
                        )
                        total_duration_ms = int(
                            (time.monotonic() - start_time) * 1000
                        )
                        update_workflow_execution(
                            db_session, execution.id,
                            steps_executed=steps_executed,
                            total_tokens=total_tokens,
                            total_duration_ms=total_duration_ms,
                        )
                        # Trace: close the running agent node as paused + persist
                        try:
                            trace_builder.finish_agent(
                                agent_node_id,
                                _strip_needs_input_prefix(agent_output),
                                status="paused",
                            )
                            trace_builder.finalize(
                                "paused", total_tokens, total_duration_ms
                            )
                            persist_workflow_trace(
                                trace_builder.trace, include_message_key=True
                            )
                        except Exception:
                            logger.debug("[Trace] pause persist failed", exc_info=True)
                        logger.info(
                            "[Trace] PAUSE agent='%s' files_available=%d "
                            "execution_id=%d",
                            agent_tool.display_name,
                            len(_trace_file_names),
                            execution.id,
                        )
                        # Close the step
                        yield Packet(
                            placement=agent_placement,
                            obj=WorkflowStepEnd(
                                step_name=agent_tool.display_name,
                                output_key=agent_tool.output_key,
                            ),
                        )
                        yield Packet(
                            placement=agent_placement, obj=SectionEnd()
                        )
                        # Emit pause packet with questions (inside timeline)
                        pause_placement = Placement(
                            turn_index=turn_index + 1
                        )
                        pause_questions = _strip_needs_input_prefix(agent_output)
                        yield Packet(
                            placement=pause_placement,
                            obj=WorkflowPauseForInput(
                                step_name=agent_tool._step_name,
                                agent_name=agent_tool._agent.name,
                                questions=pause_questions,
                            ),
                        )
                        yield Packet(
                            placement=pause_placement, obj=SectionEnd()
                        )
                        # Also emit as main message content
                        msg_placement = Placement(
                            turn_index=turn_index + 2
                        )
                        yield Packet(
                            placement=msg_placement,
                            obj=AgentResponseStart(),
                        )
                        yield Packet(
                            placement=msg_placement,
                            obj=AgentResponseDelta(
                                content=pause_questions
                            ),
                        )
                        yield Packet(
                            placement=msg_placement, obj=SectionEnd()
                        )
                        yield Packet(
                            placement=Placement(turn_index=turn_index + 3),
                            obj=OverallStop(type="stop"),
                        )
                        return  # Stop execution, free thread

                    # Yield the authoritative agent output, reconciling
                    # (replace=True) any live-streamed prose chunks.
                    yield Packet(
                        placement=agent_placement,
                        obj=WorkflowStepDelta(
                            content=agent_output, replace=bool(agent_output)
                        ),
                    )

                    # Store in context using output_key (M2 fix)
                    context.step_outputs[agent_tool.output_key] = agent_output

                    task_input = json.dumps(tool_call.tool_args)
                    step_tokens = token_counter(task_input) + token_counter(agent_output)
                    total_tokens += step_tokens

                    step_duration_ms = int(
                        (time.monotonic() - step_start_time) * 1000
                    )

                    logger.info(
                        "[LLM-Decision] STEP DONE agent='%s' "
                        "duration=%dms tokens=%d output_words=%d "
                        "total_elapsed=%.1fs",
                        agent_tool.display_name,
                        step_duration_ms,
                        step_tokens,
                        len(agent_output.split()),
                        time.monotonic() - start_time,
                    )

                    steps_executed.append({
                        "step_id": agent_tool.step_id,
                        "agent_id": agent_tool.id,
                        "step_name": agent_tool.display_name,
                        "input_text": task_input[:500],
                        "output_text": agent_output[:2000],
                        "duration_ms": step_duration_ms,
                        "tokens_used": step_tokens,
                    })

                    # Trace: close the running agent node as completed
                    try:
                        trace_builder.finish_agent(
                            agent_node_id,
                            agent_output,
                            status="completed",
                            duration_ms=step_duration_ms,
                            tokens=step_tokens,
                        )
                    except Exception:
                        logger.debug("[Trace] finish_agent failed", exc_info=True)

                    # Add tool result to orchestrator history
                    tool_call_msg = agent_call(
                            tool_call.tool_call_id, tool_call.tool_name,
                            tool_call.tool_args, token_counter,
                        )
                    msg_history.append(tool_call_msg)

                    # Summarize agent output for orchestrator context (Tier 2.1)
                    # Full output is in context.step_outputs for downstream agents.
                    summarized = _summarize_for_orchestrator(
                        agent_tool.display_name,
                        result.llm_facing_response or "",
                    )
                    msg_history.append(
                        agent_result(tool_call.tool_call_id, summarized, token_counter)
                    )

                    # Save checkpoint after step completion (crash recovery)
                    step_checkpoint = WorkflowCheckpoint(
                        step_outputs=dict(context.step_outputs),
                        shared_data={
                            **context.shared_data,
                            "_original_user_input": context.shared_data.get(
                                "_original_user_input", context.user_input
                            ),
                        },
                        completed_step_ids=[
                            s.id for s in steps
                            if s.output_key in context.step_outputs
                        ],
                        orchestrator_history=serialize_history(
                            msg_history
                        ),
                        cycle_count=cycle + 1,
                        agent_call_counts=dict(agent_call_counts),
                        turn_index=turn_index,
                    )
                    save_checkpoint(
                        db_session, execution.id, step_checkpoint
                    )
                    # Trace: persist after each step (crash resilience — a hard
                    # kill skips the except/finalize blocks). Execution-keyed
                    # only; the message-keyed copy is written at terminal points.
                    persist_workflow_trace(trace_builder.trace)

                    # Emit step end BEFORE promote_output so no tool
                    # packet follows the promoted message_start (which
                    # would reset finalAnswerComing in the frontend).
                    yield Packet(
                        placement=agent_placement,
                        obj=WorkflowStepEnd(
                            step_name=agent_tool.display_name,
                            output_key=agent_tool.output_key,
                        ),
                    )
                    yield Packet(placement=agent_placement, obj=SectionEnd())

                    # Output promotion: emit as MESSAGE packets so the
                    # frontend renders it as main content outside the
                    # timeline. Emitted AFTER step end so no trailing
                    # tool packet resets finalAnswerComing.
                    if agent_tool.promote_output and agent_output:
                        promoted_placement = Placement(
                            turn_index=turn_index + 1
                        )
                        yield Packet(
                            placement=promoted_placement,
                            obj=AgentResponseStart(),
                        )
                        yield Packet(
                            placement=promoted_placement,
                            obj=AgentResponseDelta(content=agent_output),
                        )
                        yield Packet(
                            placement=promoted_placement,
                            obj=SectionEnd(),
                        )
                        turn_index += 1
                        promoted_output_emitted = True

                if cancelled:
                    break
                turn_index += 1
            else:
                # No answer and no tool calls — unusual, break
                logger.warning("Orchestrator produced no answer and no tool calls")
                break

        total_duration_ms = int((time.monotonic() - start_time) * 1000)
        final_status = "cancelled" if cancelled else "completed"
        logger.info(
            "[LLM-Decision] COMPLETE execution_id=%d status=%s "
            "agents_ran=%d total_tokens=%d total_time=%dms "
            "per_agent_times=[%s]",
            execution.id,
            final_status,
            len(steps_executed),
            total_tokens,
            total_duration_ms,
            ", ".join(
                f"{s['step_name']}={s['duration_ms']}ms"
                for s in steps_executed
            ),
        )
        update_workflow_execution(
            db_session,
            execution.id,
            status=final_status,
            steps_executed=steps_executed,
            total_tokens=total_tokens,
            total_duration_ms=total_duration_ms,
        )

        # Trace: record final answer + persist the completed graph
        if final_answer_text:
            trace_builder.add_finish(final_answer_text)
        trace_builder.finalize(final_status, total_tokens, total_duration_ms)
        persist_workflow_trace(trace_builder.trace, include_message_key=True)

    except Exception as e:
        logger.exception("[LLM-Decision] Workflow execution failed")
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
        try:
            trace_builder.finalize("failed", total_tokens, total_duration_ms)
            persist_workflow_trace(trace_builder.trace, include_message_key=True)
        except Exception:
            logger.debug("[Trace] failed-path persist error", exc_info=True)
        raise

    # Fallback: if the orchestrator loop ended without producing a final
    # answer (e.g. max_steps exhausted, timeout, or model kept calling
    # blocked agents), synthesize a basic answer from available outputs
    # so the user isn't left with nothing.
    # Skip fallback if promoted output was already emitted as main content.
    if not cancelled and not final_answer_emitted and not promoted_output_emitted and context.step_outputs:
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
    chat_session_id: UUID | None = None,
    chat_files: list[ChatFile] | None = None,
    sandbox_session_id: str | None = None,
    assistant_message_id: int | None = None,
) -> Generator[Packet, None, None]:
    """Main entry point — dispatches to the appropriate orchestration mode.

    If chat_session_id is provided, checks for a paused execution to resume
    (human-in-the-loop support).
    """
    mode = workflow.orchestration_mode
    step_names = [s.step_name for s in sorted(workflow.steps, key=lambda s: s.step_order)]

    logger.info(
        "[Workflow] START workflow_id=%d name='%s' mode=%s steps=%s "
        "max_steps=%d timeout=%ds user=%s message='%s'",
        workflow.id,
        workflow.name,
        mode,
        step_names,
        workflow.max_steps,
        workflow.timeout_seconds,
        user.email if user else "?",
        user_message[:100],
    )

    # Check for a paused execution to resume
    paused_execution = None
    if chat_session_id:
        paused_execution = get_paused_execution(
            db_session, workflow.id, chat_session_id
        )
        if paused_execution:
            logger.info(
                "[Workflow] RESUME paused execution_id=%d paused_at_step_id=%s "
                "checkpoint_keys=%s",
                paused_execution.id,
                paused_execution.paused_at_step_id,
                list(paused_execution.checkpoint_data.keys())
                if paused_execution.checkpoint_data else "none",
            )

    workflow_start = time.monotonic()

    if mode == "sequential":
        run_sequential = (
            run_workflow_sequential_v2
            if WORKFLOW_ENGINE_V2
            else run_workflow_sequential
        )
        yield from run_sequential(
            workflow, user_message, emitter, db_session, user,
            is_connected=is_connected,
            chat_session_id=chat_session_id,
            paused_execution=paused_execution,
            chat_files=chat_files,
            sandbox_session_id=sandbox_session_id,
            assistant_message_id=assistant_message_id,
        )
    elif mode == "llm_decision":
        yield from run_workflow_llm_decision(
            workflow, user_message, emitter, db_session, user,
            is_connected=is_connected,
            chat_session_id=chat_session_id,
            paused_execution=paused_execution,
            chat_files=chat_files,
            sandbox_session_id=sandbox_session_id,
            assistant_message_id=assistant_message_id,
        )
    else:
        raise ValueError(f"Unsupported orchestration mode: {mode}")

    total_elapsed = time.monotonic() - workflow_start
    logger.info(
        "[Workflow] END workflow_id=%d name='%s' total_time=%.1fs",
        workflow.id,
        workflow.name,
        total_elapsed,
    )
