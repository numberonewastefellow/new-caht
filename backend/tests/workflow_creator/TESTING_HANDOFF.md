# Workflow Testing — Hands-off / Resume Doc

_Last run: 2026-08-03 14:58 (auto-triggered when OpenAI credits were funded). Server: http://localhost:3000.
Model pinned: gpt-4.1. Detailed evidence in scratchpad `wf_test_run/RESULTS_REPORT.md` + per-suite `*.log`._

## Status at a glance

| Suite | Result | Notes |
|-------|--------|-------|
| Coding (`test_coding_workflows.py`) | **11/12** ✅ | sequential; #5 House Price = no chart PNG (soft) |
| Showcase (`test_all_workflows.py`, 18) | **14/18** ✅ | 4 fails ran ~3–5s (throttle-empty): Legal Contract, IT Incident, Citizen Complaint, Code Debug |
| Medical Diagnosis | **4/4** ✅ | fully clean — proves the domain workflows work end-to-end |
| Financial Crime | 1/4 | #1 ran full (5 agents/183s); #2–3 throttled to 2 agents |
| Engineering Failure | 0/3 | #1 ran full (6 agents); FAIL = PythonTool agent narrated instead of executing code |
| Cybersecurity IR | 1/4 | #1 full (7 agents/118s); #2 (1 agent), #3 (0 agents/1.1s throttle-empty) |
| Insurance Claims (inline) | 0/3 | #1 3 agents/90s; #2–3 throttled |
| M&A Due Diligence | 0/3 | #1 full (8 agents/94s); #2–3 throttled to 1 agent |
| Drug Development | 0/3 | #1 1 agent; #3 0 agents |
| Insurance CL1 (file-upload) | guard-rail FAIL | all expected specialists ran; 2 extra (Fraud, Subrogation) — mild over-routing |

## Read the domain results carefully (throttle confound)
The **first case in every domain suite ran fully** (5–8 agents, 80–180s of real work); **later back-to-back
cases collapsed to 0–1 agents in 1–9s** — the OpenAI **rate-limit → empty-completion** signature (0 tokens,
"orchestrator produced no answer"). So domain "0/3" is mostly a **pacing artifact**, not broken workflows
(Medical 4/4 proves the engine is sound). Genuine findings still visible on the FULL runs:
- **PythonTool agents narrate instead of executing code** (engineering F1, coding #5 no-chart) — consistent, real.
- Insurance/M&A/etc. over-route to a couple of wrong specialists on the inline path.

## To get clean domain numbers — re-run with intra-case pacing
`run_clean.sh` paces 60s **between suites** but suites loop their 3–4 cases **back-to-back** with no delay →
throttling. Fix: run each domain suite **one case at a time** with a delay, e.g.
`for t in 1 2 3; do python -u test_medical_diagnosis.py --key $KEY --test $t; sleep 45; done`, or add an
inter-case sleep. Verify OpenAI credits first (direct call — an exhausted account returns HTTP 429
`insufficient_quota`, which the app silently turns into an empty completion).

## Resume mechanics (scratchpad `wf_test_run/`)
- `run_clean.sh` — single-instance lock, `python -u`, 60s inter-suite cooldown; order = domain → showcase → insurance upload.
- `run_coding.py` — wrapper remapping stale coding IDs 45/47/48 → live 20/22/23 (committed runner hardcodes stale IDs).
- `poll_credits_resume.sh` — polls OpenAI credits directly; auto-launches `run_clean.sh` on funding (this is what ran the 08-03 pass).
- Rules: **never run suites in parallel; never allow two orchestrators** (a concurrent burst exhausted the account rate/quota earlier).

## Product finding to flag (no fix without approval)
The workflow engine **swallows the OpenAI 429/quota error into an empty (0-token) completion** instead of
surfacing "LLM quota/rate exceeded." This made a credit outage look like the model "produced no answer" and
cost significant diagnosis time. Surfacing provider errors to the workflow result/logs would turn a silent
failure into an obvious one.
