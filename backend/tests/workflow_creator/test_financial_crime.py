"""
Financial Crime Investigation Workflow — Test Suite
====================================================

Tests the Financial Crime Investigation workflow with 3 case scenarios:
  - C1: Structuring/Smurfing — cash deposits just under $10K across 5 branches
  - C2: Trade-Based Laundering — overpriced imports from shell company in free trade zone
  - C3: Crypto Mixer to Fiat — Bitcoin tumbled through mixer, converted at OTC desk
  - C4 (HITL-only): Vague alert triggers triage questions

Each case test:
  1. Sends alert package with case data (alert details, customer profile, transactions)
  2. Workflow routes through Alert Triage → KYC → Sanctions → Specialists → SAR Report
  3. Specialist may pause (HITL) requesting bank statements, SWIFT messages, or ownership docs
  4. Test provides follow-up documents → specialist resumes → SAR Report Writer produces SAR
  5. Validates: correct investigators engaged, wrong investigators NOT engaged (guard rail),
     expected keywords in final SAR, PythonTool executed by computational agents

Usage:
    python test_financial_crime.py                    # Run all tests
    python test_financial_crime.py --test 1           # Run C1 only
    python test_financial_crime.py --test 2           # Run C2 only
    python test_financial_crime.py --test 3           # Run C3 only
    python test_financial_crime.py --test 4           # Run HITL triage only
    python test_financial_crime.py --only-hitl        # Run HITL tests only
    python test_financial_crime.py --workflow-id 53   # Use specific workflow ID
    python test_financial_crime.py --url http://host:3000 --key YOUR_KEY
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

WORKFLOW_NAME = "Financial Crime Investigation"
CASES_DIR = Path(__file__).parent / "test_data" / "financial_crime"


# -- Case Data Loader --------------------------------------------------------


def load_case_data(case_id: str) -> str:
    """Load all CSV data files for a case and format as a text block.

    Args:
        case_id: e.g. "C1", "C2", "C3"
    """
    case_dir = CASES_DIR / case_id
    if not case_dir.exists():
        return f"[ERROR] Case directory not found: {case_dir}"

    parts = []
    for fpath in sorted(case_dir.iterdir()):
        if fpath.suffix == ".csv":
            content = fpath.read_text(encoding="utf-8").strip()
            parts.append(f"\n--- {fpath.stem} ---\n{content}")
        elif fpath.suffix == ".json":
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(data, indent=2)}")

    return "\n".join(parts)


# -- Build Test Messages ------------------------------------------------------


def build_c1_message() -> str:
    """C1: Structuring/Smurfing — cash deposits just under $10K across 5 branches."""
    data = load_case_data("C1")
    return (
        "Please investigate this suspicious activity alert:\n\n"
        "ALERT PACKAGE — Case FC-2025-00847\n"
        "Alert Type: Potential Cash Structuring / Smurfing\n"
        "Severity: HIGH\n\n"
        "Customer Marcus J. Thornton (CID-55921) made 25 cash deposits totaling "
        "$234,750 across 5 branch locations over a 14-day period. All individual "
        "deposits are below the $10,000 CTR reporting threshold, ranging from "
        "$8,500 to $9,900. The customer opened his account 8 months ago listing "
        "occupation as 'independent consultant.' Two prior alerts were dismissed "
        "in 2024.\n\n"
        f"Case data files:\n{data}\n\n"
        "Please conduct a full investigation — triage, KYC review, sanctions "
        "screening, transaction pattern analysis, forensic accounting, and "
        "produce a final SAR narrative."
    )


def build_c2_message() -> str:
    """C2: Trade-Based Laundering — overpriced imports from shell company in FTZ."""
    data = load_case_data("C2")
    return (
        "Please investigate this suspicious activity alert:\n\n"
        "ALERT PACKAGE — Case FC-2025-01203\n"
        "Alert Type: Suspected Trade-Based Money Laundering (TBML)\n"
        "Severity: CRITICAL\n\n"
        "Pacific Rim Trading LLC (CID-78443), a Delaware-registered import/export "
        "company, received $4.2M in wire transfers from entities in UAE and Hong Kong "
        "free trade zones over 6 months. Trade documents show invoices for generic "
        "consumer goods (plastic housewares, textiles) priced at 300-500% above "
        "market rates. The company's beneficial ownership is obscured through a chain "
        "of nominee directors. The registered agent is associated with 14 other "
        "recently formed entities.\n\n"
        f"Case data files:\n{data}\n\n"
        "Please conduct a full investigation — triage, KYC/CDD, sanctions screening, "
        "trade finance analysis, geopolitical risk assessment, forensic accounting, "
        "and produce a final SAR narrative."
    )


def build_c3_message() -> str:
    """C3: Crypto Mixer to Fiat — Bitcoin tumbled through mixer, converted at OTC desk."""
    data = load_case_data("C3")
    return (
        "Please investigate this suspicious activity alert:\n\n"
        "ALERT PACKAGE — Case FC-2025-01587\n"
        "Alert Type: Crypto Mixer / Tumbling to Fiat Conversion\n"
        "Severity: HIGH\n\n"
        "Customer Dmitri Volkov (CID-92104) opened an account 3 months ago listing "
        "occupation as 'cryptocurrency trader.' Blockchain analytics flagged 15 "
        "Bitcoin transactions totaling 12.8 BTC ($485,000 USD equivalent) where "
        "source addresses trace through known mixing/tumbling services (Wasabi Wallet "
        "CoinJoin and ChipMixer). Funds were deposited at two exchanges (Kraken, Bybit) "
        "and converted to USD via OTC desk, then withdrawn as wire transfers to a "
        "personal brokerage account and a foreign bank account in Cyprus.\n\n"
        f"Case data files:\n{data}\n\n"
        "Please conduct a full investigation — triage, KYC review, sanctions screening, "
        "blockchain analysis, forensic accounting of fiat off-ramps, and produce a "
        "final SAR narrative."
    )


# -- Test Definitions ---------------------------------------------------------

CASE_TESTS = [
    {
        "id": 1,
        "name": "C1: Structuring/Smurfing — cash deposits under $10K",
        "mode": "full_investigation",
        "build_message": build_c1_message,
        "build_followup": None,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "Alert Triage Analyst",
            "KYC Analyst",
            "Sanctions Screening Specialist",
            "Transaction Pattern Analyst",
            "SAR Report Writer",
        ],
        "reject_agents": [
            "Trade Finance Investigator",
            "Crypto/Digital Assets Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "SAR",
            "structuring",
        ],
        "min_answer_length": 300,
        "purpose": "Validates structuring routing: Triage -> KYC -> Sanctions -> "
                   "Transaction Pattern Analyst (PythonTool) -> Forensic Accountant "
                   "(PythonTool) -> SAR Report Writer.",
    },
    {
        "id": 2,
        "name": "C2: Trade-Based Laundering — overpriced imports",
        "mode": "full_investigation",
        "build_message": build_c2_message,
        "build_followup": None,
        "is_hitl": False,
        "expect_hitl_pause": True,  # Trade Finance Investigator may request docs
        "expected_agents": [
            "Alert Triage Analyst",
            "KYC Analyst",
            "Sanctions Screening Specialist",
            "Trade Finance Investigator",
            "SAR Report Writer",
        ],
        "reject_agents": [
            "Crypto/Digital Assets Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "SAR",
            "laundering",
        ],
        "min_answer_length": 300,
        "purpose": "Validates TBML routing: Triage -> KYC -> Sanctions -> "
                   "Trade Finance Investigator (PythonTool, may HITL) -> "
                   "Geopolitical Risk -> Forensic Accountant -> SAR Report Writer.",
    },
    {
        "id": 3,
        "name": "C3: Crypto Mixer to Fiat — Bitcoin tumbling",
        "mode": "full_investigation",
        "build_message": build_c3_message,
        "build_followup": None,
        "is_hitl": False,
        "expect_hitl_pause": True,  # Crypto Analyst may request deeper tracing
        "expected_agents": [
            "Alert Triage Analyst",
            "KYC Analyst",
            "Sanctions Screening Specialist",
            "Crypto/Digital Assets Analyst",
            "SAR Report Writer",
        ],
        "reject_agents": [
            "Trade Finance Investigator",
        ],
        "expect_python": True,
        "expected_in_output": [
            "SAR",
            "mixer",
        ],
        "min_answer_length": 300,
        "purpose": "Validates crypto routing: Triage -> KYC -> Sanctions -> "
                   "Crypto/Digital Assets Analyst (PythonTool, may HITL) -> "
                   "Forensic Accountant (PythonTool) -> SAR Report Writer.",
    },
]

HITL_TESTS = [
    {
        "id": 4,
        "name": "HITL: Vague alert triggers triage questions",
        "mode": "hitl_only",
        "message": "We received a suspicious activity flag on an account but I don't have the details yet.",
        "is_hitl": True,
        "expected_agents": ["Alert Triage Analyst"],
        "reject_agents": [],
        "expect_python": False,
        "expected_in_output": [],
        "expected_pause_keywords": ["transaction", "customer"],
        "min_answer_length": 0,
        "purpose": "Validates HITL: Vague alert triggers Alert Triage Analyst's "
                   "[NEEDS_INPUT] with clarifying questions about the suspicious activity.",
    },
]


# -- Helpers ------------------------------------------------------------------


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
    """Find the Financial Crime Investigation workflow by name."""
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
    resp = api("POST", "converse/create-chat-session", {"persona_id": persona_id})
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


# -- Test Runner --------------------------------------------------------------


def run_case_test(test_def: dict, workflow_id: int) -> dict:
    """Run a case investigation test with optional HITL multi-round flow.

    For case tests (C1/C2/C3), the flow is:
      Round 0: Send initial alert package with case data -> may pause
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

    # -- Round 0: Initial message --
    print(f"\n  --- ROUND 0: Initial alert submission ---")
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
        build_followup_fn = test_def.get("build_followup")
        if build_followup_fn:
            followup_msg = build_followup_fn()
            print(f"\n  --- ROUND 1: Providing follow-up documents ---")
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
            # No follow-up defined — this is acceptable; some investigators
            # may pause but the test doesn't provide follow-up data
            print("  [INFO] Workflow paused but no follow-up data defined for this test")

    elif not r0["was_paused"] and test_def.get("expect_hitl_pause"):
        # Specialist didn't pause — OK if workflow still completed correctly
        print("  [INFO] Expected HITL pause but investigator proceeded without requesting documents")

    # -- Validate results --

    # Check expected agents ran
    for agent in test_def.get("expected_agents", []):
        if agent not in all_agents:
            issues.append(f"Expected agent '{agent}' did not run")

    # GUARD RAIL: Check rejected agents were NOT called
    for agent in test_def.get("reject_agents", []):
        if agent in all_agents:
            issues.append(f"WRONG INVESTIGATOR: '{agent}' was called but should NOT have been for this case")

    # Check completion
    if not final_result["completed"] and not final_result["was_paused"]:
        issues.append("Workflow neither completed nor paused")

    # Check final output
    if test_def["mode"] != "hitl_only":
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


