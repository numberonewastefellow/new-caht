"""Fake agent / LLM / DB / file-store layer for the engine golden harness.

Everything the workflow engine touches outside its own control flow is
replaced at a *module boundary*:

====================================  ==========================================
Boundary                              Replacement
====================================  ==========================================
``AgentTool.run``                     ``_fake_agent_run`` - scripted, emits real
                                      packets on ``self.emitter`` (the bus the
                                      engine polls) and returns a real
                                      ``ToolResponse``. AgentTool construction
                                      and its properties stay REAL.
``run_llm_step`` (orchestrator)       ``FakeOrchestrator`` - scripted decisions
``get_llm_for_agent`` /
``get_default_llm`` /
``llm_from_provider`` /
``fetch_llm_provider_view`` /
``get_llm_token_counter``             ``FakeLLM`` labels + word-count tokenizer
``get_paused_execution``              in-memory lookup over ``FakeSession``
``save_checkpoint``                   recording wrapper around the REAL function
``persist_workflow_trace``            recording wrapper around the REAL function
``trace_models.get_default_file_store``  ``InMemoryFileStore``
``db_session``                        ``FakeSession`` (add/get/commit only)
====================================  ==========================================

The REAL ``create_workflow_execution``, ``update_workflow_execution``,
``load_checkpoint``, ``load_workflow_trace``, ``WorkflowTraceBuilder`` and
``evaluate_condition`` run unchanged against the fakes.

Patching is done by identity: every module under ``om.workflows`` (plus the
source module) that holds a reference to the original object gets the
replacement. That way a refactored engine that moves code into new modules
inside ``om.workflows`` is still hooked without touching this file - as long as
it keeps calling the same boundary functions.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import pkgutil
import sys
import threading
import time
from collections import defaultdict
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from typing import Callable

from om.chat.models import LlmStepResult
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import AgentResponseDelta
from om.server.query_and_chat.streaming_models import AgentResponseStart
from om.server.query_and_chat.streaming_models import CustomToolDelta
from om.server.query_and_chat.streaming_models import CustomToolStart
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import ReasoningDelta
from om.server.query_and_chat.streaming_models import ReasoningDone
from om.server.query_and_chat.streaming_models import ReasoningStart
from om.server.query_and_chat.streaming_models import SectionEnd
from om.tools.models import ToolCallKickoff
from om.tools.models import ToolResponse

# ---------------------------------------------------------------------------
# Active harness state (one scenario at a time; agent runs happen in a
# background thread, so a module global is the simplest shared handle).
# ---------------------------------------------------------------------------

_ACTIVE: "HarnessState | None" = None


def active() -> "HarnessState":
    if _ACTIVE is None:
        raise RuntimeError("engine_golden: no active harness state")
    return _ACTIVE


def digest_text(text: str, limit: int = 240) -> str:
    """Keep short strings verbatim; summarise long ones by head + hash."""
    if len(text) <= limit:
        return text
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{text[:120]}...<len={len(text)} sha1={h}>"


# The checkpoint fields the legacy engine writes. Goldens compare ONLY these,
# so additive checkpoint fields (checkpoint_version, completed_node_keys, ...)
# don't churn the goldens; the real save_checkpoint still stores everything.
LEGACY_CHECKPOINT_FIELDS = (
    "step_outputs",
    "shared_data",
    "completed_step_ids",
    "orchestrator_history",
    "cycle_count",
    "agent_call_counts",
    "turn_index",
    "clarification_conversation",
    "paused_agent_original_task",
)


def legacy_checkpoint_fields(dump: dict[str, Any]) -> dict[str, Any]:
    return {k: dump.get(k) for k in LEGACY_CHECKPOINT_FIELDS}


class HarnessState:
    """Per-scenario mutable state shared by every fake."""

    def __init__(
        self,
        agent_script: dict[str, list[dict[str, Any]]] | None,
        orchestrator_script: list[dict[str, Any]] | None,
    ) -> None:
        self.agent_script = agent_script or {}
        self.orchestrator_script = list(orchestrator_script or [])
        self.orchestrator_pos = 0
        self.agent_call_counts: dict[str, int] = defaultdict(int)
        self.run_index = 0
        # Logs (reset per run by the recorder via begin_run)
        self.agent_calls: list[dict[str, Any]] = []
        self.orchestrator_calls: list[dict[str, Any]] = []
        self.checkpoints: list[dict[str, Any]] = []
        self.trace_persists: list[dict[str, Any]] = []
        # Stop / cancel plumbing
        self.stop = threading.Event()
        self.release = threading.Event()
        self.agent_threads: list[threading.Thread] = []
        self.file_store = InMemoryFileStore()

    def begin_run(self, run_index: int) -> None:
        self.run_index = run_index
        self.agent_calls = []
        self.orchestrator_calls = []
        self.checkpoints = []
        self.trace_persists = []
        self.stop.clear()
        self.release.clear()
        self.agent_threads = []

    def end_run(self) -> None:
        # Unblock any agent thread left running by a mid-step cancel.
        self.release.set()
        for t in self.agent_threads:
            t.join(timeout=10)

    def behavior_for(self, step_name: str, call_index: int) -> dict[str, Any]:
        script = self.agent_script.get(step_name) or []
        if call_index < len(script):
            return script[call_index] or {}
        return {}


# ---------------------------------------------------------------------------
# Fake LLMs
# ---------------------------------------------------------------------------


class FakeLLM:
    """Stand-in for om.llm.interfaces.LLM; only identity + config are read."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.config = SimpleNamespace(
            max_input_tokens=10_000_000,
            model_name=label,
            model_provider="fake",
        )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"FakeLLM({self.label})"


