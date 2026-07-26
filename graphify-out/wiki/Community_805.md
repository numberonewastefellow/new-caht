# Community 805

> 17 nodes · cohesion 0.14

## Key Concepts

- **_mock_llm_server.py** (17 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **_generate_fake_data()** (10 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **._stream_anthropic_tool_use()** (10 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **_BedrockConverseRequest** (5 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **_generate_from_schema()** (4 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **_sanitize_for_postgres()** (4 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **_generate_anthropic_tool_use_id()** (3 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **_generate_bedrock_tool_use_id()** (3 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **AnthropicToolUnionParam** (2 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **Mock LLM server for integration testing.  This module provides a lightweight H** (1 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **Stream a tool use block for Anthropic using Pydantic models.** (1 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **Wrapper for Bedrock ConverseStream request validation.      Uses arbitrary_typ** (1 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **Generate Anthropic-style tool use ID (toolu_01XXXX...).** (1 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **Generate Bedrock-style tool use ID (tooluse_XXXX...).** (1 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **Sanitize generated data to remove characters that PostgreSQL can't handle.** (1 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **Generate data conforming to a JSON schema using stdlib random.      Thread-saf** (1 connections) — `phoenix/tests/integration/_mock_llm_server.py`
- **Generate fake data from a JSON schema.      Uses _generate_from_schema() which** (1 connections) — `phoenix/tests/integration/_mock_llm_server.py`

## Relationships

- [[Community 338]] (14 shared connections)
- [[Community 688]] (6 shared connections)
- [[Community 434]] (2 shared connections)
- [[Community 355]] (1 shared connections)
- [[Community 106]] (1 shared connections)
- [[Community 970]] (1 shared connections)
- [[Community 1052]] (1 shared connections)
- [[Analytics & Usage Models (WS-H)]] (1 shared connections)
- [[Community 138]] (1 shared connections)

## Source Files

- `phoenix/tests/integration/_mock_llm_server.py`

## Audit Trail

- EXTRACTED: 63 (95%)
- INFERRED: 3 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*