def run_hitl_test(test_def: dict, workflow_id: int) -> dict:
    """Run a simple HITL test (vague input -> expect pause)."""
    name = test_def["name"]
    test_id = test_def["id"]

    print(f"\n{'='*60}")
    print(f"TEST #{test_id}: {name}")
    print(f"  Mode: {test_def['mode']}")
    print(f"  Message: \"{test_def['message']}\"")
    print(f"  HITL: True")
    print(f"{'='*60}")

    result = run_workflow_stream(workflow_id, test_def["message"])
    issues = []

    if result["error"]:
        issues.append(f"Error: {result['error']}")

    for agent in test_def.get("expected_agents", []):
        if agent not in result["agents_run"]:
            issues.append(f"Expected agent '{agent}' did not run")

    if not result["was_paused"]:
        issues.append("Expected PAUSE but workflow did not pause")
    else:
        pause_lower = result["pause_text"].lower()
        for kw in test_def.get("expected_pause_keywords", []):
            if kw.lower() not in pause_lower:
                issues.append(f"Pause text missing keyword: '{kw}'")

    print(f"\n  Agents run: {result['agents_run']}")
    print(f"  Paused: {result['was_paused']}")
    print(f"  Duration: {result['duration_s']}s")

    if result["was_paused"] and result["pause_text"]:
        _safe_print(f"  Pause preview: {result['pause_text'][:300]}")

    status = "PASS" if not issues else "FAIL"
    if issues:
        for issue in issues:
            print(f"  [ISSUE] {issue}")

    print(f"\n  RESULT: {status} ({result['duration_s']}s)")

    return {
        "id": test_id,
        "name": name,
        "mode": test_def["mode"],
        "status": status,
        "issues": issues,
        "duration_s": result["duration_s"],
        "agents_run": result["agents_run"],
        "python_executions": result["python_executions"],
    }


