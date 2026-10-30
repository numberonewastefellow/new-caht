"""Turn a workflow definition (template JSON or inline fixture dict) into the
in-memory ORM objects the engine reads.

Nothing is persisted. Field defaults are applied the same way the real create
path does it (``WorkflowCreate`` / ``WorkflowStepCreate`` pydantic models, then
the same column mapping as ``om.db.workflow._add_step``) because SQLAlchemy
column defaults are only applied on INSERT and would otherwise be ``None`` on a
transient object.

Definition format (superset of the template JSON files)::

    {
      "name": ..., "orchestration_mode": "sequential" | "llm_decision",
      "max_steps": ..., "max_calls_per_agent": ..., "timeout_seconds": ...,
      "orchestrator_prompt": ..., "orchestrator_llm_provider": ..., ...,
      "steps": [
        {
          "step_name": ..., "step_order": ..., "output_key": ...,
          "step_type": "agent" | "conditional_router",
          "condition": {...},                # routers only
          "input_mapping": {...}, "is_terminal": ..., "can_request_input": ...,
          "promote_output": ..., "<any *_override field>": ...,
          "agent_name": "...",               # template style
          "agent_def": {"name": ..., "description": ..., "tool_ids": [...],
                        "tool_names": [...], "llm_model_provider_override": ...,
                        "llm_model_version_override": ..., "deleted": false},
        },
      ],
    }

Synthetic ids: workflow ``1``; step ids ``step_id_base + index`` in definition
order; agent ids ``1001 + n`` in order of first appearance (agents are shared
by name, like ``resolve_or_create_agent``). Pass the same ``AgentRegistry`` to
rebuild a workflow with new step ids but the same agents ("edit" scenarios).
"""

from __future__ import annotations

import copy
from typing import Any

from om.db.models import Agent
from om.db.models import AgentWorkflow
from om.db.models import AgentWorkflowStep
from om.db.models import Tool
from om.workflows.models import WorkflowCreate
from om.workflows.models import WorkflowStepCreate

WORKFLOW_ID = 1

_WORKFLOW_FIELDS = (
    "name",
    "description",
    "orchestration_mode",
    "orchestrator_prompt",
    "orchestrator_llm_provider",
    "orchestrator_llm_model",
    "max_steps",
    "max_calls_per_agent",
    "timeout_seconds",
    "is_public",
    "icon_name",
)

_STEP_FIELDS = set(WorkflowStepCreate.model_fields)


class AgentRegistry:
    """Synthetic agents, shared by name across builds of one scenario."""

    def __init__(self, base_id: int = 1001) -> None:
        self._next_id = base_id
        self.by_name: dict[str, Agent] = {}
        self._tools: dict[int, Tool] = {}

    @property
    def by_id(self) -> dict[int, Agent]:
        return {a.id: a for a in self.by_name.values()}

    def _tool(self, tool_id: int) -> Tool:
        if tool_id not in self._tools:
            self._tools[tool_id] = Tool(id=tool_id, name=f"tool_{tool_id}")
        return self._tools[tool_id]

    def get_or_create(self, agent_def: dict[str, Any]) -> Agent:
        name = agent_def["name"]
        if name in self.by_name:
            return self.by_name[name]
        tool_ids = agent_def.get("tool_ids") or []
        if isinstance(tool_ids, str):
            tool_ids = [int(t) for t in tool_ids.strip("[]").split(",") if t.strip()]
        tool_ids = list(tool_ids)
        # tool_names resolve to synthetic ids 900+ (resolved by name in prod)
        for i, _ in enumerate(agent_def.get("tool_names") or []):
            tool_ids.append(900 + i)
        agent = Agent(
            id=self._next_id,
            name=name,
            description=agent_def.get("description") or "",
            deleted=bool(agent_def.get("deleted", False)),
            llm_model_provider_override=agent_def.get("llm_model_provider_override"),
            llm_model_version_override=agent_def.get("llm_model_version_override"),
            max_output_tokens=agent_def.get("max_output_tokens"),
        )
        agent.tools = [self._tool(int(t)) for t in tool_ids]
        self._next_id += 1
        self.by_name[name] = agent
        return agent


