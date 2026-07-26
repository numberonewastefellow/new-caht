# Backend Agent/API Test Fixtures

> 292 nodes · cohesion 0.01

## Key Concepts

- **DATestUser** (233 connections) — `backend/tests/integration/common_utils/test_models.py`
- **get_session_with_current_tenant()** (187 connections) — `backend/om/db/engine/sql_engine.py`
- **DocumentIndexClient** (47 connections) — `backend/tests/integration/common_utils/document_index.py`
- **DATestLLMProvider** (39 connections) — `backend/tests/integration/common_utils/test_models.py`
- **test_models.py** (28 connections) — `backend/tests/integration/common_utils/test_models.py`
- **DATestAPIKey** (24 connections) — `backend/tests/integration/common_utils/test_models.py`
- **MockConnectorCheckpoint** (22 connections) — `backend/om/connectors/mock_connector/connector.py`
- **DiscordBotManager** (20 connections) — `backend/tests/integration/common_utils/managers/discord_bot.py`
- **DATestImageGenerationConfig** (19 connections) — `backend/tests/integration/common_utils/test_models.py`
- **SimpleTestDocument** (18 connections) — `backend/tests/integration/common_utils/test_models.py`
- **DATestUser** (16 connections) — `backend/tests/integration/common_utils/managers/discord_bot.py`
- **DATestUser** (16 connections) — `backend/tests/integration/conftest.py`
- **DATestUser** (15 connections) — `backend/tests/integration/common_utils/managers/agent.py`
- **DATestAgent** (14 connections) — `backend/tests/integration/common_utils/test_models.py`
- **conftest.py** (13 connections) — `backend/tests/integration/conftest.py`
- **DATestAgentLabel** (13 connections) — `backend/tests/integration/common_utils/test_models.py`
- **DATestTeam** (12 connections) — `backend/tests/integration/common_utils/test_models.py`
- **DATestImageGenerationConfig** (11 connections) — `backend/tests/integration/conftest.py`
- **DATestLLMProvider** (11 connections) — `backend/tests/integration/conftest.py`
- **DocumentBuilderType** (11 connections) — `backend/tests/integration/conftest.py`
- **DocumentIndexClient** (11 connections) — `backend/tests/integration/conftest.py`
- **AgentManager** (11 connections) — `backend/tests/integration/common_utils/managers/agent.py`
- **DocumentIndexClient** (10 connections) — `backend/tests/integration/tests/team/test_team_deletion.py`
- **DATestDiscordChannelConfig** (10 connections) — `backend/tests/integration/common_utils/test_models.py`
- **DATestDiscordGuildConfig** (10 connections) — `backend/tests/integration/common_utils/test_models.py`
- *... and 267 more nodes in this community*

## Relationships

- [[Community 67]] (101 shared connections)
- [[User Roles & Agent Config]] (36 shared connections)
- [[Community 186]] (25 shared connections)
- [[Community 335]] (25 shared connections)
- [[Analytics & Usage Models (WS-H)]] (24 shared connections)
- [[Community 489]] (12 shared connections)
- [[Community 744]] (12 shared connections)
- [[Community 664]] (10 shared connections)
- [[Community 362]] (9 shared connections)
- [[Community 85]] (8 shared connections)
- [[Community 644]] (8 shared connections)
- [[Document Indexing Adapter]] (8 shared connections)

## Source Files

- `backend/om/connectors/mock_connector/connector.py`
- `backend/om/db/engine/sql_engine.py`
- `backend/scripts/hard_delete_chats.py`
- `backend/tests/integration/common_utils/chat.py`
- `backend/tests/integration/common_utils/document_index.py`
- `backend/tests/integration/common_utils/managers/agent.py`
- `backend/tests/integration/common_utils/managers/api_key.py`
- `backend/tests/integration/common_utils/managers/discord_bot.py`
- `backend/tests/integration/common_utils/managers/document.py`
- `backend/tests/integration/common_utils/managers/file.py`
- `backend/tests/integration/common_utils/managers/llm_provider.py`
- `backend/tests/integration/common_utils/managers/pat.py`
- `backend/tests/integration/common_utils/managers/team.py`
- `backend/tests/integration/common_utils/managers/tool.py`
- `backend/tests/integration/common_utils/managers/user.py`
- `backend/tests/integration/common_utils/test_document_utils.py`
- `backend/tests/integration/common_utils/test_models.py`
- `backend/tests/integration/conftest.py`
- `backend/tests/integration/tests/agents/test_agent_label_updates.py`
- `backend/tests/integration/tests/connector/test_connector_deletion.py`

## Audit Trail

- EXTRACTED: 789 (45%)
- INFERRED: 959 (55%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*