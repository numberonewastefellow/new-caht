"""A workflow save must not lose edits or history (real Postgres).

Covers concurrent saves, atomicity of steps + version row, and the first save of
a workflow that predates version history. No LLM calls.
"""

import threading
import time
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from om.configs.constants import DEFAULT_AGENT_ID
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.models import Agent
from om.db.models import AgentWorkflow
from om.db.models import AgentWorkflowVersion
from om.db.workflow import get_workflow_by_id
from om.db.workflow_version import get_latest_workflow_version
from om.db.workflow_version import list_workflow_versions
from om.workflows import saving
from om.workflows.graph import graph_from_workflow
from om.workflows.models import WorkflowCreate
from om.workflows.models import WorkflowStepCreate
from om.workflows.models import WorkflowUpdate
from om.workflows.nodes.builtin import get_node_registry
from om.workflows.saving import restore_workflow_version
from om.workflows.saving import save_new_workflow
from om.workflows.saving import save_workflow_update
from om.workflows.saving import WorkflowSaveError
from om.workflows.saving import WorkflowVersionConflictError
from om.workflows.workflow_engine import _pinned_version_id


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
def workflow_id(db_session: Session, agent_id: int) -> Generator[int, None, None]:
    workflow = save_new_workflow(
        db_session,
        WorkflowCreate(
            name="flow-nodes save safety",
            orchestration_mode="sequential",
            steps=[_step(0, agent_id, "A")],
        ),
        user_id=None,
    )
    yield workflow.id
    db_session.rollback()
    row = db_session.get(AgentWorkflow, workflow.id)
    if row is not None:
        db_session.delete(row)
    db_session.commit()


def _step(order: int, agent_id: int, name: str) -> WorkflowStepCreate:
    return WorkflowStepCreate(
        node_key=f"k_{name.lower()}",
        step_type="agent",
        agent_id=agent_id,
        step_order=order,
        step_name=name,
        output_key=name.lower(),
    )


def _step_names(db_session: Session, workflow_id: int) -> list[str]:
    db_session.expire_all()
    workflow = get_workflow_by_id(db_session, workflow_id)
    assert workflow is not None
    return [s.step_name for s in sorted(workflow.steps, key=lambda s: s.step_order)]


def _version_numbers(db_session: Session, workflow_id: int) -> list[int]:
    db_session.expire_all()
    return sorted(v.version for v in list_workflow_versions(db_session, workflow_id))


def _make_pre_migration(db_session: Session, workflow_id: int) -> None:
    """Put a workflow in the state migration 0002 left old workflows in."""
    db_session.execute(
        delete(AgentWorkflowVersion).where(AgentWorkflowVersion.workflow_id == workflow_id)
    )
    workflow = db_session.get(AgentWorkflow, workflow_id)
    assert workflow is not None
    workflow.version = 1
    db_session.commit()


