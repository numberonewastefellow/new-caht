# PROGRESS TRACKER — Gov-Department AI-Workflow Initiative

> **Keep this file updated at the START and END of every session on this initiative.** It is the focus-tracker
> that survives `/compact` and new sessions. Last updated: **2026-08-06** (file-upload demo starters + step-agent fix).

## 🆕 2026-08-06 — File-upload demo + "ask for files" HITL + step-agent fix (agent-config only, NO backend change)
- **Why:** user wants each gov workflow to demo BOTH the quick inline-starter run AND a **file-upload** run
  (attach the case documents), and to **ask for the files (HITL)** when none are attached — with no backend edits.
- **Root-caused a reported "fabrication":** the user had chatted a *step* agent directly — **473 "WF Cyber2 Case
  Synthesizer"** — which, standalone, has no upstream drafts → hallucinates. Only the **wrapper 474 "Cybercrime
  Investigation (Sequential)"** runs the real pipeline. `tag_test_files.py` had wrongly tagged step agents too,
  inviting this. Insurance (356) = `llm_decision` with a *soft* file-request + always-rich starters → it proceeds
  (not a regression).
- **Changes (live via API PATCH; scripts in `backend/tests/workflow_creator/`):**
  - `add_file_upload_starter.py` — appended one **"📎 Upload …"** starter to every gov wrapper (+ insurance +
    both cybercrime variants); each wrapper now has **4 starters**. Names the case docs; expects an attachment.
  - `fix_agent_tags.py` — replaced the test-data tag on the **70 step agents** with an *"[Internal step of the
    '<workflow>' workflow - run the workflow directly, not this agent standalone]"* note; wrappers keep the tag.
  - `smoke_upload.py` — verifier. **Verified:** Collectorate & Prosecution → no-file click **pauses** asking for
    the files (no fabrication). With-files path is backend-verified (`file_descriptors` → `AgentTool` → step
    system prompt; upload endpoint `POST /api/converse/file`) + covered by the passing inline case tests.
  - gpt-4.1 overrides **preserved** by both scripts (verified on Collectorate 443/447/448).
- **⚠️ Post-deploy re-apply** (like `set_agent_model.py`): after any `create_workflows.py --update`/re-seed, re-run
  `add_file_upload_starter.py` + `fix_agent_tags.py` (+ `set_agent_model.py`). Not in the workflow JSONs.
- **Open (user):** 30-sec UI click-test — Collectorate → "📎 Upload reference & coordinate" → attach
  `test_data/collectorate/CO1/` → expect output grounded in Smt. Lakshmi Devi / COLL/INW/2026/04412.

## 🎯 North-star GOAL

## 🎯 North-star GOAL
Build **production VirtualAI multi-agent WORKFLOWS** for the 9 selected Telangana/AP government departments —
each a full workflow **like the `Insurance Claims` reference**: a **workflow JSON**, its **specialist agents**,
**per-case mock test datasets**, and a **guard-rail `test_<dept>.py`**. Design specs = `gtm-government/departments/*.md`.
Positioning: offline/on-prem (Ollama), officer-decides-always, no facial-recognition/surveillance, honest projections.

## ✅ DONE
### Research (design specs) — complete
9 department briefs + `README.md`, `00_executive_summary.md`, `01_capability_inventory.md`, `shortlist.md`, `wave1/`.
Final 9: Cybercrime · State Police charge-sheet · CID · Directorate of Prosecutions · High Courts Registry ·
Land Mutation & ROR · District Collectorate Coordination · Aarogyasri pre-auth · ePASS Scholarship.

### Department #1 — CYBERCRIME — BUILT & GREEN (the validated template) ✅
- **Workflow:** `backend/tests/workflow_creator/workflows/33_cybercrime.json` — "Cybercrime Investigation" (wf **ID=37**), `llm_decision`, **7-step fan-out**.
- **Generator (authoring aid):** `gen_cyber_workflow.py` (edit prompts here → regenerate JSON). **Agents 395–401.**
  Steps: Cyber Complaint Extractor → Fraud-Ring Linker (PythonTool) → Records & Registry Verifier →
  {Golden-Hour Freeze Drafter | Refund & MRM Petition Drafter | Charge-Sheet Drafter} → Cyber Case Synthesizer.
- **Mock data:** `gen_cyber_testdata.py` → `test_data/cybercrime/{CC1,CC2,CC3}/*.csv`.
- **Guard-rail suite:** `test_cybercrime.py` — **CC1/CC2/CC3 + CC4(HITL) = 4/4 PASS (reliably).**
- **Agent-first probes:** `agent_probe.py` — 8/8 pass (each agent tested in isolation before wiring).
- **Model helper:** `set_agent_model.py` (per-agent model escalation; see gotcha below).

