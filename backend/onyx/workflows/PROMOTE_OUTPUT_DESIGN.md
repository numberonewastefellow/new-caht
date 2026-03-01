# Workflow Output Promotion — Enterprise UX Research

## Problem (from user review)
Workflow step outputs (e.g., budget tables, itineraries) are rendered INSIDE the collapsible
timeline panel ("thinking"). The user wants selective control: some agents' output inside the
timeline (intermediate thinking), some promoted OUTSIDE as main message content (final deliverables).

## How Enterprise Frameworks Handle This

### LangGraph Studio / LangSmith
- Graph nodes have explicit `output` designation
- Output nodes' content renders as the main response
- Intermediate nodes collapsible in trace view
- Pattern: **node-level output flag**

### CrewAI
- Tasks have `output_type` (text, JSON, Pydantic model)
- Final task's output is the crew's output — shown as main content
- Intermediate tasks shown in execution trace (collapsible)
- `expected_output` field guides what the task produces
- Pattern: **last task = final output, others = intermediate**

### AutoGen / Semantic Kernel
- Agents have roles: orchestrator, worker, summarizer
- "Summarizer" agent's output becomes the group chat response
- Other agents' messages are in conversation history (expandable)
- Pattern: **role-based output routing**

### Vercel AI SDK / v0
- Tool calls → collapsible steps
- `streamText()` output → main content area
- Artifacts (code, charts) → side panel
- Pattern: **tool output vs. text output separation**

### Claude Artifacts / ChatGPT Canvas
- Inline tool results → collapsible
- Rich content (code, docs) → artifact/canvas panel
- Summary text → main chat area
- Pattern: **content-type routing** (rich → panel, text → inline)

## Recommended Enterprise Pattern for Our System

### Option A: Step-level `promote_output` flag (Recommended)
- Add `promote_output: bool` to WorkflowStepDefinition
- Steps with flag → output emitted as MESSAGE_START/DELTA (display content)
- Steps without flag → output stays as WORKFLOW_STEP_DELTA (timeline)
- Workflow editor exposes this as "Show output as message" toggle
- Pro: Maximum flexibility, per-step control
- Con: Requires user to configure per step

### Option B: Last-step auto-promotion
- The last step in execution order automatically has output promoted
- All other steps stay in timeline
- Pro: Zero configuration
- Con: Not always correct (last step might be a cleanup/logging step)

### Option C: Output-key based routing
- Steps whose `output_key` matches a special name (e.g., "final_output") get promoted
- Pro: Convention-based, no new fields
- Con: Implicit, harder to discover

### Option D: Hybrid (Best Enterprise UX)
- `promote_output: bool` per step (default: false)
- If NO step has `promote_output=True`, auto-promote the last step
- Workflow editor shows clear visual distinction between "thinking" and "output" steps
- The promoted output REPLACES the auto-generated final summary (no duplication)
- Timeline shows all steps but promoted ones are marked with an icon

## Implementation Notes (for when we build this)
- Backend: Add `promote_output` to WorkflowStep model + WorkflowStepStart packet
- Backend: In engine, emit MESSAGE_START/DELTA for promoted steps after completion
- Backend: Skip auto-generated final summary if any step was promoted
- Frontend: No changes needed — MESSAGE packets already render as display content
- Frontend: Optional enhancement — mark promoted steps with a special icon in timeline

## Status: NOT IMPLEMENTED — research only (user requested analysis, not implementation)