def fake_get_llm_for_agent(
    agent: Any,
    user: Any,
    llm_override: Any = None,
    additional_headers: Any = None,  # noqa: ARG001
) -> FakeLLM:
    provider = None
    model = None
    if llm_override is not None:
        provider = getattr(llm_override, "model_provider", None)
        model = getattr(llm_override, "model_version", None)
    if agent is not None:
        provider = provider or agent.llm_model_provider_override
        model = model or agent.llm_model_version_override
    return FakeLLM(f"agent_llm:{provider or 'default'}/{model or 'default'}")


def fake_get_default_llm(*_args: Any, **_kwargs: Any) -> FakeLLM:
    return FakeLLM("default_llm")


def fake_fetch_llm_provider_view(db_session: Any = None, provider_name: str | None = None, **_: Any) -> Any:  # noqa: ARG001
    return SimpleNamespace(name=provider_name)


def fake_llm_from_provider(model_name: str, llm_provider: Any, *_a: Any, **_k: Any) -> FakeLLM:
    return FakeLLM(f"provider_llm:{llm_provider.name}/{model_name}")


def fake_get_llm_token_counter(llm: Any) -> Callable[[str], int]:  # noqa: ARG001
    return lambda text: len((text or "").split())


# ---------------------------------------------------------------------------
# Fake agent run (AgentTool.run replacement)
# ---------------------------------------------------------------------------

DEFAULT_QUESTION = (
    "[NEEDS_INPUT] Which details are missing for {key}? "
    "Please provide the budget and the deadline."
)


def _canned_output(output_key: str, task: str) -> str:
    return f"{output_key} result for: {task[:40]}"


def _emit(emitter: Any, placement: Placement, obj: Any) -> None:
    emitter.emit(Packet(placement=placement, obj=obj))


