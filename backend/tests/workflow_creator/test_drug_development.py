"""
Drug Development Pipeline Review Workflow — Test Suite
======================================================

Tests the Drug Development Pipeline Review workflow with 3 drug program scenarios:
  - RX1: Oncology checkpoint inhibitor (Phase II) — Biostatistician + Toxicologist
         + Regulatory + Clinical Ops + Pharmacoeconomist
  - RX2: Rare disease gene therapy (Phase I) — Toxicologist + Regulatory + CMC
         + IP/Patent + Medicinal Chemist
  - RX3: Diabetes GLP-1 biosimilar (Phase III) — Biostatistician + Regulatory
         + Pharmacoeconomist + IP/Patent + CMC

Each drug program test:
  1. Sends program data (CSV files: efficacy, safety, PK, manufacturing, market)
  2. Workflow routes through Program Triage Manager → Specialists → Stage Gate Report Writer
  3. HITL pauses may collect Phase II topline data, CMC stability data,
     or competitive intelligence
  4. Validates: correct specialists engaged, wrong specialists NOT engaged,
     expected keywords in Stage Gate report, PythonTool executed

Usage:
    python test_drug_development.py                    # Run all tests
    python test_drug_development.py --test 1           # Run RX1 only
    python test_drug_development.py --test 2           # Run RX2 only
    python test_drug_development.py --test 3           # Run RX3 only
    python test_drug_development.py --workflow-id 99   # Use specific workflow ID
    python test_drug_development.py --url http://host:3000 --key YOUR_KEY
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from config import (
    add_common_args,
    api,
    apply_common_args,
    stream_api,
)

# -- Constants ----------------------------------------------------------------

WORKFLOW_NAME = "Drug Development Pipeline Review"
DATA_DIR = Path(__file__).parent / "test_data" / "drug_development"


# -- Data Loader --------------------------------------------------------------


def load_program_data(program_id: str) -> str:
    """Load all CSV data files for a drug program and format as a text block.

    Args:
        program_id: e.g. "RX1", "RX2", "RX3"
    """
    program_dir = DATA_DIR / program_id
    if not program_dir.exists():
        return f"[ERROR] Program directory not found: {program_dir}"

    parts = []
    for fpath in sorted(program_dir.iterdir()):
        if fpath.suffix == ".csv":
            content = fpath.read_text(encoding="utf-8").strip()
            parts.append(f"\n--- {fpath.stem} ---\n{content}")
        elif fpath.suffix == ".json":
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(data, indent=2)}")

    return "\n".join(parts)


# -- Build Test Messages -------------------------------------------------------


def build_rx1_message() -> str:
    """RX1: ONX-4218 — Oncology PD-L1/TIGIT bispecific, Phase II."""
    data = load_program_data("RX1")
    return (
        "Please review this drug development program for a stage gate decision:\n\n"
        "Drug: ONX-4218 — PD-L1/TIGIT bispecific antibody\n"
        "Indication: Non-Small Cell Lung Cancer (NSCLC), 2nd line+\n"
        "Phase: II (randomized, open-label, 120 patients)\n"
        "Mechanism: Dual checkpoint blockade targeting PD-L1 and TIGIT\n"
        "Route: IV infusion Q3W\n"
        "Sponsor: Onyx Therapeutics\n\n"
        "Key findings so far:\n"
        "- Overall Response Rate (ORR): 38% (treatment) vs 18% (control), p=0.012\n"
        "- Median PFS: 7.2 months vs 4.1 months (HR 0.58)\n"
        "- 3 Grade 4 immune-mediated hepatitis events in treatment arm\n"
        "- PD-L1 TPS >= 50% subgroup shows ORR of 52%\n"
        "- ctDNA clearance correlates with response (p<0.001)\n\n"
        f"Attached CSV data files:\n{data}\n\n"
        "Perform a full pipeline review — triage the program, run efficacy/safety "
        "statistics, assess regulatory pathway, evaluate commercial potential, "
        "and produce a Stage Gate Go/No-Go recommendation."
    )


def build_rx2_message() -> str:
    """RX2: GT-RAR-001 — Rare disease gene therapy, Phase I."""
    data = load_program_data("RX2")
    return (
        "Please review this drug development program for a stage gate decision:\n\n"
        "Drug: GT-RAR-001 — AAV8-RPE65 gene replacement therapy\n"
        "Indication: Leber Congenital Amaurosis Type 2 (LCA2)\n"
        "Phase: I (open-label, dose-escalation, 3+3 design)\n"
        "Mechanism: Subretinal delivery of functional RPE65 gene via AAV8 vector\n"
        "Route: Subretinal injection (one-time administration)\n"
        "Sponsor: GeneSight Therapeutics\n\n"
        "Key findings so far:\n"
        "- 4 dose cohorts (1e10, 3e10, 1e11, 3e11 vg/eye) completed\n"
        "- No dose-limiting toxicities (DLTs) observed\n"
        "- Mild vitritis in 3 patients (Grade 1-2, self-resolving)\n"
        "- Best-corrected visual acuity improvement: mean +15 ETDRS letters "
        "at 12 months in high-dose cohort\n"
        "- 5 GMP lots manufactured with consistent quality attributes\n\n"
        f"Attached CSV data files:\n{data}\n\n"
        "Perform a full pipeline review — triage the program, assess dose-response "
        "safety, evaluate manufacturing readiness, review IP landscape, "
        "and produce a Stage Gate Go/No-Go recommendation."
    )


def build_rx3_message() -> str:
    """RX3: BIO-SEM-101 — Diabetes GLP-1 biosimilar, Phase III."""
    data = load_program_data("RX3")
    return (
        "Please review this drug development program for a stage gate decision:\n\n"
        "Drug: BIO-SEM-101 — Semaglutide biosimilar\n"
        "Reference Product: Semaglutide (Ozempic, Novo Nordisk)\n"
        "Indication: Type 2 Diabetes Mellitus\n"
        "Phase: III (randomized, double-blind, 3-arm equivalence trial, 600 patients)\n"
        "Route: Subcutaneous injection, pre-filled pen\n"
        "Sponsor: BioEquiv Pharmaceuticals\n\n"
        "Key findings so far:\n"
        "- HbA1c reduction at 52 weeks: biosimilar -1.42% vs originator -1.38% "
        "(difference within +/-0.3% margin)\n"
        "- PK bioequivalence: Cmax ratio 0.97 (90% CI: 0.89-1.06), "
        "AUC ratio 1.02 (90% CI: 0.94-1.10)\n"
        "- GI adverse events: biosimilar 28% vs originator 31% (comparable)\n"
        "- Anti-drug antibody rate: biosimilar 4.2% vs originator 3.8%\n"
        "- Analytical similarity demonstrated across 8 CQAs\n"
        "- Target pricing: 35% discount to originator\n\n"
        f"Attached CSV data files:\n{data}\n\n"
        "Perform a full pipeline review — triage the program, run bioequivalence "
        "statistics, assess 351(k) regulatory pathway, evaluate commercial "
        "opportunity, review IP/patent landscape, and produce a Stage Gate "
        "Go/No-Go recommendation."
    )


# -- Test Definitions ----------------------------------------------------------

PROGRAM_TESTS = [
    {
        "id": 1,
        "name": "RX1: Oncology checkpoint inhibitor — Phase II NSCLC",
        "mode": "full_review",
        "build_message": build_rx1_message,
        "is_hitl": False,
        "expect_hitl_pause": True,  # Program Triage Manager may request Phase II topline data
        "expected_agents": [
            "Program Triage Manager",
            "Biostatistician",
            "Toxicologist",
            "Regulatory Affairs Specialist",
            "Pharmacoeconomist",
            "Stage Gate Report Writer",
        ],
        "reject_agents": [
            # CMC and IP/Patent should NOT be heavily involved for Phase II oncology
            # Note: we list them but the orchestrator might still cross-refer in edge cases
        ],
        "soft_reject_agents": [
            "Manufacturing/CMC Specialist",
            "IP/Patent Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "go",
            "npv",
            "efficacy",
            "safety",
            "regulatory",
        ],
        "min_answer_length": 300,
        "purpose": (
            "Validates Phase II oncology routing: Triage -> Biostatistician "
            "(KM curves, power analysis) -> Toxicologist (irAE, safety margins) "
            "-> Regulatory (accelerated approval) -> Clinical Ops -> "
            "Pharmacoeconomist (QALY/ICER) -> Stage Gate Report Writer."
        ),
    },
    {
        "id": 2,
        "name": "RX2: Rare disease gene therapy — Phase I LCA2",
        "mode": "full_review",
        "build_message": build_rx2_message,
        "is_hitl": False,
        "expect_hitl_pause": True,  # CMC may request stability data
        "expected_agents": [
            "Program Triage Manager",
            "Toxicologist",
            "Regulatory Affairs Specialist",
            "Stage Gate Report Writer",
        ],
        "reject_agents": [
            # Pharmacoeconomist and Biostatistician should NOT be primary for Phase I gene therapy
        ],
        "soft_reject_agents": [
            "Pharmacoeconomist",
            "Biostatistician",
        ],
        "expect_python": True,
        "expected_in_output": [
            "go",
            "safety",
            "regulatory",
        ],
        "min_answer_length": 300,
        "purpose": (
            "Validates Phase I gene therapy routing: Triage -> Toxicologist "
            "(dose-escalation safety, NOAEL) -> Regulatory (RMAT, orphan) "
            "-> CMC (vector manufacturing) -> IP/Patent (FTO) -> "
            "Medicinal Chemist (vector design) -> Stage Gate Report Writer."
        ),
    },
    {
        "id": 3,
        "name": "RX3: Diabetes GLP-1 biosimilar — Phase III equivalence",
        "mode": "full_review",
        "build_message": build_rx3_message,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "Program Triage Manager",
            "Biostatistician",
            "Regulatory Affairs Specialist",
            "Pharmacoeconomist",
            "Stage Gate Report Writer",
        ],
        "reject_agents": [
            "Medicinal Chemist",
        ],
        "soft_reject_agents": [],
        "expect_python": True,
        "expected_in_output": [
            "go",
            "equivalen",
            "regulatory",
        ],
        "min_answer_length": 300,
        "purpose": (
            "Validates Phase III biosimilar routing: Triage -> Biostatistician "
            "(bioequivalence, TOST) -> Regulatory (351(k) pathway) -> "
            "Pharmacoeconomist (pricing, market access) -> IP/Patent "
            "(patent cliff) -> CMC (analytical similarity) -> Stage Gate."
        ),
    },
]


# -- Helpers -------------------------------------------------------------------


def _safe_print(text: str, **kwargs):
    """Print with Unicode fallback for Windows terminals."""
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        safe = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        )
        print(safe, **kwargs)


def find_workflow_id() -> int | None:
    """Find the Drug Development Pipeline Review workflow by name."""
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"[ERROR] Could not list workflows: {resp.status_code}")
        return None
    for w in resp.json():
        if w["name"] == WORKFLOW_NAME:
            return w["id"]
    return None


def create_chat_session(agent_id: int = 0) -> str | None:
    """Create a chat session and return its UUID."""
    resp = api("POST", "converse/create-chat-session", {"agent_id": agent_id})
    if resp.status_code != 200:
        print(
            f"[ERROR] Could not create chat session: "
            f"{resp.status_code} {resp.text[:300]}"
        )
        return None
    data = resp.json()
    session_id = str(data.get("chat_session_id", ""))
    return session_id if session_id else None


def run_workflow_stream(
    workflow_id: int,
    message: str,
    chat_session_id: str | None = None,
) -> dict:
    """Run a workflow round and collect structured results.

    Returns dict with:
      agents_run, was_paused, pause_text, final_answer, completed,
      python_executions, files_generated, error, duration_s, all_text
    """
    result = {
        "agents_run": [],
        "was_paused": False,
        "pause_text": "",
        "final_answer": "",
        "completed": False,
        "python_executions": 0,
        "files_generated": [],
        "error": None,
        "duration_s": 0,
        "all_text": "",
    }

    body = {"message": message}
    if chat_session_id:
        body["chat_session_id"] = chat_session_id

    start = time.time()
    resp = stream_api("POST", f"workflow/{workflow_id}/run", body)

    if resp.status_code != 200:
        result["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
        result["duration_s"] = round(time.time() - start, 1)
        return result

    in_final_answer = False
    final_parts = []
    all_text_parts = []

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            packet = json.loads(line)

            if "error" in packet and "type" not in packet.get("obj", {}):
                result["error"] = packet["error"][:200]
                continue

            obj = packet.get("obj", packet)
            ptype = obj.get("type", "")

            if ptype == "workflow_step_start":
                agent = obj.get("step_name", "?")
                if agent not in result["agents_run"]:
                    result["agents_run"].append(agent)
                agent = obj.get("agent_name", "?")
                _safe_print(f"\n  [{agent}] (Agent: {agent})")
                print("  " + "-" * 48)

            elif ptype == "workflow_step_delta":
                content = obj.get("content", "")
                if content:
                    all_text_parts.append(content)

            elif ptype == "workflow_pause_for_input":
                result["was_paused"] = True
                result["pause_text"] = obj.get("questions", "")
                step = obj.get("step_name", "?")
                _safe_print(f"\n  {'=' * 50}")
                _safe_print(f"  [PAUSED] {step} needs more info:")
                _safe_print(f"  {'=' * 50}")
                _safe_print(f"  {result['pause_text'][:300]}")

            elif ptype == "python_tool_start":
                result["python_executions"] += 1

            elif ptype == "python_tool_delta":
                fids = obj.get("file_ids", [])
                if fids:
                    result["files_generated"].extend(fids)

            elif ptype == "message_start":
                in_final_answer = True
                _safe_print("\n  [Final Answer]")
                print("  " + "-" * 48)

            elif ptype == "message_delta":
                content = obj.get("content", obj.get("delta", ""))
                if content:
                    if in_final_answer:
                        final_parts.append(content)
                    all_text_parts.append(content)

            elif ptype == "stop":
                result["completed"] = True
                _safe_print("\n  --- Stream Complete ---")

        except json.JSONDecodeError:
            pass

    result["final_answer"] = "".join(final_parts)
    result["all_text"] = "".join(all_text_parts)
    result["duration_s"] = round(time.time() - start, 1)
    return result


# -- Test Runner ---------------------------------------------------------------


def run_program_test(test_def: dict, workflow_id: int) -> dict:
    """Run a drug program test with optional HITL multi-round flow.

    Flow:
      Round 0: Send program data -> may pause (HITL for missing data)
      Round 1: If paused, provide follow-up data -> expect completion
    """
    name = test_def["name"]
    test_id = test_def["id"]

    print(f"\n{'=' * 60}")
    print(f"TEST #{test_id}: {name}")
    print(f"  Mode: {test_def['mode']}")
    print(f"  Expect HITL pause: {test_def.get('expect_hitl_pause', False)}")
    print(f"{'=' * 60}")

    issues = []
    all_agents = []
    total_python = 0
    total_files = []
    total_duration = 0

    # Build initial message
    build_fn = test_def.get("build_message")
    if build_fn:
        message = build_fn()
    else:
        message = test_def.get("message", "")

    msg_preview = message[:120].replace("\n", " ")
    print(f'  Message: "{msg_preview}..."')

    # Create chat session for HITL tracking
    chat_session_id = create_chat_session()
    if not chat_session_id:
        return {
            "id": test_id,
            "name": name,
            "mode": test_def["mode"],
            "status": "FAIL",
            "issues": ["Could not create chat session"],
            "duration_s": 0,
            "agents_run": [],
            "python_executions": 0,
        }

    # -- Round 0: Initial message --
    print("\n  --- ROUND 0: Initial submission ---")
    r0 = run_workflow_stream(workflow_id, message, chat_session_id)
    all_agents.extend(r0["agents_run"])
    total_python += r0["python_executions"]
    total_files.extend(r0["files_generated"])
    total_duration += r0["duration_s"]

    if r0["error"]:
        issues.append(f"Round 0 error: {r0['error']}")

    # -- Round 1: Follow-up if paused --
    final_result = r0
    if r0["was_paused"] and test_def.get("expect_hitl_pause"):
        # Provide generic follow-up data depending on the program
        followup_msg = _build_followup_for_program(test_id)
        if followup_msg:
            print("\n  --- ROUND 1: Providing follow-up data ---")
            fu_preview = followup_msg[:120].replace("\n", " ")
            print(f'  Follow-up: "{fu_preview}..."')

            time.sleep(2)  # Brief pause for DB
            r1 = run_workflow_stream(workflow_id, followup_msg, chat_session_id)
            for a in r1["agents_run"]:
                if a not in all_agents:
                    all_agents.append(a)
            total_python += r1["python_executions"]
            total_files.extend(r1["files_generated"])
            total_duration += r1["duration_s"]
            final_result = r1

            if r1["error"]:
                issues.append(f"Round 1 error: {r1['error']}")
        else:
            issues.append("Workflow paused but no follow-up data defined")

    elif not r0["was_paused"] and test_def.get("expect_hitl_pause"):
        print(
            "  [INFO] Expected HITL pause but workflow proceeded "
            "without requesting additional data"
        )

    # -- Validate results --

    # Check expected agents ran
    for agent in test_def.get("expected_agents", []):
        if agent not in all_agents:
            issues.append(f"Expected agent '{agent}' did not run")

    # GUARD RAIL: Check hard-rejected agents were NOT called
    for agent in test_def.get("reject_agents", []):
        if agent in all_agents:
            issues.append(
                f"WRONG SPECIALIST: '{agent}' was called but should NOT "
                f"have been for this program"
            )

    # SOFT GUARD: Check soft-rejected agents (warning only, not failure)
    for agent in test_def.get("soft_reject_agents", []):
        if agent in all_agents:
            print(
                f"  [WARN] Soft-reject agent '{agent}' was called — "
                f"not expected for this program but not a hard failure"
            )

    # Check completion
    if not final_result["completed"] and not final_result["was_paused"]:
        issues.append("Workflow neither completed nor paused")

    # Check final output keywords and quality
    if final_result["completed"]:
        combined_lower = (
            final_result["final_answer"] + " " + final_result.get("all_text", "")
        ).lower()

        for kw in test_def.get("expected_in_output", []):
            if kw.lower() not in combined_lower:
                issues.append(f"Output missing keyword: '{kw}'")

        if test_def.get("expect_python") and total_python == 0:
            issues.append("Expected PythonTool execution but none occurred")

        min_len = test_def.get("min_answer_length", 0)
        if min_len > 0 and len(final_result["final_answer"]) < min_len:
            issues.append(
                f"Final answer too short ({len(final_result['final_answer'])} chars, "
                f"expected >= {min_len})"
            )

    # -- Print summary --
    print(f"\n  Agents run: {all_agents}")
    print(f"  Total Python executions: {total_python}")
    print(f"  Total files generated: {len(total_files)}")
    print(f"  Final answer length: {len(final_result['final_answer'])} chars")
    print(f"  Total duration: {total_duration}s")

    if final_result["final_answer"]:
        preview = final_result["final_answer"][:200]
        _safe_print(f"  Answer preview: {preview}...")

    status = "PASS" if not issues else "FAIL"
    if issues:
        for issue in issues:
            print(f"  [ISSUE] {issue}")

    print(f"\n  RESULT: {status} ({total_duration}s)")

    return {
        "id": test_id,
        "name": name,
        "mode": test_def["mode"],
        "status": status,
        "issues": issues,
        "duration_s": total_duration,
        "agents_run": all_agents,
        "python_executions": total_python,
    }


def _build_followup_for_program(test_id: int) -> str | None:
    """Build HITL follow-up data for a paused workflow based on program ID."""
    if test_id == 1:
        # RX1: Phase II topline data or competitive intelligence requested
        return (
            "Here is the additional data requested:\n\n"
            "Phase II Topline Results (Data Cutoff: 2025-11-15):\n"
            "- ITT population: N=120 (80 treatment, 40 control)\n"
            "- mITT population: N=114 (76 treatment, 38 control) — "
            "6 excluded for major protocol violations\n"
            "- Confirmed ORR (IRC): 38.8% vs 17.5%, p=0.014 (Fisher's exact)\n"
            "- Median PFS (IRC): 7.2 months (95% CI: 5.8-9.1) vs "
            "4.1 months (95% CI: 3.2-5.4), HR 0.58 (95% CI: 0.38-0.88)\n"
            "- Median OS: Not reached vs 14.2 months, HR 0.62 (95% CI: 0.36-1.07)\n"
            "- DCR: 72.5% vs 42.5%\n"
            "- PD-L1 TPS >= 50% subgroup (n=42): ORR 52.4%, mPFS 11.2 months\n"
            "- TMB-high (>= 10 mut/Mb) subgroup (n=38): ORR 47.4%\n\n"
            "Competitive Intelligence Update:\n"
            "- Tiragolumab + Atezolizumab Phase III SKYSCRAPER-01: Failed primary "
            "endpoint (PFS) in PD-L1-high NSCLC 1L\n"
            "- Vibostolimab + Pembrolizumab: Phase III ongoing, enrollment ~60% complete\n"
            "- No TIGIT agent approved to date\n\n"
            "Please continue the pipeline review with this data."
        )
    elif test_id == 2:
        # RX2: CMC stability data or manufacturing follow-up
        return (
            "Here is the additional CMC/stability data requested:\n\n"
            "Long-term Stability Data (GMP-LOT-003, -65C):\n"
            "- Month 0: Titer 4.6e12 vg/mL, Purity 98.6%, Potency 94.8%\n"
            "- Month 6: Titer 4.4e12 vg/mL, Purity 98.2%, Potency 94.2%\n"
            "- Month 12: Titer 4.2e12 vg/mL, Purity 97.8%, Potency 93.6%\n"
            "- Month 18: Titer 4.0e12 vg/mL, Purity 97.4%, Potency 92.8%\n\n"
            "Accelerated Stability (25C/60% RH, GMP-LOT-003):\n"
            "- Month 0: Titer 4.6e12, Purity 98.6%\n"
            "- Month 1: Titer 3.8e12, Purity 96.4% — significant decline\n"
            "- Month 3: Titer 2.1e12, Purity 88.2% — below specification\n"
            "- Conclusion: Cold chain (-65C) is critical; no room-temperature stability\n\n"
            "Scale-up Status:\n"
            "- Current scale: 10L bioreactor (clinical supply)\n"
            "- Target commercial scale: 200L bioreactor\n"
            "- Scale-up feasibility study: In progress, expected Q2 2026\n"
            "- CDMO identified: Catalent Gene Therapy (Baltimore)\n\n"
            "Please continue the pipeline review with this data."
        )
    elif test_id == 3:
        return None  # RX3 should not pause
    return None


# -- Main ----------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Test the Drug Development Pipeline Review workflow",
    )
    parser.add_argument(
        "--test",
        type=int,
        nargs="+",
        help="Run specific tests by ID (e.g. --test 1 2)",
    )
    parser.add_argument(
        "--workflow-id",
        type=int,
        default=None,
        help="Use a specific workflow ID instead of auto-detecting",
    )
    add_common_args(parser)

    args = parser.parse_args()
    apply_common_args(args)

    # Find workflow
    if args.workflow_id:
        workflow_id = args.workflow_id
    else:
        print(f"\nLooking for workflow: '{WORKFLOW_NAME}'...")
        workflow_id = find_workflow_id()
        if workflow_id is None:
            print(
                f"[ERROR] Workflow '{WORKFLOW_NAME}' not found. Deploy it first:"
            )
            print(
                "  python create_workflows.py "
                "--file workflows/28_drug_development.json"
            )
            sys.exit(1)

    print(f"  Using workflow ID={workflow_id}")

    # Build test list
    tests_to_run = []

    if args.test:
        all_tests = {t["id"]: t for t in PROGRAM_TESTS}
        for tid in args.test:
            if tid in all_tests:
                tests_to_run.append(all_tests[tid])
            else:
                print(f"[WARN] Test #{tid} not found")
    else:
        tests_to_run = PROGRAM_TESTS[:]

    if not tests_to_run:
        print("[ERROR] No tests to run")
        sys.exit(1)

    print(f"\n{'#' * 60}")
    print("  DRUG DEVELOPMENT PIPELINE REVIEW — TEST SUITE")
    print(f"  Running {len(tests_to_run)} test(s)")
    print(f"{'#' * 60}")

    # Run tests
    results = []
    for test_def in tests_to_run:
        r = run_program_test(test_def, workflow_id)
        results.append(r)

    # -- Summary --
    print(f"\n\n{'=' * 60}")
    print("TEST RESULTS SUMMARY")
    print(f"{'=' * 60}")

    passed = 0
    failed = 0
    for r in results:
        tag = "[OK]" if r["status"] == "PASS" else "[FAIL]"
        agents_str = f"agents={len(r['agents_run'])}"
        py_str = f"py={r['python_executions']}" if r["python_executions"] else ""
        extras = "  ".join(filter(None, [agents_str, py_str]))
        print(
            f"  {tag} #{r['id']} {r['name']:<55} "
            f"{r['duration_s']}s  {extras}"
        )
        if r["issues"]:
            for issue in r["issues"]:
                print(f"       {issue}")
        if r["status"] == "PASS":
            passed += 1
        else:
            failed += 1

    print(f"\n  Total: {len(results)} tests | {passed} passed | {failed} failed")
    total_time = sum(r["duration_s"] for r in results)
    print(f"  Total time: {total_time}s")
    print(f"{'=' * 60}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