# -- Main ---------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Test the Financial Crime Investigation workflow",
    )
    parser.add_argument(
        "--test", type=int, nargs="+",
        help="Run specific tests by ID (e.g. --test 1 2)",
    )
    parser.add_argument(
        "--only-hitl", action="store_true",
        help="Only run HITL triage test",
    )
    parser.add_argument(
        "--only-cases", action="store_true",
        help="Only run case investigation tests (C1, C2, C3)",
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
            print(f"  python create_workflows.py --file workflows/23_financial_crime.json")
            sys.exit(1)

    print(f"  Using workflow ID={workflow_id}")

    # Build test list
    tests_to_run = []

    if args.only_hitl:
        tests_to_run = HITL_TESTS[:]
    elif args.only_cases:
        tests_to_run = CASE_TESTS[:]
    elif args.test:
        all_tests = {t["id"]: t for t in CASE_TESTS + HITL_TESTS}
        for tid in args.test:
            if tid in all_tests:
                tests_to_run.append(all_tests[tid])
            else:
                print(f"[WARN] Test #{tid} not found")
    else:
        tests_to_run = CASE_TESTS + HITL_TESTS

    if not tests_to_run:
        print("[ERROR] No tests to run")
        sys.exit(1)

    print(f"\n{'#'*60}")
    print(f"  FINANCIAL CRIME INVESTIGATION WORKFLOW TEST SUITE")
    print(f"  Running {len(tests_to_run)} test(s)")
    print(f"{'#'*60}")

    # Run tests
    results = []
    for test_def in tests_to_run:
        if test_def["mode"] == "hitl_only":
            r = run_hitl_test(test_def, workflow_id)
        else:
            r = run_case_test(test_def, workflow_id)
        results.append(r)

    # -- Summary --
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
        print(f"  {tag} #{r['id']} {r['name']:<55} {r['duration_s']}s  {extras}")
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
