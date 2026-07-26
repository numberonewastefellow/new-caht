# Phoenix Playground LLM Clients

> 204 nodes · cohesion 0.09

## Key Concepts

- **GenerativeProviderKey** (231 connections) — `phoenix/src/phoenix/server/api/types/GenerativeProvider.py`
- **RateLimiter** (157 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **ToolCallChunk** (126 connections) — `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- **GenerativeModelInput** (116 connections) — `phoenix/src/phoenix/server/api/input_types/GenerativeModelInput.py`
- **defaultdict** (113 connections) — `phoenix/src/phoenix/server/api/helpers/playground_clients.py`
- **GenerativeModelBuiltinProviderInput** (112 connections) — `phoenix/src/phoenix/server/api/input_types/GenerativeModelInput.py`
- **GenerativeModelCustomProviderInput** (112 connections) — `phoenix/src/phoenix/server/api/input_types/GenerativeModelInput.py`
- **ChatCompletionMessageRole** (111 connections) — `phoenix/src/phoenix/server/api/types/ChatCompletionMessageRole.py`
- **TextChunk** (108 connections) — `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- **GenerativeCredentialInput** (96 connections) — `phoenix/src/phoenix/server/api/input_types/GenerativeCredentialInput.py`
- **RateLimitError** (87 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **OpenAIStreamingClient** (85 connections) — `phoenix/src/phoenix/server/api/helpers/playground_clients.py`
- **FunctionCallChunk** (73 connections) — `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- **JSONInvocationParameter** (69 connections) — `phoenix/src/phoenix/server/api/input_types/InvocationParameters.py`
- **IntInvocationParameter** (68 connections) — `phoenix/src/phoenix/server/api/input_types/InvocationParameters.py`
- **BoundedFloatInvocationParameter** (67 connections) — `phoenix/src/phoenix/server/api/input_types/InvocationParameters.py`
- **StringListInvocationParameter** (66 connections) — `phoenix/src/phoenix/server/api/input_types/InvocationParameters.py`
- **InvocationParameterInput** (65 connections) — `phoenix/src/phoenix/server/api/input_types/InvocationParameters.py`
- **PlaygroundToolCall** (64 connections) — `phoenix/src/phoenix/server/api/helpers/message_helpers.py`
- **FloatInvocationParameter** (64 connections) — `phoenix/src/phoenix/server/api/input_types/InvocationParameters.py`
- **StringInvocationParameter** (64 connections) — `phoenix/src/phoenix/server/api/input_types/InvocationParameters.py`
- **CanonicalParameterName** (63 connections) — `phoenix/src/phoenix/server/api/input_types/InvocationParameters.py`
- **GenericType** (62 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **ParameterSpec** (62 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- **AsyncCallable** (61 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- *... and 179 more nodes in this community*

## Relationships

- [[Phoenix GraphQL Schema]] (265 shared connections)
- [[Phoenix Evaluators]] (200 shared connections)
- [[Community 108]] (124 shared connections)
- [[Phoenix Experiment Comparison Queries]] (74 shared connections)
- [[Phoenix Experiment Queries]] (44 shared connections)
- [[Community 79]] (30 shared connections)
- [[Community 247]] (27 shared connections)
- [[Community 126]] (21 shared connections)
- [[Community 345]] (20 shared connections)
- [[Community 416]] (15 shared connections)
- [[Community 280]] (13 shared connections)
- [[Community 248]] (12 shared connections)

## Source Files

- `phoenix/packages/phoenix-client/src/phoenix/client/utils/rate_limiters.py`
- `phoenix/src/phoenix/server/api/evaluators.py`
- `phoenix/src/phoenix/server/api/helpers/message_helpers.py`
- `phoenix/src/phoenix/server/api/helpers/playground_clients.py`
- `phoenix/src/phoenix/server/api/input_types/GenerativeCredentialInput.py`
- `phoenix/src/phoenix/server/api/input_types/GenerativeModelInput.py`
- `phoenix/src/phoenix/server/api/input_types/InvocationParameters.py`
- `phoenix/src/phoenix/server/api/types/ChatCompletionMessageRole.py`
- `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- `phoenix/src/phoenix/server/api/types/GenerativeProvider.py`
- `phoenix/tests/unit/server/api/helpers/test_playground_clients.py`

## Audit Trail

- EXTRACTED: 911 (19%)
- INFERRED: 3872 (81%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*