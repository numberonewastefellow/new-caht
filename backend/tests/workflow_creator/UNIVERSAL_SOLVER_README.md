# Universal Problem Solver — Implementation Guide

## Overview

Ad-hoc autonomous problem solving without picking a specific workflow.
Two approaches that complement each other:

| Approach | Best For | How It Works |
|----------|----------|-------------|
| **Universal Agent** (persona) | Quick tasks, simple-to-medium problems | Single agent with ALL tools, decides its own approach (ChatGPT/Gemini style) |
| **Universal Problem Solver** (workflow) | Complex multi-step problems | 7 specialist agents coordinated by an orchestrator LLM |

Users select either one from the chat UI agent picker.

---

## Architecture

### How ChatGPT / Gemini Do It

They use a **single super-agent** with multiple tools. The model itself plans, executes tools, sees results, and iterates. No multi-agent orchestration.

### Our Dual Approach

**1. Super Agent Persona** — Same pattern. One persona with PythonTool + SearchTool + WebSearchTool + OpenURLTool + FileReaderTool. A ReAct-style system prompt teaches it to Think → Plan → Act → Reflect → Answer.

**2. Multi-Agent Workflow** — For complex tasks where a single agent isn't deep enough. An orchestrator LLM classifies the problem and routes to specialist agents. Each agent has its own tools and 5 internal tool-call cycles.

### Why Both?

| Scenario | Use Super Agent | Use Multi-Agent Workflow |
|----------|----------------|------------------------|
| "Fix this Python bug" | Yes (fast, 1-2 min) | Overkill |
| "What is quicksort?" | Yes (instant) | Overkill |
| "Analyze this dataset, build ML model, create report" | Too shallow | Yes (deep pipeline) |
| "Research topic + write code + visualize" | Maybe | Yes (specialists shine) |
| Vague input needing clarification | No HITL support | Yes (Analyzer asks questions) |

---

## The 7 Sub-Agents (Multi-Agent Workflow)

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR LLM                      │
│         (classifies problem, routes to agents)           │
└────────┬──────┬──────┬──────┬──────┬──────┬─────────────┘
         │      │      │      │      │      │
         ▼      ▼      ▼      ▼      ▼      ▼
┌──────┐┌────┐┌────┐┌────┐┌────┐┌──────┐┌─────────┐
│Analyz││Res-││Code││Data││ ML ││Gener-││  Report  │
│  er  ││ear-││Eng-││Ana-││Eng-││  al  ││Synthesi-│
│  &   ││cher││neer││lyst││neer││Solver││   zer   │
│Plann-││    ││    ││    ││    ││      ││         │
│  er  ││    ││    ││    ││    ││      ││         │
└──────┘└────┘└────┘└────┘└────┘└──────┘└─────────┘
 HITL    Search Python Python Python  ALL     none
 none    Web                         tools  (promote)
         URL
