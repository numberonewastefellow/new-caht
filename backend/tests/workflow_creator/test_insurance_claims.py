"""
Insurance Claims Investigation Workflow — Test Suite
=====================================================

Tests the Insurance Claims Investigation workflow with 3 claim scenarios:
  - CL1: Residential kitchen fire — legitimate claim, $180K damage
        Expected: Property Damage Assessor + Policy Coverage Analyst
        Rejected: Auto Reconstructionist, Fraud Investigator, Weather/CAT Analyst
  - CL2: Staged auto rear-end collision — fraud indicators, inflated medical bills
        Expected: Auto Accident Reconstructionist + Fraud Investigator + Medical Claims Reviewer + Coverage
        Rejected: Property Damage Assessor, Weather/CAT Analyst
  - CL3: Hurricane wind/water damage — legitimate, subrogation against HOA for tree
        Expected: Property Damage Assessor + Weather/CAT Analyst + Subrogation Specialist + Coverage
        Rejected: Auto Reconstructionist, Fraud Investigator

Each claim test:
  1. Sends claim details with all available documentation as CSV data
  2. Workflow routes through Triage → Specialist Investigators → Coverage → Settlement
  3. HITL agents (Triage, Medical Reviewer) may pause requesting documents
  4. Test provides follow-up data if paused → specialist resumes → Settlement Writer produces report
  5. Validates: correct specialists engaged, wrong specialists NOT engaged (guard rail),
     expected keywords in settlement report, PythonTool executed

Usage:
    python test_insurance_claims.py                    # Run all tests
    python test_insurance_claims.py --test 1           # Run CL1 only
    python test_insurance_claims.py --test 2           # Run CL2 only
    python test_insurance_claims.py --test 3           # Run CL3 only
    python test_insurance_claims.py --workflow-id 53   # Use specific workflow ID
    python test_insurance_claims.py --url http://host:3000 --key YOUR_KEY
"""

import argparse
import json
import sys
import time
from pathlib import Path

from config import (
    add_common_args,
    api,
    apply_common_args,
    stream_api,
)

# ── Constants ────────────────────────────────────────────────────────────────

WORKFLOW_NAME = "Insurance Claims Investigation"
CLAIMS_DIR = Path(__file__).parent / "test_data" / "insurance_claims"


# ── Claim Data Loader ──────────────────────────────────────────────────────


def load_claim_data(claim_id: str) -> str:
    """Load all CSV data files for a claim and format as a text block.

    Args:
        claim_id: e.g. "CL1", "CL2", "CL3"
    """
    claim_dir = CLAIMS_DIR / claim_id
    if not claim_dir.exists():
        return f"[ERROR] Claim directory not found: {claim_dir}"

    parts = []
    for fpath in sorted(claim_dir.iterdir()):
        if fpath.suffix == ".csv":
            content = fpath.read_text(encoding="utf-8").strip()
            parts.append(f"\n--- {fpath.stem} ---\n{content}")
        elif fpath.suffix == ".json":
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(data, indent=2)}")

    return "\n".join(parts)


# ── Build Test Messages ─────────────────────────────────────────────────────


def build_cl1_message() -> str:
    """CL1: Residential kitchen fire — legitimate claim, $180K damage."""
    data = load_claim_data("CL1")
    return (
        "Please investigate this insurance claim:\n\n"
        "Claim ID: CLM-2025-08742\n"
        "Type: Residential Property - Kitchen Fire\n"
        "Insured: Margaret & Robert Chen, 4821 Oakridge Drive, Naperville, IL 60540\n"
        "Policy: HO-3 Homeowner's, Policy #HWP-2022-445891\n"
        "Date of Loss: 2025-01-15\n\n"
        "Description: Grease fire originated on kitchen stove while insured was cooking. "
        "Fire spread to cabinets, countertops, and ceiling. Smoke damage to adjacent "
        "living room and hallway. Fire department responded within 8 minutes and contained "
        "fire to kitchen. No injuries. Insured has temporary living expenses.\n\n"
        "Estimated claim amount: $180,000\n\n"
        f"Available documentation:\n{data}\n\n"
        "Please perform a complete claims investigation — triage, assess property damage, "
        "verify coverage, check for red flags, and produce a settlement recommendation."
    )


