"""Every golden scenario: the 47 templates plus inline fixtures for paths no
template covers.

Naming:
  <template_stem>                  template forced into sequential mode
  <template_stem>__llm_decision    llm_decision templates, scripted orchestrator
  fx_<name>                        inline fixture
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from tests.unit.om.workflows.engine_golden.fake_layer import FakeSession
from tests.unit.om.workflows.engine_golden.recorder import RunSpec
from tests.unit.om.workflows.engine_golden.recorder import Scenario

TEMPLATE_DIR = Path(__file__).resolve().parents[4] / "workflow_creator" / "workflows"

TEMPLATE_INPUT = (
    "Prepare a complete assessment for case GOLD-001 covering all required sections."
)
RESUME_INPUT = (
    "Here are the missing details: budget 5000 USD, deadline Friday, region South."
)
RESUME_INPUT_2 = "Region is South-East and the audience is the district board."

NEEDS_INPUT = {"kind": "needs_input"}
NORMAL: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def template_paths() -> list[Path]:
    return sorted(TEMPLATE_DIR.glob("*.json"))


def _template_agent_script(defn: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    script: dict[str, list[dict[str, Any]]] = {}
    steps = sorted(defn["steps"], key=lambda s: s["step_order"])
    hitl = [s for s in steps if s.get("can_request_input")]
    if hitl:
        script[hitl[0]["step_name"]] = [dict(NEEDS_INPUT)]
    # Office/MCP builder agents "create" a document, so step_files + the final
    # file de-dup run on real template shapes.
    for s in steps:
        if (s.get("agent_def") or {}).get("tool_names"):
            calls = script.setdefault(s["step_name"], [])
            ext = ".pptx" if "ppt" in json.dumps(s["agent_def"]["tool_names"]).lower() else ".docx"
            # If the step's first call pauses, the resumed call creates the file.
            calls.append({"files": [f"{s['output_key']}{ext}"]})
    return script


def _template_runs(defn: dict[str, Any]) -> list[RunSpec]:
    runs = [RunSpec(TEMPLATE_INPUT, message_id=5001)]
    if any(s.get("can_request_input") for s in defn["steps"]):
        runs.append(RunSpec(RESUME_INPUT, message_id=5002))
    return runs


def _template_orchestrator_script(defn: dict[str, Any]) -> list[dict[str, Any]]:
    script: list[dict[str, Any]] = []
    for i, s in enumerate(sorted(defn["steps"], key=lambda s: s["step_order"])):
        d: dict[str, Any] = {
            "call": s.get("agent_name") or s["agent_def"]["name"],
            "task": f"Step '{s['step_name']}': work on: {TEMPLATE_INPUT}",
            "reasoning": i == 0,
        }
        if i % 2 == 0:
            d["thinking"] = f"Next I will delegate to {s['step_name']}."
        script.append(d)
    script.append({"answer": "Final synthesis: all specialists were consulted."})
    return script


def template_scenarios() -> list[Scenario]:
    out: list[Scenario] = []
    for path in template_paths():
        defn = json.loads(path.read_text(encoding="utf-8"))
        stem = path.stem
        out.append(
            Scenario(
                name=stem,
                description=f"Template {path.name} forced into sequential mode.",
                definition=defn,
                runs=_template_runs(defn),
                agent_script=_template_agent_script(defn),
                mode_override="sequential",
                covers=["template", "sequential"],
            )
        )
        if defn.get("orchestration_mode") == "llm_decision":
            out.append(
                Scenario(
                    name=f"{stem}__llm_decision",
                    description=(
                        f"Template {path.name} in llm_decision mode; the fake "
                        "orchestrator calls every step's agent once in step_order, "
                        "then answers."
                    ),
                    definition=defn,
                    runs=_template_runs(defn),
                    agent_script=_template_agent_script(defn),
                    orchestrator_script=_template_orchestrator_script(defn),
                    mode_override="llm_decision",
                    covers=["template", "llm_decision"],
                )
            )
    return out


# ---------------------------------------------------------------------------
# Inline fixture helpers
# ---------------------------------------------------------------------------


def agent_step(order: int, name: str, key: str, **kw: Any) -> dict[str, Any]:
    agent_def = kw.pop("agent_def", {})
    return {
        "step_name": name,
        "step_order": order,
        "output_key": key,
        "agent_def": {"name": f"FX {name}", "description": f"Fixture agent {name}", **agent_def},
        **kw,
    }


def router_step(
    order: int, name: str, key: str, field: str, operator: str, value: str,
    true_steps: list[int], false_steps: list[int],
) -> dict[str, Any]:
    return {
        "step_type": "conditional_router",
        "step_name": name,
        "step_order": order,
        "output_key": key,
        "condition": {
            "condition_field": field,
            "operator": operator,
            "match_value": value,
            "true_steps": true_steps,
            "false_steps": false_steps,
        },
    }


def wf(name: str, steps: list[dict[str, Any]], mode: str = "sequential", **kw: Any) -> dict[str, Any]:
    return {"name": name, "orchestration_mode": mode, "steps": steps, **kw}


def _abc(mode: str = "sequential", **kw: Any) -> dict[str, Any]:
    return wf(
        "FX three steps",
        [agent_step(0, "Alpha", "alpha"), agent_step(1, "Beta", "beta"), agent_step(2, "Gamma", "gamma")],
        mode=mode,
        **kw,
    )


def _hitl_def(mode: str = "sequential") -> dict[str, Any]:
    return wf(
        "FX HITL",
        [
            agent_step(0, "Intake", "intake"),
            agent_step(1, "Clarifier", "clarified", can_request_input=True),
            agent_step(2, "Writer", "final_doc"),
        ],
        mode=mode,
    )


def _router_def(name: str) -> dict[str, Any]:
    return wf(
        name,
        [
            agent_step(0, "Classifier", "a"),
            router_step(1, "Route", "route", "$a.output", "contains", "urgent", [2], [3]),
            agent_step(2, "Urgent Handler", "urgent"),
            agent_step(3, "Routine Handler", "routine"),
            agent_step(4, "Summary", "summary", input_mapping={"route": "$route", "classification": "$a"}),
        ],
    )


def _strip_clarification(session: FakeSession) -> None:
    """Downgrade the paused checkpoint to the pre-'enterprise' format."""
    for e in session.executions.values():
        if e.status == "paused" and e.checkpoint_data:
            data = dict(e.checkpoint_data)
            data.pop("clarification_conversation", None)
            data.pop("paused_agent_original_task", None)
            e.checkpoint_data = data


def _corrupt_checkpoint(session: FakeSession) -> None:
    for e in session.executions.values():
        if e.status == "paused":
            e.checkpoint_data = {"step_outputs": "not-a-dict"}


def _llmd_abc_script(*extra: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"call": "FX Alpha", "task": "Collect the facts", "thinking": "Start with Alpha.", "reasoning": True},
        {"call": "FX Beta", "task": "Analyse the facts from Alpha"},
        {"call": "FX Gamma", "task": "Write the final report", "thinking": "Gamma writes it up."},
        *extra,
        {"answer": "Orchestrator final answer: report complete."},
    ]


# ---------------------------------------------------------------------------
# Inline fixtures
# ---------------------------------------------------------------------------


def fixture_scenarios() -> list[Scenario]:
    S = Scenario
    R = RunSpec
    I = TEMPLATE_INPUT  # noqa: E741
    fx: list[Scenario] = []

    # ---- conditional router -------------------------------------------------
    fx.append(S(
        "fx_router_true", "Router evaluates TRUE: false_steps [3] skipped, router output 'true' visible via $route.",
        _router_def("FX router true"), [R(I, 5001)],
        agent_script={"Classifier": [{"output": "URGENT: water main burst on 5th street"}]},
        covers=["conditional_router", "true_steps/false_steps", "router output substitution"],
    ))
    fx.append(S(
        "fx_router_false", "Router evaluates FALSE: true_steps [2] skipped.",
        _router_def("FX router false"), [R(I, 5001)],
        agent_script={"Classifier": [{"output": "routine maintenance request"}]},
        covers=["conditional_router"],
    ))
    fx.append(S(
        "fx_router_chain",
        "Router after a router (R2 reads R1's 'true'), a router inside a skipped branch "
        "(R4, never evaluated), a router on an unresolved reference (R3: $missing is_empty "
        "-> TRUE), and a final mapping that references an unset router key ($r4 stays literal).",
        wf("FX router chain", [
            agent_step(0, "Scorer", "a"),
            router_step(1, "R1", "r1", "$a.output", "contains", "urgent", [2, 3], [6]),
            router_step(2, "R2", "r2", "$r1", "equals", "true", [3], [4]),
            agent_step(3, "B", "b"),
            agent_step(4, "C", "c"),
            router_step(5, "R3", "r3", "$missing", "is_empty", "", [], [7]),
            router_step(6, "R4", "r4", "$a.output", "contains", "never", [], []),
            agent_step(7, "E", "e"),
            agent_step(8, "F", "final", input_mapping={
                "routing": "r1=$r1 r2=$r2 r3=$r3 r4=$r4", "b": "$b.output",
            }),
        ]),
        [R(I, 5001)],
        agent_script={"Scorer": [{"output": "urgent: score 7"}]},
        covers=["router after router", "router in skipped branch", "unresolved router reference"],
    ))
    fx.append(S(
        "fx_router_skip_lost_on_resume",
        "Router TRUE skips step 3, then step 2 pauses. On resume the skip set is NOT restored "
        "(it lives only in a local variable), so the inactive-branch step 3 runs. Known bug.",
        wf("FX router + pause", [
            agent_step(0, "Classifier", "a"),
            router_step(1, "Route", "route", "$a.output", "contains", "urgent", [2], [3]),
            agent_step(2, "Urgent Clarifier", "urgent", can_request_input=True),
            agent_step(3, "Routine Handler", "routine"),
            agent_step(4, "Summary", "summary"),
        ]),
        [R(I, 5001), R(RESUME_INPUT, 5002)],
        agent_script={
            "Classifier": [{"output": "urgent leak"}],
            "Urgent Clarifier": [NEEDS_INPUT],
        },
        covers=["conditional_router", "HITL resume", "BUG: skip set lost on resume"],
    ))

    # ---- HITL -----------------------------------------------------------------
    fx.append(S(
        "fx_hitl_pause_resume",
        "Step 1 pauses with [NEEDS_INPUT]; resume re-runs it with the conversation-aware task "
        "built from the saved checkpoint, then continues.",
        _hitl_def(), [R(I, 5001), R(RESUME_INPUT, 5002)],
        agent_script={"Clarifier": [NEEDS_INPUT]},
        covers=["HITL pause", "checkpoint", "conversation-aware resume"],
    ))
    fx.append(S(
        "fx_hitl_double_pause",
        "The paused step asks again after the first answer; the clarification conversation "
        "accumulates across three runs.",
        _hitl_def(), [R(I, 5001), R(RESUME_INPUT, 5002), R(RESUME_INPUT_2, 5003)],
        agent_script={"Clarifier": [
            NEEDS_INPUT,
            {"kind": "needs_input", "output": "[NEEDS_INPUT] Thanks. Which region and audience should we cover?"},
        ]},
        covers=["HITL re-pause", "clarification_conversation accumulation"],
    ))
    fx.append(S(
        "fx_hitl_detection_modes",
        "Pause detection: 'STATUS: COMPLETE' suppresses a question (no pause); a [NEEDS_INPUT] "
        "marker on a step WITHOUT can_request_input is ignored (raw marker shown); the heuristic "
        "('?' + signal word on one line) pauses.",
        wf("FX detection", [
            agent_step(0, "Completer", "done", can_request_input=True),
            agent_step(1, "Marker Without HITL", "marker"),
            agent_step(2, "Heuristic Asker", "asked", can_request_input=True),
            agent_step(3, "Writer", "final_doc"),
        ]),
        [R(I, 5001), R(RESUME_INPUT, 5002)],
        agent_script={
            "Completer": [{"output": "What is next? Nothing.\nSTATUS: COMPLETE"}],
            "Marker Without HITL": [{"output": "[NEEDS_INPUT] What budget should I assume?"}],
            "Heuristic Asker": [{"output": "Could you tell me the travel dates?\nThe rest is ready."}],
        },
        covers=["_agent_requests_input modes", "can_request_input gating"],
    ))
    fx.append(S(
        "fx_hitl_resume_after_edit",
        "Pause, then the workflow is saved again (update_workflow deletes and recreates steps, so "
        "every step id changes), then resume. completed_step_ids and paused_at_step_id no longer "
        "match: completed steps re-run and the conversation-aware task is not applied.",
        _hitl_def(),
        [R(I, 5001), R(RESUME_INPUT, 5002, step_id_base=201)],
        agent_script={"Clarifier": [NEEDS_INPUT]},
        covers=["HITL resume", "BUG: step ids recreated on edit"],
    ))
    edited = copy.deepcopy(_hitl_def())
    for s in edited["steps"]:
        s["step_order"] += 1
    edited["steps"].insert(0, agent_step(0, "New First Step", "new_first"))
    fx.append(S(
        "fx_hitl_resume_after_edit_insert_step",
        "Pause, then the workflow is edited to insert a new first step (new ids, shifted "
        "orders), then resume.",
        _hitl_def(),
        [R(I, 5001), R(RESUME_INPUT, 5002, definition=edited, step_id_base=201)],
        agent_script={"Clarifier": [NEEDS_INPUT]},
        covers=["HITL resume", "workflow edited while paused"],
    ))
    fx.append(S(
        "fx_hitl_resume_legacy_checkpoint",
        "Resume from a pre-'enterprise' checkpoint (no clarification_conversation / "
        "paused_agent_original_task): FALLBACK path folds all user messages into user_input.",
        _hitl_def(),
        [R(I, 5001), R(RESUME_INPUT, 5002, mutate_db=_strip_clarification)],
        agent_script={"Clarifier": [NEEDS_INPUT]},
        covers=["HITL fallback resume", "old checkpoint format"],
    ))
    fx.append(S(
        "fx_hitl_resume_corrupted_checkpoint",
        "Resume with unreadable checkpoint_data: the paused execution is marked failed and a "
        "fresh execution starts with the resume message as user input.",
        _hitl_def(),
        [R(I, 5001), R(RESUME_INPUT, 5002, mutate_db=_corrupt_checkpoint)],
        agent_script={"Clarifier": [NEEDS_INPUT, NEEDS_INPUT]},
        covers=["corrupted checkpoint"],
    ))

    # ---- stop / timeout / errors ---------------------------------------------
    fx.append(S(
        "fx_stop_between_steps", "Stop requested right after step Beta ends: Gamma never starts.",
        _abc(), [R(I, 5001, stop_after_step_end="Beta")],
        covers=["stop/cancel before step", "OverallStop user_cancelled"],
    ))
    fx.append(S(
        "fx_stop_mid_step",
        "Stop requested while Beta is running: the engine closes Beta's step and stops; "
        "status 'cancelled' (not terminal for update_workflow_execution, checkpoint kept).",
        _abc(), [R(I, 5001)],
        agent_script={"Beta": [{"kind": "cancel_mid"}]},
        covers=["stop/cancel mid-step"],
    ))
    fx.append(S(
        "fx_timeout_slow_step",
        "timeout_seconds=1 and Alpha takes 1.1s: the loop breaks after Alpha but the run is "
        "reported 'completed' with Alpha's output as the final answer. Known bug.",
        _abc(timeout_seconds=1), [R(I, 5001)],
        agent_script={"Alpha": [{"sleep": 1.1}]},
        covers=["timeout", "BUG: timeout reports completed"],
    ))
    fx.append(S(
        "fx_step_error", "Beta raises: execution 'failed' with the error, exception propagates.",
        _abc(), [R(I, 5001)],
        agent_script={"Beta": [{"kind": "error", "message": "beta exploded"}]},
        covers=["step error"],
    ))

    # ---- output handling --------------------------------------------------------
    fx.append(S(
        "fx_promote_output_with_files",
        "Middle step promotes its output (main message right after its step end). Because a step "
        "promoted, no final summary is emitted, only a file-links message, de-duplicated by "
        "filename (last writer wins). Default input mapping lists previous files.",
        wf("FX promote", [
            agent_step(0, "Drafter", "draft"),
            agent_step(1, "Publisher", "published", promote_output=True),
            agent_step(2, "Archiver", "archive"),
        ]),
        [R(I, 5001)],
        agent_script={
            "Drafter": [{"files": ["report.docx"]}],
            "Publisher": [{"files": ["report.docx", "summary.pdf"]}],
        },
        covers=["promote_output", "step files", "file de-dup"],
    ))
    fx.append(S(
        "fx_final_summary_files_dedup",
        "No promoted step: the final summary is the LAST output, with de-duplicated file links.",
        _abc(), [R(I, 5001)],
        agent_script={
            "Alpha": [{"files": ["report.docx"]}],
            "Beta": [{"files": ["report.docx", "chart.pptx"]}],
        },
        covers=["final summary", "file de-dup"],
    ))
    fx.append(S(
        "fx_is_terminal", "Beta is_terminal: Gamma never runs; final summary is Beta's output.",
        wf("FX terminal", [
            agent_step(0, "Alpha", "alpha"),
            agent_step(1, "Beta", "beta", is_terminal=True),
            agent_step(2, "Gamma", "gamma"),
        ]),
        [R(I, 5001)],
        covers=["is_terminal"],
    ))
    fx.append(S(
        "fx_duplicate_output_key",
        "Steps 0 and 2 share output_key 'draft'. completed_step_ids is derived from output_key, "
        "so after step 0 the checkpoint already lists step 2 as completed; on resume from the "
        "pause at step 1, step 2 is skipped. Known bug.",
        wf("FX duplicate key", [
            agent_step(0, "First Draft", "draft"),
            agent_step(1, "Reviewer", "review", can_request_input=True),
            agent_step(2, "Second Draft", "draft"),
            agent_step(3, "Finaliser", "final"),
        ]),
        [R(I, 5001), R(RESUME_INPUT, 5002)],
        agent_script={"Reviewer": [NEEDS_INPUT]},
        covers=["duplicate output_key", "BUG: completion keyed by output_key"],
    ))
    fx.append(S(
        "fx_key_substring_collision",
        "$research is replaced before $research_notes, so '$research_notes' becomes "
        "'<research output>_notes'. Known bug (plain str.replace, insertion order).",
        wf("FX collision", [
            agent_step(0, "Researcher", "research"),
            agent_step(1, "Note Taker", "research_notes"),
            agent_step(2, "Writer", "final", input_mapping={
                "notes": "$research_notes",
                "research": "$research",
                "dotted": "$research.output | $research_notes.output",
            }),
        ]),
        [R(I, 5001)],
        covers=["BUG: $key substring collision"],
    ))
    fx.append(S(
        "fx_input_mapping_forms",
        "input_mapping with $user_input, $key.output, bare $key, an unknown $ref (left "
        "literal), non-string values (str() of the value), then a step with no mapping "
        "(default: user request + every previous output).",
        wf("FX mapping", [
            agent_step(0, "Alpha", "alpha"),
            agent_step(1, "Mapper", "mapped", input_mapping={
                "q": "$user_input",
                "prev": "$alpha.output",
                "bare": "[$alpha]",
                "unknown": "$nope stays",
                "count": 3,
                "nested": {"x": "$alpha"},
            }),
            agent_step(2, "Default", "default_out"),
        ]),
        [R(I, 5001)],
        covers=["input_mapping"],
    ))
    fx.append(S(
        "fx_raw_and_empty_outputs",
        "Agent returns non-JSON text (used verbatim) and an empty output (WorkflowStepDelta "
        "replace=False).",
        _abc(), [R(I, 5001)],
        agent_script={"Alpha": [{"kind": "raw", "output": "plain text, not json"}], "Beta": [{"kind": "empty"}]},
        covers=["output parsing fallbacks"],
    ))
    fx.append(S(
        "fx_deleted_agent", "Beta's agent is deleted: the step is silently skipped.",
        wf("FX deleted agent", [
            agent_step(0, "Alpha", "alpha"),
            agent_step(1, "Beta", "beta", agent_def={"deleted": True}),
            agent_step(2, "Gamma", "gamma"),
        ]),
        [R(I, 5001)],
        covers=["missing/deleted agent"],
    ))
    overrides_steps = [
        agent_step(0, "Overridden", "over", agent_def={"tool_ids": [1]},
                   llm_provider_override="step-provider", llm_model_override="step-model",
                   max_output_tokens_override=123, system_prompt_override="SYS OVERRIDE",
                   task_prompt_override="TASK OVERRIDE", tool_ids_override=[],
                   document_set_ids_override=[7], replace_base_system_prompt_override=True),
        agent_step(1, "Agent Level LLM", "agent_llm", agent_def={
            "tool_ids": [2], "llm_model_provider_override": "agent-provider",
            "llm_model_version_override": "agent-model"}),
    ]
    fx.append(S(
        "fx_step_overrides",
        "Step-level overrides in sequential mode: today the step LLM override and the "
        "tool_ids_override-based has_tools are IGNORED (only agent-level LLM, bool(agent.tools)).",
        wf("FX overrides", copy.deepcopy(overrides_steps)), [R(I, 5001)],
        covers=["step overrides", "BUG: sequential ignores step LLM/tool overrides"],
    ))
    fx.append(S(
        "fx_chat_files_trace", "Chat files: trace start node is 'Claim submitted' with file names.",
        _abc(), [R(I, 5001, chat_files=["claim.pdf", "photo.jpg"])],
        covers=["chat_files", "trace start"],
    ))

    # ---- llm_decision -----------------------------------------------------------
    L = "llm_decision"
    fx.append(S(
        "fx_llmd_basic",
        "Orchestrator calls Alpha (with reasoning + thinking), Beta, Gamma, then answers.",
        _abc(L), [R(I, 5001)], orchestrator_script=_llmd_abc_script(), mode_override=L,
        covers=["llm_decision", "orchestrator thinking", "final answer"],
    ))
    fx.append(S(
        "fx_step_overrides__llm_decision",
        "Same overrides as fx_step_overrides in llm_decision mode (honoured here).",
        wf("FX overrides", copy.deepcopy(overrides_steps), mode=L), [R(I, 5001)],
        orchestrator_script=[
            {"call": "FX Overridden", "task": "Use your overrides"},
            {"call": "FX Agent Level LLM", "task": "Use the agent LLM"},
        ],
        mode_override=L,
        covers=["llm_decision", "step overrides"],
    ))
    fx.append(S(
        "fx_llmd_call_limit_and_unknown_tool",
        "max_calls_per_agent=1: second call to Alpha is refused (error injected in history, "
        "Alpha filtered from available tools); an unknown tool is ignored; two tool calls in one "
        "cycle (Beta + Gamma) both run.",
        _abc(L, max_calls_per_agent=1), [R(I, 5001)],
        orchestrator_script=[
            {"call": "FX Alpha", "task": "first"},
            {"call": "FX Alpha", "task": "again"},
            {"tool": "delegate_to_ghost", "task": "nobody home"},
            {"calls": [{"agent": "FX Beta", "task": "b"}, {"agent": "FX Gamma", "task": "g"}],
             "thinking": "Run Beta and Gamma together."},
            {"answer": "Done after limits."},
        ],
        mode_override=L,
        covers=["llm_decision", "max_calls_per_agent", "unknown tool", "multiple tool calls per cycle"],
    ))
    fx.append(S(
        "fx_llmd_pause_resume",
        "Beta pauses; resume re-calls Beta DIRECTLY (bypassing the orchestrator) with the "
        "clarification task, then the orchestrator loop continues.",
        wf("FX llmd HITL", [
            agent_step(0, "Alpha", "alpha"),
            agent_step(1, "Beta", "beta", can_request_input=True),
            agent_step(2, "Gamma", "gamma"),
        ], mode=L),
        [R(I, 5001), R(RESUME_INPUT, 5002)],
        agent_script={"Beta": [NEEDS_INPUT]},
        orchestrator_script=_llmd_abc_script(), mode_override=L,
        covers=["llm_decision", "HITL pause", "direct re-call resume"],
    ))
    fx.append(S(
        "fx_llmd_repause",
        "Beta pauses twice (direct re-call re-pause), completes on the third run.",
        wf("FX llmd re-pause", [
            agent_step(0, "Alpha", "alpha"),
            agent_step(1, "Beta", "beta", can_request_input=True, promote_output=True),
            agent_step(2, "Gamma", "gamma"),
        ], mode=L),
        [R(I, 5001), R(RESUME_INPUT, 5002), R(RESUME_INPUT_2, 5003)],
        agent_script={"Beta": [NEEDS_INPUT, {"kind": "needs_input", "output": "[NEEDS_INPUT] And which region?"}]},
        orchestrator_script=_llmd_abc_script(), mode_override=L,
        covers=["llm_decision", "HITL re-pause", "promote on direct re-call"],
    ))
    fx.append(S(
        "fx_llmd_resume_legacy_checkpoint",
        "llm_decision resume from an old-format checkpoint: user reply injected as a "
        "TOOL_CALL_RESPONSE and the orchestrator decides.",
        wf("FX llmd legacy", [
            agent_step(0, "Alpha", "alpha"),
            agent_step(1, "Beta", "beta", can_request_input=True),
            agent_step(2, "Gamma", "gamma"),
        ], mode=L),
        [R(I, 5001), R(RESUME_INPUT, 5002, mutate_db=_strip_clarification)],
        agent_script={"Beta": [NEEDS_INPUT]},
        orchestrator_script=[
            {"call": "FX Alpha", "task": "a"},
            {"call": "FX Beta", "task": "b"},
            {"call": "FX Beta", "task": "b again with the user's reply"},
            {"call": "FX Gamma", "task": "g"},
        ],
        mode_override=L,
        covers=["llm_decision", "HITL fallback resume"],
    ))
    fx.append(S(
        "fx_llmd_max_steps_fallback",
        "max_steps=2 exhausts the loop without a final answer: fallback answer concatenates "
        "every output.",
        _abc(L, max_steps=2), [R(I, 5001)], orchestrator_script=_llmd_abc_script(), mode_override=L,
        covers=["llm_decision", "max_steps", "fallback answer"],
    ))
    fx.append(S(
        "fx_llmd_promote_no_fallback",
        "max_steps=2 with a promoted step: no fallback answer is emitted.",
        wf("FX llmd promote", [
            agent_step(0, "Alpha", "alpha"),
            agent_step(1, "Beta", "beta", promote_output=True),
            agent_step(2, "Gamma", "gamma"),
        ], mode=L, max_steps=2),
        [R(I, 5001)], orchestrator_script=_llmd_abc_script(), mode_override=L,
        covers=["llm_decision", "promote_output"],
    ))
    fx.append(S(
        "fx_llmd_empty_decision",
        "Orchestrator returns neither answer nor tool calls: loop breaks, fallback answer.",
        _abc(L), [R(I, 5001)],
        orchestrator_script=[{"call": "FX Alpha", "task": "a"}, {"empty": True}], mode_override=L,
        covers=["llm_decision", "empty decision"],
    ))
    fx.append(S(
        "fx_llmd_stop_mid_step", "Stop while Beta runs (llm_decision).",
        _abc(L), [R(I, 5001)], agent_script={"Beta": [{"kind": "cancel_mid"}]},
        orchestrator_script=_llmd_abc_script(), mode_override=L,
        covers=["llm_decision", "stop/cancel mid-step"],
    ))
    fx.append(S(
        "fx_llmd_stop_between_steps", "Stop right after Alpha ends (checked at the next cycle start).",
        _abc(L), [R(I, 5001, stop_after_step_end="Agent: FX Alpha")],
        orchestrator_script=_llmd_abc_script(), mode_override=L,
        covers=["llm_decision", "stop/cancel before cycle"],
    ))
    fx.append(S(
        "fx_llmd_timeout",
        "timeout_seconds=1, Alpha takes 1.1s: next cycle breaks on timeout, fallback answer, "
        "status 'completed'. Known bug.",
        _abc(L, timeout_seconds=1), [R(I, 5001)], agent_script={"Alpha": [{"sleep": 1.1}]},
        orchestrator_script=_llmd_abc_script(), mode_override=L,
        covers=["llm_decision", "BUG: timeout reports completed"],
    ))
    fx.append(S(
        "fx_llmd_error", "Beta raises in llm_decision mode.",
        _abc(L), [R(I, 5001)], agent_script={"Beta": [{"kind": "error", "message": "beta exploded"}]},
        orchestrator_script=_llmd_abc_script(), mode_override=L,
        covers=["llm_decision", "step error"],
    ))
    return fx


def all_scenarios() -> list[Scenario]:
    scenarios = template_scenarios() + fixture_scenarios()
    names = [s.name for s in scenarios]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        raise ValueError(f"duplicate scenario names: {sorted(dupes)}")
    return scenarios


# ---------------------------------------------------------------------------
# ALLOWED_DIFFS - intentional behaviour changes a NEW engine may introduce.
#
# Applied only when ENGINE_IMPL != "legacy" (legacy must match exactly).
# Keys: scenario name or glob ('*' only) over scenario names.
# Values: list of (json_path_pattern, reason). Paths look like
#   runs[0].executions[0].status
#   runs[*].trace.status
# and are glob-matched: only "*" is special and it also spans "." and "[]"
# segments; brackets are literal.
# Every entry MUST say why the difference is intended.
# ---------------------------------------------------------------------------

ALLOWED_DIFFS: dict[str, list[tuple[str, str]]] = {
    "fx_timeout_slow_step": [
        ("runs[0].executions[*].status", "timeout reports 'failed'/'timeout' instead of 'completed'"),
        ("runs[0].executions[*].error_message", "timeout carries an error message"),
        ("runs[0].executions[*].has_checkpoint", "terminal status clears checkpoint"),
        ("runs[0].executions[*].completed_at_set", "terminal status sets completed_at"),
        ("runs[0].trace.status", "trace status follows the execution status"),
        ("runs[0].trace_persists[*].status", "trace status follows the execution status"),
    ],
    "fx_llmd_timeout": [
        ("runs[0].executions[*].status", "timeout reports 'failed'/'timeout' instead of 'completed'"),
        ("runs[0].executions[*].error_message", "timeout carries an error message"),
        ("runs[0].trace.status", "trace status follows the execution status"),
        ("runs[0].trace_persists[*].status", "trace status follows the execution status"),
    ],
    # Intentional fixes in engine v2 (docs/flow-nodes/DESIGN.md "Engine rules").
    "fx_step_overrides": [
        ("runs[0].*", "sequential honours step LLM/tool overrides (tool_ids_override=[] "
                      "means no tools), like llm_decision mode"),
    ],
    "fx_router_skip_lost_on_resume": [
        ("runs[1].*", "router skip set restored on resume: the inactive-branch step no "
                      "longer runs"),
    ],
    "fx_duplicate_output_key": [
        ("runs[*].checkpoints[*].checkpoint.completed_step_ids*",
         "completion keyed by node_key, not output_key"),
        ("runs[1].*", "Second Draft (shares an output key) now runs on resume"),
    ],
    "fx_hitl_resume_after_edit": [
        ("runs[1].*", "the paused run resumes on the definition it was pinned to (and "
                      "applies the user's answer) instead of silently re-running steps of "
                      "the edited workflow without it; unpinned runs restart with "
                      "everything the user said"),
    ],
    "fx_hitl_resume_after_edit_insert_step": [
        ("runs[1].*", "the paused run resumes on the definition it was pinned to (and "
                      "applies the user's answer) instead of silently re-running steps of "
                      "the edited workflow without it; unpinned runs restart with "
                      "everything the user said"),
    ],
}
