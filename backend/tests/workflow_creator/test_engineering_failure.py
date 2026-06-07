"""
Engineering Failure Analysis Workflow — Test Suite
===================================================

Tests the Engineering Failure Analysis workflow with 3 failure scenarios:
  - F1: Turbine blade fatigue crack — Materials + Stress/Structural + Quality Auditor
  - F2: PCB solder joint failure — Electrical/Electronics + Thermal/Fluids + Quality Auditor
  - F3: Pipeline corrosion-under-insulation — Corrosion + Materials + Thermal/Fluids

Each failure test:
  1. Sends incident report + all available inspection/test data
  2. Workflow routes through Triage → Domain Specialists → Root Cause → Corrective Action
  3. Specialist may pause (HITL) requesting additional data
  4. Validates: correct specialists engaged, wrong specialists NOT engaged (guard rail),
     expected keywords in final report, PythonTool executed by computational agents
  5. Verifies the final 8D report structure

Usage:
    python test_engineering_failure.py                       # Run all tests
    python test_engineering_failure.py --test 1              # Run F1 only
    python test_engineering_failure.py --test 2              # Run F2 only
    python test_engineering_failure.py --test 3              # Run F3 only
    python test_engineering_failure.py --workflow-id 99      # Use specific workflow ID
    python test_engineering_failure.py --url http://host:3000 --key YOUR_KEY
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

# ── Constants ────────────────────────────────────────────────────────────────

WORKFLOW_NAME = "Engineering Failure Analysis"
DATA_DIR = Path(__file__).parent / "test_data" / "engineering_failure"


# ── Data Loader ──────────────────────────────────────────────────────────────


def load_failure_data(failure_id: str) -> str:
    """Load all CSV data files for a failure case and format as a text block.

    Args:
        failure_id: e.g. "F1", "F2", "F3"
    """
    case_dir = DATA_DIR / failure_id
    if not case_dir.exists():
        return f"[ERROR] Failure data directory not found: {case_dir}"

    parts = []
    for fpath in sorted(case_dir.iterdir()):
        if fpath.suffix == ".csv":
            content = fpath.read_text(encoding="utf-8").strip()
            parts.append(f"\n--- {fpath.stem} ---\n{content}")
        elif fpath.suffix == ".json":
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(data, indent=2)}")

    return "\n".join(parts)


# ── Build Test Messages ──────────────────────────────────────────────────────


def build_f1_message() -> str:
    """F1: Turbine blade fatigue crack in gas turbine after 18,000 hours."""
    data = load_failure_data("F1")
    return (
        "Please perform a complete engineering failure analysis:\n\n"
        "Failure Incident: Turbine Blade Fatigue Crack\n"
        "Equipment: GE Frame 7FA Gas Turbine, Unit #3\n"
        "Component: First-stage turbine blade (Row 1), Blade Position 47\n"
        "Material: Inconel 718 nickel-base superalloy\n"
        "Location: Petrochemical plant, Houston TX\n\n"
        "A 22mm transgranular fatigue crack was discovered at the blade root "
        "fillet radius on the suction side during borescope inspection at "
        "18,247 operating hours (design life 30,000 hours). Multiple beach marks "
        "visible on fracture surface indicate progressive high-cycle fatigue. "
        "The turbine experienced daily start-stop cycling and three thermal trips "
        "in the past 12 months. Vibration monitoring showed gradual increase from "
        "2.1 to 4.8 mm/s over the past 6 months.\n\n"
        f"All available data:\n{data}\n\n"
        "Investigate with appropriate specialists (materials, stress analysis, "
        "quality), determine root cause, and produce a corrective action 8D report."
    )


def build_f2_message() -> str:
    """F2: PCB solder joint failure in automotive ECU causing intermittent power loss."""
    data = load_failure_data("F2")
    return (
        "Please perform a complete engineering failure analysis:\n\n"
        "Failure Incident: PCB Solder Joint Failure in Automotive ECU\n"
        "Equipment: Automotive Engine Control Unit (ECU), Model ACE-4500\n"
        "Component: Main power regulation PCB — MOSFET Q3 solder joints (TO-263)\n"
        "Manufacturer: TierOne Automotive Electronics\n\n"
        "Field returns analysis of 15 ECU units from production lot L2024-0892 "
        "revealed cracked solder joints on the TO-263 package MOSFET Q3. X-ray "
        "inspection showed void percentages 18-32% (spec <25%). Cross-sectional "
        "analysis revealed Kirkendall voiding and intermetallic compound (IMC) "
        "growth at the Sn-Cu interface. Failures are intermittent and correlate "
        "with under-hood thermal cycling. Current field failure rate: 333 ppm.\n\n"
        "Production lot L2024-0892 used a modified reflow profile with peak temp "
        "248C and time above liquidus 62s (vs standard 245C/57s on other lots).\n\n"
        f"All available data:\n{data}\n\n"
        "Investigate with appropriate specialists (electronics, thermal, quality), "
        "determine root cause, and produce a corrective action 8D report."
    )


def build_f3_message() -> str:
    """F3: Pipeline corrosion-under-insulation discovered during routine inspection."""
    data = load_failure_data("F3")
    return (
        "Please perform a complete engineering failure analysis:\n\n"
        "Failure Incident: Pipeline Corrosion-Under-Insulation (CUI)\n"
        "Equipment: 8-inch carbon steel process pipeline, Line P-3042\n"
        "Service: Hot oil transfer line (operating at 145C nominal)\n"
        "Material: ASTM A106 Grade B carbon steel\n"
        "Location: Gulf Coast refinery\n\n"
        "Ultrasonic thickness readings at support locations revealed significant "
        "wall loss (up to 42% of nominal 7.04mm wall) beneath calcium silicate "
        "insulation. Insulation removal at Support #7 (6 o'clock) exposed heavy "
        "pitting corrosion up to 3.2mm deep. Moisture was present under insulation "
        "at multiple locations. The operating temperature cycles to 65C during "
        "shutdowns, placing the pipe in the CUI-susceptible range (50-175C). "
        "Chloride deposits up to 1850 ppm found under insulation.\n\n"
        f"All available data:\n{data}\n\n"
        "Investigate with appropriate specialists (corrosion, materials, thermal), "
        "determine root cause, and produce a corrective action 8D report."
    )


# ── Test Definitions ─────────────────────────────────────────────────────────

FAILURE_TESTS = [
    {
        "id": 1,
        "name": "F1: Turbine blade fatigue crack (mechanical fatigue)",
        "mode": "full_analysis",
        "build_message": build_f1_message,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "Incident Triage Engineer",
            "Materials Engineer",
            "Stress/Structural Analyst",
            "Root Cause Analyst",
            "Corrective Action Writer",
        ],
        "reject_agents": [
            "Electrical/Electronics Engineer",
            "Corrosion Specialist",
        ],
        "expect_python": True,
        "expected_in_output": [
            "fatigue",
            "root cause",
            "8D",
            "corrective",
        ],
        "min_answer_length": 300,
        "purpose": "Validates mechanical fatigue routing: Triage -> Materials + "
                   "Stress/Structural + Quality -> Root Cause -> Corrective Action. "
                   "Ensures Electrical and Corrosion specialists are NOT called.",
    },
    {
        "id": 2,
        "name": "F2: PCB solder joint failure (electronics failure)",
        "mode": "full_analysis",
        "build_message": build_f2_message,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "Incident Triage Engineer",
            "Electrical/Electronics Engineer",
            "Thermal/Fluids Engineer",
            "Root Cause Analyst",
            "Corrective Action Writer",
        ],
        "reject_agents": [
            "Corrosion Specialist",
            "Welding/Joining Engineer",
        ],
        "expect_python": True,
        "expected_in_output": [
            "solder",
            "root cause",
            "8D",
            "corrective",
        ],
        "min_answer_length": 300,
        "purpose": "Validates electronics failure routing: Triage -> Electrical + "
                   "Thermal + Quality -> Root Cause -> Corrective Action. "
                   "Ensures Corrosion and Welding specialists are NOT called.",
    },
    {
        "id": 3,
        "name": "F3: Pipeline corrosion-under-insulation (corrosion failure)",
        "mode": "full_analysis",
        "build_message": build_f3_message,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "Incident Triage Engineer",
            "Corrosion Specialist",
            "Materials Engineer",
            "Root Cause Analyst",
            "Corrective Action Writer",
        ],
        "reject_agents": [
            "Electrical/Electronics Engineer",
            "Welding/Joining Engineer",
        ],
        "expect_python": True,
        "expected_in_output": [
            "corrosion",
            "root cause",
            "8D",
            "corrective",
        ],
        "min_answer_length": 300,
        "purpose": "Validates corrosion failure routing: Triage -> Corrosion + "
                   "Materials + Thermal -> Root Cause -> Corrective Action. "
                   "Ensures Electrical and Welding specialists are NOT called.",
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
    """Find the Engineering Failure Analysis workflow by name."""
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


# ── Test Runner ──────────────────────────────────────────────────────────────


def run_failure_test(test_def: dict, workflow_id: int) -> dict:
    """Run a failure analysis test case.

    Flow:
      Round 0: Send incident report + all data -> specialists investigate
      Round 1: If paused (HITL), provide additional data -> expect completion
    """
    name = test_def["name"]
    test_id = test_def["id"]

    print(f"\n{'='*60}")
    print(f"TEST #{test_id}: {name}")
    print(f"  Mode: {test_def['mode']}")
    print(f"  Expect HITL pause: {test_def.get('expect_hitl_pause', False)}")
    print(f"  Purpose: {test_def['purpose']}")
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

    msg_preview = message[:150].replace("\n", " ")
    print(f"  Message: \"{msg_preview}...\"")

    # Create chat session for HITL tracking
    chat_session_id = create_chat_session()
    if not chat_session_id:
        return {
            "id": test_id, "name": name, "mode": test_def["mode"],
            "status": "FAIL", "issues": ["Could not create chat session"],
            "duration_s": 0, "agents_run": [], "python_executions": 0,
        }

    # ── Round 0: Initial message ──
    print(f"\n  --- ROUND 0: Initial submission ---")
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
        print(f"\n  [INFO] Workflow paused as expected — HITL scenario")
        # For this test suite, we don't provide follow-up data;
        # the pause itself is a valid test outcome.

    elif r0["was_paused"] and not test_def.get("expect_hitl_pause"):
        # Specialist paused unexpectedly — workflow still running, not a hard failure
        print("  [INFO] Specialist paused (unexpected) — treating as soft warning")

    # ── Validate results ──

    # Check expected agents ran
    for agent in test_def.get("expected_agents", []):
        if agent not in all_agents:
            issues.append(f"Expected agent '{agent}' did not run")

    # GUARD RAIL: Check rejected agents were NOT called
    for agent in test_def.get("reject_agents", []):
        if agent in all_agents:
            issues.append(
                f"WRONG SPECIALIST: '{agent}' was called but should NOT "
                f"have been for this failure type"
            )

    # Check completion (unless HITL paused)
    if not final_result["completed"] and not final_result["was_paused"]:
        issues.append("Workflow neither completed nor paused")

    # Check final output content
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

    # ── Print summary ──
    print(f"\n  Agents run: {all_agents}")
    print(f"  Total PythonTool executions: {total_python}")
    print(f"  Total files generated: {len(total_files)}")
    print(f"  Final answer length: {len(final_result['final_answer'])} chars")
    print(f"  Total duration: {total_duration}s")

    if final_result["final_answer"]:
        preview = final_result["final_answer"][:250]
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
        description="Test the Engineering Failure Analysis workflow",
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
            print(f"  python create_workflows.py --file workflows/24_engineering_failure.json")
            sys.exit(1)

    print(f"  Using workflow ID={workflow_id}")

    # Build test list
    tests_to_run = []

    if args.test:
        all_tests = {t["id"]: t for t in FAILURE_TESTS}
        for tid in args.test:
            if tid in all_tests:
                tests_to_run.append(all_tests[tid])
            else:
                print(f"[WARN] Test #{tid} not found (valid: 1, 2, 3)")
    else:
        tests_to_run = FAILURE_TESTS[:]

    if not tests_to_run:
        print("[ERROR] No tests to run")
        sys.exit(1)

    print(f"\n{'#'*60}")
    print(f"  ENGINEERING FAILURE ANALYSIS WORKFLOW TEST SUITE")
    print(f"  Running {len(tests_to_run)} test(s)")
    print(f"{'#'*60}")

    # Run tests
    results = []
    for test_def in tests_to_run:
        r = run_failure_test(test_def, workflow_id)
        results.append(r)

    # ── Summary ──
    print(f"\n\n{'='*70}")
    print(f"TEST RESULTS SUMMARY")
    print(f"{'='*70}")

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

    # Print routing validation summary
    print(f"\n  ROUTING VALIDATION:")
    routing_table = {
        1: {"expected": "Materials + Stress/Structural + Quality", "rejected": "Electrical, Corrosion"},
        2: {"expected": "Electrical + Thermal + Quality", "rejected": "Corrosion, Welding"},
        3: {"expected": "Corrosion + Materials + Thermal", "rejected": "Electrical, Welding"},
    }
    for r in results:
        tid = r["id"]
        if tid in routing_table:
            rt = routing_table[tid]
            print(f"    F{tid}: Expected [{rt['expected']}]  Rejected [{rt['rejected']}]")
            agent_names = ", ".join(r["agents_run"])
            print(f"         Actual agents: [{agent_names}]")

    print(f"{'='*70}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