def build_cl2_message() -> str:
    """CL2: Staged auto rear-end collision — fraud indicators."""
    data = load_claim_data("CL2")
    return (
        "Please investigate this insurance claim:\n\n"
        "Claim ID: CLM-2025-11056\n"
        "Type: Auto Accident - Rear-End Collision (3 vehicles)\n"
        "Insured: David Martinez, 2019 Toyota Camry\n"
        "Policy: Auto Policy #AUT-2023-778234\n"
        "Date of Loss: 2025-02-03\n\n"
        "Description: Insured reports being rear-ended at intersection of Elm St & 5th Ave "
        "while stopped at red light, pushed into vehicle ahead. Three vehicles involved. "
        "All three drivers claiming soft-tissue injuries. Police report filed. All claimants "
        "retained attorney within 24 hours. Medical bills totaling $89,400 for chiropractic "
        "treatment (3x/week, 16 weeks) and MRI referrals.\n\n"
        "CRITICAL RED FLAGS identified by initial review:\n"
        "- Attorney pre-retained before medical treatment\n"
        "- Treating provider on SIU watch list\n"
        "- 2 prior claims at same intersection\n"
        "- Social media shows claimant at gym 2 days post-accident\n"
        "- All 3 claimants from same ZIP code\n"
        "- Phone records show calls between 'stranger' drivers before accident\n"
        "- Minimal vehicle damage inconsistent with claimed injuries\n\n"
        "Estimated claim amount: $102,200\n\n"
        f"Available documentation:\n{data}\n\n"
        "Please perform a complete claims investigation — triage, reconstruct accident, "
        "analyze medical claims, investigate fraud indicators, verify coverage, and produce "
        "a settlement recommendation."
    )


def build_cl3_message() -> str:
    """CL3: Hurricane wind/water damage — legitimate, subrogation potential."""
    data = load_claim_data("CL3")
    return (
        "Please investigate this insurance claim:\n\n"
        "Claim ID: CLM-2025-15893\n"
        "Type: Residential Property - Hurricane Wind and Water Damage\n"
        "Insured: James & Patricia Morrison, 1247 Seaside Blvd, Pensacola, FL 32507\n"
        "Policy: HO-3 Homeowner's with Wind/Hail Coverage, Policy #HWP-2024-332156\n"
        "Date of Loss: 2025-09-12 (Hurricane Helene)\n\n"
        "Description: Category 2 hurricane. Sustained winds 96-110 mph with gusts to 130 mph. "
        "Damage includes: 60% of roof shingles torn off, 3 broken windows, fallen trees "
        "(one dead oak from neighbor's property that crushed detached garage), water intrusion "
        "through damaged roof and windows, flooding in ground-floor rooms.\n\n"
        "CRITICAL ISSUE: Policy covers wind and hail but EXCLUDES flood. Must distinguish "
        "wind-driven rain damage (covered) from rising water/flood damage (excluded). "
        "Neighbor's dead oak tree fell on garage — potential subrogation against neighbor/HOA.\n\n"
        "Estimated claim amount: $320,000\n\n"
        f"Available documentation:\n{data}\n\n"
        "Please perform a complete claims investigation — triage, assess property damage, "
        "correlate with weather data, evaluate subrogation potential, determine covered vs "
        "excluded damage, and produce a settlement recommendation."
    )


# ── Test Definitions ─────────────────────────────────────────────────────────

