# Workflow Event Triggers (Autonomous Runs)

## Status: NOT IMPLEMENTED — Design Only

## Context

Workflows can only be started by a user sending a chat message (`WorkflowRunRequest.message` →
`POST /workflow/{id}/run`). There is no way for a workflow to run **on its own** — on a schedule, or in response to
an external event. This is the "autonomous agent" capability that Copilot Studio ships as its flagship feature.

This doc designs **schedule (cron) triggers first**, then **webhook triggers**. Email triggers are deferred.

**Approach**: a single periodic `check-for-workflow-triggers` beat task that scans a new `workflow_trigger` table
and enqueues due runs — *not* one Celery beat entry per user trigger (see "Why not per-trigger beat entries"). The
existing `run_workflow()` path is reused unchanged; only the **entry point** and the **output sink** are new.

**Confidence**: ~85% for the schedule path, ~60% for the open questions below (run-as identity and pause handling
are genuine policy decisions, not implementation details).

---

## Why not per-trigger beat entries

The obvious design — register each user's cron as a Celery beat entry — **does not work here**:

1. `get_tasks_to_schedule()` (`backend/onyx/background/celery/tasks/beat_schedule.py`) returns a **static list** of
   system tasks. It is not user data and is not DB-backed.
2. `DynamicTenantScheduler._compare_schedules()` (`backend/onyx/background/celery/apps/beat.py:228-234`) compares
   **task names only**:
   ```python
   current_tasks = set(name for name, _ in schedule1)
   new_tasks = set(schedule2.keys())
   return current_tasks == new_tasks
   ```
   So if a user edited a cron expression while the task name stayed the same, the schedule would **never update**.

Instead, follow the codebase's own idiom: every existing beat task is a `check-for-*` poller on a `timedelta`
(e.g. `check-for-indexing` every 15 s, `check-for-pruning` every 20 s) that queries the DB and enqueues work. We
add one more of exactly that shape.

---

## Data Model

### `WorkflowTrigger`

| Column | Type | Notes |
|--------|------|-------|
| `id` | int PK | |
| `workflow_id` | int FK → `agent_workflow.id` | cascade delete |
| `trigger_type` | str | `"schedule"` \| `"webhook"` |
| `config` | JSONB | see below |
| `enabled` | bool | default `true` |
| `created_by` | UUID FK → `user.id` | **run-as identity** |
| `last_fired_at` | datetime \| null | drives cron due-calculation |
| `on_overlap` | str | `"skip"` (default) \| `"queue"` |
| `created_at` / `updated_at` | datetime | |

`config` by type:
- **schedule**: `{ "cron": "0 9 * * 1", "message": "competitor news this week", "timezone": "UTC" }`
- **webhook**: `{ "url_token": "<opaque>", "message_template": "..." }`

---

## Phase 1 — Schema

- Alembic migration creating `workflow_trigger`. **Do not run alembic directly** — the backend applies pending
  migrations on startup (restart the container).
- ORM `WorkflowTrigger` in `backend/onyx/db/models.py`, next to `AgentWorkflow`.
- Pydantic `WorkflowTriggerCreate` / `WorkflowTriggerResponse` in `backend/onyx/workflows/models.py`.
- CRUD in `backend/onyx/db/workflow.py`: `create_trigger`, `list_triggers`, `get_due_triggers`, `set_last_fired`.

### Cron parsing — decision required
**`croniter` is not currently a dependency** (checked `backend/requirements/*.txt`). Two options:

| Option | Pros | Cons |
|---|---|---|
| **A. Add `croniter`** *(recommended)* | Real cron expressions, timezone-aware, standard | One new dependency |
| B. Interval-only (`every_seconds: int`) | Zero new deps, trivial | No "9am every Monday"; much weaker UX |

Recommend **A**. Store `cron` + `timezone`; compute the next fire time from `last_fired_at` (or `created_at` on
first run) and compare to `now()`.

