# Parallel Agent Execution (Queue-Based)

## Status: NOT IMPLEMENTED — Future Enhancement

## Context

The workflow engine currently runs all agents sequentially. Independent agents (e.g., Flight Finder + Hotel Finder) could run in parallel, saving ~25-35s per pair. Users configure which steps are parallel via a `parallel_group` field in the Step configuration UI.

**Approach**: stdlib `queue.Queue` per agent + simple multiplexer. Per-thread DB sessions via `get_session_with_current_tenant()`. No Redis Streams (over-engineered for this use case). Shared step_outputs via `dict` + `threading.Lock`.

**Confidence**: ~90% for parallel path, ~98% for sequential path unchanged.

---

## How It Works (User Perspective)

In the Workflow Editor, each step has an optional **Parallel Group** number:

| Step | Agent | Parallel Group |
|------|-------|----------------|
| 1 | Destination Researcher | -- (sequential) |
| 2 | Flight Finder | **1** |
| 3 | Hotel Finder | **1** |
| 4 | Activity Planner | -- (sequential) |
| 5 | Budget Calculator | -- (sequential) |
| 6 | Itinerary Builder | -- (sequential) |

- Steps 2 & 3 share group "1" so they run **simultaneously**
- All other steps run sequentially, in order
- Leave the field empty = sequential (exactly like today)
- Only applies to `sequential` orchestration mode (`llm_decision` ignores it)

---

## Phase 1: DB Migration + Schema Updates

### 1.1 Alembic Migration

**New file**: `backend/alembic/versions/xxxx_add_parallel_group.py`

```python
op.add_column("agent_workflow_step", sa.Column("parallel_group", sa.Integer(), nullable=True))
```

Nullable integer. Steps with same non-null value run concurrently. `NULL` = sequential (backward compatible).

### 1.2 SQLAlchemy Model

**File**: `backend/onyx/db/models.py` (~line 5076, before `is_terminal`)

```python
parallel_group: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

### 1.3 Pydantic Schemas

**File**: `backend/onyx/workflows/models.py`

- `WorkflowStepCreate`: add `parallel_group: int | None = None`
- `WorkflowStepResponse`: add `parallel_group: int | None = None`

### 1.4 CRUD

**File**: `backend/onyx/db/workflow.py` — pass `parallel_group=step_create.parallel_group` in `_add_step()`

### 1.5 TypeScript Interfaces

**File**: `web/src/lib/workflows/interfaces.ts`

- `WorkflowStepSnapshot`: add `parallel_group: number | null`
- `WorkflowStepCreate`: add `parallel_group?: number | null`

---

## Phase 2: Engine — Step Grouping

### `_group_steps()` function

**File**: `backend/onyx/workflows/workflow_engine.py`

```python
def _group_steps(steps: list[AgentWorkflowStep]) -> list[list[AgentWorkflowStep]]:
    """Group steps into execution batches.
    - Steps with same non-null parallel_group -> one batch (run concurrently)
    - Steps with null parallel_group -> individual batch (run sequentially)
    - Batches ordered by minimum step_order in each group
    """
```

---

## Phase 3: Engine — Parallel Execution

### `_run_parallel_group()` — Core

**File**: `backend/onyx/workflows/workflow_engine.py`

Thread architecture:

```
Main Thread (SSE generator)
  |
  +-- Agent Thread 1: own DB session, own Queue, own Emitter
  +-- Agent Thread 2: own DB session, own Queue, own Emitter
  |
  +-- Multiplexer: poll all Queues (50ms round-robin), yield packets
```

**Each agent thread** (`_run_agent_in_thread`):

1. Creates own DB session via `get_session_with_current_tenant()` (contextvars propagated automatically)
2. Creates own `queue.Queue` + `Emitter`
3. Builds `AgentTool` with thread-local DB session
4. Calls `agent_tool.run()` (blocks until done, emits packets to local Queue)
5. On completion: writes output to shared `step_outputs` dict (protected by Lock)

**Multiplexer** (main thread):

1. Launches N threads via `run_in_background()` (one per parallel step)
2. Round-robin polls all N queues: `queue.get(timeout=0.05)`
3. Yields deserialized packets as they arrive
4. When all threads complete -> final drain of all queues -> break
5. Checks `is_connected()` for stop signals each cycle

### Shared State

```python
step_outputs_lock = threading.Lock()
step_outputs: dict[str, str] = {}  # output_key -> agent output

# In agent thread, after completion:
with step_outputs_lock:
    step_outputs[step.output_key] = agent_output
```

### Integration into `run_workflow_sequential()`

```python
for group in _group_steps(steps):
    if len(group) == 1 and group[0].parallel_group is None:
        # Sequential -- existing code, unchanged
        yield from _run_single_step(group[0], ...)
    else:
        # Parallel group -- new
        yield from _run_parallel_group(group, context, ...)
```

### Placement

Each parallel agent gets: `Placement(turn_index=base_turn_index, tab_index=i)` where `i` is agent index within group.

### Error Handling

- One agent fails -> log warning, others continue, missing output_key skipped by downstream
- All agents fail -> abort workflow with first exception
- Stop signal -> multiplexer breaks, agent threads wind down naturally (no force-kill)

---

## Phase 4: Frontend UI

### Parallel Group Field

**File**: `web/src/refresh-pages/WorkflowEditorPage.tsx`

Add number input per step row with InfoTip tooltip:

> "Steps with the same group number run at the same time. E.g., Flight Finder (group 1) and Hotel Finder (group 1) execute simultaneously. Leave empty for sequential."

### Visual Indicators

- Color-coded left border on steps sharing same `parallel_group`
- Small badge: "Parallel Group 1"

### Validation

- `parallel_group: Yup.number().nullable().min(1)`
- Pass through in `handleSubmit`

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/onyx/db/models.py` | Add `parallel_group` column to `AgentWorkflowStep` |
| `backend/onyx/workflows/models.py` | Add `parallel_group` to Pydantic schemas |
| `backend/onyx/db/workflow.py` | Pass `parallel_group` in `_add_step()` |
| `web/src/lib/workflows/interfaces.ts` | Add `parallel_group` to TS interfaces |
| `web/src/refresh-pages/WorkflowEditorPage.tsx` | Add parallel group UI field + visual indicators |
| `backend/onyx/workflows/workflow_engine.py` | Add `_group_steps()`, `_run_parallel_group()`, integrate into sequential runner |
| **NEW** alembic migration | Add `parallel_group` column |

## Existing Utilities to Reuse

| Utility | Location |
|---------|----------|
| `get_session_with_current_tenant()` | `backend/onyx/db/engine/sql_engine.py` |
| `run_in_background()` | `backend/onyx/utils/threadpool_concurrency.py` |
| `Emitter` | `backend/onyx/chat/emitter.py` |
| `queue.Queue` | Python stdlib |
| `threading.Lock` | Python stdlib |

---

## Implementation Order

1. Phase 1: DB migration + all schema updates
2. Phase 2: `_group_steps()` logic
3. Phase 3: `_run_parallel_group()` + integration into sequential runner
4. Phase 4: Frontend UI
5. Test: Update Travel Planner with Flight+Hotel in `parallel_group=1`

## Verification

1. Update `04_travel_planner.json`: set `parallel_group: 1` on Flight Finder + Hotel Finder steps
2. Run: `python create_workflows.py --run 5 "Plan a 5-day trip to Tokyo..."`
3. Verify both agents start simultaneously, packets interleave correctly
4. Verify sequential workflows (no `parallel_group` set) work identically to before
5. Expected savings: ~25-35s from overlapping Flight+Hotel execution
