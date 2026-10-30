"""Built-in node type ``conditional_router``: deterministic if/else branch.

Evaluates one condition against the workflow context (no LLM call), stores
"true"/"false" under the node's output key, and skips the losing branch's
nodes later in the block (skip-forward only).

Versions:
    1: legacy. Condition lives in the ``condition`` column; branch targets are
       ``step_order`` numbers (``true_steps`` / ``false_steps``), which break
       when steps are re-ordered. Deprecated; existing nodes keep running.
    2: branch targets are stable node keys (``true_node_keys`` /
       ``false_node_keys``). Upgraded from v1 by mapping step orders to keys.
"""

from __future__ import annotations

from collections.abc import Generator
from collections.abc import Iterable
from typing import Any
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import ValidationError

from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import Packet
from om.server.query_and_chat.streaming_models import SectionEnd
from om.server.query_and_chat.streaming_models import WorkflowStepDelta
from om.server.query_and_chat.streaming_models import WorkflowStepEnd
from om.server.query_and_chat.streaming_models import WorkflowStepStart
from om.utils.logger import setup_logger
from om.workflows.models import ConditionConfig
from om.workflows.nodes.base import SaveContext
from om.workflows.nodes.base import StepOutcome
from om.workflows.nodes.base import StepSaveError
from om.workflows.nodes.base import StepStatus
from om.workflows.nodes.base import UpgradeContext
from om.workflows.step_runners.conditional_router import evaluate_condition

if TYPE_CHECKING:
    from om.db.models import AgentWorkflowStep
    from om.workflows.graph import WorkflowNode
    from om.workflows.models import WorkflowStepCreate
    from om.workflows.state import RunContext

logger = setup_logger()

ROUTER_NODE_TYPE = "conditional_router"


class ConditionFields(BaseModel):
    """The condition shared by all router versions.

    Defaults mirror the legacy evaluator (``evaluate_condition``), which treated
    missing keys leniently. ``operator`` stays a plain string so an unknown
    operator still evaluates to False at run time instead of failing the load;
    the save API validates operators strictly.
    """

    condition_field: str = ""
    operator: str = "contains"
    match_value: str = ""
    case_sensitive: bool = False

    def condition_dict(self) -> dict[str, Any]:
        return self.model_dump(include=set(ConditionFields.model_fields))


class RouterConfigV1(ConditionFields):
    """``conditional_router`` v1: branch targets by step order."""

    true_steps: list[int] = []
    false_steps: list[int] = []


class RouterConfigV2(ConditionFields):
    """``conditional_router`` v2: branch targets by node key."""

    true_node_keys: list[str] = []
    false_node_keys: list[str] = []


def load_router_config_v1(step: AgentWorkflowStep) -> dict[str, Any]:
    """Read a ``conditional_router`` v1 config from the legacy ``condition`` column."""
    return dict(step.condition or {})


def store_router_config_v1(config: dict[str, Any]) -> dict[str, Any]:
    """v1 configs live in the legacy ``condition`` field."""
    return {"condition": RouterConfigV1.model_validate(config).model_dump()}


def prepare_router_step_v1(
    step: WorkflowStepCreate, ctx: SaveContext
) -> WorkflowStepCreate:
    """v1 keeps its legacy ``condition`` (targets by step order)."""
    if step.condition is None:
        raise StepSaveError(f"Condition step '{step.step_name}' has no condition")
    return step.model_copy(update={"config": None})


def prepare_router_step_v2(
    step: WorkflowStepCreate, ctx: SaveContext
) -> WorkflowStepCreate:
    """Normalize to a v2 config (node-key targets) and mirror it as a legacy condition.

    Accepts either a v2 ``config`` or a legacy ``condition`` with step-order
    targets (older clients). Targets must be steps that come after the router,
    since branches only skip forward. The mirrored ``condition`` keeps the
    legacy engine (``WORKFLOW_ENGINE_V2=false``) working for this step.
    """
    if step.config is not None:
        config = _validated(RouterConfigV2, step.config, step.step_name)
    elif step.condition is not None:
        upgraded = upgrade_router_v1_to_v2(
            step.condition.model_dump(),
            UpgradeContext(step_order_to_node_key=ctx.step_order_to_node_key),
        )
        config = _validated(RouterConfigV2, upgraded, step.step_name)
    else:
        raise StepSaveError(f"Condition step '{step.step_name}' has no condition")

    key_to_order = {key: order for order, key in ctx.step_order_to_node_key.items()}
    for key in [*config.true_node_keys, *config.false_node_keys]:
        order = key_to_order.get(key)
        if order is None:
            raise StepSaveError(
                f"Condition step '{step.step_name}' targets an unknown step ({key})"
            )
        if order <= step.step_order:
            raise StepSaveError(
                f"Condition step '{step.step_name}' can only skip steps that come "
                f"after it"
            )
        target = ctx.steps.get(key)
        if target is not None and (target.parent_key, target.branch_index) != (
            step.parent_key,
            step.branch_index,
        ):
            raise StepSaveError(
                f"Condition step '{step.step_name}' can only skip steps in its own "
                f"branch"
            )

    try:
        mirror = ConditionConfig(
            condition_field=config.condition_field,
            operator=config.operator,  # type: ignore[arg-type]
            match_value=config.match_value,
            case_sensitive=config.case_sensitive,
            true_steps=[key_to_order[k] for k in config.true_node_keys],
            false_steps=[key_to_order[k] for k in config.false_node_keys],
        )
    except ValidationError as e:
        raise StepSaveError(
            f"Condition step '{step.step_name}': {e.errors()[0]['msg']}"
        ) from e
    return step.model_copy(update={"config": config.model_dump(), "condition": mirror})


