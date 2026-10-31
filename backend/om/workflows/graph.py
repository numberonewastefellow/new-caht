"""Immutable, serializable view of a workflow definition.

The engine runs on a ``WorkflowGraph`` instead of ORM rows:

- it is plain data, so it is safe to share with worker threads;
- it serializes to the definition JSON stored in ``agent_workflow_version``,
  so a paused run can resume against the exact definition it started on.

Build one from ORM rows with ``graph_from_workflow`` (live runs, saves) or from
a stored definition with ``graph_from_definition`` (pinned runs, resume).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from collections.abc import Mapping
from functools import cached_property
from typing import Any
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import model_validator

from om.workflows.nodes.registry import NodeTypeRegistry

if TYPE_CHECKING:
    from om.db.models import AgentWorkflow
    from om.db.models import AgentWorkflowStep

# Format of the serialized definition document. Bump it when the document
# structure changes and add a migration to _DEFINITION_MIGRATIONS.
DEFINITION_FORMAT = 1

# Legacy rows have no node_key column value until migrated; the migration
# backfills the same "s<id>" form, so keys stay identical either way.
LEGACY_NODE_KEY_PREFIX = "s"


class WorkflowNode(BaseModel):
    """One node (step) of a workflow, with its config already validated."""

    model_config = ConfigDict(frozen=True)

    node_key: str
    # Database id of the step row; None for nodes not persisted yet.
    step_id: int | None = None
    node_type: str
    type_version: int
    step_order: int
    name: str
    description: str | None = None
    output_key: str = "output"
    input_mapping: dict[str, Any] | None = None
    config: dict[str, Any] = {}
    is_terminal: bool = False
    can_request_input: bool = False
    promote_output: bool = False
    # Container membership: the parent container's node key and the branch
    # within it. None for top-level nodes.
    parent_key: str | None = None
    branch_index: int | None = None


class WorkflowSettings(BaseModel):
    """Workflow-level settings, versioned with the steps so a restore brings them back."""

    model_config = ConfigDict(frozen=True)

    description: str | None = None
    orchestrator_prompt: str | None = None
    orchestrator_llm_provider: str | None = None
    orchestrator_llm_model: str | None = None
    max_steps: int | None = None
    max_calls_per_agent: int | None = None
    is_public: bool | None = None
    icon_name: str | None = None


class WorkflowGraph(BaseModel):
    """A workflow's nodes in execution order, plus the settings the engine needs."""

    model_config = ConfigDict(frozen=True)

    definition_format: int = DEFINITION_FORMAT
    workflow_id: int
    name: str
    orchestration_mode: str
    schema_version: int = 1
    timeout_seconds: int = 1800
    # None in definitions recorded before settings were versioned.
    settings: WorkflowSettings | None = None
    nodes: list[WorkflowNode] = []

    @model_validator(mode="after")
    def _validate_structure(self) -> WorkflowGraph:
        keys = [n.node_key for n in self.nodes]
        if len(keys) != len(set(keys)):
            raise ValueError("Workflow nodes must have unique node keys")
        orders = [n.step_order for n in self.nodes]
        if len(orders) != len(set(orders)):
            raise ValueError("Workflow nodes must have unique step orders")
        if orders != sorted(orders):
            raise ValueError("Workflow nodes must be sorted by step order")

        by_key = {n.node_key: n for n in self.nodes}
        for node in self.nodes:
            if node.parent_key is None:
                continue
            parent = by_key.get(node.parent_key)
            if parent is None:
                raise ValueError(
                    f"Node {node.node_key} is inside unknown container {node.parent_key}"
                )
            if node.step_order <= parent.step_order:
                raise ValueError(
                    f"Node {node.node_key} must come after its container {parent.node_key}"
                )
            if node.branch_index is None or node.branch_index < 0:
                raise ValueError(f"Node {node.node_key} needs a branch index")
        return self

    # ── Lookups ───────────────────────────────────────────────────────────

    @cached_property
    def _by_key(self) -> dict[str, WorkflowNode]:
        return {n.node_key: n for n in self.nodes}

    @cached_property
    def _by_step_id(self) -> dict[int, WorkflowNode]:
        return {n.step_id: n for n in self.nodes if n.step_id is not None}

    def node(self, node_key: str) -> WorkflowNode:
        return self._by_key[node_key]

    def node_for_key(self, node_key: str) -> WorkflowNode | None:
        return self._by_key.get(node_key)

    def has_node(self, node_key: str) -> bool:
        return node_key in self._by_key

    def node_for_step_id(self, step_id: int) -> WorkflowNode | None:
        return self._by_step_id.get(step_id)

    def step_order_to_node_key(self) -> dict[int, str]:
        return {n.step_order: n.node_key for n in self.nodes}

    def top_level(self) -> list[WorkflowNode]:
        """Nodes outside any container, in execution order."""
        return [n for n in self.nodes if n.parent_key is None]

    def branches(self, container_key: str) -> list[list[WorkflowNode]]:
        """The container's branches (by branch index), each in execution order.

        Branch indexes without nodes are not returned.
        """
        by_branch: dict[int, list[WorkflowNode]] = {}
        for node in self.nodes:
            if node.parent_key == container_key and node.branch_index is not None:
                by_branch.setdefault(node.branch_index, []).append(node)
        return [by_branch[index] for index in sorted(by_branch)]

    def depth(self, node_key: str) -> int:
        """Container nesting depth: 0 for top-level nodes."""
        depth = 0
        node = self._by_key[node_key]
        while node.parent_key is not None:
            depth += 1
            node = self._by_key[node.parent_key]
        return depth

    # ── Serialization ─────────────────────────────────────────────────────

    def to_definition(self) -> dict[str, Any]:
        """The JSON document stored in ``agent_workflow_version.definition``."""
        return self.model_dump(mode="json")

    def content_hash(self) -> str:
        """SHA-256 of the canonical definition; equal content gives equal hashes."""
        canonical = json.dumps(
            self.to_definition(), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── Builders ──────────────────────────────────────────────────────────────


def graph_from_workflow(
    workflow: AgentWorkflow, registry: NodeTypeRegistry
) -> WorkflowGraph:
    """Build the graph for a workflow from its ORM rows.

    Each step's config is read through its node type spec (legacy columns for
    ``agent``/``conditional_router`` v1, the ``config`` column otherwise) and
    validated against that version's config model.

    Raises:
        UnknownNodeTypeError: A step uses an unregistered type or version.
        pydantic.ValidationError: A step's config is invalid for its version.
    """
    steps = sorted(workflow.steps, key=lambda s: s.step_order)
    key_by_step_id = {s.id: s.node_key or f"{LEGACY_NODE_KEY_PREFIX}{s.id}" for s in steps}
    return WorkflowGraph(
        workflow_id=workflow.id,
        name=workflow.name,
        orchestration_mode=workflow.orchestration_mode,
        # Unflushed ORM objects don't have column defaults applied yet.
        schema_version=workflow.schema_version or 1,
        timeout_seconds=(
            workflow.timeout_seconds if workflow.timeout_seconds is not None else 1800
        ),
        settings=WorkflowSettings(
            description=workflow.description or None,
            orchestrator_prompt=workflow.orchestrator_prompt or None,
            orchestrator_llm_provider=workflow.orchestrator_llm_provider or None,
            orchestrator_llm_model=workflow.orchestrator_llm_model or None,
            max_steps=workflow.max_steps,
            max_calls_per_agent=workflow.max_calls_per_agent,
            is_public=workflow.is_public,
            icon_name=workflow.icon_name or None,
        ),
        nodes=[_node_from_step(step, registry, key_by_step_id) for step in steps],
    )


def graph_from_definition(definition: Mapping[str, Any]) -> WorkflowGraph:
    """Rebuild a graph from a stored definition, migrating older formats first."""
    data = dict(definition)
    fmt = int(data.get("definition_format", 1))
    if fmt > DEFINITION_FORMAT:
        raise ValueError(
            f"Workflow definition format {fmt} is newer than this server "
            f"supports ({DEFINITION_FORMAT})"
        )
    while fmt < DEFINITION_FORMAT:
        data = _DEFINITION_MIGRATIONS[fmt](data)
        fmt += 1
        data["definition_format"] = fmt
    return WorkflowGraph.model_validate(data)


def _node_from_step(
    step: AgentWorkflowStep,
    registry: NodeTypeRegistry,
    key_by_step_id: Mapping[int, str],
) -> WorkflowNode:
    node_type = step.step_type or "agent"
    type_version = step.type_version or 1
    spec = registry.get(node_type, type_version)
    raw_config = (
        spec.load_legacy_config(step)
        if spec.load_legacy_config is not None
        else dict(step.config or {})
    )
    config = spec.validate_config(raw_config).model_dump(mode="json")
    return WorkflowNode(
        node_key=step.node_key or f"{LEGACY_NODE_KEY_PREFIX}{step.id}",
        step_id=step.id,
        node_type=node_type,
        type_version=type_version,
        step_order=step.step_order,
        name=step.step_name,
        description=step.step_description,
        output_key=step.output_key or "output",
        input_mapping=step.input_mapping,
        config=config,
        is_terminal=bool(step.is_terminal),
        can_request_input=bool(step.can_request_input),
        promote_output=bool(step.promote_output),
        parent_key=(
            key_by_step_id.get(step.parent_step_id)
            if step.parent_step_id is not None
            else None
        ),
        branch_index=step.branch_index,
    )


# Structural migrations of the definition document: format N -> N + 1.
# Each must be pure and idempotent, and covered by a fixture test.
_DEFINITION_MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}
