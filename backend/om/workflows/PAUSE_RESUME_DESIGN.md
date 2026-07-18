# Enterprise-Grade Pause/Resume for Workflow Engine

## Status: Design Complete — Implementation Pending

---

## Context

The HITL (Human-in-the-Loop) test revealed that **pause works correctly but resume is broken**. When a paused workflow resumes after user input:

- **Sequential mode**: User's answer is concatenated as a flat string — agent doesn't see a proper conversation history
- **LLM-Decision mode**: User's answer is injected as `TOOL_CALL_RESPONSE` telling orchestrator "please re-call the agent" — orchestrator LLM **ignores the instruction** and proceeds with other agents using incomplete data

### Test Evidence

```
Round 0: "I want to go to Bali"     → PASS (paused, asked 8 questions)
Round 1: "March, about 5 days"      → FAIL (orchestrator skipped Details Collector,
                                            ran all remaining agents with incomplete data)
```

Logs confirmed: resume worked mechanically (checkpoint loaded, call count decremented), but orchestrator LLM decided not to re-call the Details Collector.

---

## Enterprise Patterns (Research)

### How Other Frameworks Handle Resume

| Framework | On Resume | Who Runs Next |
|-----------|-----------|---------------|
| **LangGraph** | Same node **re-runs from scratch** with user input as `interrupt()` return value | Graph router decides after node completes |
| **CrewAI** | Task **re-runs** with feedback appended to message history | Crew coordinator continues after approval |
| **AWS Bedrock** | Agent **continues** with invocation results injected | Agent's LLM orchestrator decides |

### Key Insight

LangGraph and CrewAI (most relevant to our case) **RE-RUN the paused agent/node directly** rather than asking an orchestrator to re-call it. The orchestrator is bypassed during the resume re-call. Only after the agent finishes does the orchestrator regain control.

### Three Philosophies

| Philosophy | Framework | Pattern |
|-----------|-----------|---------|
| **Node-level Restart** | LangGraph | Pause within node → user input → entire node re-runs → router decides next |
| **Task-level Iteration** | CrewAI | Pause after task output → user feedback → task re-runs with feedback → coordinator continues |
| **Continuation** | AWS Bedrock | Pause at action → external execution → agent continues with results |

---

## Design: Direct Agent Re-Call on Resume

### Core Principle

On resume, the engine **force-runs the paused agent directly** (deterministic, no LLM compliance needed). The orchestrator is bypassed for the re-call. After the agent finishes, its output is injected into the orchestrator's history and the orchestrator loop continues normally.

### Flow Diagrams

**Sequential Mode Resume:**
```
User sends answer
  → load_checkpoint()
  → has clarification_conversation? YES
  → append user's answer to conversation
  → _build_clarification_task(original_task, conversation)
  → skip completed steps, reach paused step
  → run agent with built task (NOT _apply_input_mapping)
  → agent still needs info? → re-pause with accumulated conversation
  → agent finished? → store output, continue to next step
```

**LLM-Decision Mode Resume:**
```
User sends answer
  → load_checkpoint()
  → has clarification_conversation? YES
  → append user's answer to conversation
  → _build_clarification_task(original_task, conversation)
  → find paused agent via tools_by_step_id
  → run agent DIRECTLY (bypass orchestrator)
  → agent still needs info? → re-pause with accumulated conversation
  → agent finished?
    → inject synthetic tool_call + response into msg_history
    → store output in context.step_outputs
    → fall through to orchestrator loop (decides next agent normally)
```

---

## Phase 1: Checkpoint Enhancement

### File: `backend/om/workflows/models.py`

Add 2 fields to `WorkflowCheckpoint` (lines 157-171):

```python
class WorkflowCheckpoint(BaseModel):
    step_outputs: dict[str, str] = {}
    shared_data: dict[str, Any] = {}
    completed_step_ids: list[int] = []
    orchestrator_history: list[dict] = []
    cycle_count: int = 0
    agent_call_counts: dict[str, int] = {}
    turn_index: int = 0
    # NEW
    clarification_conversation: list[dict[str, str]] = []   # [{"role": "agent"|"user", "content": "..."}]
    paused_agent_original_task: str = ""                     # task string given to the paused agent
```

**`clarification_conversation`** accumulates across rounds:

| Round | Conversation State |
|-------|-------------------|
| 1 (first pause) | `[{agent: "What dates? How many travelers?"}]` |
| 2 (resume + re-pause) | `[{agent: "What dates?..."}, {user: "March, 5 days"}, {agent: "How many travelers?"}]` |
| 3 (resume + finish) | Conversation cleared, agent produces final structured output |

**`paused_agent_original_task`**: The exact task string the agent originally received.
- Sequential mode: output of `_apply_input_mapping()`
- LLM-Decision mode: orchestrator's `tool_call.tool_args["task"]`

No DB migration needed — stored in existing `checkpoint_data` JSONB column with Pydantic defaults.

---

## Phase 2: Clarification Task Builder

