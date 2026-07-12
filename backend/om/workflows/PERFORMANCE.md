# Workflow Engine Performance Analysis & Optimization

## Overview

The multi-agent workflow engine supports two orchestration modes:
- **`sequential`** — fixed-order execution, no orchestrator LLM overhead
- **`llm_decision`** — orchestrator LLM dynamically routes to agents each step

This document covers the performance characteristics, identified bottlenecks,
and optimizations applied (or planned) to reduce end-to-end latency.

---

## Benchmark: Travel Planner (6-agent, `llm_decision` mode)

**Test**: 6 agents (Details Collector → Activities Planner → Flight Finder →
Hotel Finder → Itinerary Builder → Trip Summary), `max_calls_per_agent=1`.

| Phase | Duration | % of Total |
|-------|----------|-----------|
| Agent LLM generation (6 agents) | ~183s | 46% |
| Orchestrator LLM calls (7 calls) | ~215s | 54% |
| **Total** | **~398s (6.6 min)** | 100% |

### Per-step timing breakdown

```
[0.0s]   Orchestrator call #1 (init)         6.7s
[6.7s]   Agent: Details Collector            10.2s
[17.0s]  Orchestrator call #2               33.6s  ← context: ~200 words
[50.6s]  Agent: Activities Planner          22.2s
[72.7s]  Orchestrator call #3               22.6s  ← context: ~800 words
[95.3s]  Agent: Flight Finder               25.1s
[120.4s] Orchestrator call #4               33.5s  ← context: ~1500 words
[153.9s] Agent: Hotel Finder                27.6s
[181.5s] Orchestrator call #5               30.7s  ← context: ~2200 words
[212.2s] Agent: Itinerary Builder           31.0s
[243.2s] Orchestrator call #6               32.2s  ← context: ~3000 words
[275.4s] Agent: Trip Summary                66.7s
[342.0s] Orchestrator call #7 (final)       56.4s  ← context: ~4000 words
[398.4s] WORKFLOW COMPLETE
```

**Key insight**: Orchestrator calls get slower as context grows linearly.
Call #1 (just user message) = 6.7s. Call #7 (all 6 agent outputs) = 56.4s.

---

## Root Causes

### 1. Orchestrator LLM Overhead (54% of runtime)

In `llm_decision` mode, the orchestrator LLM runs **between every agent call**
to decide the next step. For a fixed-order workflow like Travel Planner, this
is pure overhead — the orchestrator just follows the same sequence every time.

Each orchestrator call:
1. Receives ALL prior agent outputs in `msg_history` (grows linearly)
2. Rebuilds message history via `construct_message_history()`
3. Calls `run_llm_step()` with full tool definitions
4. Drains emitter bus, parses result

**Enterprise comparison**: CrewAI uses a "deterministic backbone" (Flow) and
only invokes LLM for actual decision points. AWS Bedrock has "smart routing"
that bypasses the orchestrator for simple/obvious routes.

### 2. Agent Infrastructure Overhead (~40s)

Each `AgentTool.run()` call:
- Creates a new LLM instance via `get_llm_for_persona()` (~50-100ms)
- Calls `construct_tools()` even for no-tool personas (~200-500ms)
  - `get_current_search_settings()` — DB query
  - `get_default_document_index()` — DB query + index init
- Builds message history, translates to LLM format
- Polls emitter bus at 300ms intervals (tail latency)

### 3. No Context Management

The orchestrator receives ALL previous outputs verbatim. By step 6, it's
processing ~4000+ words just to make a routing decision. Enterprise frameworks
use context summarization, observation masking, or context isolation to keep
orchestrator inputs small.

### 4. No Parallelization

Agents always run sequentially. Independent agents like Flight Finder and
Hotel Finder (both depend only on travel details) could run in parallel.
Enterprise pattern: scatter-gather / MapReduce for independent tasks.

---

## Optimizations Applied

### Tier 1: Quick Wins (infrastructure, no architecture changes)