### Department #2 — STATE POLICE CHARGE-SHEET — BUILT & GREEN ✅
- **Workflow:** `workflows/34_police_chargesheet.json` (wf **ID=38**), **`sequential`** mode, 7-step self-gating fan-out. Generator `gen_police_workflow.py`, data `gen_police_testdata.py`, suite `test_police.py`. **Agents 403–409.**
  Steps: Case-File Extractor → Antecedents & Linkage → BNSS Compliance & Section-Mapping Verifier → {Charge-Sheet | Compliance Deficiency Memo | Default-Bail Risk} Drafter → Case Synthesizer.
- **SP1 (ready→charge-sheet) · SP2 (compliance-gap→deficiency memo) · SP3 (deadline-critical→default-bail) · SP4 (HITL) = 4/4 PASS.**
- gpt-4.1 on: Case-File Extractor + Compliance Deficiency Memo Drafter (adjacent-stage discrimination); other 5 on gpt-4o-mini.

### Departments #3–#4 — DELEGATED & GREEN ✅ (background agents, same `sequential` template)
- **Directorate of Prosecutions** — `workflows/36_prosecution.json` (wf **ID=39**, agents 411–417). 4/4: PR1 fit→Fit-for-Trial Opinion · PR2 curable gaps→Return-Memo · PR3 insufficient→Weak-Case Opinion · PR4 HITL. gpt-4.1: Case Extractor + Return-Memo + Weak-Case drafters. Toolchain `gen_prosecution_*` / `test_prosecution.py` / `test_data/prosecution/`.
- **CID Economic Offences & AHT** — `workflows/35_cid.json` (wf **ID=40**, agents 419–425). 4/4: CID1→Fund-Trail Report · CID2→AHT Victim-Rescue Report · CID3→Investigation Report · CID4 HITL. gpt-4.1: Case Extractor + Investigation Report Drafter. Toolchain `gen_cid_*` / `test_cid.py` / `test_data/cid/`.
- **High Court Registry** — `workflows/37_registry.json` (wf **ID=41**, agents 427–433). 4/4: HC1→Defect Memo · HC2→Cause-List Entry · HC3→Judgment Headnote · HC4 HITL. gpt-4.1: Filing Extractor + Defect Memo + Cause-List drafters. Clerical-only guardrail; added a `_verify_markers()` startup self-check. Toolchain `gen_registry_*` / `test_registry.py` / `test_data/registry/`.
- **Land Mutation & ROR Correction** — `workflows/38_land.json` (wf **ID=42**, agents 435–441). 4/4: LM1→Mutation Order · LM2→Objection Memo · LM3→RoR Correction · LM4 HITL. gpt-4.1: Extractor + all 3 drafters. Introduced the **forced gate-check preamble** (strongest gate form — see memory [[workflow-build-patterns]]). Toolchain `gen_land_*` / `test_land.py` / `test_data/land/`.
- **District Collectorate Coordination** — `workflows/39_collectorate.json` (wf **ID=43**, agents 443–449). 4/4: CO1→VIP Reply · CO2→Tasking Letter · CO3→Review Brief · CO4 HITL. gpt-4.1: Intake Extractor + Tasking Letter + Review Brief drafters (adjacent-pair). Toolchain `gen_collectorate_*` / `test_collectorate.py` / `test_data/collectorate/`.
- **Aarogyasri Claim Pre-Authorization** — `workflows/40_aarogyasri.json` (wf **ID=44**, agents 451–457). 4/4: AR1→Approval Note · AR2→Query Memo · AR3→Rejection Note · AR4 HITL. gpt-4.1: Preauth Extractor + Query + Rejection drafters. Extractor uses a **STRICT PRIORITY ORDER** (REJECT→QUERY→APPROVE) to separate adjacent decisions cleanly. Toolchain `gen_aarogyasri_*` / `test_aarogyasri.py` / `test_data/aarogyasri/`.
- **ePASS Post-Matric Scholarship Verification** — `workflows/41_epass.json` (wf **ID=45**, agents 459–465). 4/4: EP1→Sanction Order · EP2→Query Note · EP3→Rejection Order · EP4 HITL. gpt-4.1: Application Extractor + Query + Rejection drafters. Toolchain `gen_epass_*` / `test_epass.py` / `test_data/epass/`.