### File: `backend/om/workflows/workflow_engine.py` — new helper functions

```python
def _build_clarification_task(
    original_task: str,
    clarification_conversation: list[dict[str, str]],
) -> str:
    """Build a structured prompt for an agent resuming from clarification."""
    parts = [f"TASK:\n{original_task}"]

    if clarification_conversation:
        conv_lines = []
        for entry in clarification_conversation:
            label = "You previously asked" if entry["role"] == "agent" else "The user responded"
            conv_lines.append(f"{label}:\n{entry['content']}")
        parts.append(f"\nCLARIFICATION HISTORY:\n" + "\n\n".join(conv_lines))

    parts.append(
        "\nINSTRUCTIONS: You now have the user's responses above. "
        "If you have all the information you need, produce your complete "
        "final output. If you still need more details, ask your follow-up questions."
    )
    return "\n\n".join(parts)


def _strip_needs_input_prefix(output: str) -> str:
    """Strip [NEEDS_INPUT] prefix from agent output before saving to conversation."""
    stripped = output.strip()
    if stripped.upper().startswith(_NEEDS_INPUT_PREFIX):
        return stripped[len(_NEEDS_INPUT_PREFIX):].strip()
    return stripped
```

**What the agent sees on round 2 resume:**
```
TASK:
<original task from orchestrator or input_mapping>

CLARIFICATION HISTORY:
You previously asked:
What dates are you planning? How many travelers? Budget?

The user responded:
Sometime in March, about 5 days

INSTRUCTIONS: You now have the user's responses above. If you have all
the information you need, produce your complete final output. If you
still need more details, ask your follow-up questions.
```

---

## Phase 3: Sequential Mode Changes

### File: `backend/om/workflows/workflow_engine.py`

### 3.1 First Pause — Save original task (lines ~661-678)

When agent first pauses, capture the task it received AND the agent's questions:

```python
pause_checkpoint = WorkflowCheckpoint(
    step_outputs=dict(context.step_outputs),
    shared_data={**context.shared_data, "_original_user_input": context.user_input},
    completed_step_ids=[...],
    turn_index=turn_index,
    # NEW
    paused_agent_original_task=task_input,  # from _apply_input_mapping() at line 598
    clarification_conversation=[
        {"role": "agent", "content": _strip_needs_input_prefix(agent_output)},
    ],
)
```

### 3.2 Resume — Conversation-aware re-call (lines ~467-497)

Replace the flat-string concatenation with:

```python
if paused_execution:
    checkpoint = load_checkpoint(paused_execution)
    if checkpoint and checkpoint.clarification_conversation:
        # Conversation-aware resume
        conversation = list(checkpoint.clarification_conversation)
        conversation.append({"role": "user", "content": user_message})

        resume_task = _build_clarification_task(
            checkpoint.paused_agent_original_task,
            conversation,
        )

        # Restore context with ORIGINAL user_input (not concatenated)
        original_input = checkpoint.shared_data.get("_original_user_input", user_message)
        context = WorkflowContext(
            user_input=original_input,
            step_outputs=checkpoint.step_outputs,
            shared_data=checkpoint.shared_data,
        )
        resume_task_override = resume_task
        resume_conversation = conversation
    else:
        # Existing logic (crash recovery / no clarification)
        ...
```

### 3.3 Use override when running paused step (lines ~596-608)

```python
if resume_task_override and step.id == paused_step_id:
    task_input = resume_task_override
else:
    task_input = _apply_input_mapping(step.input_mapping, context)
```

### 3.4 Re-pause with accumulated conversation (lines ~654-712)

```python
if step.can_request_input and _agent_requests_input(agent_output):
    accumulated = list(resume_conversation) if resume_conversation else []
    accumulated.append({"role": "agent", "content": _strip_needs_input_prefix(agent_output)})

    pause_checkpoint = WorkflowCheckpoint(
        ...,
        paused_agent_original_task=(
            checkpoint.paused_agent_original_task if checkpoint else task_input
        ),
        clarification_conversation=accumulated,
    )
```

---

## Phase 4: LLM-Decision Mode Changes

### File: `backend/om/workflows/workflow_engine.py`

### 4.1 First Pause — Save original task (lines ~1280-1302)

```python
pause_checkpoint = WorkflowCheckpoint(
    ...,
    orchestrator_history=_serialize_history(msg_history),
    cycle_count=cycle + 1,
    agent_call_counts=dict(agent_call_counts),
    # NEW
    paused_agent_original_task=tool_call.tool_args.get("task", ""),
    clarification_conversation=[
        {"role": "agent", "content": _strip_needs_input_prefix(agent_output)},
    ],
)
```

### 4.2 Resume — Direct agent re-call BEFORE orchestrator loop (lines ~948-998)

**Remove** the current `TOOL_CALL_RESPONSE` injection (lines 920-929). Replace with direct agent execution:

