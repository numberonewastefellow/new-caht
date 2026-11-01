#!/usr/bin/env python3
"""Read-only check before and after an engine upgrade. Nothing is saved and no LLM is called.

- Every template in workflows/: known node types, valid settings, valid references.
- Every workflow in the database: loads on the engine, in the saved order, on usable agents.
- Every paused run: can still resume, or restarts with what the user said (by design).

Problems are reported by id and step name, never prompts or outputs. Run it inside the API
container, where the database is reachable. The container has no tests/ folder, so copy this
file and workflows/ into it first:

    docker cp dry_run_workflows.py <api container>:/tmp/
    docker cp workflows <api container>:/tmp/workflows
    docker exec -w /app -e PYTHONPATH=/app <api container> \
        python /tmp/dry_run_workflows.py [--templates-only]

Exits with 1 if it finds a problem.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select

from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.engine.sql_engine import SqlEngine
from om.db.models import AgentWorkflow
from om.db.models import WorkflowExecution
from om.workflows.graph import graph_from_workflow
from om.workflows.nodes.agent import load_step_agent
from om.workflows.nodes.agent import UnusableStepAgentError
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.nodes.registry import NodeTypeRegistry
from om.workflows.nodes.registry import UnknownNodeTypeError
from om.workflows.reference_check import reference_problem
from om.workflows.sequential import load_checkpoint
from om.workflows.state import restore_run_state
from om.workflows.state import ResumeIncompatibleError

TEMPLATES = Path(__file__).parent / "workflows"
MAX_PROBLEMS_SHOWN = 30


def _template_step(raw: dict[str, Any], order: int) -> SimpleNamespace:
    return SimpleNamespace(
        node_key=raw.get("node_key") or f"step_{order}",
        step_type=raw.get("step_type", "agent"),
        step_name=raw.get("step_name", f"Step {order}"),
        step_order=raw.get("step_order", order),
        output_key=raw.get("output_key", "output"),
        parent_key=raw.get("parent_key"),
        branch_index=raw.get("branch_index"),
        input_mapping=raw.get("input_mapping"),
        config=raw.get("config"),
        condition=raw.get("condition"),
    )


def check_templates(
    registry: NodeTypeRegistry, stats: Counter[str], problems: list[str]
) -> None:
    for path in sorted(TEMPLATES.glob("*.json")):
        stats["templates"] += 1
        template = json.loads(path.read_text(encoding="utf-8"))
        steps = template.get("steps") or []
        for order, raw in enumerate(steps):
            step_type = raw.get("step_type", "agent")
            if step_type == "agent" or raw.get("config") is None:
                continue
            try:
                spec = registry.resolve(step_type, raw.get("type_version"))
                spec.validate_config(raw["config"])
            except (UnknownNodeTypeError, ValidationError) as e:
                problems.append(f"template {path.name} step {order}: {type(e).__name__}: {e}")
        if template.get("schema_version", 1) >= 2:
            problem = reference_problem([_template_step(s, i) for i, s in enumerate(steps)])
            if problem:
                problems.append(f"template {path.name}: {problem}")


def check_database(
    registry: NodeTypeRegistry, stats: Counter[str], problems: list[str]
) -> None:
    SqlEngine.init_engine(pool_size=2, max_overflow=1)
    with get_session_with_current_tenant() as db:
        try:
            workflows = (
                db.execute(select(AgentWorkflow).where(AgentWorkflow.deleted.is_(False)))
                .unique()
                .scalars()
                .all()
            )
            graphs = {}
            for workflow in workflows:
                stats["workflows"] += 1
                stats[f"mode:{workflow.orchestration_mode}"] += 1
                try:
                    graph = graph_from_workflow(workflow, registry)
                except Exception as e:
                    problems.append(
                        f"workflow {workflow.id}: doesn't load: {type(e).__name__}: {str(e)[:200]}"
                    )
                    continue
                graphs[workflow.id] = graph
                rows = sorted(workflow.steps, key=lambda s: s.step_order)
                if [s.id for s in rows] != [n.step_id for n in graph.nodes]:
                    problems.append(f"workflow {workflow.id}: step order differs")
                for node, row in zip(graph.nodes, rows):
                    stats["steps"] += 1
                    stats[f"type:{node.node_type}/v{node.type_version}"] += 1
                    if node.node_type == "agent":
                        try:
                            load_step_agent(db, row.agent_id)
                        except UnusableStepAgentError as e:
                            problems.append(f"workflow {workflow.id} step {row.id}: {e}")

            paused = (
                db.execute(select(WorkflowExecution).where(WorkflowExecution.status == "paused"))
                .unique()
                .scalars()
                .all()
            )
            for execution in paused:
                stats["paused"] += 1
                graph = graphs.get(execution.workflow_id)
                if graph is None:
                    stats["paused:workflow_gone"] += 1
                    continue
                checkpoint = load_checkpoint(execution)
                if checkpoint is None:
                    stats["paused:no_checkpoint"] += 1
                    continue
                if graph.orchestration_mode != "sequential":
                    stats["paused:llm_decision"] += 1
                    continue
                try:
                    restore_run_state(checkpoint, graph, "dry run reply", execution.paused_at_step_id)
                    stats["paused:resumable"] += 1
                except ResumeIncompatibleError:
                    # By design: the run restarts with everything the user said.
                    stats["paused:restarts_with_user_text"] += 1
                except Exception as e:
                    problems.append(
                        f"execution {execution.id}: resume failed: {type(e).__name__}: {str(e)[:200]}"
                    )
        finally:
            db.rollback()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--templates-only", action="store_true", help="skip the database")
    args = parser.parse_args()

    registry = get_node_registry()
    stats: Counter[str] = Counter()
    problems: list[str] = []
    check_templates(registry, stats, problems)
    if not args.templates_only:
        check_database(registry, stats, problems)

    for key in sorted(stats):
        print(f"{key}: {stats[key]}")
    print(f"problems: {len(problems)}")
    for problem in problems[:MAX_PROBLEMS_SHOWN]:
        print(f"  - {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
