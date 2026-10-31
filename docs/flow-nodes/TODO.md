# Flow nodes: TODO

**Where we are:** 3c, 3d and 3f are built and live on port 3000, **waiting for the user's screen check**. Next: 3e.

Work top to bottom, one item at a time: implement, test, check on screen, tick, add a progress line. Why each item exists: [FIX_PLAN.md](FIX_PLAN.md) (evidence) and the plan review in the progress log below.

**Rules:**
- Commit only when the user asks; never push; explicit `git add` paths; never run the alembic CLI; keep both editors in sync.
- **No workarounds (user, 2026-10-31):** if an existing workflow fails, upgrade that workflow; don't add fallbacks. Back up first; backups are in `D:/llm/backups/`.
- Keep it simple, in small modules.
- **Verify the goal, not just `completed`:** read what agents actually received and answered. A completed run can still be wrong.

**Testing setup:**
- Main stack with `dev.bat`. `flowdev.bat` and the `flowdev` containers are retired.
- Backend code is bind-mounted: `dev.bat restart api background`. Pulse: `dev.bat build pulse`. Web: `dev.bat build web`.
- DB tests use the `flow_dev` database (env file `D:/tmp/flowdev.env`), never the real DB. Point the sandbox tests at `CODE_INTERPRETER_BASE_URL=http://code-interpreter:8000` with the token from `.env`.
- Live checks use throwaway keys, scripts in `D:/tmp`: `main_agent_flow.py`, `main_demo_e2e.py`, `main_saves_e2e.py`, `main_regression.sh`.
- Screen checks: no test login exists on the real DB, so ask the user for a screenshot.

## Done

| # | Item | Verified by |
|---|---|---|
| 1.0 | Steps use dedicated agents (save + run) | Unit, DB, live API; user's checks |
| 2a | Saves are atomic, row lock, 409 on a race | DB tests reproduced the bug first; 5 runs of the concurrency test |
| 2b | Old workflows keep a restorable "before" version | DB tests; live restore |
| 2c | Duplicate and reserved output keys refused; `llm_decision` refuses containers | Unit, DB, live API; 47 templates and the real DB have none |
| 2d | `llm_decision` runs record their version | DB tests; live runs |
| 2e | Frontend validation mirrors the backend | jest per rule |
| 2f | Editor parity: shared step options and limits | jest; user's checks |
| 2g | **Core fix:** the `llm_decision` orchestrator now sees its agents' results | Real pipeline tests; 48/48 paused runs valid; live runs; Cybercrime 5/5; Medical P1 |
| 2h | Orchestrator limits hidden in Sequential mode, both editors | jest. On screen at the next check |
| 2j | Version snapshots include workflow-level settings; restore brings them back | DB tests; unit + goldens on both engines |
| 3a | Research notes: `research/04-container-ui.md` | Sources linked |
| 3b | Tree model and depth-first save; chain per block; router reorder fixed | jest, including the demo's payload unchanged |

## To do

