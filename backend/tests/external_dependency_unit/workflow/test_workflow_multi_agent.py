"""Integration tests for the Multi-Agent Workflow system.

Creates 3 agents (Math Solver, Verifier, Summarizer) and tests
both CRUD operations and workflow execution in sequential mode.

Requires a running PostgreSQL database and LLM provider.
Run with: pytest tests/external_dependency_unit/workflow/test_workflow_multi_agent.py -v
"""

import json
from collections.abc import Generator
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.engine.sql_engine import SqlEngine
from onyx.db.models import AgentWorkflow
from onyx.db.models import AgentWorkflowStep
from onyx.db.models import Persona
from onyx.db.models import User
from onyx.db.models import UserRole
from onyx.db.persona import upsert_persona
from onyx.db.workflow import create_workflow
from onyx.db.workflow import delete_workflow
from onyx.db.workflow import get_workflow_by_id
from onyx.db.workflow import list_workflows
from onyx.db.workflow import update_workflow
from onyx.server.features.persona.models import PersonaSnapshot
from onyx.server.manage.models import RecencyBiasSetting
from onyx.workflows.models import WorkflowCreate
from onyx.workflows.models import WorkflowStepCreate
from onyx.workflows.models import WorkflowUpdate
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR
from tests.external_dependency_unit.constants import TEST_TENANT_ID


# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_session() -> Generator[Session, None, None]:
    """Module-scoped DB session for all tests in this file."""
    SqlEngine.init_engine(pool_size=5, max_overflow=2)
    token = CURRENT_TENANT_ID_CONTEXTVAR.set(TEST_TENANT_ID)
    try:
        with get_session_with_current_tenant() as session:
            yield session
    finally:
        CURRENT_TENANT_ID_CONTEXTVAR.reset(token)


@pytest.fixture(scope="module")
def test_user(db_session: Session) -> User:
    """Create a test user for workflow ownership."""
    from fastapi_users.password import PasswordHelper

    pw = PasswordHelper()
    user = User(
        id=uuid4(),
        email=f"workflow_test_{uuid4().hex[:8]}@example.com",
        hashed_password=pw.hash(pw.generate()),
        is_active=True,
        is_superuser=True,
        is_verified=True,
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="module")
def math_solver_persona(db_session: Session, test_user: User) -> Persona:
    """Agent 1: Math Solver — takes a math problem and solves it step by step."""
    persona = upsert_persona(
        user=test_user,
        name="Test Math Solver",
        description="Solves math problems step by step with clear working.",
        num_chunks=0,
        llm_relevance_filter=False,
        llm_filter_extraction=False,
        recency_bias=RecencyBiasSetting.BASE_DECAY,
        llm_model_provider_override=None,
        llm_model_version_override=None,
        starter_messages=None,
        system_prompt=(
            "You are a precise math solver. When given a math problem, "
            "solve it step by step showing all working. Always end with "
            "'ANSWER: <number>' on its own line."
        ),
        task_prompt="",
        datetime_aware=False,
        is_public=True,
        db_session=db_session,
        tool_ids=[],
    )
    return db_session.get(Persona, persona.id)


@pytest.fixture(scope="module")
def verifier_persona(db_session: Session, test_user: User) -> Persona:
    """Agent 2: Verifier — checks a math solution for correctness."""
    persona = upsert_persona(
        user=test_user,
        name="Test Verifier",
        description="Verifies mathematical solutions for correctness.",
        num_chunks=0,
        llm_relevance_filter=False,
        llm_filter_extraction=False,
        recency_bias=RecencyBiasSetting.BASE_DECAY,
        llm_model_provider_override=None,
        llm_model_version_override=None,
        starter_messages=None,
        system_prompt=(
            "You are a math verification expert. Review the solution provided "
            "and check if it is correct. State VERIFIED if correct, or "
            "INCORRECT with the right answer if wrong."
        ),
        task_prompt="",
        datetime_aware=False,
        is_public=True,
        db_session=db_session,
        tool_ids=[],
    )
    return db_session.get(Persona, persona.id)


