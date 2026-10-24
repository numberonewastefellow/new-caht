# Pulse (Scheduled Workflows) — Progress Tracker

> **Resume protocol for a new session:** read this file top-to-bottom, then `DESIGN.md` (same folder, = approved
> plan + research citations). Work ONLY in the worktree `D:/llm/danswer_sched_wt` (branch
> `feature/scheduled-workflows`, based on `main_multi_agent_stable` @ `eb6902e66`). The main checkout
> `D:/llm/danswer20022026` is being heavily refactored by another agent — never edit it, never restart its
> `virtualai-*` containers. **Commits:** LOCAL commit at the end of each phase on this branch only (user-approved
> 2026-10-25), explicit `git add <paths>`, NEVER push (repo is public). Never run alembic CLI by hand.

## Goal
n8n-style scheduled workflows ("Pulse"): pick any workflow, schedule it (cron / interval / once), it runs in the
background repeatedly, results saved to DB, each run = a chat session (shown in a "Scheduled" sidebar section).
Managed from UI. HA (`pulse_scheduler` ×2), scalable (`pulse_worker` ×N), easy to use.

## Status board
| Phase | Description | Status |
|---|---|---|
| 0 | Worktree + research (3 agents) + design debate (2 reviewer agents) + user Q&A | ✅ DONE |
| 1 | DESIGN.md + PROGRESS.md + HTML mockup agent (parallel) | 🔄 mockup agent running |
| 2 | pulse.txt, models, migration 0009, om/db/pulse.py, om/pulse/timing.py + unit tests | TODO |
| 3 | scheduler loop, constants, Celery pulse_worker app, Dockerfile.pulse, entrypoint, compose, Helm, env | TODO |
| 4 | runner (headless executor) + Celery task + notifications | TODO |
| 5 | /pulse API + chat-list filter / pulse_schedule_id | TODO |
| 6 | Frontend per mockup | TODO |
| 7 | Demo workflow + isolated test stack + E2E | TODO |
| 8 | Multi-agent review → fix → re-test | TODO |
| 9 | USER_GUIDE.md, OPERATIONS.md, final PROGRESS, graphify update | TODO |

## Test-stack isolation
Same image as `virtualai-api_server-1` (05fb5ec06800 / om/om-backend), network `virtualai_default`,
`POSTGRES_DB=sched_dev` (pg_dump clone of `postgres`), `REDIS_DB_NUMBER=3`, `REDIS_DB_NUMBER_CELERY=11`,
`REDIS_DB_NUMBER_CELERY_RESULT_BACKEND=10` (main uses 0/15/14), API on host :8090, compose project `pulsedev`.

## Log
- 2026-10-24: worktree created. Research subagents died once on a network outage (DNS ENOTFOUND; laptop sleep) → resumed.
- 2026-10-25: plan approved (brand **Pulse**; own HA scheduler service + worker service; Dockerfile.pulse thin
  FROM backend image; requirements/pulse.txt = croniter). Mockup agent launched → `mockups/schedules.html`.