class TestConcurrentSaves:
    def test_only_one_of_two_saves_from_the_same_version_wins(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        start_version = db_session.get(AgentWorkflow, workflow_id).version  # type: ignore[union-attr]
        names = ["First", "Second"]
        barrier = threading.Barrier(2)
        outcomes: dict[str, str] = {}
        real_prepare = saving.prepare_steps

        def slow_prepare(*args: Any, **kwargs: Any) -> Any:
            # Holds each save between its version check and its write.
            result = real_prepare(*args, **kwargs)
            time.sleep(0.5)
            return result

        def save(name: str) -> None:
            with get_session_with_current_tenant() as session:
                barrier.wait(timeout=10)
                try:
                    save_workflow_update(
                        session,
                        workflow_id,
                        WorkflowUpdate(
                            expected_version=start_version,
                            steps=[_step(0, agent_id, name)],
                        ),
                        user_id=None,
                    )
                    outcomes[name] = "saved"
                except WorkflowVersionConflictError:
                    outcomes[name] = "conflict"
                except IntegrityError:
                    outcomes[name] = "integrity_error"

        with patch.object(saving, "prepare_steps", slow_prepare):
            threads = [threading.Thread(target=save, args=(n,)) for n in names]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)

        assert sorted(outcomes.values()) == ["conflict", "saved"], outcomes
        winner = next(n for n, outcome in outcomes.items() if outcome == "saved")
        assert _step_names(db_session, workflow_id) == [winner]
        assert _version_numbers(db_session, workflow_id) == [start_version, start_version + 1]

    def test_stale_save_changes_nothing(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        start_version = db_session.get(AgentWorkflow, workflow_id).version  # type: ignore[union-attr]
        save_workflow_update(
            db_session,
            workflow_id,
            WorkflowUpdate(expected_version=start_version, steps=[_step(0, agent_id, "Mine")]),
            user_id=None,
        )
        with pytest.raises(WorkflowVersionConflictError):
            save_workflow_update(
                db_session,
                workflow_id,
                WorkflowUpdate(expected_version=start_version, steps=[_step(0, agent_id, "Theirs")]),
                user_id=None,
            )
        assert _step_names(db_session, workflow_id) == ["Mine"]


class TestAtomicSave:
    def test_failed_version_row_leaves_the_steps_untouched(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        versions_before = _version_numbers(db_session, workflow_id)
        real_pin = saving.pin_workflow_version
        calls = {"n": 0}

        def fail_on_new_definition(session: Session, workflow: Any, graph: Any, **kwargs: Any) -> Any:
            # The snapshot of the current definition is allowed; recording the edit fails.
            if any(node.name == "Edited" for node in graph.nodes):
                calls["n"] += 1
                raise RuntimeError("version row could not be written")
            return real_pin(session, workflow, graph, **kwargs)

        with patch.object(saving, "pin_workflow_version", fail_on_new_definition):
            with pytest.raises(RuntimeError):
                save_workflow_update(
                    db_session,
                    workflow_id,
                    WorkflowUpdate(steps=[_step(0, agent_id, "Edited")]),
                    user_id=None,
                )
        assert calls["n"] == 1
        assert _step_names(db_session, workflow_id) == ["A"]
        assert _version_numbers(db_session, workflow_id) == versions_before

    def test_losing_a_version_number_race_is_a_conflict_not_a_server_error(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        real_pin = saving.pin_workflow_version

        def lose_race(session: Session, workflow: Any, graph: Any, **kwargs: Any) -> Any:
            if any(node.name == "Edited" for node in graph.nodes):
                raise IntegrityError("insert", {}, Exception("duplicate version"))
            return real_pin(session, workflow, graph, **kwargs)

        with patch.object(saving, "pin_workflow_version", lose_race):
            with pytest.raises(WorkflowVersionConflictError):
                save_workflow_update(
                    db_session,
                    workflow_id,
                    WorkflowUpdate(steps=[_step(0, agent_id, "Edited")]),
                    user_id=None,
                )
        assert _step_names(db_session, workflow_id) == ["A"]


class TestPreMigrationWorkflows:
    def test_first_save_keeps_the_previous_definition_restorable(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        _make_pre_migration(db_session, workflow_id)

        save_workflow_update(
            db_session,
            workflow_id,
            WorkflowUpdate(steps=[_step(0, agent_id, "Edited")]),
            user_id=None,
        )

        assert _version_numbers(db_session, workflow_id) == [1, 2]
        assert db_session.get(AgentWorkflow, workflow_id).version == 2  # type: ignore[union-attr]
        restored = restore_workflow_version(db_session, workflow_id, 1, user_id=None)
        assert restored is not None
        assert _step_names(db_session, workflow_id) == ["A"]

    def test_second_admin_holding_version_1_gets_a_conflict(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        _make_pre_migration(db_session, workflow_id)

        save_workflow_update(
            db_session,
            workflow_id,
            WorkflowUpdate(expected_version=1, steps=[_step(0, agent_id, "First admin")]),
            user_id=None,
        )
        with pytest.raises(WorkflowVersionConflictError):
            save_workflow_update(
                db_session,
                workflow_id,
                WorkflowUpdate(expected_version=1, steps=[_step(0, agent_id, "Second admin")]),
                user_id=None,
            )
        assert _step_names(db_session, workflow_id) == ["First admin"]

    def test_saving_without_changes_adds_only_the_baseline(
        self, db_session: Session, workflow_id: int
    ) -> None:
        _make_pre_migration(db_session, workflow_id)
        workflow = get_workflow_by_id(db_session, workflow_id)
        assert workflow is not None

        save_workflow_update(
            db_session, workflow_id, WorkflowUpdate(name=workflow.name), user_id=None
        )

        assert _version_numbers(db_session, workflow_id) == [1]
        assert db_session.get(AgentWorkflow, workflow_id).version == 1  # type: ignore[union-attr]

    def test_live_definition_always_matches_the_latest_version(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        _make_pre_migration(db_session, workflow_id)
        save_workflow_update(
            db_session,
            workflow_id,
            WorkflowUpdate(steps=[_step(0, agent_id, "Edited")]),
            user_id=None,
        )
        db_session.expire_all()
        workflow = get_workflow_by_id(db_session, workflow_id)
        assert workflow is not None
        latest = max(list_workflow_versions(db_session, workflow_id), key=lambda v: v.version)
        graph = graph_from_workflow(workflow, get_node_registry())
        assert latest.content_hash == graph.content_hash()


class TestLlmDecisionRunsRecordTheirVersion:
    @pytest.fixture
    def llm_workflow(self, db_session: Session, agent_id: int) -> Generator[AgentWorkflow, None, None]:
        workflow = save_new_workflow(
            db_session,
            WorkflowCreate(
                name="flow-nodes llm pin",
                orchestration_mode="llm_decision",
                steps=[_step(0, agent_id, "A")],
            ),
            user_id=None,
        )
        yield workflow
        db_session.rollback()
        row = db_session.get(AgentWorkflow, workflow.id)
        if row is not None:
            db_session.delete(row)
        db_session.commit()

    def test_run_of_a_pre_migration_workflow_gets_a_version(
        self, db_session: Session, llm_workflow: AgentWorkflow
    ) -> None:
        _make_pre_migration(db_session, llm_workflow.id)
        user = MagicMock(id=None)

        version_id = _pinned_version_id(db_session, llm_workflow, user)

        assert version_id is not None
        assert _pinned_version_id(db_session, llm_workflow, user) == version_id
        assert _version_numbers(db_session, llm_workflow.id) == [1]


class TestVersionsIncludeWorkflowSettings:
    def test_editing_only_the_orchestrator_prompt_records_a_version(
        self, db_session: Session, workflow_id: int
    ) -> None:
        before = _version_numbers(db_session, workflow_id)
        save_workflow_update(
            db_session,
            workflow_id,
            WorkflowUpdate(orchestrator_prompt="Route billing questions to Billing."),
            user_id=None,
        )
        assert len(_version_numbers(db_session, workflow_id)) == len(before) + 1

    def test_restore_brings_settings_back(
        self, db_session: Session, workflow_id: int
    ) -> None:
        save_workflow_update(
            db_session,
            workflow_id,
            WorkflowUpdate(orchestrator_prompt="First prompt", max_steps=7),
            user_id=None,
        )
        version = db_session.get(AgentWorkflow, workflow_id).version  # type: ignore[union-attr]
        save_workflow_update(
            db_session,
            workflow_id,
            WorkflowUpdate(orchestrator_prompt="Second prompt", max_steps=9),
            user_id=None,
        )
        restore_workflow_version(db_session, workflow_id, version, user_id=None)
        db_session.expire_all()
        workflow = db_session.get(AgentWorkflow, workflow_id)
        assert workflow is not None
        assert workflow.orchestrator_prompt == "First prompt"
        assert workflow.max_steps == 7

    def test_restore_clears_a_setting_the_version_did_not_have(
        self, db_session: Session, workflow_id: int
    ) -> None:
        version = db_session.get(AgentWorkflow, workflow_id).version  # type: ignore[union-attr]
        save_workflow_update(
            db_session,
            workflow_id,
            WorkflowUpdate(orchestrator_prompt="Added later"),
            user_id=None,
        )
        restore_workflow_version(db_session, workflow_id, version, user_id=None)
        db_session.expire_all()
        workflow = db_session.get(AgentWorkflow, workflow_id)
        assert workflow is not None
        assert not workflow.orchestrator_prompt

    def test_restoring_an_older_definition_keeps_the_current_settings(
        self, db_session: Session, workflow_id: int
    ) -> None:
        rows = list_workflow_versions(db_session, workflow_id)
        oldest = min(rows, key=lambda v: v.version)
        definition = dict(oldest.definition)
        definition.pop("settings", None)
        oldest.definition = definition
        db_session.commit()
        save_workflow_update(
            db_session,
            workflow_id,
            WorkflowUpdate(orchestrator_prompt="Current prompt"),
            user_id=None,
        )
        restore_workflow_version(db_session, workflow_id, oldest.version, user_id=None)
        db_session.expire_all()
        workflow = db_session.get(AgentWorkflow, workflow_id)
        assert workflow is not None
        assert workflow.orchestrator_prompt == "Current prompt"


class TestReviewFindings:
    def test_saving_a_new_workflow_is_all_or_nothing(
        self, db_session: Session, agent_id: int, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        name = "flow-nodes atomic create"

        def fail(*_: object, **__: object) -> None:
            raise RuntimeError("no wrapper agent")

        monkeypatch.setattr(
            "om.workflows.saving.create_or_update_workflow_agent", fail
        )
        with pytest.raises(RuntimeError):
            save_new_workflow(
                db_session,
                WorkflowCreate(
                    name=name,
                    orchestration_mode="sequential",
                    steps=[_step(0, agent_id, "A")],
                ),
                user_id=None,
            )
        assert (
            db_session.execute(
                select(AgentWorkflow).where(AgentWorkflow.name == name)
            ).first()
            is None
        )

    def test_a_new_workflow_gets_its_wrapper_agent(
        self, db_session: Session, workflow_id: int
    ) -> None:
        wrappers = db_session.execute(
            select(Agent).where(Agent.workflow_id == workflow_id)
        ).scalars().all()
        assert len(wrappers) == 1
        # The fixture removes the workflow; its wrapper goes first.
        db_session.delete(wrappers[0])
        db_session.commit()

    def test_a_run_pins_what_is_saved_not_what_it_read_earlier(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        stale = get_workflow_by_id(db_session, workflow_id)
        assert stale is not None
        before = stale.version
        with get_session_with_current_tenant() as other:
            save_workflow_update(
                other,
                workflow_id,
                WorkflowUpdate(description="saved meanwhile", expected_version=before),
                user_id=None,
            )
        # `stale` still holds the old description until the pin re-reads it.
        version_id = _pinned_version_id(db_session, stale, MagicMock(id=None))
        db_session.commit()
        row = get_latest_workflow_version(db_session, workflow_id)
        assert row is not None
        assert row.id == version_id
        assert row.version == before + 1
        assert row.definition["settings"]["description"] == "saved meanwhile"

    def test_a_metadata_save_doesnt_recheck_unchanged_steps(
        self, db_session: Session, workflow_id: int
    ) -> None:
        workflow = get_workflow_by_id(db_session, workflow_id)
        assert workflow is not None
        workflow.schema_version = 1
        # Old rows could be written with a reference the new rules refuse.
        workflow.steps[0].input_mapping = {"task": "$not_a_step.output"}
        db_session.commit()
        saved = save_workflow_update(
            db_session, workflow_id, WorkflowUpdate(description="renamed"), user_id=None
        )
        assert saved is not None and saved.description == "renamed"
        with pytest.raises(WorkflowSaveError):
            save_workflow_update(
                db_session, workflow_id, WorkflowUpdate(schema_version=2), user_id=None
            )


class TestSchemaVersions:
    def test_new_workflows_use_safe_references(
        self, db_session: Session, workflow_id: int
    ) -> None:
        assert db_session.get(AgentWorkflow, workflow_id).schema_version == 2  # type: ignore[union-attr]

    def test_a_bad_reference_is_refused_on_save(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        step = _step(0, agent_id, "A").model_copy(
            update={"input_mapping": {"task": "Use $later.output"}}
        )
        with pytest.raises(WorkflowSaveError, match=r"reads \$later.output"):
            save_workflow_update(
                db_session, workflow_id, WorkflowUpdate(steps=[step]), user_id=None
            )

    def test_an_old_workflow_keeps_its_behaviour_until_upgraded(
        self, db_session: Session, workflow_id: int, agent_id: int
    ) -> None:
        workflow = db_session.get(AgentWorkflow, workflow_id)
        assert workflow is not None
        workflow.schema_version = 1
        db_session.commit()
        step = _step(0, agent_id, "A").model_copy(
            update={"input_mapping": {"task": "Use $later.output"}}
        )
        save_workflow_update(
            db_session, workflow_id, WorkflowUpdate(steps=[step]), user_id=None
        )
        with pytest.raises(WorkflowSaveError, match=r"reads \$later.output"):
            save_workflow_update(
                db_session, workflow_id, WorkflowUpdate(schema_version=2), user_id=None
            )

    def test_upgrading_records_a_version_that_restores(
        self, db_session: Session, workflow_id: int
    ) -> None:
        workflow = db_session.get(AgentWorkflow, workflow_id)
        assert workflow is not None
        workflow.schema_version = 1
        db_session.commit()
        save_workflow_update(db_session, workflow_id, WorkflowUpdate(name="v1 name"), user_id=None)
        old_version = db_session.get(AgentWorkflow, workflow_id).version  # type: ignore[union-attr]
        save_workflow_update(db_session, workflow_id, WorkflowUpdate(schema_version=2), user_id=None)
        assert db_session.get(AgentWorkflow, workflow_id).schema_version == 2  # type: ignore[union-attr]
        restore_workflow_version(db_session, workflow_id, old_version, user_id=None)
        db_session.expire_all()
        assert db_session.get(AgentWorkflow, workflow_id).schema_version == 1  # type: ignore[union-attr]

    def test_an_unknown_schema_version_is_refused(
        self, db_session: Session, workflow_id: int
    ) -> None:
        with pytest.raises(WorkflowSaveError, match="Unknown schema version"):
            save_workflow_update(
                db_session, workflow_id, WorkflowUpdate(schema_version=9), user_id=None
            )
