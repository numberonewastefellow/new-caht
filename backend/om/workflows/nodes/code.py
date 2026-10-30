"""Built-in node type ``code`` v1: run a Python ``main(inputs) -> dict``.

The code runs in the code interpreter sandbox (no network, CPU/memory limits;
see docs/flow-nodes/OPERATIONS.md), never in the API process. No LLM is
involved. Inputs are resolved from the workflow context (``$step.output.path``
references or literals); the returned dict must match the declared outputs and
is stored as JSON under the node's output key, so later steps can reference
its fields (``$key.output.<name>``).

The node fails closed: if code steps are disabled or no code interpreter is
configured, the step fails instead of running anywhere else.
"""

from __future__ import annotations

import ast
import json
import time
from collections.abc import Generator
from typing import Any
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import Field
from pydantic import ValidationError

from om.configs.app_configs import CODE_INTERPRETER_BASE_URL
from om.configs.app_configs import WORKFLOW_CODE_NODE_ENABLED
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import SectionEnd
from om.server.query_and_chat.streaming_models import WorkflowStepDelta
from om.server.query_and_chat.streaming_models import WorkflowStepEnd
from om.server.query_and_chat.streaming_models import WorkflowStepStart
from om.tools.tool_implementations.python.code_interpreter_client import (
    CodeInterpreterClient,
)
from om.tools.tool_implementations.python.code_interpreter_client import (
    ExecuteResponse,
)
from om.tools.tool_implementations.python.code_interpreter_client import (
    RunFunctionResponse,
)
from om.tools.tool_implementations.python.code_interpreter_client import (
    RunFunctionUnsupportedError,
)
from om.utils.logger import setup_logger
from om.workflows.inputs import resolve_reference
from om.workflows.inputs import UnresolvedReferenceError
from om.workflows.nodes.base import SaveContext
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepSaveError
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.code_harness import build_harness
from om.workflows.nodes.code_harness import HarnessOutputError
from om.workflows.nodes.code_harness import new_nonce
from om.workflows.nodes.code_harness import OutputType
from om.workflows.nodes.code_harness import OutputValidationError
from om.workflows.nodes.code_harness import parse_harness_output
from om.workflows.nodes.code_harness import validate_outputs

if TYPE_CHECKING:
    from om.workflows.graph import WorkflowNode
    from om.workflows.models import WorkflowStepCreate
    from om.workflows.state import RunContext

logger = setup_logger()

CODE_NODE_TYPE = "code"
MAX_CODE_CHARS = 100_000

_IDENTIFIER = r"^[A-Za-z_][A-Za-z0-9_]*$"

DEFAULT_CODE = '''def main(inputs: dict) -> dict:
    """Return a dict with one entry per declared output."""
    text = inputs.get("text", "")
    return {"result": text.upper()}
'''


class CodeOutputSpec(BaseModel):
    """One declared output of a code step."""

    name: str = Field(pattern=_IDENTIFIER)
    type: OutputType = "string"


class CodeNodeConfigV1(BaseModel):
    """Settings of a ``code`` v1 step."""

    code: str = Field(
        default=DEFAULT_CODE,
        max_length=MAX_CODE_CHARS,
        description="Python source defining main(inputs) -> dict",
        json_schema_extra={"x-ui": "code", "x-language": "python"},
    )
    inputs: dict[str, str] = Field(
        default_factory=lambda: {"text": "$user_input"},
        description="Input name -> literal value or $reference "
        "(e.g. $user_input, $research.output.items[0])",
    )
    outputs: list[CodeOutputSpec] = Field(
        default_factory=lambda: [CodeOutputSpec(name="result")],
        min_length=1,
        description="The keys main() returns, with their types",
    )
    timeout_seconds: int = Field(default=5, ge=1, le=30)


class CodeNodeError(Exception):
    """A code step could not produce a valid result."""


# ── Save-time validation ──────────────────────────────────────────────────


def prepare_code_step_v1(step: WorkflowStepCreate, ctx: SaveContext) -> WorkflowStepCreate:
    """Validate the config and the source (parsed, never executed)."""
    if not WORKFLOW_CODE_NODE_ENABLED:
        raise StepSaveError("Code steps are disabled on this server")
    try:
        config = CodeNodeConfigV1.model_validate(step.config or {})
    except ValidationError as e:
        error = e.errors()[0]
        location = ".".join(str(p) for p in error["loc"])
        raise StepSaveError(
            f"Code step '{step.step_name}': {location}: {error['msg']}"
        ) from e

    names = [o.name for o in config.outputs]
    if len(names) != len(set(names)):
        raise StepSaveError(f"Code step '{step.step_name}': output names must be unique")
    bad_inputs = [name for name in config.inputs if not name.isidentifier()]
    if bad_inputs:
        raise StepSaveError(
            f"Code step '{step.step_name}': invalid input names {bad_inputs}"
        )
    _check_source(step.step_name, config.code)
    return step.model_copy(update={"config": config.model_dump(mode="json")})


def _check_source(step_name: str, code: str) -> None:
    # ast.parse only parses; the code is never executed on the API server.
    try:
        tree = ast.parse(code, filename="<user_code>")
    except SyntaxError as e:
        raise StepSaveError(
            f"Code step '{step_name}': syntax error on line {e.lineno}: {e.msg}"
        ) from e
    has_main = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main"
        for node in tree.body
    )
    if not has_main:
        raise StepSaveError(
            f"Code step '{step_name}': define a function main(inputs) that returns a dict"
        )


# ── Runner ────────────────────────────────────────────────────────────────


