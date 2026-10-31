"""Which agents a workflow step may run, enforced at save time and at run time."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from om.configs.constants import DEFAULT_AGENT_ID
from om.workflows.models import WorkflowStepCreate
from om.workflows.nodes.agent import AgentStepConfigV1
from om.workflows.nodes.agent import load_agent_config_v1
from om.workflows.nodes.agent import load_step_agent
from om.workflows.nodes.agent import prepare_agent_step_v1
from om.workflows.nodes.agent import store_agent_config_v1
from om.workflows.nodes.agent import UnusableStepAgentError
from om.workflows.nodes.agent_tools import AgentToolCache
from om.workflows.nodes.base import StepSaveError


def _session(agent: Any) -> MagicMock:
    session = MagicMock()
    session.get.return_value = agent
    return session


def _agent(agent_id: int = 7, *, deleted: bool = False, workflow_id: int | None = None) -> Any:
    return SimpleNamespace(id=agent_id, deleted=deleted, workflow_id=workflow_id)


UNUSABLE = [
    pytest.param(_agent(deleted=True), 7, "not found or deleted", id="deleted"),
    pytest.param(None, 7, "not found or deleted", id="missing"),
    pytest.param(None, None, "not found or deleted", id="no_agent_id"),
    pytest.param(
        _agent(DEFAULT_AGENT_ID), DEFAULT_AGENT_ID, "default Assistant", id="default_assistant"
    ),
    pytest.param(_agent(workflow_id=3), 7, "a workflow's own agent", id="wrapper"),
]


class TestLoadStepAgent:
    def test_dedicated_agent_is_returned(self) -> None:
        agent = _agent()
        assert load_step_agent(_session(agent), 7) is agent

    @pytest.mark.parametrize("agent,agent_id,message", UNUSABLE)
    def test_unusable_agents_are_rejected(
        self, agent: Any, agent_id: int | None, message: str
    ) -> None:
        with pytest.raises(UnusableStepAgentError, match=message):
            load_step_agent(_session(agent), agent_id)

    def test_no_agent_id_does_not_query(self) -> None:
        session = _session(None)
        with pytest.raises(UnusableStepAgentError):
            load_step_agent(session, None)
        session.get.assert_not_called()


class TestSaveHook:
    @staticmethod
    def _step(agent_id: int | None) -> WorkflowStepCreate:
        return WorkflowStepCreate(
            step_type="agent",
            agent_id=agent_id,
            step_order=0,
            step_name="Research",
            output_key="research",
            config={"stale": True},
        )

    def test_dedicated_agent_saves_and_keeps_settings_in_legacy_fields(self) -> None:
        ctx = MagicMock(db_session=_session(_agent()))
        assert prepare_agent_step_v1(self._step(7), ctx).config is None

    # The payload model already refuses an agent step without an agent_id.
    @pytest.mark.parametrize(
        "agent,agent_id,message", [p for p in UNUSABLE if p.id != "no_agent_id"]
    )
    def test_unusable_agent_is_rejected_naming_the_step(
        self, agent: Any, agent_id: int | None, message: str
    ) -> None:
        ctx = MagicMock(db_session=_session(agent))
        with pytest.raises(StepSaveError, match=message) as e:
            prepare_agent_step_v1(self._step(agent_id), ctx)
        assert str(e.value).startswith('"Research" uses ')


class TestRunHook:
    @pytest.mark.parametrize("agent,agent_id,message", UNUSABLE)
    def test_cache_refuses_unusable_agents(
        self, agent: Any, agent_id: int | None, message: str
    ) -> None:
        cache = AgentToolCache(
            db_session=_session(agent), user=MagicMock(), emitter=MagicMock()
        )
        config = MagicMock(agent_id=agent_id)
        with pytest.raises(UnusableStepAgentError, match=message):
            cache.get(MagicMock(node_key="a"), config)


class TestExpectedOutputStorage:
    """The schema lives in the step's config column; the rest stays in its own columns."""

    SCHEMA = {"type": "object", "properties": {"days": {"type": "array"}}}

    def test_no_schema_leaves_the_config_as_it_was(self) -> None:
        dumped = AgentStepConfigV1(agent_id=1).model_dump()
        assert "output_schema" not in dumped
        assert "output_schema" not in store_agent_config_v1({"agent_id": 1})
        assert "config" not in store_agent_config_v1({"agent_id": 1})

    def test_a_schema_round_trips(self) -> None:
        stored = store_agent_config_v1({"agent_id": 1, "output_schema": self.SCHEMA})
        assert stored["config"] == {"output_schema": self.SCHEMA}
        step = SimpleNamespace(
            **{
                field: stored.get(field)
                for field in AgentStepConfigV1.model_fields
                if field != "output_schema"
            },
            config=stored["config"],
        )
        loaded = load_agent_config_v1(step)
        assert AgentStepConfigV1.model_validate(loaded).output_schema == self.SCHEMA

    def _prepare(self, schema: Any, mode: str = "sequential", **fields: Any) -> WorkflowStepCreate:
        agent = SimpleNamespace(id=5, deleted=False, workflow_id=None)
        return prepare_agent_step_v1(
            WorkflowStepCreate(
                step_name="Outline",
                step_order=0,
                agent_id=5,
                config={"output_schema": schema} if schema else {"junk": 1},
                **fields,
            ),
            SimpleNamespace(db_session=_session(agent), orchestration_mode=mode),
        )

    def test_save_keeps_a_good_schema(self) -> None:
        assert self._prepare(self.SCHEMA).config == {"output_schema": self.SCHEMA}

    def test_save_drops_everything_else_from_config(self) -> None:
        assert self._prepare(None).config is None

    def test_save_refuses_a_bad_schema(self) -> None:
        with pytest.raises(StepSaveError, match="Outline"):
            self._prepare({"type": "array"})

    def test_save_refuses_it_on_a_step_that_can_pause(self) -> None:
        with pytest.raises(StepSaveError, match="ask the user"):
            self._prepare(self.SCHEMA, can_request_input=True)

    def test_save_refuses_it_outside_sequential(self) -> None:
        with pytest.raises(StepSaveError, match="Sequential"):
            self._prepare(self.SCHEMA, mode="llm_decision")
