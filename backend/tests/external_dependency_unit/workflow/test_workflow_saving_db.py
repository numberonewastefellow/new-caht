"""Workflow saving + versioning against a real Postgres.

Covers the save path used by the API (om/workflows/saving.py): node keys,
upsert by node key (stable step ids), version history, router conversion and
validation, optimistic concurrency, and restore.

Requires Postgres with migration 0002_workflow_nodes applied and at least one
non-workflow agent (see tests/external_dependency_unit). No LLM calls.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from om.configs.constants import DEFAULT_AGENT_ID
from om.db.models import Agent
from om.db.models import AgentWorkflow
from om.db.workflow import create_or_update_workflow_agent
from om.db.workflow import get_workflow_by_id
from om.db.workflow_version import list_workflow_versions
from om.workflows.graph import graph_from_workflow
from om.workflows.models import ConditionConfig
from om.workflows.models import WorkflowCreate
from om.workflows.models import WorkflowStepCreate
from om.workflows.models import WorkflowUpdate
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.saving import restore_workflow_version
from om.workflows.saving import save_new_workflow
from om.workflows.saving import save_workflow_update
from om.workflows.saving import WorkflowSaveError
from om.workflows.saving import WorkflowVersionConflictError
from om.workflows.versioning import pin_workflow_version


@pytest.fixture
def agent_id(db_session: Session) -> int:
    agent = db_session.execute(
        select(Agent)
        .where(Agent.deleted.is_(False))
        .where(Agent.workflow_id.is_(None))
        .where(Agent.id != DEFAULT_AGENT_ID)
        .limit(1)
    ).scalar_one_or_none()
    if agent is None:
        pytest.skip("needs at least one dedicated agent in the test database")
    return agent.id


@pytest.fixture
def created(db_session: Session) -> Generator[list[int], None, None]:
    """Workflow ids created by a test; hard-deleted afterwards."""
    ids: list[int] = []
    yield ids
    db_session.rollback()
    for workflow_id in ids:
        workflow = db_session.get(AgentWorkflow, workflow_id)
        if workflow is not None:
            db_session.delete(workflow)
    db_session.commit()


def _agent(order: int, agent_id: int, name: str, **kwargs: object) -> WorkflowStepCreate:
    return WorkflowStepCreate(
        step_type="agent",
        agent_id=agent_id,
        step_order=order,
        step_name=name,
        output_key=name.lower(),
        **kwargs,  # type: ignore[arg-type]
    )


def _create(
    db_session: Session, created: list[int], steps: list[WorkflowStepCreate],
    mode: str = "sequential",
) -> AgentWorkflow:
    workflow = save_new_workflow(
        db_session,
        WorkflowCreate(name="flow-nodes save test", orchestration_mode=mode, steps=steps),  # type: ignore[arg-type]
        user_id=None,
    )
    created.append(workflow.id)
    return workflow


def _steps_payload(workflow: AgentWorkflow) -> list[WorkflowStepCreate]:
    """What an editor sends back: the loaded steps, keys included."""
    return [
        WorkflowStepCreate(
            node_key=s.node_key,
            step_type=s.step_type,
            type_version=s.type_version,
            config=s.config,
            agent_id=s.agent_id,
            step_order=s.step_order,
            step_name=s.step_name,
            output_key=s.output_key,
            condition=s.condition,
        )
        for s in sorted(workflow.steps, key=lambda s: s.step_order)
    ]


def test_new_workflow_gets_keys_and_first_version(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    workflow = _create(
        db_session, created, [_agent(0, agent_id, "Research"), _agent(1, agent_id, "Write")]
    )
    keys = [s.node_key for s in workflow.steps]
    assert all(k.startswith("n_") for k in keys) and len(set(keys)) == 2
    assert all(s.type_version == 1 for s in workflow.steps)
    versions = list_workflow_versions(db_session, workflow.id)
    assert [v.version for v in versions] == [1]
    assert workflow.version == 1


def test_update_by_node_key_keeps_step_ids(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    workflow = _create(
        db_session, created,
        [_agent(0, agent_id, "A"), _agent(1, agent_id, "B"), _agent(2, agent_id, "C")],
    )
    before = {s.node_key: s.id for s in workflow.steps}
    a, b, c = _steps_payload(workflow)

    # Swap B and C, drop nothing: ids must survive the re-order.
    reordered = [
        a,
        c.model_copy(update={"step_order": 1}),
        b.model_copy(update={"step_order": 2}),
    ]
    updated = save_workflow_update(
        db_session, workflow.id, WorkflowUpdate(steps=reordered), user_id=None
    )
    assert updated is not None
    after = {s.node_key: s.id for s in updated.steps}
    assert after == before
    assert [s.step_name for s in sorted(updated.steps, key=lambda s: s.step_order)] == [
        "A", "C", "B",
    ]
    assert updated.version == 2


def test_removed_steps_are_deleted_and_new_ones_added(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    workflow = _create(db_session, created, [_agent(0, agent_id, "A"), _agent(1, agent_id, "B")])
    a, _b = _steps_payload(workflow)
    updated = save_workflow_update(
        db_session,
        workflow.id,
        WorkflowUpdate(steps=[a, _agent(1, agent_id, "New")]),
        user_id=None,
    )
    assert updated is not None
    names = sorted(s.step_name for s in updated.steps)
    assert names == ["A", "New"]
    assert next(s for s in updated.steps if s.step_name == "A").node_key == a.node_key


def test_unchanged_save_records_no_new_version(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    workflow = _create(db_session, created, [_agent(0, agent_id, "A")])
    save_workflow_update(
        db_session, workflow.id, WorkflowUpdate(steps=_steps_payload(workflow)), user_id=None
    )
    assert [v.version for v in list_workflow_versions(db_session, workflow.id)] == [1]


def test_pin_is_idempotent(db_session: Session, created: list[int], agent_id: int) -> None:
    workflow = _create(db_session, created, [_agent(0, agent_id, "A")])
    graph = graph_from_workflow(workflow, get_node_registry())
    first = pin_workflow_version(db_session, workflow, graph)
    second = pin_workflow_version(db_session, workflow, graph)
    assert first.id == second.id


def test_legacy_router_payload_becomes_v2_with_mirror(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    router = WorkflowStepCreate(
        step_type="conditional_router",
        step_order=1,
        step_name="Route",
        output_key="route",
        condition=ConditionConfig(
            condition_field="$a.output",
            operator="contains",
            match_value="urgent",
            true_steps=[2],
            false_steps=[3],
        ),
    )
    workflow = _create(
        db_session, created,
        [_agent(0, agent_id, "A"), router, _agent(2, agent_id, "Fast"), _agent(3, agent_id, "Slow")],
    )
    by_name = {s.step_name: s for s in workflow.steps}
    route = by_name["Route"]
    assert route.type_version == 2
    assert route.config["true_node_keys"] == [by_name["Fast"].node_key]
    assert route.config["false_node_keys"] == [by_name["Slow"].node_key]
    # Legacy mirror kept for WORKFLOW_ENGINE_V2=false
    assert route.condition["true_steps"] == [2]
    assert route.condition["false_steps"] == [3]


def test_router_cannot_target_an_earlier_step(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    router = WorkflowStepCreate(
        step_type="conditional_router",
        step_order=1,
        step_name="Route",
        output_key="route",
        condition=ConditionConfig(condition_field="$a", true_steps=[0]),
    )
    with pytest.raises(WorkflowSaveError, match="after it"):
        _create(db_session, created, [_agent(0, agent_id, "A"), router])


def test_default_assistant_rejected_as_step_agent(
    db_session: Session, created: list[int]
) -> None:
    with pytest.raises(WorkflowSaveError, match="default Assistant"):
        _create(db_session, created, [_agent(0, DEFAULT_AGENT_ID, "A")])


def test_workflow_wrapper_agent_rejected_as_step_agent(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    workflow = _create(db_session, created, [_agent(0, agent_id, "A")])
    wrapper = create_or_update_workflow_agent(db_session, workflow)
    db_session.commit()
    try:
        with pytest.raises(WorkflowSaveError, match="a workflow's own agent"):
            _create(db_session, created, [_agent(0, wrapper.id, "A")])
    finally:
        db_session.rollback()
        db_session.delete(wrapper)
        db_session.commit()


def test_duplicate_output_key_rejected(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    first = _agent(0, agent_id, "Draft")
    second = _agent(1, agent_id, "Review").model_copy(update={"output_key": "draft"})
    with pytest.raises(WorkflowSaveError, match='Duplicate output key "draft"'):
        _create(db_session, created, [first, second])


def test_duplicate_output_key_rejected_across_parallel_branches(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    steps = [
        _parallel(0),
        _agent(1, agent_id, "Flights", parent_key="par", branch_index=0),
        _agent(2, agent_id, "Hotels", parent_key="par", branch_index=1).model_copy(
            update={"output_key": "flights"}
        ),
    ]
    with pytest.raises(WorkflowSaveError, match='Duplicate output key "flights"'):
        _create(db_session, created, steps)


@pytest.mark.parametrize("reserved", ["loop", "user_input"])
def test_reserved_output_key_rejected(
    db_session: Session, created: list[int], agent_id: int, reserved: str
) -> None:
    step = _agent(0, agent_id, "A").model_copy(update={"output_key": reserved})
    with pytest.raises(WorkflowSaveError, match="reserved output key"):
        _create(db_session, created, [step])


@pytest.mark.parametrize(
    "step_type,config",
    [
        ("parallel", {"branches": [{"label": "A"}, {"label": "B"}]}),
        ("loop", {"mode": "for_each", "items": "$a.output", "max_iterations": 3}),
        ("code", {"code": "def main(inputs):\n    return {'result': 1}\n"}),
    ],
)
def test_sequential_only_nodes_rejected_in_llm_decision(
    db_session: Session,
    created: list[int],
    agent_id: int,
    step_type: str,
    config: dict[str, object],
) -> None:
    node = WorkflowStepCreate(
        node_key="n",
        step_type=step_type,
        step_order=1,
        step_name="Node",
        output_key="node",
        config=config,
    )
    with pytest.raises(WorkflowSaveError, match="llm_decision"):
        _create(db_session, created, [_agent(0, agent_id, "A"), node], mode="llm_decision")


def test_router_not_allowed_in_llm_decision(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    router = WorkflowStepCreate(
        step_type="conditional_router",
        step_order=1,
        step_name="Route",
        output_key="route",
        condition=ConditionConfig(condition_field="$a"),
    )
    with pytest.raises(WorkflowSaveError, match="llm_decision"):
        _create(db_session, created, [_agent(0, agent_id, "A"), router], mode="llm_decision")


def test_unknown_node_type_rejected(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    step = WorkflowStepCreate(
        step_type="teleport", step_order=0, step_name="X", config={"x": 1}
    )
    with pytest.raises(WorkflowSaveError, match="teleport"):
        _create(db_session, created, [step])


def test_missing_agent_rejected(db_session: Session, created: list[int]) -> None:
    with pytest.raises(WorkflowSaveError, match="not found"):
        _create(db_session, created, [_agent(0, 999_999_999, "Ghost")])


def test_stale_expected_version_conflicts(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    workflow = _create(db_session, created, [_agent(0, agent_id, "A")])
    with pytest.raises(WorkflowVersionConflictError):
        save_workflow_update(
            db_session,
            workflow.id,
            WorkflowUpdate(name="renamed", expected_version=workflow.version + 5),
            user_id=None,
        )


def _parallel(order: int, key: str = "par", **kwargs: object) -> WorkflowStepCreate:
    return WorkflowStepCreate(
        node_key=key,
        step_type="parallel",
        step_order=order,
        step_name="Fan out",
        output_key="fan",
        config={"branches": [{"label": "Flights"}, {"label": "Hotels"}]},
        **kwargs,  # type: ignore[arg-type]
    )


def test_parallel_children_are_linked_to_their_container(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    workflow = _create(db_session, created, [
        _agent(0, agent_id, "Intake"),
        _parallel(1),
        _agent(2, agent_id, "Flights", parent_key="par", branch_index=0),
        _agent(3, agent_id, "Hotels", parent_key="par", branch_index=1),
    ])
    by_name = {s.step_name: s for s in workflow.steps}
    container_id = by_name["Fan out"].id
    assert by_name["Flights"].parent_step_id == container_id
    assert by_name["Hotels"].parent_step_id == container_id
    assert (by_name["Flights"].branch_index, by_name["Hotels"].branch_index) == (0, 1)
    graph = graph_from_workflow(workflow, get_node_registry())
    assert [n.name for n in graph.top_level()] == ["Intake", "Fan out"]
    assert [[n.name for n in b] for b in graph.branches("par")] == [["Flights"], ["Hotels"]]


def test_removing_a_container_keeps_its_moved_children(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    workflow = _create(db_session, created, [
        _parallel(0),
        _agent(1, agent_id, "Flights", parent_key="par", branch_index=0),
        _agent(2, agent_id, "Hotels", parent_key="par", branch_index=1),
    ])
    ids = {s.node_key: s.id for s in workflow.steps}
    _par, flights, hotels = _steps_payload(workflow)
    # Drop the container; the two steps become top-level (same keys).
    updated = save_workflow_update(
        db_session,
        workflow.id,
        WorkflowUpdate(steps=[
            flights.model_copy(update={"step_order": 0}),
            hotels.model_copy(update={"step_order": 1}),
        ]),
        user_id=None,
    )
    assert updated is not None
    kept = {s.node_key: s for s in updated.steps}
    assert set(kept) == {flights.node_key, hotels.node_key}
    assert all(s.parent_step_id is None and s.branch_index is None for s in kept.values())
    assert {k: s.id for k, s in kept.items()} == {k: ids[k] for k in kept}  # same rows


@pytest.mark.parametrize(
    ("child_kwargs", "message"),
    [
        ({"can_request_input": True}, "can't ask for input"),
        ({"promote_output": True}, "can't ask for input"),
        ({"parent_key": "ghost"}, "unknown container"),
    ],
)
def test_container_child_rules(
    db_session: Session, created: list[int], agent_id: int,
    child_kwargs: dict[str, object], message: str,
) -> None:
    kwargs: dict[str, object] = {"parent_key": "par", "branch_index": 0, **child_kwargs}
    with pytest.raises(WorkflowSaveError, match=message):
        _create(db_session, created, [
            _parallel(0),
            _agent(1, agent_id, "A", **kwargs),
            _agent(2, agent_id, "B", parent_key="par", branch_index=1),
        ])


def test_agent_cannot_contain_steps(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    with pytest.raises(WorkflowSaveError, match="can't contain steps"):
        _create(db_session, created, [
            _agent(0, agent_id, "Boss", node_key="boss"),
            _agent(1, agent_id, "Child", parent_key="boss", branch_index=0),
        ])


def test_router_cannot_skip_into_another_branch(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    router = WorkflowStepCreate(
        node_key="route",
        step_type="conditional_router",
        step_order=1,
        step_name="Route",
        output_key="route",
        parent_key="par",
        branch_index=0,
        config={"condition_field": "$x", "true_node_keys": ["other"], "false_node_keys": []},
    )
    with pytest.raises(WorkflowSaveError, match="own branch"):
        _create(db_session, created, [
            _parallel(0),
            router,
            _agent(2, agent_id, "Other", node_key="other", parent_key="par", branch_index=1),
        ])


def test_restore_makes_an_old_version_current(
    db_session: Session, created: list[int], agent_id: int
) -> None:
    workflow = _create(db_session, created, [_agent(0, agent_id, "Original")])
    (step,) = _steps_payload(workflow)
    save_workflow_update(
        db_session,
        workflow.id,
        WorkflowUpdate(steps=[step.model_copy(update={"step_name": "Edited"})]),
        user_id=None,
    )

    restored = restore_workflow_version(db_session, workflow.id, 1, user_id=None)
    assert restored is not None
    (restored_step,) = restored.steps
    assert restored_step.step_name == "Original"
    assert restored_step.node_key == step.node_key  # same step, not recreated
    assert [v.version for v in list_workflow_versions(db_session, workflow.id)] == [3, 2, 1]
    assert get_workflow_by_id(db_session, workflow.id).version == 3  # type: ignore[union-attr]