---

## Phase 2 — The dispatcher beat task

**New task**: `backend/onyx/background/celery/tasks/workflow_triggers/tasks.py`

```python
@shared_task(name="check_for_workflow_triggers", ...)
def check_for_workflow_triggers(tenant_id: str) -> None:
    # 1. load enabled schedule triggers for this tenant
    # 2. for each, compute next_fire(cron, last_fired_at, tz); skip if not due
    # 3. apply on_overlap policy (see below)
    # 4. enqueue run_triggered_workflow.delay(trigger_id)
    # 5. set last_fired_at = now()  (before enqueue, to avoid double-fire)
```

**Register** in `beat_schedule.py` `get_tasks_to_schedule()`, matching the existing entries:

```python
{
    "name": "check-for-workflow-triggers",
    "task": "check_for_workflow_triggers",
    "schedule": timedelta(seconds=30),
}
```

Because `get_tasks_to_schedule()` is multiplied across tenants by `_generate_schedule()`, each tenant gets its own
entry with `kwargs={"tenant_id": ...}` automatically. Tasks inherit `TenantAwareTask` (`beat.py:263`).

**Granularity note:** a 30 s poll means a cron fires within ≤30 s of its nominal time. Acceptable; document it.

**Overlap policy** (`on_overlap`): query `WorkflowExecution` for `workflow_id` with `status == "running"` started by
this trigger. `skip` → log and do nothing. `queue` → enqueue anyway.

**Double-fire safety:** set `last_fired_at` *before* enqueuing, inside the same transaction, and take a Redis lock
keyed on `trigger_id` (the codebase already uses `RedisLock` for connector credential refresh).

---

## Phase 3 — Execution entry point + output sink

A new `run_triggered_workflow(trigger_id)` Celery task resolves the trigger, builds the run context, and calls the
**existing** `run_workflow()`. Two problems must be solved because there is no HTTP request and no user session.

### Open question 1 — Run-as identity  ⚠️ policy decision

`run_workflow_sequential(..., user: User, ...)` requires a `User`. `get_llm_for_persona(persona, user)` needs one,
and document/tool ACLs key off it. An autonomous run has no request user.

**Proposal:** run as `trigger.created_by`.

**Implication that must be documented:** the workflow executes with the *creator's* permissions indefinitely — even
after that person changes roles. **Mitigations:** at fire time, re-check the user is active and still has access to
the workflow and its personas; auto-disable the trigger (and surface why) if not.

### Open question 2 — Output sink  ⚠️ policy decision

A cron run has no `chat_session_id`, but `WorkflowExecution`, the trace graph, per-step file capture, and the whole
UI all key off one.

**Proposal (default):** create a **system chat session** owned by `created_by` on each fire. This reuses everything
downstream for free — persistence, `steps_executed`, `WorkflowTraceBuilder`, file capture to MinIO, and the
existing trace-viewer UI. The user simply finds the run in their history.

Optional additional sinks, layered on top: `POST` the final output to a callback URL, and/or an in-app
notification. Both are strictly additive.

### Open question 3 — HITL pause has no human  ⚠️ genuine conflict

The engine can **pause mid-run** when a step has `can_request_input` or an agent emits `[NEEDS_INPUT]`, checkpointing
into `WorkflowCheckpoint`. In an autonomous run **nobody is there to answer**, so the execution would hang in
`paused` forever.

**Options:**
- **(a)** Reject at trigger-creation time any workflow containing a step with `can_request_input == True`. Simple,
  but blocks otherwise-useful workflows.
- **(b)** *(recommended)* Let it pause, leave the checkpoint intact, and mark the run **`needs_attention`** +
  notify `created_by`. The user opens the session and answers; the existing resume path takes over unchanged.
- **(c)** Force-suppress pausing for triggered runs (agents told to assume defaults). Risks silent bad output.

Recommend **(b)** — it reuses the shipped pause/resume machinery and degrades gracefully.