CLAIM_TESTS = [
    {
        "id": 1,
        "name": "CL1: Residential kitchen fire — legitimate claim, $180K damage",
        "mode": "full_investigation",
        "build_message": build_cl1_message,
        "build_followup": None,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "Claims Triage Adjuster",
            "Property Damage Assessor",
            "Policy Coverage Analyst",
            "Settlement Report Writer",
        ],
        "reject_agents": [
            "Auto Accident Reconstructionist",
            "Fraud Investigator",
            "Weather/Catastrophe Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "settlement",
            "coverage",
            "DISCLAIMER",
        ],
        "min_answer_length": 300,
        "purpose": "Validates property fire routing: Triage -> Property Damage Assessor "
                   "(PythonTool for RCV/ACV calculations) -> Coverage Analyst -> Settlement Writer. "
                   "Auto, Fraud, and Weather specialists should NOT be called.",
    },
    {
        "id": 2,
        "name": "CL2: Staged auto accident — fraud indicators, inflated medical bills",
        "mode": "full_investigation",
        "build_message": build_cl2_message,
        "build_followup": None,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "Claims Triage Adjuster",
            "Auto Accident Reconstructionist",
            "Fraud Investigator",
            "Medical Claims Reviewer",
            "Policy Coverage Analyst",
            "Settlement Report Writer",
        ],
        "reject_agents": [
            "Property Damage Assessor",
            "Weather/Catastrophe Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "fraud",
            "coverage",
            "DISCLAIMER",
        ],
        "min_answer_length": 300,
        "purpose": "Validates fraud investigation routing: Triage -> Auto Reconstructionist "
                   "(PythonTool for physics) -> Fraud Investigator (PythonTool for scoring) -> "
                   "Medical Claims Reviewer -> Coverage -> Settlement. "
                   "Property Damage and Weather specialists should NOT be called.",
    },
    {
        "id": 3,
        "name": "CL3: Hurricane wind/water damage — subrogation against HOA for tree",
        "mode": "full_investigation",
        "build_message": build_cl3_message,
        "build_followup": None,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "Claims Triage Adjuster",
            "Property Damage Assessor",
            "Weather/Catastrophe Analyst",
            "Subrogation Specialist",
            "Policy Coverage Analyst",
            "Settlement Report Writer",
        ],
        "reject_agents": [
            "Auto Accident Reconstructionist",
            "Fraud Investigator",
        ],
        "expect_python": True,
        "expected_in_output": [
            "settlement",
            "coverage",
            "exclusion",
            "subrogation",
            "DISCLAIMER",
        ],
        "min_answer_length": 300,
        "purpose": "Validates hurricane routing: Triage -> Property Damage Assessor "
                   "(PythonTool for RCV/ACV) -> Weather/CAT Analyst (PythonTool for weather) -> "
                   "Subrogation Specialist (neighbor's tree) -> Coverage Analyst "
                   "(wind vs flood exclusion) -> Settlement Writer. "
                   "Auto and Fraud specialists should NOT be called.",
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────


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
    """Find the Insurance Claims Investigation workflow by name."""
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"[ERROR] Could not list workflows: {resp.status_code}")
        return None
    for w in resp.json():
        if w["name"] == WORKFLOW_NAME:
            return w["id"]
    return None


def create_chat_session(persona_id: int = 0) -> str | None:
    """Create a chat session and return its UUID."""
    resp = api("POST", "chat/create-chat-session", {"persona_id": persona_id})
    if resp.status_code != 200:
        print(f"[ERROR] Could not create chat session: {resp.status_code} {resp.text[:300]}")
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
                persona = obj.get("persona_name", "?")
                _safe_print(f"\n  [{agent}] (Persona: {persona})")
                print("  " + "-" * 48)

            elif ptype == "workflow_step_delta":
                content = obj.get("content", "")
                if content:
                    all_text_parts.append(content)

            elif ptype == "workflow_pause_for_input":
                result["was_paused"] = True
                result["pause_text"] = obj.get("questions", "")
                step = obj.get("step_name", "?")
                _safe_print(f"\n  {'='*50}")
                _safe_print(f"  [PAUSED] {step} needs more info:")
                _safe_print(f"  {'='*50}")
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


# ── Test Runner ──────────────────────────────────────────────────────────────


