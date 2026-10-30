"""Unit tests for the ``code`` node: save validation, execution, runner."""

import json
import subprocess
import sys
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from om.server.query_and_chat.streaming_models import Packet
from om.tools.tool_implementations.python.code_interpreter_client import ExecuteResponse
from om.tools.tool_implementations.python.code_interpreter_client import (
    RunFunctionUnsupportedError,
)
from om.workflows.graph import WorkflowGraph
from om.workflows.graph import WorkflowNode
from om.workflows.models import WorkflowContext
from om.workflows.models import WorkflowStepCreate
from om.workflows.nodes.base import SaveContext
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepSaveError
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.nodes.code import CodeNodeConfigV1
from om.workflows.nodes.code import CodeNodeError
from om.workflows.nodes.code import CodeRunnerV1
from om.workflows.nodes.code import execute_code
from om.workflows.nodes.code import prepare_code_step_v1
from om.workflows.state import RunContext
from om.workflows.state import RunState

MODULE = "om.workflows.nodes.code"


class _LocalSandbox:
    """Stands in for CodeInterpreterClient: runs the harness in a subprocess."""

    def __init__(
        self, *, timed_out: bool = False, error_kind: str | None = None, unsupported: bool = False
    ) -> None:
        self.timed_out = timed_out
        self.error_kind = error_kind
        self.unsupported = unsupported
        self.calls: list[dict[str, Any]] = []

    def __call__(self) -> "_LocalSandbox":  # used as the client factory
        return self

    def run_function(self, program: str, timeout_ms: int, **_: Any) -> ExecuteResponse:
        if self.unsupported:
            raise RunFunctionUnsupportedError("no run_function")
        return self.execute(program, timeout_ms)

    def execute(self, code: str, timeout_ms: int, **_: Any) -> ExecuteResponse:
        self.calls.append({"timeout_ms": timeout_ms})
        if self.timed_out or self.error_kind:
            return ExecuteResponse(
                stdout="", stderr="", exit_code=None, timed_out=self.timed_out,
                duration_ms=1, files=[], error_kind=self.error_kind,
            )
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=30
        )
        return ExecuteResponse(
            stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode,
            timed_out=False, duration_ms=1, files=[],
        )


@pytest.fixture
def sandbox() -> Generator[_LocalSandbox, None, None]:
    fake = _LocalSandbox()
    with patch(f"{MODULE}.CodeInterpreterClient", fake), patch(
        f"{MODULE}.CODE_INTERPRETER_BASE_URL", "http://sandbox"
    ), patch(f"{MODULE}.WORKFLOW_CODE_NODE_ENABLED", True):
        yield fake


def _config(code: str, **kwargs: Any) -> CodeNodeConfigV1:
    return CodeNodeConfigV1(code=code, **kwargs)


ADD = "def main(inputs):\n    return {'sum': inputs['a'] + inputs['b']}\n"


class TestExecuteCode:
    def test_success(self, sandbox: _LocalSandbox) -> None:
        config = _config(ADD, outputs=[{"name": "sum", "type": "integer"}])
        assert execute_code(config, {"a": 2, "b": 3}) == {"sum": 5}
        assert sandbox.calls == [{"timeout_ms": 5000}]

    def test_user_exception(self, sandbox: _LocalSandbox) -> None:
        config = _config("def main(inputs):\n    raise KeyError('a')\n")
        with pytest.raises(CodeNodeError, match="KeyError"):
            execute_code(config, {})

    def test_result_must_match_declared_outputs(self, sandbox: _LocalSandbox) -> None:
        config = _config(ADD, outputs=[{"name": "total", "type": "integer"}])
        with pytest.raises(CodeNodeError, match="Missing outputs: total"):
            execute_code(config, {"a": 1, "b": 1})

    def test_timeout(self) -> None:
        with patch(f"{MODULE}.CodeInterpreterClient", _LocalSandbox(timed_out=True)), patch(
            f"{MODULE}.CODE_INTERPRETER_BASE_URL", "http://sandbox"
        ):
            with pytest.raises(CodeNodeError, match="timed out after 5s"):
                execute_code(_config(ADD), {})

    def test_out_of_memory(self) -> None:
        with patch(f"{MODULE}.CodeInterpreterClient", _LocalSandbox(error_kind="oom")), patch(
            f"{MODULE}.CODE_INTERPRETER_BASE_URL", "http://sandbox"
        ):
            with pytest.raises(CodeNodeError, match="out of memory"):
                execute_code(_config(ADD), {})

    def test_fails_closed_without_a_sandbox(self) -> None:
        with patch(f"{MODULE}.CODE_INTERPRETER_BASE_URL", None):
            with pytest.raises(CodeNodeError, match="no code interpreter"):
                execute_code(_config(ADD), {})

    def test_fails_closed_when_disabled(self) -> None:
        with patch(f"{MODULE}.WORKFLOW_CODE_NODE_ENABLED", False):
            with pytest.raises(CodeNodeError, match="disabled"):
                execute_code(_config(ADD), {})

    def test_falls_back_to_execute_on_older_sandboxes(self) -> None:
        legacy = _LocalSandbox(unsupported=True)
        with patch(f"{MODULE}.CodeInterpreterClient", legacy), patch(
            f"{MODULE}.CODE_INTERPRETER_BASE_URL", "http://sandbox"
        ), patch(f"{MODULE}.WORKFLOW_CODE_NODE_ENABLED", True):
            config = _config(ADD, outputs=[{"name": "sum", "type": "integer"}])
            assert execute_code(config, {"a": 1, "b": 1}) == {"sum": 2}
        assert legacy.calls == [{"timeout_ms": 5000}]

    def test_sandbox_unreachable(self) -> None:
        broken = MagicMock()
        broken.return_value.run_function.side_effect = ConnectionError("refused")
        with patch(f"{MODULE}.CodeInterpreterClient", broken), patch(
            f"{MODULE}.CODE_INTERPRETER_BASE_URL", "http://sandbox"
        ):
            with pytest.raises(CodeNodeError, match="unavailable"):
                execute_code(_config(ADD), {})