### 🎉 ALL 9 DEPARTMENT WORKFLOWS COMPLETE & GREEN — 36/36 guard-rail tests passing (workflows IDs 37–45)
Cybercrime · State Police · Prosecutions · CID · High Court Registry · Land Mutation · Collectorate · Aarogyasri · ePASS. Each = workflow JSON + 7 agents (descriptions + starter_messages) + per-case mock test data + a passing `test_<dept>.py` (3 routed cases + 1 HITL). Pattern: **sequential mode + self-gating drafters (forced gate-check preamble) + output-based guard-rail**; Extractor + adjacent drafters on gpt-4.1, rest on gpt-4o-mini. Nothing committed (untracked, for review).

**Orchestration modes (as deployed):** **`sequential` (deterministic) = 9 workflows** — Cybercrime-Sequential (wf 46), State Police (38), Prosecutions (39), CID (40), High Court Registry (41), Land (42), District Collectorate (43), Aarogyasri (44), ePASS (45). **`llm_decision` (autonomous) = 1** — the original Cybercrime Investigation (wf 37), kept only as a side-by-side reference. Sequential is the canonical/default choice: the autonomous `llm_decision` orchestrator was non-deterministic (over-routed drafters + dropped the input to the first agent → Extractor false-pause/fabrication), whereas sequential passes the user message + all prior outputs deterministically and the drafters self-gate. So the UI correctly shows "Sequential" on the 9. See memory [[workflow-build-patterns]].

### + Sequential Cybercrime variant (user-requested follow-up)
A NEW **`Cybercrime Investigation (Sequential)`** — wf **ID=46**, `workflows/42_cyber2.json`, agents `WF Cyber2 …` (467–473), `test_cybercrime_seq.py` **4/4** — was added ALONGSIDE the original wf 37 (llm_decision, untouched), reusing `test_data/cybercrime/`. So Cybercrime now has both orchestration modes side-by-side; the sequential one is canonical. **Notable:** the **forced gate-check preamble alone held all 3 drafters deterministic on gpt-4o-mini** — only the Extractor needed gpt-4.1 (no drafter escalation), the most token-efficient variant. Reinforces that the forced gate-check (not model escalation) is the strongest lever.

### 🛡️ Anti-fabrication + HITL hardening (2026-08-06) — ALL 10 Extractors
Bug found in UI testing: given a **described-but-empty** prompt (a bare item/case TYPE + topic + instructions, NO concrete data — e.g. the Collectorate VIP starter), the Extractor **fabricated** specifics (invented citizen name, department, an SLA-breach figure, even fake citations) instead of pausing. Fixed in **all 10 workflows**: (1) a `## ⚠️ NEVER FABRICATE — PAUSE INSTEAD` clause in every Extractor (a bare type+topic is NOT data → emit `[NEEDS_INPUT]` + list exactly what to paste; never invent a name/number/date/figure/citation); (2) **sample-data starter prompts** (embed real fields inline so a UI click runs end-to-end honestly, + one deliberately-sparse starter that demos the pause); (3) a **guard test (id 5)** added to every `test_<dept>.py` replaying the described-but-empty scenario → must pause. **Verified: all 10 route their data-present cases (no false pause) AND all 10 guard cases pause (`test_<dept>.py --test 5` = PASS ×10).** Gotcha: in `llm_decision` mode (Cybercrime wf37) the clause over-paused on data-rich cases until the Extractor TASK got "scan every attached table FIRST" + the orchestrator passed the user message verbatim — another reason `sequential` is the robust default.

## 🧠 CRITICAL LEARNINGS (apply to every remaining department)
1. **Agent-first works:** author agents → `agent_probe.py` each in isolation (cheap, gpt-4o-mini) → fix prompts →
   only then wire the workflow + run `test_<dept>.py`. Catches prompt bugs before expensive workflow runs.
2. **Token economy / model tiers:** default every agent + orchestrator to **gpt-4o-mini**. Escalate to **gpt-4.1**
   ONLY what fails: here the **Extractor** (dense-CSV extraction + stage classification) and the **orchestrator**
   (decision routing) needed gpt-4.1; the other 6 agents stay on gpt-4o-mini.