class CodeRunnerV1:
    """Runs a ``code`` v1 node in the code interpreter sandbox."""

    def run(self, node: WorkflowNode, ctx: RunContext) -> Generator[Packet, None, StepOutcome]:
        config = CodeNodeConfigV1.model_validate(node.config)
        state = ctx.state
        started = time.monotonic()

        placement = Placement(turn_index=state.turn.value)
        yield Packet(
            placement=placement,
            obj=WorkflowStepStart(
                step_name=node.name,
                agent_name=None,
                step_order=node.step_order,
                step_type=CODE_NODE_TYPE,
            ),
        )
        trace_id = self._trace_start(node, ctx, config)

        try:
            inputs = {
                name: resolve_reference(value, state.context, state.variables)
                for name, value in config.inputs.items()
            }
            result = execute_code(config, inputs)
        except (CodeNodeError, UnresolvedReferenceError) as e:
            message = f"Code step '{node.name}' failed: {e}"
            logger.warning("[Code] %s", message)
            yield Packet(placement=placement, obj=WorkflowStepDelta(content=message))
            yield from _close(node, placement)
            self._trace_finish(ctx, trace_id, message, "failed", started)
            state.turn.advance()
            return StepOutcome(status=StepStatus.FAILED, error=message)

        output = json.dumps(result, ensure_ascii=False)
        yield Packet(
            placement=placement,
            obj=WorkflowStepDelta(
                content=f"```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```"
            ),
        )
        yield from _close(node, placement)

        ctx.complete_node(node, output)
        duration_ms = int((time.monotonic() - started) * 1000)
        state.steps_executed.append({
            "step_id": node.step_id,
            "agent_id": None,
            "step_name": node.name,
            "input_text": json.dumps(inputs, ensure_ascii=False, default=str)[:500],
            "output_text": output[:2000],
            "duration_ms": duration_ms,
            "tokens_used": 0,
        })
        self._trace_finish(ctx, trace_id, output, "completed", started)
        state.turn.advance()
        status = StepStatus.TERMINAL if node.is_terminal else StepStatus.COMPLETED
        return StepOutcome(status=status, output=output)

    @staticmethod
    def _trace_start(
        node: WorkflowNode, ctx: RunContext, config: CodeNodeConfigV1
    ) -> str | None:
        try:
            trace_id = ctx.trace.start_step(
                step_id=node.step_id,
                name=node.name,
                node_type=CODE_NODE_TYPE,
                input_text=json.dumps(config.inputs, ensure_ascii=False),
            )
            ctx.persist_trace()
            return trace_id
        except Exception:
            logger.debug("[Trace] code start failed", exc_info=True)
            return None

    @staticmethod
    def _trace_finish(
        ctx: RunContext, trace_id: str | None, output: str, status: str, started: float
    ) -> None:
        try:
            ctx.trace.finish_agent(
                trace_id,
                output,
                status=status,  # type: ignore[arg-type]
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            ctx.persist_trace()
        except Exception:
            logger.debug("[Trace] code finish failed", exc_info=True)


def execute_code(config: CodeNodeConfigV1, inputs: dict[str, Any]) -> dict[str, Any]:
    """Run ``main(inputs)`` in the sandbox and return its validated result.

    Raises:
        CodeNodeError: disabled, no sandbox, sandbox error, timeout, user
            exception, or invalid result.
    """
    if not WORKFLOW_CODE_NODE_ENABLED:
        raise CodeNodeError("code steps are disabled on this server")
    if not CODE_INTERPRETER_BASE_URL:
        raise CodeNodeError("no code interpreter is configured")

    nonce = new_nonce()
    try:
        response = _run_in_sandbox(
            build_harness(config.code, inputs, nonce), config.timeout_seconds * 1000
        )
    except Exception as e:
        raise CodeNodeError(f"the code interpreter is unavailable ({e})") from e

    if response.timed_out or response.error_kind == "timeout":
        raise CodeNodeError(f"timed out after {config.timeout_seconds}s")
    if response.error_kind == "oom":
        raise CodeNodeError("ran out of memory")
    if response.error_kind == "sandbox_error":
        raise CodeNodeError(f"the sandbox failed to run the code: {response.stderr[-300:]}")

    try:
        result = parse_harness_output(response.stdout, nonce)
    except HarnessOutputError as e:
        detail = (response.stderr or "").strip()[-500:]
        raise CodeNodeError(f"{e}{f': {detail}' if detail else ''}") from e
    if not result.ok:
        raise CodeNodeError(f"{result.error_type}: {result.error_message}")

    declared = {o.name: o.type for o in config.outputs}
    try:
        return validate_outputs(result.result, declared)
    except OutputValidationError as e:
        raise CodeNodeError(str(e)) from e


def _run_in_sandbox(program: str, timeout_ms: int) -> RunFunctionResponse | ExecuteResponse:
    """Run the harness, preferring the low-latency single-use sandbox.

    ``run_function`` usually takes a pre-started sandbox (~0.1-0.2 s); older or
    Kubernetes-backed services don't have it, so fall back to ``execute``.
    """
    client = CodeInterpreterClient()
    try:
        return client.run_function(program, timeout_ms)
    except RunFunctionUnsupportedError:
        logger.info("[Code] run_function unsupported by the sandbox; using execute")
        return client.execute(code=program, timeout_ms=timeout_ms)


def _close(node: WorkflowNode, placement: Placement) -> Generator[Packet, None, None]:
    yield Packet(
        placement=placement,
        obj=WorkflowStepEnd(step_name=node.name, output_key=node.output_key),
    )
    yield Packet(placement=placement, obj=SectionEnd())
