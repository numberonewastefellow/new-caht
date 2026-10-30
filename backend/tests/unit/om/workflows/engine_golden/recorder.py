"""Run a scenario through an engine implementation and normalise everything it
did into a JSON-serialisable recording."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Callable
from uuid import UUID

from om.chat.emitter import get_default_emitter
from om.tools.models import ChatFile

from tests.unit.om.workflows.engine_golden import fake_layer
from tests.unit.om.workflows.engine_golden.builder import AgentRegistry
from tests.unit.om.workflows.engine_golden.builder import build_workflow
from tests.unit.om.workflows.engine_golden.builder import describe_workflow
from tests.unit.om.workflows.engine_golden.engines import EngineFn

CHAT_SESSION_ID = UUID("00000000-0000-4000-8000-000000000001")
USER_ID = UUID("00000000-0000-4000-8000-0000000000aa")


@dataclass
class RunSpec:
    message: str
    message_id: int
    # Replace the workflow definition before this run (a workflow "edit": steps
    # are recreated with new ids, like update_workflow() does).
    definition: dict[str, Any] | None = None
    step_id_base: int | None = None
    # Mutate the fake DB before the run (e.g. downgrade a checkpoint).
    mutate_db: Callable[[fake_layer.FakeSession], None] | None = None
    # Set the stop flag as soon as WorkflowStepEnd for this step is yielded.
    stop_after_step_end: str | None = None
    chat_files: list[str] | None = None


@dataclass
class Scenario:
    name: str
    description: str
    definition: dict[str, Any]
    runs: list[RunSpec]
    agent_script: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    orchestrator_script: list[dict[str, Any]] | None = None
    mode_override: str | None = None
    covers: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

_TS_KEYS = {"started_at", "ended_at", "completed_at"}
_MS_KEYS = {"duration_ms", "total_duration_ms"}


def normalize(value: Any) -> Any:
    """Strip nondeterminism: timestamps -> "<ts>", durations -> "<ms>"."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if k in _TS_KEYS and v is not None:
                out[k] = "<ts>"
            elif k in _MS_KEYS and v is not None:
                out[k] = "<ms>"
            else:
                out[k] = normalize(v)
        return out
    if isinstance(value, (list, tuple)):
        return [normalize(v) for v in value]
    if isinstance(value, UUID):
        return str(value)
    return value


def packet_to_json(pkt: Any) -> dict[str, Any]:
    p = pkt.placement
    body = pkt.obj.model_dump(mode="json", exclude={"type"})
    rec: dict[str, Any] = {
        "type": pkt.obj.type,
        "placement": [p.turn_index, p.tab_index, p.sub_turn_index],
    }
    rec.update({k: v for k, v in body.items() if v is not None})
    return rec