def _agent_def_for_step(step: dict[str, Any]) -> dict[str, Any] | None:
    if step.get("step_type", "agent") == "conditional_router":
        return None
    agent_def = dict(step.get("agent_def") or {})
    name = agent_def.get("name") or step.get("agent_name") or f"Agent {step['step_name']}"
    agent_def["name"] = name
    return agent_def


def build_workflow(
    definition: dict[str, Any],
    registry: AgentRegistry,
    *,
    step_id_base: int = 101,
    mode_override: str | None = None,
) -> AgentWorkflow:
    definition = copy.deepcopy(definition)
    wf_kwargs = {k: definition[k] for k in _WORKFLOW_FIELDS if k in definition}
    if mode_override:
        wf_kwargs["orchestration_mode"] = mode_override
    wc = WorkflowCreate(**wf_kwargs)

    workflow = AgentWorkflow(
        id=WORKFLOW_ID,
        name=wc.name,
        description=wc.description,
        user_id=None,
        orchestration_mode=wc.orchestration_mode,
        orchestrator_prompt=wc.orchestrator_prompt,
        orchestrator_llm_provider=wc.orchestrator_llm_provider,
        orchestrator_llm_model=wc.orchestrator_llm_model,
        max_steps=wc.max_steps,
        max_calls_per_agent=wc.max_calls_per_agent,
        timeout_seconds=wc.timeout_seconds,
        is_public=wc.is_public,
        is_visible=True,
        deleted=False,
        icon_name=wc.icon_name,
    )

    for attr in ("version", "schema_version"):
        if hasattr(AgentWorkflow, attr):
            setattr(workflow, attr, definition.get(attr) or 1)

    steps: list[AgentWorkflowStep] = []
    for index, raw in enumerate(definition.get("steps", [])):
        agent_def = _agent_def_for_step(raw)
        agent = registry.get_or_create(agent_def) if agent_def else None
        fields = {k: v for k, v in raw.items() if k in _STEP_FIELDS}
        fields["agent_id"] = agent.id if agent else None
        sc = WorkflowStepCreate(**fields)
        step = AgentWorkflowStep(
            id=step_id_base + index,
            workflow_id=WORKFLOW_ID,
            step_type=sc.step_type,
            agent_id=sc.agent_id,
            step_order=sc.step_order,
            step_name=sc.step_name,
            step_description=sc.step_description,
            input_mapping=sc.input_mapping,
            output_key=sc.output_key,
            condition=sc.condition.model_dump() if sc.condition else None,
            is_terminal=sc.is_terminal,
            can_request_input=sc.can_request_input,
            promote_output=sc.promote_output,
            llm_provider_override=sc.llm_provider_override,
            llm_model_override=sc.llm_model_override,
            max_output_tokens_override=sc.max_output_tokens_override,
            system_prompt_override=sc.system_prompt_override,
            task_prompt_override=sc.task_prompt_override,
            tool_ids_override=sc.tool_ids_override,
            document_set_ids_override=sc.document_set_ids_override,
            replace_base_system_prompt_override=sc.replace_base_system_prompt_override,
        )
        # Columns added by migration 0002_workflow_nodes (if present): mirror
        # the backfill ('s' || id, type_version 1) so transient steps look like
        # migrated rows instead of carrying None.
        if hasattr(AgentWorkflowStep, "node_key"):
            step.node_key = raw.get("node_key") or f"s{step.id}"
        if hasattr(AgentWorkflowStep, "type_version"):
            step.type_version = raw.get("type_version") or 1
        if agent is not None:
            step.agent = agent
        steps.append(step)
    workflow.steps = steps
    return workflow


def describe_workflow(workflow: AgentWorkflow) -> dict[str, Any]:
    """Compact, readable summary of the built workflow for the golden file."""
    return {
        "id": workflow.id,
        "name": workflow.name,
        "mode": workflow.orchestration_mode,
        "max_steps": workflow.max_steps,
        "max_calls_per_agent": workflow.max_calls_per_agent,
        "timeout_seconds": workflow.timeout_seconds,
        "steps": [
            {
                "id": s.id,
                "order": s.step_order,
                "name": s.step_name,
                "type": s.step_type,
                "agent_id": s.agent_id,
                "output_key": s.output_key,
                "flags": [
                    f
                    for f in ("can_request_input", "promote_output", "is_terminal")
                    if getattr(s, f)
                ],
            }
            for s in workflow.steps
        ],
    }
