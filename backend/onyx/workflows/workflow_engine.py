"""Multi-Agent Workflow Engine.

Orchestrates multiple personas (agents) in sequence or via LLM-driven routing.
Mirrors the proven Deep Research pattern from dr_loop.py but generalized to
support any number of persona-based sub-agents.
"""

import json
import time
from collections.abc import Generator
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
from onyx.utils.logger import setup_logger
from onyx.workflows.models import WorkflowContext

logger = setup_logger()


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
) -> list[AgentTool]:
    """Build AgentTool instances for each workflow step's persona."""
    agent_tools = []
    for step in steps:
        persona = db_session.get(Persona, step.persona_id)
        if persona is None or persona.deleted:
            logger.warning(
                f"Persona {step.persona_id} not found for workflow step {step.id}"
            )
            continue
        agent_tools.append(
            AgentTool(
                persona=persona,
                emitter=emitter,
                db_session=db_session,
                step_name=step.step_name,
                step_order=step.step_order,
                step_id=step.id,
                output_key=step.output_key,
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

IMPORTANT:
- Call ONE agent at a time with a clear task description
- After receiving an agent's output, decide whether to call another agent or provide the final answer
- When you have enough information, provide the final answer directly (without calling any more agents)
- Be specific in your task delegation — tell the agent exactly what you need

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
            # Replace $step_name.output with actual step output
            for step_name, output in context.step_outputs.items():
                resolved = resolved.replace(f"${step_name}.output", output)
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

    try:
        for i, step in enumerate(steps):
            step_start_time = time.monotonic()
            persona = db_session.get(Persona, step.persona_id)
            if persona is None or persona.deleted:
                logger.warning(f"Skipping step {step.step_name}: persona not found")
                continue

            placement = Placement(turn_index=i)

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

            # Create and run the agent tool
            agent_tool = AgentTool(
                persona=persona,
                emitter=emitter,
                db_session=db_session,
                step_name=step.step_name,
                step_order=step.step_order,
            )

            result = agent_tool.run(
                placement=placement,
                override_kwargs=None,
                task=task_input,
            )

            # Extract output from result
            try:
                result_data = json.loads(result.llm_facing_response)
                agent_output = result_data.get("agent_output", "")
            except (json.JSONDecodeError, AttributeError):
                agent_output = result.llm_facing_response or ""

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
            status="completed",
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
        placement=Placement(turn_index=len(steps)),
        obj=OverallStop(type="stop"),
    )


def run_workflow_llm_decision(
    workflow: AgentWorkflow,
    user_message: str,
    emitter: Emitter,
    db_session: Session,
    user: User,
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

    # Build agent tools
    agent_tools = _build_agent_tools(steps, emitter, db_session)
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

    try:
        for cycle in range(workflow.max_steps):
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

            # Call orchestrator LLM
            tool_defs = [tool.tool_definition() for tool in agent_tools]
            tool_choice = ToolChoiceOptions.AUTO
            citation_processor = DynamicCitationProcessor()

            llm_step_result, has_reasoned = run_llm_step(
                emitter=emitter,
                history=truncated_history,
                tool_definitions=tool_defs,
                tool_choice=tool_choice,
                llm=orchestrator_llm,
                placement=placement,
                citation_processor=citation_processor,
                state_container=state_container,
                final_documents=None,
                user_identity=None,
            )

            if has_reasoned:
                turn_index += 1

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
                break

            # Emit orchestrator thinking if there's text alongside tool calls (H1)
            if llm_step_result.answer and llm_step_result.tool_calls:
                yield Packet(
                    placement=placement,
                    obj=WorkflowOrchestratorThinking(
                        content=llm_step_result.answer,
                    ),
                )

            # Process tool calls (agent delegations)
            if llm_step_result.tool_calls:
                for tool_call in llm_step_result.tool_calls:
                    agent_tool = tools_by_name.get(tool_call.tool_name)
                    if agent_tool is None:
                        logger.warning(
                            f"Unknown agent tool: {tool_call.tool_name}"
                        )
                        continue

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

                    # Run the agent
                    result = agent_tool.run(
                        placement=agent_placement,
                        override_kwargs=None,
                        **tool_call.tool_args,
                    )

                    # Extract output
                    try:
                        result_data = json.loads(result.llm_facing_response)
                        agent_output = result_data.get("agent_output", "")
                    except (json.JSONDecodeError, AttributeError):
                        agent_output = result.llm_facing_response or ""

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

                    tool_response_msg = ChatMessageSimple(
                        message=result.llm_facing_response or "",
                        token_count=token_counter(
                            result.llm_facing_response or ""
                        ),
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

                turn_index += 1
            else:
                # No answer and no tool calls — unusual, break
                logger.warning("Orchestrator produced no answer and no tool calls")
                break

        total_duration_ms = int((time.monotonic() - start_time) * 1000)
        update_workflow_execution(
            db_session,
            execution.id,
            status="completed",
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

    # Emit overall stop
    yield Packet(
        placement=Placement(turn_index=turn_index + 1),
        obj=OverallStop(type="stop"),
    )


def run_workflow(
    workflow: AgentWorkflow,
    user_message: str,
    emitter: Emitter,
    db_session: Session,
    user: User,
) -> Generator[Packet, None, None]:
    """Main entry point — dispatches to the appropriate orchestration mode."""
    mode = workflow.orchestration_mode

    if mode == "sequential":
        yield from run_workflow_sequential(
            workflow, user_message, emitter, db_session, user
        )
    elif mode == "llm_decision":
        yield from run_workflow_llm_decision(
            workflow, user_message, emitter, db_session, user
        )
    else:
        raise ValueError(f"Unsupported orchestration mode: {mode}")