| Done | # | Item | Kind | Done when |
|---|---|---|---|---|
| [ ] | 3c | Show containers: boxes with lanes, children inside, recursive layout, correct legend. Code done, jest 117/117; **open: user's screen check** | Frontend | jest; screenshot of workflow 49 |
| [ ] | 3d | Edit structure: Run inside / Branch pickers in both editors, add into a lane, drag in/out, refuse cross-block edges, safe delete and reorder. Code done, jest 157/157; **open: user's screen check** | Frontend | jest; screenshot |
| [ ] | 3e | Forms: branch labels, loop operator dropdown, code inputs/outputs; backend validates loop operator and unique labels | Frontend + small backend | jest, unit; screenshot |
| [ ] | 3f | Wizard: children indented under their container, safe reorder and delete. Code done with 3d; **open: user's screen check** | Frontend | jest; screenshot |
| [ ] | 3h | Safe references for agent steps on new workflows; save-time check of references | Backend | Unit; goldens unchanged for `schema_version=1` |
| [ ] | 3g | Build parallel + loop from the UI in each editor, save, reload, run; nesting; agents really receive `$loop.item` | End to end | Runs complete and hand-offs verified; nesting tests added |
| [ ] | 3i | **Upgrade a couple of old workflow templates** to the new features and test only those (user's decision: no bulk LLM runs of old workflows). Candidates: `02_code_review.json` (reviewers as parallel branches), `22_medical_diagnosis.json` (Medical P2 guard-rail below) | Templates | Each runs live; hand-offs read; shown on the canvas |
| [ ] | 3j | **Make the demo a real workflow.** The first step's toy code `days = 3 if '3' in text else 2` always gives 2 days (found from the user's 6-day request; not an LLM or engine limit). Replace it: an intake agent extracts destination, days and travellers; code builds the day list; raise `max_iterations`; agents get real instructions, not "one sentence", and search where available | Workflow (real DB, new version) | The user's 6-day question gives 6 days; answers read, not just `completed` |
| [ ] | 4 | Run view: trace fields and timings, loop trace, packet branch fields, persist `step_type`, grouped timeline, fork/join. Includes the user's check of the demo's timeline | Backend + frontend | Tests; screenshot of a demo run |
| [ ] | 5 | Webhooks in Pulse (W1–W5). Back up the real DB first; migration `0003`; `flow_dev` migrates by starting the backend once with `flowdev.env` | Full stack | Tests in PROGRESS "Webhooks"; screenshot |
| [ ] | 6 | Engine hardening, in order: cancel + fail-fast + timeout; budgets + concurrency; retry; sandbox admission + code errors; opt-in router upgrade. A loop must not silently drop items beyond `max_iterations`: say so in the output and the trace. Decide whether `llm_decision` runs on the pinned definition | Backend | Each with tests; goldens green |
| [ ] | 7 | Dry-run script in the repo, template JSONs, multi-agent review, `graphify update .`, docs (`research/00-platform-survey.md`, DESIGN, HANDOVER), remove `flowdev.bat` and the flow-dev compose file, drop `flow_dev` only if the user agrees. Look at the `No active trace` log errors | Mixed | Checklist done; rollout notes for the user |

**Not scheduled; the user decides at the end:** durable runs and crash resume, idempotency for side-effecting tools, cost budgets per tenant, approvals inside containers, OpenTelemetry, audit and RBAC, draft/publish, PII retention. See `REVIEW_88eb334e5.md`.

## Progress log

- **2026-10-31, 3d + 3f.** `stepTree.ts`: `moveStep`, `removeStep`, `reorderInBlock`. `containerLanes.ts`: lanes and allowed places. `StepPlacementFields.tsx` used by both editors. Canvas: drop into a lane, drag in and out, lines stay within a block. Not exercised in a real browser by me; jest and types only.
- **2026-10-31, demo check.** User's 6-day trip gave 2 days. Trace read (execution 556): the demo's toy first step built `["Day 1", "Day 2"]`; the loop and the LLM did what they were told. Added 3j. Answered why the two orchestrator limits are hidden in Sequential mode: 0 uses in the Sequential engine; values stay saved. User confirmed they show on LLM Decision workflows.
- **2026-10-31, 3c.** `containerLayout.ts` (recursive, pure), `ContainerNode.tsx`, a `container` editor kind. Workflows without containers keep the old grid. Web rebuilt and API restarted, so 2h and 2j are live too.
- **2026-10-31, old workflows.** User: don't test all old workflows with LLM calls (tokens); pick a couple, upgrade their JSON and test those. Bulk run stopped. Results before stopping: Medical P3 and P4 pass. Medical P2 fails a guard-rail: the orchestrator also consulted the Endocrinologist, which the test forbids for this patient. Not retested; goes with the `22_medical_diagnosis.json` upgrade in 3i. Discussion and later suites did not run.
- **2026-10-31, plan review.** Added 2h (limits mislead in Sequential mode, from the user's screenshot), 2i (the core fix changed 29 workflows), 2j (the orchestrator prompt isn't versioned), 3h (references in loops). Dropped ELK for a small recursive layout: our graph is a tree of chains, ELK is async, and this adds no dependency. No lane nodes. Item 6 reordered by risk.
- **2026-10-31.** User validated the Wizard, Visual panel and Customer Support Triage. 2f confirmed.
- **2026-10-31.** Step 2 built. Found and fixed the `llm_decision` core bug. Real DB backed up first: `D:/llm/backups/virtualai_postgres_before_flow_step2_20261031_095036.dump`. Details in HANDOVER.