3. **⚠️ Model-override gotcha:** `create_workflows.py --update` / `--deploy` does NOT preserve per-agent model
   overrides (the starter-message PATCH resets them to the global default gpt-4o-mini). **After EVERY deploy/update,
   re-run `set_agent_model.py --agent "<WF Agent>" --model gpt-4.1`** for each escalated agent. (Orchestrator model
   IS preserved — it's a workflow-level field.)
4. **⭐ Deterministic routing = self-gating drafters + output-based guard-rail (THE key pattern).** `llm_decision`
   routing is non-deterministic — the orchestrator intermittently over-calls drafters (~50% flaky). DO NOT gate the
   test on which agents were *invoked* (`reject_agents`). Instead: (a) give each conditional/"drafter" agent a
   **STAGE GATE** — it self-checks the case and emits a short `NOT APPLICABLE FOR THIS CASE STAGE …` no-op when it
   shouldn't act; (b) the test asserts on **what each agent PRODUCED** (a distinctive output header, e.g.
   `charge-sheet skeleton`), captured **per-step** from the stream (`step_outputs[step_name]`). Then even if the
   orchestrator over-calls, the wrong document is never produced → the guard-rail passes deterministically.
   See `DRAFT_MARKERS` + `produced`/`not_produced` in `test_cybercrime.py` and the "## STAGE GATE" blocks in
   `gen_cyber_workflow.py`. This is the reusable template for all fan-out departments.
5. **Infra:** backend is up (Docker `virtualai-api_server-1`); a fresh **admin key** is in
   `backend/tests/agents_creator/apikey.txt` (minted via the container — see NOTES_FOR_USER.md; do NOT commit it).
   Provider `gpt` (openai); visible models incl. gpt-4o-mini, gpt-4.1, gpt-5.5/5.6. HITL pause = agent emits
   `[NEEDS_INPUT]` on line 1 + step `can_request_input:true`.

## 📐 BUILD RECIPE (per department — copy the Cybercrime toolchain)
1. Read `gtm-government/departments/<dept>.md`. Map its extract→check→verify→route&draft pipeline to agents,
   splitting the "route & draft" step into 2–4 **conditional drafters** (fan-out) each with a STAGE GATE.
2. Copy+adapt `gen_<dept>_workflow.py` (agents: description + system_prompt + starter_messages + STAGE GATE +
   `NOT APPLICABLE` no-op; pin small model; escalate Extractor/orchestrator to gpt-4.1). Pick next unused `NN`.
3. Copy+adapt `gen_<dept>_testdata.py` → `test_data/<dept>/{C1,C2,C3}/*.csv` (presence/absence of a source cues
   the right drafter; each case's stage signals unambiguous).
4. `python gen_<dept>_workflow.py` → deploy `create_workflows.py --file workflows/NN_<dept>.json --no-icons` →
   `set_agent_model.py` for escalated agents.
5. `agent_probe.py` each agent (extend PROBES) → fix prompts → regenerate/redeploy/re-escalate.
6. Copy+adapt `test_<dept>.py` (DRAFT_MARKERS + produced/not_produced + HITL) → run → fix loop → **all green**.
7. Update this file + `NOTES_FOR_USER.md`.

## ⏳ PENDING
1. **Phase 3:** coverage for the ~27 PRE-EXISTING workflows + seeded agents. Most already have a `test_*.py` (insurance, medical, discussion, coding, financial_crime, cybersecurity_ir, engineering, mna, drug, universal_solver, smartsearch, data_science_tutor, conditional_router, hitl, promote_output, step_overrides, chart, docx, execute_code, …) and there's a `test_all_workflows.py` meta-runner. A full re-run of all suites is **token-heavy** (many gpt-4.1/mini calls) — do an inventory + representative sample, not an exhaustive re-test, unless the user wants the full run.
2. *(Optional)* retrofit Cybercrime (#1) from `llm_decision` → `sequential` for consistency (it's currently green on llm_decision; edit `gen_cyber_workflow.py` orchestration_mode, redeploy, re-escalate, re-test).
3. *(Optional)* polished per-department HTML decks; run `graphify update .` to refresh the graph.

## 🔑 KEY POINTERS
- Cybercrime toolchain (copy-from): `backend/tests/workflow_creator/{gen_cyber_workflow.py, gen_cyber_testdata.py, test_cybercrime.py, agent_probe.py, set_agent_model.py, workflows/33_cybercrime.json, test_data/cybercrime/}`.
- Reference workflow: `workflows/26_insurance_claims.json`, `test_insurance_claims.py`.
- Standing rules: **never commit** (deliver untracked); no product-code changes without confirmation; may deploy/restart-backend/alembic.
- Review notes for the user: `gtm-government/NOTES_FOR_USER.md`.

## 📌 NEXT ACTION
**All 9 department workflows DONE & GREEN (36/36 guard-rail tests).** Remaining is Phase 3 — a coverage inventory of
the ~27 pre-existing workflows/agents (see PENDING; a full re-run is token-heavy, so inventory + sample) — plus the
optional Cybercrime→sequential retrofit. Open questions + the full session recap are in `NOTES_FOR_USER.md`.
