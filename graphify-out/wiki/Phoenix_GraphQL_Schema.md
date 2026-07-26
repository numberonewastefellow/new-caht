# Phoenix GraphQL Schema

> 176 nodes · cohesion 0.05

## Key Concepts

- **PlaygroundMessage** (146 connections) — `phoenix/src/phoenix/server/api/helpers/message_helpers.py`
- **DatasetVersion** (144 connections) — `phoenix/src/phoenix/server/api/types/DatasetVersion.py`
- **PlaygroundStreamingClient** (112 connections) — `phoenix/src/phoenix/server/api/helpers/playground_clients.py`
- **Tracer** (82 connections) — `phoenix/src/phoenix/tracers.py`
- **ExperimentRunAnnotation** (79 connections) — `phoenix/src/phoenix/server/api/types/ExperimentRunAnnotation.py`
- **SpanInsertEvent** (64 connections) — `phoenix/src/phoenix/server/dml_event.py`
- **ChatCompletionInput** (48 connections) — `phoenix/src/phoenix/server/api/input_types/ChatCompletionInput.py`
- **ChatCompletionOverDatasetInput** (48 connections) — `phoenix/src/phoenix/server/api/input_types/ChatCompletionInput.py`
- **EvaluationResult** (46 connections) — `phoenix/packages/phoenix-client/src/phoenix/client/resources/experiments/evaluators.py`
- **ChatCompletionSubscriptionPayload** (43 connections) — `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- **deque** (42 connections) — `phoenix/src/phoenix/server/api/subscriptions.py`
- **ChatCompletionSubscriptionError** (40 connections) — `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- **ChatCompletionSubscriptionExperiment** (37 connections) — `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- **ChatCompletionSubscriptionResult** (36 connections) — `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- **EvaluationChunk** (36 connections) — `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- **Subscription** (29 connections) — `phoenix/src/phoenix/server/api/subscriptions.py`
- **ChatCompletionMutationMixin** (29 connections) — `phoenix/src/phoenix/server/api/mutations/chat_mutations.py`
- **EvaluatorPreviewsInput** (27 connections) — `phoenix/src/phoenix/server/api/input_types/EvaluatorPreviewInput.py`
- **ChatCompletionRepetition** (27 connections) — `phoenix/src/phoenix/server/api/mutations/chat_mutations.py`
- **Context** (27 connections) — `phoenix/src/phoenix/server/api/mutations/chat_mutations.py`
- **Info** (27 connections) — `phoenix/src/phoenix/server/api/mutations/chat_mutations.py`
- **EvaluationResultDict** (26 connections) — `phoenix/src/phoenix/server/api/mutations/chat_mutations.py`
- **ChatCompletionFunctionCall** (26 connections) — `phoenix/src/phoenix/server/api/mutations/chat_mutations.py`
- **.chat_completion_over_dataset()** (26 connections) — `phoenix/src/phoenix/server/api/mutations/chat_mutations.py`
- **ChatCompletionMutationPayload** (26 connections) — `phoenix/src/phoenix/server/api/mutations/chat_mutations.py`
- *... and 151 more nodes in this community*

## Relationships

- [[Phoenix Playground LLM Clients]] (265 shared connections)
- [[Phoenix Experiment Comparison Queries]] (195 shared connections)
- [[Phoenix Experiment Queries]] (145 shared connections)
- [[Phoenix Evaluators]] (68 shared connections)
- [[Community 416]] (40 shared connections)
- [[Phoenix Dataset Events]] (32 shared connections)
- [[Community 66]] (29 shared connections)
- [[Community 108]] (24 shared connections)
- [[Community 101]] (23 shared connections)
- [[Phoenix Annotation Config & Evaluators]] (23 shared connections)
- [[Community 126]] (21 shared connections)
- [[Community 138]] (20 shared connections)

## Source Files

- `phoenix/packages/phoenix-client/src/phoenix/client/resources/experiments/evaluators.py`
- `phoenix/src/phoenix/server/api/evaluators.py`
- `phoenix/src/phoenix/server/api/exceptions.py`
- `phoenix/src/phoenix/server/api/helpers/evaluators.py`
- `phoenix/src/phoenix/server/api/helpers/message_helpers.py`
- `phoenix/src/phoenix/server/api/helpers/playground_clients.py`
- `phoenix/src/phoenix/server/api/input_types/ChatCompletionInput.py`
- `phoenix/src/phoenix/server/api/input_types/ChatCompletionMessageInput.py`
- `phoenix/src/phoenix/server/api/input_types/EvaluatorPreviewInput.py`
- `phoenix/src/phoenix/server/api/input_types/PromptTemplateOptions.py`
- `phoenix/src/phoenix/server/api/mutations/chat_mutations.py`
- `phoenix/src/phoenix/server/api/schema.py`
- `phoenix/src/phoenix/server/api/subscriptions.py`
- `phoenix/src/phoenix/server/api/types/ChatCompletionSubscriptionPayload.py`
- `phoenix/src/phoenix/server/api/types/DatasetVersion.py`
- `phoenix/src/phoenix/server/api/types/ExperimentRunAnnotation.py`
- `phoenix/src/phoenix/server/dml_event.py`
- `phoenix/src/phoenix/server/experiments/utils.py`
- `phoenix/src/phoenix/tracers.py`
- `phoenix/tests/unit/server/api/test_cancellation.py`

## Audit Trail

- EXTRACTED: 609 (23%)
- INFERRED: 2057 (77%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*