def _validated(
    model: type[RouterConfigV2], data: dict[str, Any], step_name: str
) -> RouterConfigV2:
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise StepSaveError(
            f"Condition step '{step_name}': {e.errors()[0]['msg']}"
        ) from e


def upgrade_router_v1_to_v2(
    config: dict[str, Any], context: UpgradeContext
) -> dict[str, Any]:
    """Replace step-order targets with the node keys of those steps.

    Orders that match no step are dropped (they never skipped anything).
    """
    v1 = RouterConfigV1.model_validate(config)
    order_to_key = context.step_order_to_node_key
    return {
        **v1.condition_dict(),
        "true_node_keys": [order_to_key[o] for o in v1.true_steps if o in order_to_key],
        "false_node_keys": [
            order_to_key[o] for o in v1.false_steps if o in order_to_key
        ],
    }


class _RouterRunner:
    """Shared runner logic; versions differ only in how targets are named."""

    def run(
        self, node: WorkflowNode, ctx: RunContext
    ) -> Generator[Packet, None, StepOutcome]:
        condition, true_keys, false_keys = self._resolve(node, ctx)
        state = ctx.state
        matched, explanation = evaluate_condition(condition, state.context)
        result = "true" if matched else "false"
        losing_branch = set(false_keys if matched else true_keys)

        try:
            ctx.trace.add_router(node.name, explanation, result)
            ctx.persist_trace()
        except Exception:
            logger.debug("[Trace] router node failed", exc_info=True)

        # Step lifecycle packets, so the UI shows the evaluation
        placement = Placement(turn_index=state.turn.value)
        yield Packet(
            placement=placement,
            obj=WorkflowStepStart(
                step_name=node.name,
                agent_name=None,
                step_order=node.step_order,
                step_type=ROUTER_NODE_TYPE,
            ),
        )
        yield Packet(placement=placement, obj=WorkflowStepDelta(content=explanation))
        yield Packet(
            placement=placement,
            obj=WorkflowStepEnd(step_name=node.name, output_key=node.output_key),
        )
        yield Packet(placement=placement, obj=SectionEnd())

        ctx.complete_node(node, result, skip_node_keys=losing_branch)
        state.steps_executed.append({
            "step_id": node.step_id,
            "agent_id": None,
            "step_name": node.name,
            "input_text": str(node.config)[:500],
            "output_text": explanation,
            "duration_ms": 0,
            "tokens_used": 0,
        })
        state.turn.advance()
        return StepOutcome(status=StepStatus.COMPLETED, output=result)

    def _resolve(
        self, node: WorkflowNode, ctx: RunContext
    ) -> tuple[dict[str, Any], Iterable[str], Iterable[str]]:
        """Return (condition, true-branch node keys, false-branch node keys)."""
        raise NotImplementedError


class RouterRunnerV1(_RouterRunner):
    def _resolve(
        self, node: WorkflowNode, ctx: RunContext
    ) -> tuple[dict[str, Any], Iterable[str], Iterable[str]]:
        config = RouterConfigV1.model_validate(node.config)
        order_to_key = ctx.graph.step_order_to_node_key()
        return (
            config.condition_dict(),
            [order_to_key[o] for o in config.true_steps if o in order_to_key],
            [order_to_key[o] for o in config.false_steps if o in order_to_key],
        )


class RouterRunnerV2(_RouterRunner):
    def _resolve(
        self, node: WorkflowNode, ctx: RunContext
    ) -> tuple[dict[str, Any], Iterable[str], Iterable[str]]:
        config = RouterConfigV2.model_validate(node.config)
        return config.condition_dict(), config.true_node_keys, config.false_node_keys
