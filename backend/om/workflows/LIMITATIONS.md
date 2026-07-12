# Workflow Engine Limitations

## Status: Known Limitations — To Be Addressed

## 1. No User Clarification / Interaction Mid-Workflow

### Problem

The workflow engine is a **one-directional pipeline**. Data flows forward only:

```
User message -> Agent 1 (runs once) -> Agent 2 (runs once) -> ... -> Final output
                    |                       |
              (no way back)           (no way back)
```

Each agent receives a single input, runs to completion, and produces output. There is:

- **No packet type** for "agent needs user input" or "clarification needed"
- **No pause/resume mechanism** — agents cannot wait for a user response
- **No bidirectional streaming** — packets only flow agent -> frontend, never reverse

### Impact

When a user provides incomplete information (e.g., "plan a trip to Georgia Gudauri" without dates, budget, or traveler count), the Details Collector agent **cannot ask for clarification**. Instead, it assumes defaults:

```
Dates: Flexible
Duration: 7 days
Travelers: 2
Budget: Mid-range
```

This produces a generic plan instead of a personalized one.

### Current Workaround

Agent prompts are explicitly instructed to **never ask questions** and to assume reasonable defaults:

```
RULES:
- NO follow-up questions. NO open questions. NO confirmations.
- Assume reasonable defaults for missing info.
```

This workaround exists because the engine has no infrastructure to receive user answers.

### Desired Behavior

The first agent (Details Collector) should be able to:

1. Detect missing critical information (dates, budget, travelers, departure city)
2. Emit a "clarification needed" signal with specific questions
3. **Pause** the workflow and present questions to the user
4. **Resume** the workflow once the user responds
5. Continue to the next agent with complete information

### Reference Implementation

The existing **Deep Research** feature (`backend/onyx/agents/agent_search/`) implements a similar pattern:

- Presents a research plan to the user
- Waits for user confirmation/modification
- Continues execution based on user feedback

This pattern should be analyzed and adapted for workflows.

## 2. No Parallel Agent Execution

See [PARALLEL_EXECUTION.md](./PARALLEL_EXECUTION.md) for the design document.

## 3. LLM-Decision Mode Limitations

- Orchestrator context grows linearly (mitigated by context summarization)
- No parallel tool calls when orchestrator returns multiple agents
- Orchestrator sometimes calls blocked agents (mitigated by filtering tool_defs)