```python
if checkpoint and checkpoint.clarification_conversation:
    # === Direct agent re-call (bypasses orchestrator) ===
    conversation = list(checkpoint.clarification_conversation)
    conversation.append({"role": "user", "content": user_message})

    built_task = _build_clarification_task(
        checkpoint.paused_agent_original_task,
        conversation,
    )

    paused_tool = tools_by_step_id.get(paused_step_id)
    paused_step = steps_by_id.get(paused_step_id)

    if paused_tool and paused_step:
        # Run agent directly (bypass orchestrator)
        turn_index += 1
        agent_placement = Placement(turn_index=turn_index)
        yield Packet(placement=agent_placement, obj=WorkflowStepStart(...))

        streaming_result = _StreamingAgentResult(start_turn_index=turn_index)
        yield from _stream_agent_packets(
            agent_tool=paused_tool,
            placement=agent_placement,
            emitter=emitter,
            result=streaming_result,
            is_connected=is_connected,
            task=built_task,
        )
        agent_output = streaming_result.final_output

        if paused_step.can_request_input and _agent_requests_input(agent_output):
            # Still needs more info — re-pause with accumulated conversation
            conversation.append({"role": "agent", "content": _strip_needs_input_prefix(agent_output)})
            pause_checkpoint = WorkflowCheckpoint(
                ...,
                orchestrator_history=_serialize_history(msg_history),
                clarification_conversation=conversation,
                paused_agent_original_task=checkpoint.paused_agent_original_task,
            )
            save_checkpoint(db_session, execution.id, pause_checkpoint, paused_step_id)
            yield Packet(placement=agent_placement, obj=WorkflowPauseForInput(...))
            return  # Stop execution

        # Agent finished — inject result into orchestrator history
        context.step_outputs[paused_step.output_key] = agent_output

        # Synthesize tool_call + response so orchestrator sees the result
        synthetic_id = f"resume_{paused_step_id}_{cycle_start}"
        msg_history.append(ChatMessageSimple(
            message=json.dumps({
                "tool_call_id": synthetic_id,
                "name": paused_tool.name,
                "arguments": {"task": built_task},
            }),
            token_count=50,
            message_type=MessageType.ASSISTANT,
        ))
        summarized = _summarize_for_orchestrator(paused_tool.display_name, agent_output)
        msg_history.append(ChatMessageSimple(
            message=summarized,
            token_count=token_counter(summarized),
            message_type=MessageType.TOOL_CALL_RESPONSE,
        ))

        # Clear clarification state, fall through to orchestrator loop
        # Orchestrator sees agent's final output and decides next agent normally
```

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/om/workflows/models.py` | Add `clarification_conversation` + `paused_agent_original_task` to `WorkflowCheckpoint` |
| `backend/om/workflows/workflow_engine.py` | Add `_build_clarification_task()`, `_strip_needs_input_prefix()`. Modify sequential resume, sequential first-pause, llm_decision resume, llm_decision first-pause |

No other files need changes. No DB migration. No frontend changes.

---

## Verification

1. **Restart API server** after code changes (bind-mounted, restart picks up changes)
2. **Run test**: `cd backend/tests/workflow_creator && python test_hitl.py --workflow-id 17`
3. **Expected results**:
   - Round 0: PAUSE (agent asks for missing details)
   - Round 1: PAUSE (agent asks for more — dates provided but missing travelers/budget)
   - Round 2: PAUSE (agent asks for remaining — missing budget/interests)
   - Round 3: COMPLETE (all details collected, workflow runs all 6 agents)
4. **Check logs**: `docker logs onyx-api_server-1 | grep -i "\[Workflow\]"` — verify RESUME and direct agent re-call
5. **Backward compatibility**: Run existing Travel Planner (ID=14, no `can_request_input`) — should work identically

---

## Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Agent finishes on first resume | Normal path — output stored, orchestrator continues |
| Multiple clarification rounds | `clarification_conversation` accumulates, `_build_clarification_task()` includes full history |
| Checkpoint corruption | Existing fallback: `load_checkpoint()` returns None → fresh execution |
| `paused_agent_original_task` empty | Degrade to flat-string approach as fallback, log warning |
| Step deleted between pause/resume | `tools_by_step_id.get()` returns None → mark execution failed, start fresh |
| `can_request_input=False` steps | Never reaches pause detection — no behavioral change, new fields stay at defaults |
| Context window limit | `_MAX_CLARIFICATION_ROUNDS = 5` — truncate oldest rounds in `_build_clarification_task()` |
| Concurrent resumes | First resume sets status="running", second finds no paused execution → starts fresh |

---

## Bugs Fixed During Testing

| Bug | File | Fix |
|-----|------|-----|
| `/workflow/{id}/run` didn't pass `chat_session_id` to engine | `backend/om/server/features/workflow/api.py` | Added `chat_session_id=run_request.chat_session_id` |
| `WorkflowRunRequest.chat_session_id` was `int` instead of `UUID` | `backend/om/workflows/models.py` | Changed to `UUID \| None` |