---

## Phase 4 — API + UI

- `backend/onyx/server/features/workflow/api.py`: CRUD routes `POST/GET/PATCH/DELETE /workflow/{id}/triggers`.
- A **Triggers** tab on the workflow editor listing triggers, cron, last fired, next fire, enabled toggle.
- Colors via CSS variables only (see `CLAUDE.md`); no hardcoded accent colors.

---

## Phase 5 — Webhook triggers (after schedule ships)

- Public route `POST /workflow/trigger/{url_token}` in `server/features/workflow/api.py`.
- **Security (non-negotiable):**
  - `url_token`: ≥32 bytes of `secrets.token_urlsafe`, compared with `secrets.compare_digest` (constant time).
  - Rotatable + revocable; store a hash, not the raw token.
  - Rate limit per token; cap payload size; reject on unknown/disabled token with a uniform 404.
  - Do **not** echo the payload back in errors.
- Request body becomes the workflow input (templated via `config.message_template`).
- Runs as `trigger.created_by`, same as schedule.

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/onyx/db/models.py` | New `WorkflowTrigger` ORM model |
| `backend/onyx/workflows/models.py` | `WorkflowTriggerCreate` / `WorkflowTriggerResponse` |
| `backend/onyx/db/workflow.py` | Trigger CRUD + `get_due_triggers()` |
| **NEW** `backend/onyx/background/celery/tasks/workflow_triggers/tasks.py` | Dispatcher + `run_triggered_workflow` |
| `backend/onyx/background/celery/tasks/beat_schedule.py` | Register `check-for-workflow-triggers` |
| `backend/onyx/server/features/workflow/api.py` | Trigger CRUD routes; later the webhook route |
| **NEW** alembic migration | Create `workflow_trigger` table |
| `web/` workflow editor | Triggers tab |
| `backend/requirements/default.txt` | Add `croniter` (if Option A) |

## Existing Utilities to Reuse

| Utility | Location |
|---------|----------|
| Beat scheduling / tenant fan-out | `backend/onyx/background/celery/apps/beat.py`, `tasks/beat_schedule.py` |
| `TenantAwareTask` | `backend/onyx/background/celery/apps/app_base.py` |
| `get_session_with_current_tenant()` | `backend/onyx/db/engine/sql_engine.py:311` |
| `RedisLock` (double-fire guard) | as used in `connectors/credentials_provider.py` |
| `run_workflow()` + pause/resume checkpointing | `backend/onyx/workflows/workflow_engine.py` |
| `WorkflowTraceBuilder` | `backend/onyx/workflows/trace_models.py` |

---

## Implementation Order

1. Phase 1: migration + models + CRUD (+ `croniter` decision)
2. Phase 2: dispatcher beat task, behind a `WORKFLOW_TRIGGERS_ENABLED` flag, default **off**
3. Phase 3: `run_triggered_workflow` + system-chat-session sink + run-as identity
4. Phase 4: API + Triggers UI tab
5. Phase 5: webhook triggers

## Verification

1. Create a schedule trigger firing every minute on `04_travel_planner.json`; confirm exactly **one**
   `WorkflowExecution` per minute (no double-fire) and that `last_fired_at` advances.
2. **Overlap:** set a cron faster than the workflow runtime with `on_overlap: "skip"`; confirm no concurrent runs.
3. **Identity:** confirm the run uses `created_by`'s LLM + document ACLs; deactivate the user and confirm the
   trigger auto-disables rather than running with stale privileges.
4. **Pause:** trigger a workflow whose step has `can_request_input=True`; confirm it lands in `needs_attention`
   with an intact checkpoint, and that a human can resume it through the normal UI.
5. **Tenancy:** with `MULTI_TENANT=true`, confirm each tenant gets its own beat entry and triggers do not leak
   across tenants.
6. **Restart** the backend container to apply the migration — never run `alembic upgrade` by hand.