@pytest.fixture(scope="module")
def summarizer_persona(db_session: Session, test_user: User) -> Persona:
    """Agent 3: Summarizer — produces a plain-language summary of the result."""
    persona = upsert_persona(
        user=test_user,
        name="Test Summarizer",
        description="Summarizes technical results into plain language.",
        num_chunks=0,
        llm_relevance_filter=False,
        llm_filter_extraction=False,
        recency_bias=RecencyBiasSetting.BASE_DECAY,
        llm_model_provider_override=None,
        llm_model_version_override=None,
        starter_messages=None,
        system_prompt=(
            "You are a friendly summarizer. Take the technical output from "
            "previous agents and produce a brief, plain-language summary "
            "that anyone can understand. Keep it under 3 sentences."
        ),
        task_prompt="",
        datetime_aware=False,
        is_public=True,
        db_session=db_session,
        tool_ids=[],
    )
    return db_session.get(Persona, persona.id)


# ─── Test: CRUD Operations ───────────────────────────────────────────────


class TestWorkflowCRUD:
    """Test workflow create, read, update, delete operations."""

    def test_create_workflow_with_3_agents(
        self,
        db_session: Session,
        test_user: User,
        math_solver_persona: Persona,
        verifier_persona: Persona,
        summarizer_persona: Persona,
    ) -> None:
        """Create a 3-agent sequential workflow and verify all fields."""
        workflow_data = WorkflowCreate(
            name="Math Pipeline Test",
            description="Solve -> Verify -> Summarize",
            orchestration_mode="sequential",
            max_steps=10,
            timeout_seconds=300,
            is_public=True,
            steps=[
                WorkflowStepCreate(
                    persona_id=math_solver_persona.id,
                    step_order=0,
                    step_name="Solve",
                    step_description="Solve the math problem step by step",
                    output_key="solution",
                ),
                WorkflowStepCreate(
                    persona_id=verifier_persona.id,
                    step_order=1,
                    step_name="Verify",
                    step_description="Verify the solution is correct",
                    output_key="verification",
                ),
                WorkflowStepCreate(
                    persona_id=summarizer_persona.id,
                    step_order=2,
                    step_name="Summarize",
                    step_description="Summarize the result in plain language",
                    output_key="summary",
                    is_terminal=True,
                ),
            ],
        )

        workflow = create_workflow(
            db_session=db_session,
            workflow_create=workflow_data,
            user_id=test_user.id,
        )

        # Verify workflow fields
        assert workflow.id is not None
        assert workflow.name == "Math Pipeline Test"
        assert workflow.description == "Solve -> Verify -> Summarize"
        assert workflow.orchestration_mode == "sequential"
        assert workflow.max_steps == 10
        assert workflow.timeout_seconds == 300
        assert workflow.is_public is True
        assert workflow.deleted is False

        # Verify steps
        assert len(workflow.steps) == 3

        steps_sorted = sorted(workflow.steps, key=lambda s: s.step_order)

        assert steps_sorted[0].step_name == "Solve"
        assert steps_sorted[0].persona_id == math_solver_persona.id
        assert steps_sorted[0].output_key == "solution"
        assert steps_sorted[0].is_terminal is False

        assert steps_sorted[1].step_name == "Verify"
        assert steps_sorted[1].persona_id == verifier_persona.id
        assert steps_sorted[1].output_key == "verification"

        assert steps_sorted[2].step_name == "Summarize"
        assert steps_sorted[2].persona_id == summarizer_persona.id
        assert steps_sorted[2].output_key == "summary"
        assert steps_sorted[2].is_terminal is True

        # Store workflow ID for subsequent tests
        TestWorkflowCRUD._workflow_id = workflow.id

    def test_get_workflow_by_id(self, db_session: Session) -> None:
        """Retrieve workflow by ID and verify data integrity."""
        workflow = get_workflow_by_id(
            db_session=db_session,
            workflow_id=TestWorkflowCRUD._workflow_id,
        )
        assert workflow is not None
        assert workflow.name == "Math Pipeline Test"
        assert len(workflow.steps) == 3

    def test_list_workflows(self, db_session: Session, test_user: User) -> None:
        """List workflows and confirm ours appears."""
        workflows = list_workflows(
            db_session=db_session,
            user_id=test_user.id,
            include_public=True,
        )
        ids = [w.id for w in workflows]
        assert TestWorkflowCRUD._workflow_id in ids

    def test_update_workflow(self, db_session: Session) -> None:
        """Update workflow name and max_steps."""
        updated = update_workflow(
            db_session=db_session,
            workflow_id=TestWorkflowCRUD._workflow_id,
            workflow_update=WorkflowUpdate(
                name="Math Pipeline Test (Updated)",
                max_steps=20,
            ),
        )
        assert updated is not None
        assert updated.name == "Math Pipeline Test (Updated)"
        assert updated.max_steps == 20
        # Steps should be unchanged
        assert len(updated.steps) == 3

    def test_create_llm_decision_workflow(
        self,
        db_session: Session,
        test_user: User,
        math_solver_persona: Persona,
        verifier_persona: Persona,
        summarizer_persona: Persona,
    ) -> None:
        """Create an LLM-decision mode workflow with 3 agents."""
        workflow_data = WorkflowCreate(
            name="Smart Math Pipeline",
            description="LLM orchestrator decides which agent to call",
            orchestration_mode="llm_decision",
            orchestrator_prompt=(
                "You coordinate a math problem-solving team. "
                "First call the Math Solver, then the Verifier, "
                "then the Summarizer. Return the final summary."
            ),
            max_steps=15,
            timeout_seconds=600,
            is_public=True,
            steps=[
                WorkflowStepCreate(
                    persona_id=math_solver_persona.id,
                    step_order=0,
                    step_name="Math Solver",
                    output_key="solution",
                ),
                WorkflowStepCreate(
                    persona_id=verifier_persona.id,
                    step_order=1,
                    step_name="Verifier",
                    output_key="verification",
                ),
                WorkflowStepCreate(
                    persona_id=summarizer_persona.id,
                    step_order=2,
                    step_name="Summarizer",
                    output_key="summary",
                    is_terminal=True,
                ),
            ],
        )

        workflow = create_workflow(
            db_session=db_session,
            workflow_create=workflow_data,
            user_id=test_user.id,
        )

        assert workflow.orchestration_mode == "llm_decision"
        assert workflow.orchestrator_prompt is not None
        assert "Math Solver" in workflow.orchestrator_prompt
        assert len(workflow.steps) == 3

        TestWorkflowCRUD._llm_workflow_id = workflow.id

    def test_delete_workflow(self, db_session: Session) -> None:
        """Soft-delete the LLM-decision workflow."""
        success = delete_workflow(
            db_session=db_session,
            workflow_id=TestWorkflowCRUD._llm_workflow_id,
        )
        assert success is True

        # Verify soft-deleted (still exists but marked deleted)
        workflow = get_workflow_by_id(
            db_session=db_session,
            workflow_id=TestWorkflowCRUD._llm_workflow_id,
        )
        assert workflow is None or workflow.deleted is True