```

### Agent Details

| # | Agent | Tools | When Used |
|---|-------|-------|-----------|
| 0 | **Problem Analyzer & Planner** | none | Always first. Classifies problem, creates plan. Asks user for clarification if input is vague (`can_request_input: true`). |
| 1 | **Knowledge Researcher** | SearchTool, WebSearchTool, OpenURLTool | Research questions, fact-finding, documentation lookup, comparisons. |
| 2 | **Code Engineer** | PythonTool | Bug fixing, algorithm design, code writing, testing, debugging. |
| 3 | **Data Analyst & Visualizer** | PythonTool | Statistical analysis, data profiling, chart generation (matplotlib/seaborn). |
| 4 | **ML Engineer** | PythonTool | Model training (scikit-learn), evaluation, feature engineering, ROC/confusion matrix. |
| 5 | **General Problem Solver** | ALL tools | Swiss-army-knife for tasks that don't fit specialists — file processing, mixed tasks. |
| 6 | **Report Synthesizer** | none | Always last. Compiles all agent outputs into polished final answer (`promote_output: true`). |

### Why These 7

- **Analyzer** — Without it, vague requests like "analyze my data" go straight to a specialist without context. HITL is critical.
- **Researcher vs Code/Data** — Different tool sets (search vs code execution). Can't merge.
- **Code Engineer vs Data Analyst vs ML Engineer** — Different mindsets. A debugging prompt is fundamentally different from a statistical analysis prompt or an ML pipeline prompt. Merged = diluted.
- **General Solver** — Catches everything else: file processing, mixed tasks, simple Q&A.
- **Synthesizer** — Without it, the user gets raw agent outputs. With it, they get a polished report.

---

## Orchestrator Routing

The orchestrator does NOT call all 7 agents every time. It picks the relevant 2-4 agents based on the Analyzer's classification:

| Problem Type | Agent Sequence | Example |
|-------------|---------------|---------|
| Coding bug | 0 → 2 (2-3x) → 6 | "Fix my sorting function" |
| Data analysis | 0 → 3 (2-3x) → 6 | "Analyze sales trends by region" |
| ML prototyping | 0 → 4 (2-3x) → 6 | "Build fraud detection classifier" |
| Data + ML | 0 → 3 → 4 → 6 | "Profile data then build predictive model" |
| Research | 0 → 1 → 6 | "Compare microservices vs monolith" |
| Research + Code | 0 → 1 → 2 → 6 | "Research sorting algorithms and implement the fastest" |
| Simple Q&A | 0 → 5 → 6 | "What is Big-O notation?" |
| File processing | 0 → 5 → 6 | "Read this CSV and summarize it" |
| Complex mixed | 0 → 1 → 2 → 3 → 4 → 6 | "Research, code, analyze, and model" |

---

## Implementation Checklist

### Files to Create/Modify

| # | File | Action |
|---|------|--------|
| 1 | `backend/onyx/chat/llm_loop.py` line 202 | **Modify**: `MAX_LLM_CYCLES = 6` → `20` |
| 2 | `backend/tests/workflow_creator/workflows/20_universal_problem_solver.json` | **Create**: 7-agent workflow definition |
| 3 | `backend/tests/agents_creator/assistants/29_universal_agent.json` | **Create**: Super-agent persona definition |

### Step-by-step

1. **Bump cycle limit** (enables Super Agent persona to iterate sufficiently):
   ```python
   # backend/onyx/chat/llm_loop.py line 202
   MAX_LLM_CYCLES = 20  # was 6
   ```

2. **Create Super Agent persona** (`29_universal_agent.json`):
   - ReAct-style system prompt (Think → Plan → Act → Reflect → Answer)
   - Tools: PythonTool, SearchTool, WebSearchTool, OpenURLTool, FileReaderTool
   - Deploy: `python create_assistants.py --file assistants/29_universal_agent.json`

3. **Create Multi-Agent Workflow** (`20_universal_problem_solver.json`):
   - 7 agents with detailed system prompts
   - Adaptive orchestrator prompt with problem classification
   - Config: `max_steps=20`, `max_calls_per_agent=4`, `timeout=2400s`
   - Deploy: `python create_workflows.py --file workflows/20_universal_problem_solver.json`

### Workflow Configuration

```json
{
  "name": "Universal Problem Solver",
  "orchestration_mode": "llm_decision",
  "orchestrator_llm_model": "gpt-4.1",
  "max_steps": 20,
  "max_calls_per_agent": 4,
  "timeout_seconds": 2400
}
```

---

## Testing

### Super Agent Persona

```
Deploy:  python create_assistants.py --file assistants/29_universal_agent.json
Select:  "Universal Agent" in chat UI
```

Test prompts:
- **Coding**: "Debug this Python function: `def merge_sorted(a, b):` — it fails on empty lists"
- **Data**: "Create a bar chart comparing revenue by product category: Electronics $45K, Clothing $32K, Food $28K, Books $15K"
- **Quick Q&A**: "Explain the difference between a stack and a queue with Python examples"

### Multi-Agent Workflow

```
Deploy:  python create_workflows.py --file workflows/20_universal_problem_solver.json
Select:  "Universal Problem Solver" in chat UI
```

Test prompts (verify correct agents appear in timeline):
- **Coding** (expect: Analyzer → Code Engineer → Synthesizer):
  "Bug in calculate_discount(items, threshold=100). Applies 10% off to ALL items instead of only items over threshold."

- **Data Analysis** (expect: Analyzer → Data Analyst → Synthesizer):
  "Analyze manufacturing quality data: 40 batches with temperature, pressure, humidity, defect counts. Find which conditions correlate with defects."

- **ML** (expect: Analyzer → ML Engineer → Synthesizer):
  "Build a classifier to predict student exam scores from study_hours, attendance_pct, previous_gpa, sleep_hours. Use the student_performance.csv dataset."

- **Research** (expect: Analyzer → Researcher → Synthesizer):
  "Compare React vs Vue vs Svelte for a new enterprise dashboard project"

- **HITL** (expect: Analyzer pauses for clarification):
  "Analyze our data" (intentionally vague)

### Validation Criteria

- [ ] Super Agent completes coding tasks in < 3 min
- [ ] Multi-Agent workflow routes to correct specialists (check timeline)
- [ ] Charts saved as PNG files (not `plt.show()`)
- [ ] HITL works — Analyzer asks clarification for vague inputs
- [ ] Report Synthesizer produces structured, polished output
- [ ] No agent called unnecessarily (simple tasks use 2-3 agents, not all 7)

---

## Existing Infrastructure Used (No Changes Needed)

| Component | File | What It Does |
|-----------|------|-------------|
| Workflow engine | `backend/onyx/workflows/workflow_engine.py` | `llm_decision` orchestration loop |
| AgentTool | `backend/onyx/tools/tool_implementations/agent_tool.py` | Wraps personas as callable tools for orchestrator |
| Tool constructor | `backend/onyx/tools/tool_constructor.py` | Builds tool instances for personas |
| PythonTool | `backend/onyx/tools/tool_implementations/python/python_tool.py` | Code execution sandbox |
| SearchTool | `backend/onyx/tools/tool_implementations/search/search_tool.py` | Internal KB search |
| WebSearchTool | `backend/onyx/tools/tool_implementations/web_search/web_search_tool.py` | Internet search |
| HITL (pause/resume) | `workflow_engine.py` lines 115-146, 1740-1866 | Checkpoint, pause, resume |
| Streaming packets | `backend/onyx/server/query_and_chat/streaming_models.py` | WorkflowStep*, AgentResponse* |
| Deployment scripts | `create_workflows.py`, `create_assistants.py` | Create workflows/personas via API |

---

## Future Enhancements

1. **Increase sub-agent cycles**: `max_cycles = 5` → `8` in `agent_tool.py:231` (gives each specialist more room)
2. **Per-step cycle config**: Add `max_tool_cycles` to `AgentWorkflowStep` model (DB migration)
3. **Quality Reviewer agent**: 8th agent that evaluates the Synthesizer's output and can loop back for revision
4. **Auto-routing**: Detect problem type at the API level and auto-select Super Agent vs Workflow
