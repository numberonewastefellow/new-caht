"""Core contracts for workflow node types.

A node type is identified by ``(type, version)`` and described by a
``NodeTypeSpec``: a typed config model, a runner, capabilities, and an optional
upgrade function from the previous version. Specs are registered with the
``NodeTypeRegistry`` (see ``registry.py``); the engine dispatches through the
registry and never branches on node type names.

Versioning rules (see docs/flow-nodes/DESIGN.md):
- A saved node keeps the ``type_version`` it was saved with.
- Upgrades are explicit: ``upgrade_from_previous`` converts a config from
  ``version - 1`` to ``version``. A spec without one marks a breaking change.
"""

from __future__ import annotations

import enum
import json
from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Protocol
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from om.db.models import AgentWorkflowStep
    from om.server.query_and_chat.streaming_models import Packet
    from om.workflows.graph import WorkflowNode
    from om.workflows.models import WorkflowStepCreate
    from om.workflows.state import RunContext


class StepStatus(str, enum.Enum):
    """How a node finished, as reported by its runner to the coordinator."""

    COMPLETED = "completed"
    # Completed, and the node asks the coordinator to stop the workflow
    # (e.g. ``is_terminal`` steps).
    TERMINAL = "terminal"
    # The node was passed over without being completed.
    SKIPPED = "skipped"
    # Waiting for human input; the runner persisted a pause checkpoint.
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class StepOutcome:
    """Result of running one node.

    Runners record outputs, completion and branch skips through
    ``RunContext.complete_node`` (so they land in the same checkpoint); the
    outcome only tells the coordinator how to continue.

    Attributes:
        status: How the node finished.
        output: The node's output text, if it produced one.
        error: Human-readable error when ``status`` is FAILED.
    """

    status: StepStatus
    output: str | None = None
    error: str | None = None


class NodeRunner(Protocol):
    """Executes one node. Yields streaming packets and returns a StepOutcome."""

    def run(
        self, node: WorkflowNode, ctx: RunContext
    ) -> Generator[Packet, None, StepOutcome]: ...


@dataclass(frozen=True)
class NodeCapabilities:
    """Static facts about a node type, used for save-time validation and the UI.

    Attributes:
        modes: Orchestration modes the node type may be used in.
        can_pause: Whether the node may pause the workflow for human input.
        is_container: Whether the node holds child nodes (parallel, loop).
    """

    modes: frozenset[str] = frozenset({"sequential"})
    can_pause: bool = False
    is_container: bool = False


@dataclass(frozen=True)
class UpgradeContext:
    """Workflow-level information an upgrade function may need.

    Attributes:
        step_order_to_node_key: Maps legacy step orders to stable node keys,
            e.g. for converting router targets from step orders to node keys.
    """

    step_order_to_node_key: Mapping[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StepSummary:
    """Where a step sits in the workflow being saved."""

    node_type: str
    step_order: int
    parent_key: str | None = None
    branch_index: int | None = None


@dataclass(frozen=True)
class SaveContext:
    """Workflow-level information available while validating a step for save.

    Attributes:
        db_session: For existence checks (e.g. the step's agent).
        orchestration_mode: The workflow's mode.
        step_order_to_node_key: Every step of the workflow being saved.
        steps: Every step of the workflow being saved, by node key.
    """

    db_session: Session
    orchestration_mode: str
    step_order_to_node_key: Mapping[int, str]
    steps: Mapping[str, StepSummary] = field(default_factory=dict)

    def ancestors(self, node_key: str) -> list[str]:
        """Container keys enclosing ``node_key``, innermost first."""
        result: list[str] = []
        parent = self.steps[node_key].parent_key if node_key in self.steps else None
        while parent is not None and parent not in result:
            result.append(parent)
            parent = self.steps[parent].parent_key if parent in self.steps else None
        return result


class StepSaveError(ValueError):
    """A step payload is invalid for its node type (reported as HTTP 400)."""


# Converts a config of version N-1 into a config of version N.
ConfigUpgrader = Callable[[dict[str, Any], UpgradeContext], dict[str, Any]]

# Builds a config dict from the legacy (pre-config-column) step columns.
LegacyConfigLoader = Callable[["AgentWorkflowStep"], dict[str, Any]]

# Inverse of LegacyConfigLoader: step payload fields that store a config.
LegacyConfigStorer = Callable[[dict[str, Any]], dict[str, Any]]

# Validates/normalizes a step payload for save; raises StepSaveError.
StepPreparer = Callable[["WorkflowStepCreate", SaveContext], "WorkflowStepCreate"]

# Turns a node's stored output into what the user sees as the final answer.
OutputPresenter = Callable[[str], str]


def present_json_output(output: str) -> str:
    """Show structured (JSON) output readably.

    A JSON object with exactly one string value is shown as that text (e.g. a
    code step returning ``{"plan": "## Trip plan ..."}``); other JSON is shown
    as a formatted JSON block; non-JSON text is returned unchanged.
    """
    try:
        value = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return output
    if isinstance(value, dict) and len(value) == 1:
        (only,) = value.values()
        if isinstance(only, str):
            return only
    return f"```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```"


@dataclass(frozen=True)
class NodeTypeSpec:
    """Everything the platform needs to know about one version of a node type.

    Attributes:
        node_type: Stable type name stored in ``agent_workflow_step.step_type``.
        version: Positive integer, stored in ``agent_workflow_step.type_version``.
        label: Short display name for the editor palette.
        description: One-sentence description for the editor palette.
        category: Palette grouping (e.g. "core", "logic", "data").
        config_model: Pydantic model validating the node's config. Its JSON
            schema drives the generated config form in the editors.
        runner: Executes the node.
        capabilities: Static facts used for validation and the UI.
        upgrade_from_previous: Converts a version-1 config into this version;
            ``None`` means upgrading into this version is a breaking change.
        load_legacy_config: Builds the config from legacy step columns, for
            node types that predate the ``config`` column (agent, router v1).
        store_legacy_config: Inverse of ``load_legacy_config``: the step
            payload fields that store a config (used to restore old versions).
        prepare_step: Validates and normalizes a step payload on save. Without
            one, the payload's ``config`` is validated against ``config_model``.
        present_output: How the node's output is shown when it is the
            workflow's final answer. ``None`` shows it as-is.
        deprecated: Hidden from the palette; existing nodes keep running.
    """

    node_type: str
    version: int
    label: str
    description: str
    category: str
    config_model: type[BaseModel]
    runner: NodeRunner
    capabilities: NodeCapabilities = field(default_factory=NodeCapabilities)
    upgrade_from_previous: ConfigUpgrader | None = None
    load_legacy_config: LegacyConfigLoader | None = None
    store_legacy_config: LegacyConfigStorer | None = None
    prepare_step: StepPreparer | None = None
    present_output: OutputPresenter | None = None
    deprecated: bool = False

    def __post_init__(self) -> None:
        if not self.node_type or not self.node_type.replace("_", "").isalnum():
            raise ValueError(f"Invalid node type name: {self.node_type!r}")
        if self.version < 1:
            raise ValueError(f"Node type version must be >= 1, got {self.version}")

    def validate_config(self, config: Mapping[str, Any]) -> BaseModel:
        """Validate a raw config dict against this version's config model."""
        return self.config_model.model_validate(dict(config))