# ─── Test: Workflow Model Validation ──────────────────────────────────────


class TestWorkflowModels:
    """Test Pydantic model validation for workflow schemas."""

    def test_workflow_create_defaults(self) -> None:
        """WorkflowCreate has sensible defaults."""
        wf = WorkflowCreate(name="Test")
        assert wf.orchestration_mode == "llm_decision"
        assert wf.max_steps == 10
        assert wf.timeout_seconds == 1800
        assert wf.is_public is True
        assert wf.steps == []

    def test_workflow_step_create_defaults(self) -> None:
        """WorkflowStepCreate has sensible defaults."""
        step = WorkflowStepCreate(
            persona_id=1, step_order=0, step_name="Test Step"
        )
        assert step.output_key == "output"
        assert step.is_terminal is False
        assert step.input_mapping is None
        assert step.condition is None

    def test_workflow_create_with_steps(self) -> None:
        """Full workflow creation payload validates correctly."""
        wf = WorkflowCreate(
            name="Pipeline",
            description="A test pipeline",
            orchestration_mode="sequential",
            steps=[
                WorkflowStepCreate(
                    persona_id=1,
                    step_order=0,
                    step_name="Step A",
                    output_key="result_a",
                ),
                WorkflowStepCreate(
                    persona_id=2,
                    step_order=1,
                    step_name="Step B",
                    output_key="result_b",
                    is_terminal=True,
                ),
            ],
        )
        assert len(wf.steps) == 2
        assert wf.steps[0].step_name == "Step A"
        assert wf.steps[1].is_terminal is True


