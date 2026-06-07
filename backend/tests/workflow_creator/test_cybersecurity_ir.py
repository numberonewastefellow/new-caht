"""
Cybersecurity Incident Response Workflow — Test Suite
=====================================================

Tests the Cybersecurity Incident Response workflow with 3 incident scenarios:
  - I1: Ransomware via phishing — Email + Endpoint + Network + Identity analysts
  - I2: Cloud S3 data breach — Cloud + Identity + Data Loss analysts
  - I3: Insider threat — Identity + Data Loss + Network analysts
  - I4 (HITL-only): Vague alert triggers SOC Triage questions

Each incident test:
  1. Sends initial alert data with all available logs/artifacts
  2. Workflow routes through SOC Triage -> Specialist Analysts -> Threat Intel -> Report Writer
  3. SOC Triage may pause (HITL) requesting additional alert context
  4. Validates: correct analysts engaged, wrong analysts NOT engaged (guard rail),
     expected keywords in final report, PythonTool executed by network/endpoint analysts

Usage:
    python test_cybersecurity_ir.py                    # Run all tests
    python test_cybersecurity_ir.py --test 1           # Run I1 only
    python test_cybersecurity_ir.py --test 2           # Run I2 only
    python test_cybersecurity_ir.py --test 3           # Run I3 only
    python test_cybersecurity_ir.py --test 4           # Run HITL triage only
    python test_cybersecurity_ir.py --only-hitl        # Run HITL tests only
    python test_cybersecurity_ir.py --workflow-id 53   # Use specific workflow ID
    python test_cybersecurity_ir.py --url http://host:3000 --key YOUR_KEY
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

WORKFLOW_NAME = "Cybersecurity Incident Response"
INCIDENTS_DIR = Path(__file__).parent / "test_data" / "cybersecurity"


# -- Incident Data Loader ----------------------------------------------------


def load_incident_data(incident_id: str) -> str:
    """Load all CSV data files for an incident and format as a text block.

    Args:
        incident_id: e.g. "I1", "I2", "I3"
    """
    incident_dir = INCIDENTS_DIR / incident_id
    if not incident_dir.exists():
        return f"[ERROR] Incident directory not found: {incident_dir}"

    parts = []
    for fpath in sorted(incident_dir.iterdir()):
        if fpath.suffix == ".csv":
            content = fpath.read_text(encoding="utf-8").strip()
            parts.append(f"\n--- {fpath.stem} ---\n{content}")
        elif fpath.suffix == ".json":
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(data, indent=2)}")

    return "\n".join(parts)


# -- Build Test Messages ------------------------------------------------------


def build_i1_message() -> str:
    """I1: Ransomware attack via phishing email with Cobalt Strike."""
    data = load_incident_data("I1")
    return (
        "INCIDENT ALERT: Ransomware Attack via Phishing\n\n"
        "At 2024-11-15T08:23:00Z, our SOC received a critical alert from CrowdStrike EDR "
        "indicating ransomware activity on multiple endpoints. Initial investigation reveals:\n\n"
        "- A phishing email was received by user jsmith@acme-corp.com at 07:45 UTC containing "
        "a macro-enabled Word document (Invoice_Q4_2024.docm)\n"
        "- The macro executed a PowerShell command that downloaded a Cobalt Strike beacon from 203.0.113.42\n"
        "- Lateral movement detected via SMB to 3 additional hosts in the finance department\n"
        "- File encryption activity (.locked extension) detected starting at 08:15 UTC on "
        "WKS-FIN-001, WKS-FIN-002, and SRV-FILE-01\n"
        "- A ransom note (README_RESTORE.txt) was dropped in multiple directories\n"
        "- AD logon anomalies detected: svc_backup account used for interactive logon from WKS-FIN-001\n\n"
        "Please analyze the following incident data:\n"
        f"{data}\n\n"
        "Perform a complete incident response — triage, analyze with appropriate specialists, "
        "map to MITRE ATT&CK, and produce a final incident report with remediation plan."
    )


def build_i2_message() -> str:
    """I2: Cloud S3 data breach via compromised IAM credentials."""
    data = load_incident_data("I2")
    return (
        "INCIDENT ALERT: AWS S3 Data Breach via Compromised IAM Credentials\n\n"
        "At 2024-11-18T14:30:00Z, Amazon GuardDuty generated a HIGH severity finding for "
        "unusual S3 API activity. Investigation reveals:\n\n"
        "- Unusual ListBuckets and GetObject API calls from IP 203.0.113.88 "
        "(geolocated to Eastern Europe)\n"
        "- The calls were authenticated using access keys belonging to IAM user 'data-pipeline-svc'\n"
        "- The access key is 847 days old and has no MFA enforcement\n"
        "- S3 bucket 'acme-customer-data-prod' had its bucket policy modified to allow public read access\n"
        "- Bulk download of approximately 2.3 GB of data containing PII "
        "(customer SSNs, addresses, financial records)\n"
        "- A new IAM access key was created for the compromised user during the incident\n"
        "- No CloudTrail logging gaps detected, full audit trail available\n\n"
        "Please analyze the following incident data:\n"
        f"{data}\n\n"
        "Perform a complete incident response — triage, analyze with appropriate specialists, "
        "map to MITRE ATT&CK, and produce a final incident report with remediation plan."
    )


def build_i3_message() -> str:
    """I3: Insider threat — employee exfiltrating data via personal email and USB."""
    data = load_incident_data("I3")
    return (
        "INCIDENT ALERT: Insider Threat - Data Exfiltration by Employee\n\n"
        "At 2024-11-20T09:15:00Z, the DLP (Data Loss Prevention) system generated multiple "
        "alerts for user mthompson@acme-corp.com. Investigation reveals:\n\n"
        "- Employee Michael Thompson (Senior Financial Analyst, Finance Department) has been "
        "flagged for unusual data access patterns over the past 30 days\n"
        "- DLP detected 12 instances of classified documents being sent to a personal Gmail address\n"
        "- USB storage device events detected on 8 occasions with large file transfers\n"
        "- File access logs show access to confidential documents outside the employee's normal scope "
        "(HR records, M&A documents, executive compensation data)\n"
        "- HR context: Employee was passed over for promotion 45 days ago, filed a formal complaint "
        "30 days ago, and submitted resignation 5 days ago with a 2-week notice period\n"
        "- The employee's access has NOT been revoked pending this investigation\n\n"
        "Please analyze the following incident data:\n"
        f"{data}\n\n"
        "Perform a complete incident response — triage, analyze with appropriate specialists, "
        "map to MITRE ATT&CK, and produce a final incident report with remediation plan."
    )


# -- Test Definitions ---------------------------------------------------------

INCIDENT_TESTS = [
    {
        "id": 1,
        "name": "I1: Ransomware via phishing (Cobalt Strike + lateral movement)",
        "mode": "full_ir",
        "build_message": build_i1_message,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "SOC Triage Analyst",
            "Email/Phishing Analyst",
            "Endpoint/Malware Analyst",
            "Network Forensics Analyst",
            "Identity/Access Analyst",
            "Threat Intelligence Analyst",
            "Incident Report Writer",
        ],
        "reject_agents": [
            "Cloud Security Analyst",
            "Data Loss Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "IOC",
            "remediation",
            "containment",
        ],
        "min_answer_length": 300,
        "purpose": "Validates ransomware routing: SOC Triage -> Email/Phishing + "
                   "Endpoint/Malware + Network Forensics + Identity/Access -> "
                   "Threat Intel -> Report Writer. Cloud and Data Loss should NOT be called.",
    },
    {
        "id": 2,
        "name": "I2: Cloud S3 data breach (IAM compromise + data exfiltration)",
        "mode": "full_ir",
        "build_message": build_i2_message,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "SOC Triage Analyst",
            "Cloud Security Analyst",
            "Identity/Access Analyst",
            "Data Loss Analyst",
            "Threat Intelligence Analyst",
            "Incident Report Writer",
        ],
        "reject_agents": [
            "Email/Phishing Analyst",
            "Endpoint/Malware Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "IOC",
            "remediation",
            "containment",
        ],
        "min_answer_length": 300,
        "purpose": "Validates cloud breach routing: SOC Triage -> Cloud Security + "
                   "Identity/Access + Data Loss -> Threat Intel -> Report Writer. "
                   "Email/Phishing and Endpoint/Malware should NOT be called.",
    },
    {
        "id": 3,
        "name": "I3: Insider threat (data exfiltration via email and USB)",
        "mode": "full_ir",
        "build_message": build_i3_message,
        "is_hitl": False,
        "expect_hitl_pause": False,
        "expected_agents": [
            "SOC Triage Analyst",
            "Identity/Access Analyst",
            "Data Loss Analyst",
            "Network Forensics Analyst",
            "Threat Intelligence Analyst",
            "Incident Report Writer",
        ],
        "reject_agents": [
            "Cloud Security Analyst",
            "Email/Phishing Analyst",
        ],
        "expect_python": True,
        "expected_in_output": [
            "IOC",
            "remediation",
            "containment",
        ],
        "min_answer_length": 300,
        "purpose": "Validates insider threat routing: SOC Triage -> Identity/Access + "
                   "Data Loss + Network Forensics -> Threat Intel -> Report Writer. "
                   "Cloud Security and Email/Phishing should NOT be called.",
    },
]

HITL_TESTS = [
    {
        "id": 4,
        "name": "HITL: Vague alert triggers SOC Triage questions",
        "mode": "hitl_only",
        "message": "We think we may have been hacked. Some users are reporting issues.",
        "is_hitl": True,
        "expected_agents": ["SOC Triage Analyst"],
        "reject_agents": [],
        "expect_python": False,
        "expected_in_output": [],
        "expected_pause_keywords": ["alert", "log"],
        "min_answer_length": 0,
        "purpose": "Validates HITL: Vague incident description triggers SOC Triage Analyst's "
                   "[NEEDS_INPUT] with requests for specific alert data and log sources.",
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
    """Find the Cybersecurity IR workflow by name."""
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


def run_incident_test(test_def: dict, workflow_id: int) -> dict:
    """Run an incident test and validate the results.

    For incident tests (I1/I2/I3), the flow is:
      Round 0: Send initial message with alert data + all logs -> expect completion
    """
    name = test_def["name"]
    test_id = test_def["id"]

    print(f"\n{'='*60}")
    print(f"TEST #{test_id}: {name}")
    print(f"  Mode: {test_def['mode']}")
    print(f"  Purpose: {test_def['purpose']}")
    print(f"{'='*60}")

    issues = []

    # Build initial message
    build_fn = test_def.get("build_message")
    if build_fn:
        message = build_fn()
    else:
        message = test_def.get("message", "")

    msg_preview = message[:120].replace("\n", " ")
    print(f"  Message: \"{msg_preview}...\"")

    # Create chat session
    chat_session_id = create_chat_session()
    if not chat_session_id:
        return {
            "id": test_id, "name": name, "mode": test_def["mode"],
            "status": "FAIL", "issues": ["Could not create chat session"],
            "duration_s": 0, "agents_run": [], "python_executions": 0,
        }

    # -- Round 0: Initial submission --
    print(f"\n  --- ROUND 0: Initial incident submission ---")
    r0 = run_workflow_stream(workflow_id, message, chat_session_id)

    if r0["error"]:
        issues.append(f"Round 0 error: {r0['error']}")

    # -- Validate results --

    # Check expected agents ran
    for agent in test_def.get("expected_agents", []):
        if agent not in r0["agents_run"]:
            issues.append(f"Expected agent '{agent}' did not run")

    # GUARD RAIL: Check rejected agents were NOT called
    for agent in test_def.get("reject_agents", []):
        if agent in r0["agents_run"]:
            issues.append(
                f"WRONG ANALYST: '{agent}' was called but should NOT have been "
                f"for this incident type"
            )

    # Check completion
    if not r0["completed"] and not r0["was_paused"]:
        issues.append("Workflow neither completed nor paused")

    # Check final output keywords
    if r0["completed"]:
        combined_lower = (r0["final_answer"] + " " + r0.get("all_text", "")).lower()

        for kw in test_def.get("expected_in_output", []):
            if kw.lower() not in combined_lower:
                issues.append(f"Output missing keyword: '{kw}'")

        # Check for MITRE ATT&CK references in all text
        if "att&ck" not in combined_lower and "mitre" not in combined_lower and "t1" not in combined_lower:
            issues.append("Output missing MITRE ATT&CK references")

        if test_def.get("expect_python") and r0["python_executions"] == 0:
            issues.append("Expected PythonTool execution but none occurred")

        min_len = test_def.get("min_answer_length", 0)
        if min_len > 0 and len(r0["final_answer"]) < min_len:
            issues.append(
                f"Final answer too short ({len(r0['final_answer'])} chars, "
                f"expected >= {min_len})"
            )

    # -- Print summary --
    print(f"\n  Agents run: {r0['agents_run']}")
    print(f"  Python executions: {r0['python_executions']}")
    print(f"  Files generated: {len(r0['files_generated'])}")
    print(f"  Final answer length: {len(r0['final_answer'])} chars")
    print(f"  Duration: {r0['duration_s']}s")

    if r0["final_answer"]:
        preview = r0["final_answer"][:200]
        _safe_print(f"  Answer preview: {preview}...")

    status = "PASS" if not issues else "FAIL"
    if issues:
        for issue in issues:
            print(f"  [ISSUE] {issue}")

    print(f"\n  RESULT: {status} ({r0['duration_s']}s)")

    return {
        "id": test_id,
        "name": name,
        "mode": test_def["mode"],
        "status": status,
        "issues": issues,
        "duration_s": r0["duration_s"],
        "agents_run": r0["agents_run"],
        "python_executions": r0["python_executions"],
    }


def run_hitl_test(test_def: dict, workflow_id: int) -> dict:
    """Run a simple HITL test (vague alert -> expect pause)."""
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
        description="Test the Cybersecurity Incident Response workflow",
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
        "--only-incidents", action="store_true",
        help="Only run incident response tests (I1, I2, I3)",
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
            print(f"  python create_workflows.py --file workflows/25_cybersecurity_ir.json")
            sys.exit(1)

    print(f"  Using workflow ID={workflow_id}")

    # Build test list
    tests_to_run = []

    if args.only_hitl:
        tests_to_run = HITL_TESTS[:]
    elif args.only_incidents:
        tests_to_run = INCIDENT_TESTS[:]
    elif args.test:
        all_tests = {t["id"]: t for t in INCIDENT_TESTS + HITL_TESTS}
        for tid in args.test:
            if tid in all_tests:
                tests_to_run.append(all_tests[tid])
            else:
                print(f"[WARN] Test #{tid} not found")
    else:
        tests_to_run = INCIDENT_TESTS + HITL_TESTS

    if not tests_to_run:
        print("[ERROR] No tests to run")
        sys.exit(1)

    print(f"\n{'#'*60}")
    print(f"  CYBERSECURITY INCIDENT RESPONSE WORKFLOW TEST SUITE")
    print(f"  Running {len(tests_to_run)} test(s)")
    print(f"{'#'*60}")

    # Run tests
    results = []
    for test_def in tests_to_run:
        if test_def["mode"] == "hitl_only":
            r = run_hitl_test(test_def, workflow_id)
        else:
            r = run_incident_test(test_def, workflow_id)
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
