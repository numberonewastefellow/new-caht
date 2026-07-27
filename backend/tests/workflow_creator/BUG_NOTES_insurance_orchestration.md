# Bug note — Insurance Claims workflow: non-deterministic orchestration (CL1)

Status: **RESOLVED / NOT-A-PRODUCT-BUG** for the intended (file-upload) path. Recorded 2026-07-27.
No code changed. Compare against `main_multi_agent_stable` before any change.

## UPDATE 2026-07-27 — file-upload path VERIFIED WORKING (owner was right)

Re-ran CL1 the way it's actually used — **claim data as attached files** (22 files via
`POST /api/workflow/30/run` `file_descriptors`), narrative-only message, no inline CSV text:
- Trace: `workflow start … chat_files=22`; and **every specialist received all files** —
  `WF Claims Triage Adjuster files=22 branch=inlined`, `WF Property Damage Assessor files=22
  branch=sandbox` (PythonTool, files pre-loaded), `WF Policy Coverage Analyst files=22 branch=inlined`,
  `WF Settlement Report Writer files=22 branch=inlined`.
- Result: **completed, no stall**, 7 PythonTool runs, 35 220-char settlement report, keywords
  settlement/coverage/disclaimer present, **routing correct (no Auto/Fraud/Weather over-routing)**.

Conclusion: the file-upload path works end-to-end. The failures below were an artifact of the **test
harness feeding inline TEXT with zero files** (the fragile path where a specialist depends on the
orchestrator re-typing the data). HITL asking for a *genuinely* missing file is intended behavior.
Remaining watch-item: orchestrator specialist-routing can still vary run-to-run (a model-reliability
trait) — not a broken data path. The flaky text-path findings below are retained for context only.

## Symptom

`python test_insurance_claims.py --test 1` (CL1 kitchen fire, data fed as inline TEXT, no file uploads)
**fails, and fails differently each run** (flaky):

| Run | Duration | What happened | Why it failed |
|-----|----------|---------------|---------------|
| 1 | 41.8s | Triage ran, then **Property Damage Assessor paused** "No claim data present" → Coverage Analyst & Settlement Writer never ran (2 agents total) | Orchestrator did **not** forward the claim data to the specialist |
| 2 | 370.7s | All 4 expected agents ran (no stall), workflow completed | Orchestrator **over-routed**: also called Auto Reconstructionist + Fraud Investigator + Weather/CAT Analyst on a kitchen-fire claim (guard-rail violation) |

## Root cause (confirmed by code + runtime trace)

`llm_decision` orchestration hands each specialist **only** the `task` string the orchestrator LLM types,
plus any uploaded files:
- `backend/om/tools/tool_implementations/agent_tool.py` — `tool_definition()` exposes one param `task`
  (L206-213); `run()` builds `user_message = ChatMessageSimple(message=task)` and
  `msg_history = [user_message]` (L361-367). **No conversation history, no original user message** reaches
  the specialist. It only sees: its system prompt + `task` + inlined `chat_files` (attached uploads).
- Runtime trace of run 1: `[Trace] agent='WF Property Damage Assessor' has_python_tool=True files=0` — the
  PythonTool specialist received **zero files** and (this run) no data in `task`, so it escalated. Its own
  prompt is correct — it says "work from inline tables… do NOT stall… escalate ONLY when data is ENTIRELY
  absent" — it stalled only because it genuinely received nothing.

So data reaches specialists **only** if (a) the orchestrator LLM copies it verbatim into every `task`
(unreliable for large blobs — run 1 shows it skipping this), or (b) the user **uploads files** (chat_files),
which PythonTool agents get pre-loaded in their sandbox (`agent_tool.py` L330-338) — the reliable path.
Routing to the correct specialists is likewise an unconstrained LLM decision (run 2 shows over-routing).

## Git comparison — this is NOT a refactor (onyx→om) regression

- `agent_tool.py`: diff vs `main_multi_agent_stable:backend/onyx/tools/tool_implementations/agent_tool.py`
  is **64 insertions / 64 deletions — a symmetric `onyx.`→`om.` import rename**. `msg_history = [task]` and
  the file-inlining helper are identical on main.
- `workflow_engine.py`: differs more (175/109) but the non-rename delta is the commit
  `93a106b25 feat(workflows): stream sub-agent prose + reasoning live` — display/streaming, **not data-flow**.
- Workflow def `workflows/26_insurance_claims.json`: orchestrator prompt + specialist prompts are
  **unchanged vs main** (only our `persona_*`→`agent_*` and `orchestrator_llm_provider "v"`→`"gpt"` edits).
  Its own history has prior `insurance agent fix` / `agent file access fix` commits — the data hand-off was
  already known-fragile and prompt-patched.

**Conclusion:** the mechanism is identical pre/post refactor. "Worked before the refactor" is most likely
(a) the run was driven via **file uploads** (reliable sandbox path) rather than inline text, and/or
(b) **LLM non-determinism** — some runs the orchestrator forwards data + routes correctly and it passes.

## Fix directions (for later — require owner confirmation, do NOT apply now)

1. **Engine-level (most robust):** give each delegated specialist the original claim data / relevant
   conversation context automatically, instead of relying on the orchestrator to re-type it into `task`
   (e.g. thread the workflow `context.step_outputs` / original user input into `AgentTool.run`'s
   `msg_history`). Fixes run-1 class.
2. **Routing guard:** constrain specialist selection (the orchestrator over-called on run 2) — e.g. a
   routing/allow-list step or stricter orchestrator instructions per claim type. Fixes run-2 class.
3. **Operational workaround (no code):** drive the workflow with **file uploads** (CL1/documents/) so
   PythonTool specialists read files from their sandbox — the reliable path — rather than inline text.

## Repro
`cd backend/tests/workflow_creator && python test_insurance_claims.py --test 1 --key <admin-key>`
(run it 2–3× to see the flakiness). Workflow id=30 on this instance; agents pinned to gpt-4.1.