def _fake_agent_run(
    self: Any,
    placement: Placement,
    override_kwargs: Any = None,  # noqa: ARG001
    **llm_kwargs: Any,
) -> ToolResponse:
    """Scripted replacement for AgentTool.run.

    Behaviour dict keys (all optional):
      kind:   normal | needs_input | error | cancel_mid | raw | empty
      output: explicit output text (overrides the canned text)
      files:  list of filenames the step "creates"
      sleep:  seconds to sleep before answering (timeout path)
      reasoning: emit reasoning packets (default True)
    """
    st = active()
    st.agent_threads.append(threading.current_thread())
    task = str(llm_kwargs.get("task", ""))
    step_name = self._step_name
    call_index = st.agent_call_counts[step_name]
    st.agent_call_counts[step_name] += 1
    beh = st.behavior_for(step_name, call_index)
    kind = beh.get("kind", "normal")

    st.agent_calls.append(
        {
            "step_name": step_name,
            "step_id": self._step_id,
            "step_order": self._step_order,
            "output_key": self._output_key,
            "agent": self._agent.name,
            "call_index": call_index,
            "behavior": kind,
            "placement": [
                placement.turn_index,
                placement.tab_index,
                placement.sub_turn_index,
            ],
            "task": task,
            "extra_kwargs": sorted(k for k in llm_kwargs if k != "task"),
            "has_tools": self._has_tools,
            "llm": getattr(self._cached_llm, "label", repr(self._cached_llm)),
            "promote_output": self._promote_output,
            "overrides": {
                "max_output_tokens": self._max_output_tokens_override,
                "system_prompt": self._system_prompt_override,
                "task_prompt": self._task_prompt_override,
                "tool_ids": self._tool_ids_override,
                "document_set_ids": self._document_set_ids_override,
                "replace_base_system_prompt": self._replace_base_system_prompt_override,
            },
        }
    )

    if kind == "error":
        raise RuntimeError(beh.get("message") or f"fake agent failure in '{step_name}'")

    if beh.get("sleep"):
        time.sleep(float(beh["sleep"]))

    if kind == "needs_input":
        output = beh.get("output") or DEFAULT_QUESTION.format(key=self._output_key)
    elif kind == "empty":
        output = ""
    else:
        output = beh.get("output") or _canned_output(self._output_key, task)

    emitter = self.emitter
    if beh.get("reasoning", True):
        _emit(emitter, placement, ReasoningStart())
        _emit(emitter, placement, ReasoningDelta(reasoning=f"Thinking about {step_name}"))
        _emit(emitter, placement, ReasoningDone())

    # Nested tool call (real AgentTool tool kickoffs use turn_index + 1).
    if self._has_tools:
        tool_placement = Placement(
            turn_index=placement.turn_index + 1, tab_index=0
        )
        _emit(emitter, tool_placement, CustomToolStart(tool_name="fake_search"))
        _emit(
            emitter,
            tool_placement,
            CustomToolDelta(
                tool_name="fake_search",
                response_type="json",
                data={"hits": 3, "step": step_name},
            ),
        )
        _emit(emitter, tool_placement, SectionEnd())

    _emit(emitter, placement, AgentResponseStart())
    if output:
        mid = len(output) // 2
        for chunk in (output[:mid], output[mid:]):
            if chunk:
                _emit(emitter, placement, AgentResponseDelta(content=chunk))

    file_ids: list[str] = []
    file_details: list[dict[str, str]] = []
    for i, fname in enumerate(beh.get("files") or []):
        file_ids.append(f"file_{self._step_id}_{call_index}_{i}")
        file_details.append({"file_path": f"/app/output/{fname}", "filename": fname})
    if file_ids:
        # Mirrors collect_pending_files(): one CustomTool group at step placement
        _emit(emitter, placement, CustomToolStart(tool_name="document_files"))
        _emit(
            emitter,
            placement,
            CustomToolDelta(
                tool_name="document_files",
                response_type="json",
                data={
                    "tool_result": "Generated document files",
                    "_file_ids": file_ids,
                    "_file_details": file_details,
                },
                file_ids=file_ids,
            ),
        )
        _emit(emitter, placement, SectionEnd())

    if kind == "cancel_mid":
        # Wait until the engine has pulled every packet off the bus, THEN flip
        # the stop flag, then block until the recorder releases us. This makes
        # the cancel point deterministic (all packets above are yielded, the
        # next idle poll sees is_connected() == False).
        deadline = time.monotonic() + 10
        while not emitter.bus.empty() and time.monotonic() < deadline:
            time.sleep(0.001)
        st.stop.set()
        st.release.wait(timeout=10)
        return ToolResponse(
            rich_response="late",
            llm_facing_response=json.dumps({"agent_name": self._agent.name, "agent_output": "late"}),
        )

    if kind == "raw":
        return ToolResponse(rich_response=output, llm_facing_response=output)

    response: dict[str, Any] = {"agent_name": self._agent.name, "agent_output": output}
    if file_ids:
        response["_file_ids"] = file_ids
        response["_file_details"] = file_details
    return ToolResponse(rich_response=output, llm_facing_response=json.dumps(response))