def _messages(packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group top-level message_start/message_delta blocks (the main answer)."""
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for p in packets:
        if p["type"] == "message_start":
            current = {"turn_index": p["placement"][0], "content": "", "file_ids": [], "file_names": []}
            blocks.append(current)
        elif p["type"] == "message_delta" and current is not None:
            current["content"] += p.get("content", "")
            current["file_ids"] += p.get("file_ids") or []
            current["file_names"] += p.get("file_names") or []
        elif p["type"] == "section_end":
            current = None
    return blocks


def _execution_state(e: Any) -> dict[str, Any]:
    return {
        "id": e.id,
        "workflow_id": e.workflow_id,
        "status": e.status,
        "paused_at_step_id": e.paused_at_step_id,
        "has_checkpoint": bool(e.checkpoint_data),
        "completed_at_set": e.completed_at is not None,
        "error_message": e.error_message,
        "total_tokens": e.total_tokens,
        "total_duration_ms": e.total_duration_ms,
        "steps_executed": copy.deepcopy(e.steps_executed),
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_scenario(scenario: Scenario, engine: EngineFn, monkeypatch: Any) -> dict[str, Any]:
    state = fake_layer.HarnessState(scenario.agent_script, scenario.orchestrator_script)
    fake_layer.install(monkeypatch, state)

    registry = AgentRegistry()
    workflow = build_workflow(scenario.definition, registry, mode_override=scenario.mode_override)
    session = fake_layer.FakeSession(registry.by_id)
    session.steps_by_id = {s.id: s for s in workflow.steps}
    user = type("FakeUser", (), {"id": USER_ID, "email": "golden@example.com"})()

    recording: dict[str, Any] = {
        "scenario": scenario.name,
        "description": scenario.description,
        "covers": scenario.covers,
        "runs": [],
    }

    for run_index, run in enumerate(scenario.runs):
        if run.definition is not None or run.step_id_base is not None:
            workflow = build_workflow(
                run.definition if run.definition is not None else scenario.definition,
                registry,
                step_id_base=run.step_id_base or 101,
                mode_override=scenario.mode_override,
            )
            session.agents_by_id = registry.by_id
            session.steps_by_id = {s.id: s for s in workflow.steps}
        if run.mutate_db is not None:
            run.mutate_db(session)

        state.begin_run(run_index)
        emitter = get_default_emitter()
        chat_files = (
            [ChatFile(filename=f, content=b"x") for f in run.chat_files]
            if run.chat_files
            else None
        )
        packets: list[dict[str, Any]] = []
        raised: dict[str, str] | None = None
        try:
            gen = engine(
                workflow=workflow,
                user_message=run.message,
                emitter=emitter,
                db_session=session,
                user=user,
                is_connected=lambda: not state.stop.is_set(),
                chat_session_id=CHAT_SESSION_ID,
                chat_files=chat_files,
                sandbox_session_id=None,
                assistant_message_id=run.message_id,
            )
            for pkt in gen:
                packets.append(packet_to_json(pkt))
                if (
                    run.stop_after_step_end
                    and pkt.obj.type == "workflow_step_end"
                    and pkt.obj.step_name == run.stop_after_step_end
                ):
                    state.stop.set()
        except Exception as e:  # noqa: BLE001 - recorded, not swallowed silently
            raised = {"type": type(e).__name__, "message": str(e)}
        finally:
            state.end_run()

        messages = _messages(packets)
        exec_ids = sorted(session.executions)
        latest_exec = session.executions[exec_ids[-1]] if exec_ids else None
        trace = trace_msg = None
        if latest_exec is not None:
            trace = state.file_store.read_json(f"wftrace_{latest_exec.id}")
            trace_msg = state.file_store.read_json(f"wftrace_msg_{run.message_id}")

        recording["runs"].append(
            {
                "user_message": run.message,
                "message_id": run.message_id,
                "workflow": describe_workflow(workflow),
                "raised": raised,
                "packets": packets,
                "messages": messages,
                "final_answer": messages[-1]["content"] if messages else None,
                "agent_calls": copy.deepcopy(state.agent_calls),
                "orchestrator_calls": copy.deepcopy(state.orchestrator_calls),
                "checkpoints": _compact_checkpoints(state.checkpoints),
                "final_step_outputs": (
                    state.checkpoints[-1]["checkpoint"]["step_outputs"]
                    if state.checkpoints
                    else None
                ),
                "trace_persists": copy.deepcopy(state.trace_persists),
                "trace": trace,
                "trace_by_message_matches_execution_trace": (
                    None if trace_msg is None else trace_msg == trace
                ),
                "executions": [_execution_state(session.executions[i]) for i in exec_ids],
            }
        )

    return normalize(recording)


def _compact_checkpoints(checkpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Checkpoints verbatim, except orchestrator history entries are digested
    (the system prompt alone can be several KB and repeats in every save)."""
    out = copy.deepcopy(checkpoints)
    for c in out:
        hist = c["checkpoint"].get("orchestrator_history") or []
        c["checkpoint"]["orchestrator_history"] = [
            [h.get("message_type"), h.get("token_count"), fake_layer.digest_text(h.get("message", ""))]
            for h in hist
        ]
    return out