def _step(config: dict[str, Any]) -> WorkflowStepCreate:
    return WorkflowStepCreate(
        step_type="code", step_order=0, step_name="Transform", config=config
    )


_SAVE_CTX = SaveContext(
    db_session=MagicMock(), orchestration_mode="sequential", step_order_to_node_key={}
)


class TestPrepare:
    def test_defaults_are_filled(self) -> None:
        prepared = prepare_code_step_v1(_step({}), _SAVE_CTX)
        assert prepared.config is not None
        assert "def main" in prepared.config["code"]
        assert prepared.config["outputs"] == [{"name": "result", "type": "string"}]

    @pytest.mark.parametrize(
        ("config", "message"),
        [
            ({"code": "def main(:"}, "syntax error on line 1"),
            ({"code": "x = 1"}, "define a function main"),
            ({"code": ADD, "outputs": []}, "outputs"),
            ({"code": ADD, "outputs": [{"name": "a"}, {"name": "a"}]}, "unique"),
            ({"code": ADD, "outputs": [{"name": "bad name"}]}, "outputs"),
            ({"code": ADD, "inputs": {"bad name": "x"}}, "invalid input names"),
            ({"code": ADD, "timeout_seconds": 99}, "timeout_seconds"),
        ],
    )
    def test_rejects(self, config: dict[str, Any], message: str) -> None:
        with pytest.raises(StepSaveError, match=message):
            prepare_code_step_v1(_step(config), _SAVE_CTX)

    def test_source_is_never_executed_on_save(self) -> None:
        # A module-level side effect would run if the source were executed.
        code = "import os\nos._exit(9)\ndef main(inputs):\n    return {}\n"
        prepare_code_step_v1(_step({"code": code}), _SAVE_CTX)  # no exit


def _ctx(node: WorkflowNode, context: WorkflowContext) -> RunContext:
    ctx = RunContext(
        graph=WorkflowGraph(
            workflow_id=1, name="wf", orchestration_mode="sequential", nodes=[node]
        ),
        registry=get_node_registry(),
        state=RunState(context=context),
        db_session=MagicMock(),
        user=MagicMock(),
        emitter=MagicMock(),
        execution=MagicMock(id=1),
        trace=MagicMock(),
        agent_tools=MagicMock(),
    )
    ctx.save_checkpoint = MagicMock()  # type: ignore[method-assign]
    return ctx


def _drive(gen: Generator[Packet, None, StepOutcome]) -> tuple[list[Packet], StepOutcome]:
    packets: list[Packet] = []
    while True:
        try:
            packets.append(next(gen))
        except StopIteration as stop:
            return packets, stop.value


def _node(config: dict[str, Any]) -> WorkflowNode:
    return WorkflowNode(
        node_key="c", step_id=5, node_type="code", type_version=1, step_order=1,
        name="Count", output_key="stats",
        config=CodeNodeConfigV1.model_validate(config).model_dump(mode="json"),
    )


class TestRunner:
    def test_resolves_inputs_and_stores_json_output(self, sandbox: _LocalSandbox) -> None:
        node = _node({
            "code": "def main(inputs):\n    return {'n': len(inputs['items'])}\n",
            "inputs": {"items": "$research.output.items"},
            "outputs": [{"name": "n", "type": "integer"}],
        })
        context = WorkflowContext(
            user_input="x", step_outputs={"research": json.dumps({"items": [1, 2, 3]})}
        )
        ctx = _ctx(node, context)

        packets, outcome = _drive(CodeRunnerV1().run(node, ctx))

        assert outcome.status == StepStatus.COMPLETED
        assert json.loads(ctx.state.context.step_outputs["stats"]) == {"n": 3}
        assert ctx.state.completed_keys == {"c"}
        assert [p.obj.type for p in packets] == [
            "workflow_step_start", "workflow_step_delta", "workflow_step_end", "section_end",
        ]
        assert packets[0].obj.step_type == "code"  # type: ignore[union-attr]
        assert ctx.state.turn.value == 1

    def test_failure_is_shown_and_reported(self, sandbox: _LocalSandbox) -> None:
        node = _node({"code": "def main(inputs):\n    return 1 / 0\n"})
        ctx = _ctx(node, WorkflowContext(user_input="x"))

        packets, outcome = _drive(CodeRunnerV1().run(node, ctx))

        assert outcome.status == StepStatus.FAILED
        assert "ZeroDivisionError" in (outcome.error or "")
        assert "ZeroDivisionError" in packets[1].obj.content  # type: ignore[union-attr]
        assert ctx.state.completed_keys == set()

    def test_unresolved_reference_fails_without_running(self, sandbox: _LocalSandbox) -> None:
        node = _node({"code": ADD, "inputs": {"a": "$missing.output.x"}})
        ctx = _ctx(node, WorkflowContext(user_input="x"))
        _, outcome = _drive(CodeRunnerV1().run(node, ctx))
        assert outcome.status == StepStatus.FAILED
        assert sandbox.calls == []


def test_registered_and_sequential_only() -> None:
    spec = get_node_registry().latest("code")
    assert spec.version == 1
    assert spec.capabilities.modes == frozenset({"sequential"})
    schema = spec.config_model.model_json_schema()
    assert schema["properties"]["code"]["x-ui"] == "code"
