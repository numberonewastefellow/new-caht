# Community 82

> 137 nodes · cohesion 0.03

## Key Concepts

- **Session** (20 connections) — `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`
- **workflow.py** (20 connections) — `backend/om/db/workflow.py`
- **Session** (17 connections) — `backend/om/db/workflow.py`
- **api.py** (15 connections) — `backend/om/server/features/workflow/api.py`
- **User** (14 connections) — `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`
- **get_workflow_by_id()** (13 connections) — `backend/om/db/workflow.py`
- **test_workflow_multi_agent.py** (13 connections) — `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`
- **User** (12 connections) — `backend/om/server/features/workflow/api.py`
- **Agent** (12 connections) — `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`
- **Session** (11 connections) — `backend/om/server/features/workflow/api.py`
- **create_or_update_workflow_agent()** (11 connections) — `backend/om/db/workflow.py`
- **TestWorkflowCRUD** (11 connections) — `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`
- **run_workflow_endpoint()** (10 connections) — `backend/om/server/features/workflow/api.py`
- **create_workflow_endpoint()** (9 connections) — `backend/om/server/features/workflow/api.py`
- **update_workflow_endpoint()** (9 connections) — `backend/om/server/features/workflow/api.py`
- **WorkflowExecution** (8 connections) — `backend/om/db/workflow.py`
- **get_workflow_endpoint()** (8 connections) — `backend/om/server/features/workflow/api.py`
- **get_workflow_trace()** (8 connections) — `backend/om/server/features/workflow/api.py`
- **get_workflow_trace_by_message()** (8 connections) — `backend/om/server/features/workflow/api.py`
- **list_executions_endpoint()** (8 connections) — `backend/om/server/features/workflow/api.py`
- **_workflow_to_response()** (8 connections) — `backend/om/server/features/workflow/api.py`
- **TestAgentTool** (8 connections) — `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`
- **TestWorkflowEngine** (8 connections) — `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`
- **TestWorkflowModels** (8 connections) — `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`
- **AgentWorkflow** (7 connections) — `backend/om/db/workflow.py`
- *... and 112 more nodes in this community*

## Relationships

- [[Agent Chat Packets & Citations]] (30 shared connections)
- [[User Roles & Agent Config]] (11 shared connections)
- [[Community 103]] (8 shared connections)
- [[Community 119]] (7 shared connections)
- [[Chat Datetime & OAuth Tokens]] (3 shared connections)
- [[Community 106]] (3 shared connections)
- [[Community 438]] (3 shared connections)
- [[Community 195]] (3 shared connections)
- [[Analytics & Usage Models (WS-H)]] (2 shared connections)
- [[Community 135]] (1 shared connections)
- [[Community 332]] (1 shared connections)
- [[Community 161]] (1 shared connections)

## Source Files

- `backend/om/db/workflow.py`
- `backend/om/server/features/workflow/api.py`
- `backend/om/tools/tool_implementations/agent_tool.py`
- `backend/om/workflows/models.py`
- `backend/tests/external_dependency_unit/workflow/test_workflow_multi_agent.py`

## Audit Trail

- EXTRACTED: 479 (83%)
- INFERRED: 101 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*