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
| 1 | DESIGN.md + PROGRESS.md + HTML mockup (`mockups/schedules.html`) | ✅ DONE |
| 2 | pulse.txt, models, migration 0009, om/db/pulse.py, om/pulse/timing.py + 43 unit tests | ✅ DONE (da18d4bad) |
| 3 | scheduler loop, constants, Celery pulse_worker app, Dockerfile.pulse, entrypoint, compose, Helm, env | ✅ DONE (499419498) |
| 4 | runner (headless executor) + Celery task + notifications | ✅ DONE (499419498) |
| 5 | /pulse API + chat-list filter / pulse_schedule_id | ✅ DONE (44a9e4527) |
| 6 | Frontend per mockup | 🔄 frontend agent running (web/ only) |
| 7 | Isolated test stack + DB/integration tests + chaos (kill replica / kill worker) | ✅ DONE (e98f2a516); demo workflow TODO |
| 8 | Multi-agent review → fix → re-test | TODO |
| 9 | USER_GUIDE.md, OPERATIONS.md, final PROGRESS, graphify update | TODO |

## Test-stack isolation
Same image as `virtualai-api_server-1` (05fb5ec06800 / om/om-backend), network `virtualai_default`,
`POSTGRES_DB=sched_dev` (pg_dump clone of `postgres`), `REDIS_DB_NUMBER=3`, `REDIS_DB_NUMBER_CELERY=11`,
`REDIS_DB_NUMBER_CELERY_RESULT_BACKEND=10` (main uses 0/15/14), API on host :8090, compose project `pulsedev`.

## Test stack runbook (pulsedev)
- Env file (secrets, NOT in git): `D:/tmp/pulsedev/base.env`; admin API key: `D:/tmp/pulsedev/apikey.txt` (sched_dev only).
- Image: `docker tag <virtualai-api_server image> pulsedev/backend-base:local` then
  `docker build -f backend/Dockerfile.pulse --build-arg OM_BACKEND_IMAGE=pulsedev/backend-base:local -t om/pulse:dev backend`
- Up: `cd deployment/docker_compose && PULSEDEV_ENV_FILE=D:/tmp/pulsedev/base.env docker compose -p pulsedev -f docker-compose.pulse-dev.yml up -d`
  (API :8090; bind-mounts the worktree → `docker restart pulsedev-…` after code changes).
- DB tests (stop pulsedev schedulers first): `POSTGRES_HOST=localhost POSTGRES_DB=sched_dev REDIS_HOST=localhost REDIS_DB_NUMBER=3 pytest tests/external_dependency_unit/pulse`
- API tests: `PULSE_API_URL=http://localhost:8090 PULSE_API_KEY=$(cat D:/tmp/pulsedev/apikey.txt) pytest tests/integration/tests/pulse`

## Verified behaviour (2026-10-24/25, live)
- run-now → succeeded in ~7–21s; chat session saved, `{{date}}` rendered, hidden from "Your chats", shown with include_scheduled.
- 60s interval: consecutive slots fired once each, 0 duplicate slots across 2 replicas (DB check).
- Kill scheduler replica 1 → replica 2 fired the next slots on time; health showed 1 replica alive.
- Kill worker mid-run → reaper marked `interrupted` in ~85s, execution failed, chat shows explanation (bug found+fixed: placeholder text + Redis processing flag).

## Open questions for the user (from mockup review)
1. Scheduled-run chats: only in "Scheduled" section + search (as built) or also in "Your chats" with badge?
2. Sidebar row click → latest run chat (as built) or schedule page?
3. `{{window_start}}` on the first run (currently: one period before)?
4. 5-minute minimum interval OK? (env PULSE_MIN_INTERVAL_SECONDS)
5. Running spinner in accent color OK?
6. "Needs attention" banner on list, or filter tab + pills enough?
7. Keep replied/shared run chats beyond "keep last N"? (as built: yes)

## Log
- 2026-10-24: worktree created. Research subagents died once on a network outage (DNS ENOTFOUND; laptop sleep) → resumed.
- 2026-10-25: plan approved (brand **Pulse**; own HA scheduler service + worker service; Dockerfile.pulse thin
  FROM backend image; requirements/pulse.txt = croniter). Mockup agent launched → `mockups/schedules.html`.