# ---------------------------------------------------------------------------
# Fake orchestrator (run_llm_step replacement)
# ---------------------------------------------------------------------------


def tool_name_for_agent(agent_name: str) -> str:
    from om.tools.tool_implementations.agent_tool import _sanitize_tool_name

    return _sanitize_tool_name(agent_name)


def fake_run_llm_step(
    emitter: Any,
    history: list[Any],
    tool_definitions: list[dict],
    tool_choice: Any,  # noqa: ARG001
    llm: Any,
    placement: Placement,
    *_args: Any,
    **_kwargs: Any,
) -> tuple[LlmStepResult, bool]:
    """Scripted orchestrator. Decision dict forms:

    {"call": "<agent name>", "task": "...", "thinking": "...", "reasoning": bool}
    {"calls": [{"agent": "...", "task": "..."}, ...], "thinking": "..."}
    {"tool": "<raw tool name>", "task": "..."}   (e.g. an unknown tool)
    {"answer": "..."}
    {"empty": true}                               (no answer, no tool calls)

    When the script is exhausted the orchestrator answers with a synthesis.
    """
    st = active()
    st.orchestrator_calls.append(
        {
            "placement": [placement.turn_index, placement.tab_index, placement.sub_turn_index],
            "llm": getattr(llm, "label", repr(llm)),
            "available_tools": [td["function"]["name"] for td in tool_definitions],
            "history": [
                [m.message_type.value, digest_text(m.message)] for m in history
            ],
        }
    )
    if st.orchestrator_pos < len(st.orchestrator_script):
        decision = st.orchestrator_script[st.orchestrator_pos]
    else:
        decision = {"answer": f"Final synthesis after {st.orchestrator_pos} orchestrator decisions."}
    st.orchestrator_pos += 1

    has_reasoned = bool(decision.get("reasoning"))
    if has_reasoned:
        emitter.emit(Packet(placement=placement, obj=ReasoningStart()))
        emitter.emit(Packet(placement=placement, obj=ReasoningDelta(reasoning="routing...")))
        emitter.emit(Packet(placement=placement, obj=ReasoningDone()))

    if decision.get("empty"):
        return LlmStepResult(reasoning=None, answer=None, tool_calls=None), has_reasoned
    if "answer" in decision:
        return (
            LlmStepResult(reasoning=None, answer=decision["answer"], tool_calls=None),
            has_reasoned,
        )

    calls: list[tuple[str, str]] = []
    if "call" in decision:
        calls.append((tool_name_for_agent(decision["call"]), decision.get("task", "")))
    if "tool" in decision:
        calls.append((decision["tool"], decision.get("task", "")))
    for c in decision.get("calls", []):
        name = c["tool"] if "tool" in c else tool_name_for_agent(c["agent"])
        calls.append((name, c.get("task", "")))

    kickoffs = [
        ToolCallKickoff(
            tool_call_id=f"call_{st.orchestrator_pos}_{i}",
            tool_name=name,
            tool_args={"task": task},
            placement=Placement(turn_index=placement.turn_index, tab_index=i),
        )
        for i, (name, task) in enumerate(calls)
    ]
    return (
        LlmStepResult(
            reasoning=None,
            answer=decision.get("thinking"),
            tool_calls=kickoffs,
        ),
        has_reasoned,
    )


# ---------------------------------------------------------------------------
# Fake DB session + file store
# ---------------------------------------------------------------------------