def run_claim_test(test_def: dict, workflow_id: int) -> dict:
    """Run a claim investigation test with optional HITL multi-round flow.

    For claim tests (CL1/CL2/CL3), the flow is:
      Round 0: Send initial claim with all documentation -> may pause
      Round 1: If paused, send follow-up documents -> expect completion
    """
    name = test_def["name"]
    test_id = test_def["id"]

    print(f"\n{'='*60}")
    print(f"TEST #{test_id}: {name}")
    print(f"  Mode: {test_def['mode']}")
    print(f"  Expect HITL pause: {test_def.get('expect_hitl_pause', False)}")
    print(f"{'='*60}")

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
    print(f"  Message: \"{msg_preview}...\"")

    # Create chat session for HITL tracking
    chat_session_id = create_chat_session()
    if not chat_session_id:
        return {
            "id": test_id, "name": name, "mode": test_def["mode"],
            "status": "FAIL", "issues": ["Could not create chat session"],
            "duration_s": 0, "agents_run": [], "python_executions": 0,
        }

    # ── Round 0: Initial claim submission ──
    print(f"\n  --- ROUND 0: Initial claim submission ---")
    r0 = run_workflow_stream(workflow_id, message, chat_session_id)
    all_agents.extend(r0["agents_run"])
    total_python += r0["python_executions"]
    total_files.extend(r0["files_generated"])
    total_duration += r0["duration_s"]

    if r0["error"]:
        issues.append(f"Round 0 error: {r0['error']}")

    # ── Round 1: Follow-up if paused ──
    final_result = r0
    if r0["was_paused"] and test_def.get("expect_hitl_pause"):
        build_followup_fn = test_def.get("build_followup")
        if build_followup_fn:
            followup_msg = build_followup_fn()
            print(f"\n  --- ROUND 1: Providing follow-up documentation ---")
            fu_preview = followup_msg[:120].replace("\n", " ")
            print(f"  Follow-up: \"{fu_preview}...\"")

            time.sleep(2)  # Brief pause for DB
            r1 = run_workflow_stream(workflow_id, followup_msg, chat_session_id)
            # Merge agents from round 1
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
        # Specialist didn't pause — OK if workflow still completed correctly
        print("  [INFO] Expected HITL pause but specialist proceeded without requesting documents")

    # ── Validate results ──

    # Check expected agents ran
    for agent in test_def.get("expected_agents", []):
        if agent not in all_agents:
            issues.append(f"Expected agent '{agent}' did not run")

    # GUARD RAIL: Check rejected agents were NOT called
    for agent in test_def.get("reject_agents", []):
        if agent in all_agents:
            issues.append(f"WRONG SPECIALIST: '{agent}' was called but should NOT have been for this claim")

    # Check completion
    if not final_result["completed"] and not final_result["was_paused"]:
        issues.append("Workflow neither completed nor paused")

    # Check final output
    if final_result["completed"]:
        combined_lower = (final_result["final_answer"] + " " + final_result.get("all_text", "")).lower()

        for kw in test_def.get("expected_in_output", []):
            if kw.lower() not in combined_lower:
                issues.append(f"Output missing keyword: '{kw}'")

        if test_def.get("expect_python") and total_python == 0:
            issues.append("Expected Python code execution but none occurred")

        min_len = test_def.get("min_answer_length", 0)
        if min_len > 0 and len(final_result["final_answer"]) < min_len:
            issues.append(
                f"Final answer too short ({len(final_result['final_answer'])} chars, "
                f"expected >= {min_len})"
            )

    # ── Print summary ──
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


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Test the Insurance Claims Investigation workflow",
    )
    parser.add_argument(
        "--test", type=int, nargs="+",
        help="Run specific tests by ID (e.g. --test 1 2)",
    )
    parser.add_argument(
        "--workflow-id", type=int, default=None,
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
            print(f"[ERROR] Workflow '{WORKFLOW_NAME}' not found. Deploy it first:")
            print(f"  python create_workflows.py --file workflows/26_insurance_claims.json")
            sys.exit(1)

    print(f"  Using workflow ID={workflow_id}")

    # Build test list
    tests_to_run = []

    if args.test:
        all_tests = {t["id"]: t for t in CLAIM_TESTS}
        for tid in args.test:
            if tid in all_tests:
                tests_to_run.append(all_tests[tid])
            else:
                print(f"[WARN] Test #{tid} not found")
    else:
        tests_to_run = CLAIM_TESTS[:]

    if not tests_to_run:
        print("[ERROR] No tests to run")
        sys.exit(1)

    print(f"\n{'#'*60}")
    print(f"  INSURANCE CLAIMS INVESTIGATION WORKFLOW TEST SUITE")
    print(f"  Running {len(tests_to_run)} test(s)")
    print(f"{'#'*60}")

    # Run tests
    results = []
    for test_def in tests_to_run:
        r = run_claim_test(test_def, workflow_id)
        results.append(r)

    # ── Summary ──
    print(f"\n\n{'='*60}")
    print(f"TEST RESULTS SUMMARY")
    print(f"{'='*60}")

    passed = 0
    failed = 0
    for r in results:
        tag = "[OK]" if r["status"] == "PASS" else "[FAIL]"
        agents_str = f"agents={len(r['agents_run'])}"
        py_str = f"py={r['python_executions']}" if r["python_executions"] else ""
        extras = "  ".join(filter(None, [agents_str, py_str]))
        print(f"  {tag} #{r['id']} {r['name']:<60} {r['duration_s']}s  {extras}")
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
    print(f"{'='*60}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