| # | Optimization | File | Savings |
|---|-------------|------|---------|
| 1.1 | Skip `construct_tools` for no-tool personas | `agent_tool.py` | ~1-2s |
| 1.2 | Cache `tool_defs` in orchestrator loop | `workflow_engine.py` | ~50ms |
| 1.3 | Reduce polling interval 300ms → 50ms | `workflow_engine.py` | ~0.5-1s |
| 1.4 | Eager-load `persona.tools` in DB query | `workflow.py` | ~50-200ms |
| 1.5 | Cache LLM instances per workflow run | `agent_tool.py` | ~200-600ms |

### Tier 2: Major Optimizations

| # | Optimization | File | Savings |
|---|-------------|------|---------|
| 2.1 | Context summarization (truncate agent outputs for orchestrator) | `workflow_engine.py` | ~60-120s |
| 2.2 | Lighter orchestrator model (use `orchestrator_llm_model` config) | UI/config | ~100-150s |
| 2.3 | Pre-compute shared DB resources (search settings, doc index) | `agent_tool.py`, `tool_constructor.py` | ~1.5-3s |

### Bug Fix

- **`get_llm_for_persona` called with wrong argument**: `agent_tool.py:147`
  passed `db_session` where `user` was expected. Agents always fell back to
  default LLM instead of using persona-specific configuration.

---

## Actual Results (Travel Planner, 6 agents)

| Configuration | Runtime | Speedup |
|---------------|---------|---------|
| Baseline (default model, no optimizations) | 398s (6.6 min) | 1.0x |
| **All Tier 1+2** (gpt-4.1 orchestrator + context summarization + caching) | **182s (3.0 min)** | **2.2x** |

Orchestrator overhead dropped from **215s → 16s** (13x faster routing).
Each orchestrator call: **~30s → ~2s**.

Note: gpt-5-mini was too weak for this orchestrator prompt (kept re-calling
the same agent). gpt-4.1 is the sweet spot: fast enough (~2s/call) and smart
enough to follow the 6-agent routing sequence correctly.

---

## Enterprise Patterns Reference

Patterns from production multi-agent frameworks that informed this work:

| Framework | Key Pattern | How We Apply It |
|-----------|------------|----------------|
| **CrewAI** | Deterministic backbone (Flow) + selective agent steps | `sequential` mode for fixed-order; `llm_decision` only when routing varies |
| **AWS Bedrock** | Smart routing — classifier bypasses orchestrator for simple requests | Context summarization reduces orchestrator work |
| **OpenAI Agents SDK** | Explicit handoffs with context transfer, no hidden state | `input_mapping` per step controls what context each agent receives |
| **LangGraph** | Subagent context isolation (67% fewer tokens) | Summarize agent outputs before passing to orchestrator |
| **Microsoft AutoGen** | Async event-driven with flexible message passing | Background thread agent execution with emitter bus |

### Future Roadmap (Tier 3)

- **Parallel agent execution**: `parallel_group` field on steps, concurrent execution
- **Hybrid orchestration**: deterministic backbone + LLM only at conditional branches
- **Classifier-based routing**: embeddings-based agent selection, no LLM call
- **Context isolation**: agents receive only `input_mapping` data, not full history

---

## Configuration Guide

### Orchestrator Model Selection

The workflow's `orchestrator_llm_provider` and `orchestrator_llm_model` fields
control which model handles routing decisions. For simple routing, use a
faster/cheaper model:

- **Routing decisions** (which agent next?): gpt-5-mini, gpt-4.1, llama3.2
- **Content generation** (agent work): gpt-5.2, claude-sonnet, etc.

Configure via the Workflow Editor UI or the API:
```json
{
  "orchestrator_llm_provider": "v",
  "orchestrator_llm_model": "gpt-5-mini"
}
```

### When to Use Each Mode

| Mode | Best For | Overhead |
|------|----------|----------|
| `sequential` | Fixed-order pipelines (research→write→review) | Zero orchestrator calls |
| `llm_decision` | Dynamic routing (support triage, conditional flows) | 1 orchestrator call per step |

### max_calls_per_agent

Per-workflow limit preventing the orchestrator from calling the same agent
repeatedly. Set to `1` for workflows where each agent should run exactly once.
Configurable via UI.