class FakeSession:
    """Minimal Session: only what the engine + om.db.workflow helpers use."""

    def __init__(self, agents_by_id: dict[int, Any]) -> None:
        from om.db.models import WorkflowExecution

        self._execution_cls = WorkflowExecution
        self.executions: dict[int, Any] = {}
        self.agents_by_id = agents_by_id
        # Current workflow's steps (the v2 engine checks a paused step still exists).
        self.steps_by_id: dict[int, Any] = {}
        # Workflow version rows written by the v2 engine (om.db.workflow_version).
        self.workflow_versions: list[Any] = []
        self._next_execution_id = 1

    def add(self, obj: Any) -> None:
        if isinstance(obj, self._execution_cls):
            if obj.id is None:
                obj.id = self._next_execution_id
                self._next_execution_id += 1
            self.executions[obj.id] = obj
            return
        raise NotImplementedError(
            f"engine_golden FakeSession.add({type(obj).__name__}) not supported"
        )

    def get(self, cls: Any, ident: Any) -> Any:
        from om.db.models import Agent
        from om.db.models import AgentWorkflowStep

        if cls is self._execution_cls:
            return self.executions.get(ident)
        if cls is Agent:
            return self.agents_by_id.get(ident)
        if cls is AgentWorkflowStep:
            return self.steps_by_id.get(ident)
        raise NotImplementedError(
            f"engine_golden FakeSession.get({getattr(cls, '__name__', cls)}) not supported"
        )

    def begin_nested(self) -> Any:
        import contextlib

        return contextlib.nullcontext()

    def commit(self) -> None:
        pass

    def flush(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def refresh(self, *_a: Any, **_k: Any) -> None:
        pass

    def execute(self, *_a: Any, **_k: Any) -> Any:
        raise NotImplementedError(
            "engine_golden FakeSession.execute: raw queries are not supported - "
            "patch the om.db helper that issues them in fake_layer.install()"
        )


def fake_get_paused_execution(db_session: FakeSession, workflow_id: int, chat_session_id: Any) -> Any:
    candidates = [
        e
        for e in db_session.executions.values()
        if e.workflow_id == workflow_id
        and e.chat_session_id == chat_session_id
        and e.status == "paused"
    ]
    return max(candidates, key=lambda e: e.id) if candidates else None


class InMemoryFileStore:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def save_file(self, content: Any, display_name: Any = None, file_origin: Any = None,
                  file_type: Any = None, file_metadata: Any = None, file_id: str | None = None,
                  **_: Any) -> str:
        fid = file_id or f"mem_{len(self.files)}"
        self.files[fid] = content.read()
        return fid

    def read_file(self, file_id: str, mode: Any = None, **_: Any) -> BytesIO:  # noqa: ARG002
        if file_id not in self.files:
            raise FileNotFoundError(file_id)
        return BytesIO(self.files[file_id])

    def read_json(self, file_id: str) -> dict | None:
        raw = self.files.get(file_id)
        return json.loads(raw) if raw is not None else None


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

_SCAN_PREFIXES = ("om.workflows",)


def _import_engine_modules() -> None:
    """Import every om.workflows submodule so identity patching reaches them."""
    import om.workflows as pkg

    for info in pkgutil.walk_packages(pkg.__path__, "om.workflows."):
        try:
            importlib.import_module(info.name)
        except Exception:  # pragma: no cover - a half-written module mid-refactor
            pass


def _patch_identity(monkeypatch: Any, module: Any, attr: str, replacement: Any) -> Any:
    """Patch module.attr and every om.workflows.* alias of the same object."""
    original = getattr(module, attr)
    monkeypatch.setattr(module, attr, replacement)
    for name, mod in list(sys.modules.items()):
        if mod is None or not name.startswith(_SCAN_PREFIXES):
            continue
        for key, value in list(vars(mod).items()):
            if value is original:
                monkeypatch.setattr(mod, key, replacement)
    return original


def install(monkeypatch: Any, state: HarnessState) -> None:
    """Install every fake for one scenario. monkeypatch undoes it all."""
    global _ACTIVE

    import om.db.llm as db_llm
    import om.db.workflow as db_workflow
    import om.llm.factory as llm_factory
    import om.chat.llm_step as llm_step
    import om.workflows.trace_models as trace_models
    from om.tools.tool_implementations.agent_tool import AgentTool

    _import_engine_modules()

    monkeypatch.setattr(sys.modules[__name__], "_ACTIVE", state)
    _ACTIVE = state  # also for code that already captured the module

    # Agents
    monkeypatch.setattr(AgentTool, "run", _fake_agent_run)

    # LLMs
    _patch_identity(monkeypatch, llm_factory, "get_llm_for_agent", fake_get_llm_for_agent)
    _patch_identity(monkeypatch, llm_factory, "get_default_llm", fake_get_default_llm)
    _patch_identity(monkeypatch, llm_factory, "llm_from_provider", fake_llm_from_provider)
    _patch_identity(monkeypatch, llm_factory, "get_llm_token_counter", fake_get_llm_token_counter)
    _patch_identity(monkeypatch, db_llm, "fetch_llm_provider_view", fake_fetch_llm_provider_view)
    _patch_identity(monkeypatch, llm_step, "run_llm_step", fake_run_llm_step)

    # DB
    _patch_identity(monkeypatch, db_workflow, "get_paused_execution", fake_get_paused_execution)
    real_save_checkpoint = db_workflow.save_checkpoint

    def recording_save_checkpoint(db_session: Any, execution_id: int, checkpoint: Any,
                                  paused_at_step_id: int | None = None,
                                  **kwargs: Any) -> None:
        # Extra keyword arguments (e.g. ``paused``) are passed through
        # unrecorded; the golden compares the legacy checkpoint contract.
        active().checkpoints.append(
            {
                "execution_id": execution_id,
                "paused_at_step_id": paused_at_step_id,
                "checkpoint": legacy_checkpoint_fields(checkpoint.model_dump()),
            }
        )
        real_save_checkpoint(
            db_session, execution_id, checkpoint,
            paused_at_step_id=paused_at_step_id, **kwargs,
        )

    _patch_identity(monkeypatch, db_workflow, "save_checkpoint", recording_save_checkpoint)

    # Workflow versions (v2 engine pins each run to a definition) -> in memory
    import om.db.workflow_version as db_workflow_version
    from om.db.models import AgentWorkflowVersion

    def fake_get_latest_workflow_version(db_session: Any, workflow_id: int) -> Any:
        rows = [v for v in db_session.workflow_versions if v.workflow_id == workflow_id]
        return max(rows, key=lambda v: v.version) if rows else None

    def fake_get_workflow_version(db_session: Any, version_id: int) -> Any:
        return next((v for v in db_session.workflow_versions if v.id == version_id), None)

    def fake_insert_workflow_version(db_session: Any, **fields: Any) -> Any:
        row = AgentWorkflowVersion(id=len(db_session.workflow_versions) + 1, **fields)
        db_session.workflow_versions.append(row)
        return row

    _patch_identity(monkeypatch, db_workflow_version, "get_latest_workflow_version",
                    fake_get_latest_workflow_version)
    _patch_identity(monkeypatch, db_workflow_version, "get_workflow_version",
                    fake_get_workflow_version)
    _patch_identity(monkeypatch, db_workflow_version, "insert_workflow_version",
                    fake_insert_workflow_version)

    # Trace persistence -> in-memory file store
    monkeypatch.setattr(trace_models, "get_default_file_store", lambda *a, **k: state.file_store)
    real_persist = trace_models.persist_workflow_trace

    def recording_persist(trace: Any, include_message_key: bool = False) -> Any:
        active().trace_persists.append(
            {
                "include_message_key": include_message_key,
                "status": trace.status,
                "nodes": [f"{n.id}:{n.status}" for n in trace.nodes],
            }
        )
        return real_persist(trace, include_message_key=include_message_key)

    _patch_identity(monkeypatch, trace_models, "persist_workflow_trace", recording_persist)
