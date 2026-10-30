"""The built-in node types, registered explicitly in one place.

To add a node type: create ``nodes/<type>.py`` with its config model(s) and
runner, then register each version here (in increasing version order).
"""

from __future__ import annotations

from functools import lru_cache

from om.workflows.nodes.agent import AGENT_NODE_TYPE
from om.workflows.nodes.agent import AgentRunnerV1
from om.workflows.nodes.agent import AgentStepConfigV1
from om.workflows.nodes.agent import load_agent_config_v1
from om.workflows.nodes.agent import prepare_agent_step_v1
from om.workflows.nodes.agent import store_agent_config_v1
from om.workflows.nodes.base import NodeCapabilities
from om.workflows.nodes.code import CODE_NODE_TYPE
from om.workflows.nodes.code import CodeNodeConfigV1
from om.workflows.nodes.code import CodeRunnerV1
from om.workflows.nodes.code import prepare_code_step_v1
from om.workflows.nodes.loop import LOOP_NODE_TYPE
from om.workflows.nodes.loop import LoopConfigV1
from om.workflows.nodes.loop import LoopRunnerV1
from om.workflows.nodes.loop import prepare_loop_step_v1
from om.workflows.nodes.parallel import PARALLEL_NODE_TYPE
from om.workflows.nodes.parallel import ParallelConfigV1
from om.workflows.nodes.parallel import ParallelRunnerV1
from om.workflows.nodes.parallel import prepare_parallel_step_v1
from om.workflows.nodes.base import NodeTypeSpec
from om.workflows.nodes.base import present_json_output
from om.workflows.nodes.registry import NodeTypeRegistry
from om.workflows.nodes.router import load_router_config_v1
from om.workflows.nodes.router import prepare_router_step_v1
from om.workflows.nodes.router import prepare_router_step_v2
from om.workflows.nodes.router import ROUTER_NODE_TYPE
from om.workflows.nodes.router import RouterConfigV1
from om.workflows.nodes.router import RouterConfigV2
from om.workflows.nodes.router import RouterRunnerV1
from om.workflows.nodes.router import RouterRunnerV2
from om.workflows.nodes.router import store_router_config_v1
from om.workflows.nodes.router import upgrade_router_v1_to_v2

_SEQUENTIAL = frozenset({"sequential"})
_ALL_MODES = frozenset({"sequential", "llm_decision"})


def register_builtin_node_types(registry: NodeTypeRegistry) -> None:
    registry.register(
        NodeTypeSpec(
            node_type=AGENT_NODE_TYPE,
            version=1,
            label="Agent",
            description="Runs an agent with its tools and knowledge.",
            category="core",
            config_model=AgentStepConfigV1,
            runner=AgentRunnerV1(),
            capabilities=NodeCapabilities(modes=_ALL_MODES, can_pause=True),
            load_legacy_config=load_agent_config_v1,
            store_legacy_config=store_agent_config_v1,
            prepare_step=prepare_agent_step_v1,
        )
    )
    registry.register(
        NodeTypeSpec(
            node_type=ROUTER_NODE_TYPE,
            version=1,
            label="Condition",
            description="Branches on a condition (targets by step order).",
            category="logic",
            config_model=RouterConfigV1,
            runner=RouterRunnerV1(),
            capabilities=NodeCapabilities(modes=_SEQUENTIAL),
            load_legacy_config=load_router_config_v1,
            store_legacy_config=store_router_config_v1,
            prepare_step=prepare_router_step_v1,
            deprecated=True,
        )
    )
    registry.register(
        NodeTypeSpec(
            node_type=ROUTER_NODE_TYPE,
            version=2,
            label="Condition",
            description="Branches on a condition: runs one branch, skips the other.",
            category="logic",
            config_model=RouterConfigV2,
            runner=RouterRunnerV2(),
            capabilities=NodeCapabilities(modes=_SEQUENTIAL),
            upgrade_from_previous=upgrade_router_v1_to_v2,
            prepare_step=prepare_router_step_v2,
        )
    )
    registry.register(
        NodeTypeSpec(
            node_type=CODE_NODE_TYPE,
            version=1,
            label="Code",
            description="Runs Python main(inputs) in a sandbox; returns typed outputs.",
            category="data",
            config_model=CodeNodeConfigV1,
            runner=CodeRunnerV1(),
            capabilities=NodeCapabilities(modes=_SEQUENTIAL),
            prepare_step=prepare_code_step_v1,
            present_output=present_json_output,
        )
    )
    registry.register(
        NodeTypeSpec(
            node_type=PARALLEL_NODE_TYPE,
            version=1,
            label="Parallel",
            description="Runs branches of steps at the same time, then joins them.",
            category="logic",
            config_model=ParallelConfigV1,
            runner=ParallelRunnerV1(),
            capabilities=NodeCapabilities(modes=_SEQUENTIAL, is_container=True),
            prepare_step=prepare_parallel_step_v1,
            present_output=present_json_output,
        )
    )
    registry.register(
        NodeTypeSpec(
            node_type=LOOP_NODE_TYPE,
            version=1,
            label="Loop",
            description="Repeats its steps for each item of a list, or while a condition holds.",
            category="logic",
            config_model=LoopConfigV1,
            runner=LoopRunnerV1(),
            capabilities=NodeCapabilities(modes=_SEQUENTIAL, is_container=True),
            prepare_step=prepare_loop_step_v1,
            present_output=present_json_output,
        )
    )


@lru_cache(maxsize=1)
def get_node_registry() -> NodeTypeRegistry:
    """The process-wide registry with all built-in node types."""
    registry = NodeTypeRegistry()
    register_builtin_node_types(registry)
    return registry