# ─── Test: Agent Tool Adapter ─────────────────────────────────────────────


class TestAgentTool:
    """Test the AgentTool adapter that wraps Persona as a callable tool."""

    def test_agent_tool_definition(
        self,
        db_session: Session,
        math_solver_persona: Persona,
    ) -> None:
        """AgentTool produces a valid OpenAI function-call tool definition."""
        from unittest.mock import MagicMock

        from onyx.tools.tool_implementations.agent_tool import AgentTool

        mock_emitter = MagicMock()
        tool = AgentTool(
            persona=math_solver_persona,
            emitter=mock_emitter,
            db_session=db_session,
            step_name="Solve",
            step_order=0,
        )

        defn = tool.tool_definition()

        # Verify structure
        assert defn["type"] == "function"
        assert "function" in defn
        func = defn["function"]
        assert "name" in func
        assert func["name"].startswith("delegate_to_")
        assert "description" in func
        assert "Math Solver" in func["description"] or "math" in func["description"].lower()
        assert "parameters" in func
        assert func["parameters"]["type"] == "object"
        assert "task" in func["parameters"]["properties"]
        assert func["parameters"]["required"] == ["task"]

    def test_agent_tool_name_sanitization(self) -> None:
        """Tool names are properly sanitized for LLM function calls."""
        from onyx.tools.tool_implementations.agent_tool import _sanitize_tool_name

        assert _sanitize_tool_name("Math Solver") == "delegate_to_math_solver"
        assert _sanitize_tool_name("Agent #1 (test)") == "delegate_to_agent_1_test"
        assert _sanitize_tool_name("  spaces  ") == "delegate_to_spaces"
        assert _sanitize_tool_name("UPPERCASE") == "delegate_to_uppercase"

    def test_agent_tool_no_task_returns_error(
        self,
        db_session: Session,
        math_solver_persona: Persona,
    ) -> None:
        """AgentTool.run() with empty task returns error ToolResponse."""
        from unittest.mock import MagicMock

        from onyx.server.query_and_chat.placement import Placement
        from onyx.tools.tool_implementations.agent_tool import AgentTool

        mock_emitter = MagicMock()
        tool = AgentTool(
            persona=math_solver_persona,
            emitter=mock_emitter,
            db_session=db_session,
        )

        placement = Placement(turn_index=0)
        response = tool.run(placement, None, task="")

        assert response.rich_response is None
        error_data = json.loads(response.llm_facing_response)
        assert "error" in error_data


# ─── Test: Workflow Engine Structure ──────────────────────────────────────


class TestWorkflowEngine:
    """Test workflow engine setup (without requiring a live LLM)."""

    def test_sequential_workflow_steps_ordered(
        self,
        db_session: Session,
        test_user: User,
        math_solver_persona: Persona,
        verifier_persona: Persona,
        summarizer_persona: Persona,
    ) -> None:
        """Sequential workflow retrieves steps in correct order."""
        workflow = get_workflow_by_id(
            db_session=db_session,
            workflow_id=TestWorkflowCRUD._workflow_id,
        )
        assert workflow is not None

        steps = sorted(workflow.steps, key=lambda s: s.step_order)
        assert len(steps) == 3
        assert steps[0].step_name == "Solve"
        assert steps[1].step_name == "Verify"
        assert steps[2].step_name == "Summarize"

        # Each step references a valid persona
        for step in steps:
            assert step.persona is not None
            assert step.persona.name.startswith("Test ")

    def test_agent_tools_created_for_workflow(
        self,
        db_session: Session,
        test_user: User,
    ) -> None:
        """AgentTool instances are correctly created from workflow steps."""
        from unittest.mock import MagicMock

        from onyx.tools.tool_implementations.agent_tool import AgentTool

        workflow = get_workflow_by_id(
            db_session=db_session,
            workflow_id=TestWorkflowCRUD._workflow_id,
        )
        assert workflow is not None

        mock_emitter = MagicMock()
        tools = []
        for step in sorted(workflow.steps, key=lambda s: s.step_order):
            tool = AgentTool(
                persona=step.persona,
                emitter=mock_emitter,
                db_session=db_session,
                step_name=step.step_name,
                step_order=step.step_order,
            )
            tools.append(tool)

        assert len(tools) == 3

        # Verify each tool has a unique name
        names = [t.name for t in tools]
        assert len(set(names)) == 3

        # Verify tool definitions are valid
        for tool in tools:
            defn = tool.tool_definition()
            assert defn["type"] == "function"
            assert "task" in defn["function"]["parameters"]["properties"]

    def test_workflow_execution_record_created(
        self,
        db_session: Session,
        test_user: User,
    ) -> None:
        """Workflow execution records are properly created and tracked."""
        from onyx.db.workflow import create_workflow_execution
        from onyx.db.workflow import list_workflow_executions
        from onyx.db.workflow import update_workflow_execution

        execution = create_workflow_execution(
            db_session=db_session,
            workflow_id=TestWorkflowCRUD._workflow_id,
            user_id=test_user.id,
        )

        assert execution.id is not None
        assert execution.status == "running"
        assert execution.workflow_id == TestWorkflowCRUD._workflow_id

        # Update execution status
        updated = update_workflow_execution(
            db_session=db_session,
            execution_id=execution.id,
            status="completed",
            steps_executed=[
                {
                    "step_name": "Solve",
                    "persona_id": 1,
                    "output": "42",
                    "duration_ms": 1500,
                    "tokens_used": 200,
                },
                {
                    "step_name": "Verify",
                    "persona_id": 2,
                    "output": "VERIFIED",
                    "duration_ms": 800,
                    "tokens_used": 150,
                },
                {
                    "step_name": "Summarize",
                    "persona_id": 3,
                    "output": "The answer is 42.",
                    "duration_ms": 600,
                    "tokens_used": 100,
                },
            ],
            total_tokens=450,
            total_duration_ms=2900,
        )

        assert updated is not None
        assert updated.status == "completed"
        assert updated.total_tokens == 450
        assert updated.total_duration_ms == 2900
        assert len(updated.steps_executed) == 3

        # List executions
        executions = list_workflow_executions(
            db_session=db_session,
            workflow_id=TestWorkflowCRUD._workflow_id,
        )
        assert len(executions) >= 1
        assert any(e.id == execution.id for e in executions)


# ─── Cleanup ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module", autouse=True)
def cleanup(
    db_session: Session,
    test_user: User,
    math_solver_persona: Persona,
    verifier_persona: Persona,
    summarizer_persona: Persona,
) -> Generator[None, None, None]:
    """Clean up test data after all tests complete."""
    yield

    # Clean up workflows
    for wf_id in [
        getattr(TestWorkflowCRUD, "_workflow_id", None),
        getattr(TestWorkflowCRUD, "_llm_workflow_id", None),
    ]:
        if wf_id:
            try:
                delete_workflow(db_session, wf_id)
            except Exception:
                pass

    # Clean up personas
    for persona in [math_solver_persona, verifier_persona, summarizer_persona]:
        try:
            persona.deleted = True
            db_session.commit()
        except Exception:
            pass

    # Clean up user
    try:
        db_session.delete(test_user)
        db_session.commit()
    except Exception:
        pass
