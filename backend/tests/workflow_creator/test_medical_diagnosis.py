"""
Medical Diagnosis Panel Workflow — Test Suite
==============================================

Tests the Medical Diagnosis Panel workflow with 3 patient scenarios:
  - P1: Multi-system autoimmune (fatigue/thyroid/joints) — Endocrinologist + Rheumatologist + Hematologist
  - P2: Cardiac with renal involvement — Cardiologist + Nephrologist
  - P3: GI/Liver case (Hepatitis C) — Gastroenterologist + Hematologist
  - P4 (HITL-only): Vague complaint triggers triage questions

Each patient test:
  1. Sends initial symptoms + lab data
  2. Workflow routes through Triage → Lab Analyst → PCP → Specialists
  3. Specialist may pause (HITL) requesting additional tests
  4. Test provides follow-up results → specialist resumes → Synthesizer produces report
  5. Validates: correct specialists engaged, wrong specialists NOT engaged (guard rail),
     expected keywords in final diagnosis, PythonTool executed

Usage:
    python test_medical_diagnosis.py                    # Run all tests
    python test_medical_diagnosis.py --test 1           # Run P1 only
    python test_medical_diagnosis.py --test 2           # Run P2 only
    python test_medical_diagnosis.py --test 3           # Run P3 only
    python test_medical_diagnosis.py --test 4           # Run HITL triage only
    python test_medical_diagnosis.py --only-hitl        # Run HITL tests only
    python test_medical_diagnosis.py --workflow-id 53   # Use specific workflow ID
    python test_medical_diagnosis.py --url http://host:3000 --key YOUR_KEY
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

WORKFLOW_NAME = "Medical Diagnosis Panel"
PATIENTS_DIR = Path(__file__).parent / "test_data" / "patients"


# ── Patient Data Loader ─────────────────────────────────────────────────────


def load_patient_data(patient_id: str, exclude_followup: bool = True) -> str:
    """Load all initial patient data files and format as a text block.

    Args:
        patient_id: e.g. "P1", "P2", "P3"
        exclude_followup: If True, skip files with 'followup' in the name
                         (these are provided later after HITL pause)
    """
    patient_dir = PATIENTS_DIR / patient_id
    if not patient_dir.exists():
        return f"[ERROR] Patient directory not found: {patient_dir}"

    parts = []
    for fpath in sorted(patient_dir.iterdir()):
        if exclude_followup and "followup" in fpath.name.lower():
            continue

        if fpath.suffix == ".json":
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(data, indent=2)}")
        elif fpath.suffix == ".csv":
            content = fpath.read_text(encoding="utf-8").strip()
            parts.append(f"\n--- {fpath.stem} ---\n{content}")

    return "\n".join(parts)


def load_followup_data(patient_id: str) -> str:
    """Load only follow-up data files (those with 'followup' in name or
    files that are imaging/serology results provided after HITL pause)."""
    patient_dir = PATIENTS_DIR / patient_id
    followup_files = {
        "P1": ["thyroid_antibodies_followup.csv"],
        "P2": ["echocardiogram_report.json", "stress_test_report.json"],
        "P3": ["hepatitis_serology.csv", "abdominal_ultrasound_report.json"],
    }

    files = followup_files.get(patient_id, [])
    parts = []
    for fname in files:
        fpath = patient_dir / fname
        if not fpath.exists():
            continue
        if fpath.suffix == ".json":
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} (FOLLOW-UP RESULTS) ---\n{json.dumps(data, indent=2)}")
        elif fpath.suffix == ".csv":
            content = fpath.read_text(encoding="utf-8").strip()
            parts.append(f"\n--- {fpath.stem} (FOLLOW-UP RESULTS) ---\n{content}")

    return "\n".join(parts)


# ── Build Test Messages ──────────────────────────────────────────────────────


def build_p1_message() -> str:
    """P1: 38F Multi-system autoimmune (fatigue/thyroid/joints)."""
    data = load_patient_data("P1", exclude_followup=True)
    return (
        "Please evaluate this patient case:\n\n"
        "Patient: 38-year-old female presenting with progressive fatigue for 3 months, "
        "weight gain of 12 lbs, joint pain in hands and knees, hair thinning, and "
        "intermittent butterfly-pattern facial rash across cheeks.\n\n"
        "Medical history: Iron deficiency anemia (resolved), seasonal allergies. "
        "Family: mother has hypothyroidism, aunt has rheumatoid arthritis.\n"
        "Medications: Cetirizine 10mg daily. Allergies: Sulfa drugs.\n\n"
        f"Available test results:\n{data}\n\n"
        "Please perform a complete diagnostic workup — triage, analyze labs, "
        "consult appropriate specialists, and produce a final diagnosis report."
    )


def build_p1_followup() -> str:
    """P1 follow-up: Thyroid antibody results after Endocrinologist request."""
    data = load_followup_data("P1")
    return (
        "Here are the additional thyroid antibody test results that were requested:\n\n"
        f"{data}\n\n"
        "Please continue the evaluation with these new results."
    )


def build_p2_message() -> str:
    """P2: 62M Cardiac with renal involvement."""
    data = load_patient_data("P2", exclude_followup=True)
    return (
        "Please evaluate this patient case:\n\n"
        "Patient: 62-year-old male presenting with chest tightness on exertion for 2 weeks, "
        "shortness of breath when climbing stairs, bilateral ankle swelling, and elevated "
        "blood pressure readings at home (158/96).\n\n"
        "Medical history: Hypertension 10 years, Type 2 Diabetes 5 years, Hyperlipidemia. "
        "Family: father MI at 58, brother CABG at 65. Former smoker (20 pack-years).\n"
        "Medications: Amlodipine 10mg, Metformin 1000mg BID, Aspirin 81mg. "
        "Allergies: ACE inhibitors (cough).\n\n"
        f"Available test results:\n{data}\n\n"
        "Please perform a complete diagnostic workup — triage, analyze labs, "
        "consult appropriate specialists, and produce a final diagnosis report."
    )


def build_p2_followup() -> str:
    """P2 follow-up: Echocardiogram and stress test results after Cardiologist request."""
    data = load_followup_data("P2")
    return (
        "Here are the cardiac imaging results that were requested:\n\n"
        f"{data}\n\n"
        "Please continue the evaluation with these new results."
    )


def build_p3_message() -> str:
    """P3: 45M GI/Liver case."""
    # For P3, exclude hepatitis serology and ultrasound (those are follow-ups)
    data = load_patient_data("P3", exclude_followup=False)
    # Actually, filter out the follow-up files manually
    patient_dir = PATIENTS_DIR / "P3"
    followup_names = {"hepatitis_serology.csv", "abdominal_ultrasound_report.json"}
    parts = []
    for fpath in sorted(patient_dir.iterdir()):
        if fpath.name in followup_names:
            continue
        if fpath.suffix == ".json":
            d = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(d, indent=2)}")
        elif fpath.suffix == ".csv":
            content = fpath.read_text(encoding="utf-8").strip()
            parts.append(f"\n--- {fpath.stem} ---\n{content}")
    data = "\n".join(parts)

    return (
        "Please evaluate this patient case:\n\n"
        "Patient: 45-year-old male presenting with right upper quadrant pain for 6 weeks, "
        "yellowing of eyes noticed by wife, dark urine, pale stools, loss of appetite, "
        "and 8 lb weight loss.\n\n"
        "Medical history: Blood transfusion in 1998 (after motorcycle accident). "
        "No other significant history.\n"
        "Medications: Ibuprofen PRN. Allergies: None.\n\n"
        f"Available test results:\n{data}\n\n"
        "Please perform a complete diagnostic workup — triage, analyze labs, "
        "consult appropriate specialists, and produce a final diagnosis report."
    )


def build_p3_followup() -> str:
    """P3 follow-up: Hepatitis serology and ultrasound after GI request."""
    data = load_followup_data("P3")
    return (
        "Here are the hepatitis serology and imaging results that were requested:\n\n"
        f"{data}\n\n"
        "Please continue the evaluation with these new results."
    )


# ── Test Definitions ─────────────────────────────────────────────────────────

PATIENT_TESTS = [
    {
        "id": 1,
        "name": "P1: Multi-system autoimmune (fatigue/thyroid/joints)",
        "mode": "full_diagnosis",
        "build_message": build_p1_message,
        "build_followup": build_p1_followup,
        "is_hitl": False,
        "expect_hitl_pause": True,  # Endocrinologist should request antibodies
        "expected_agents": [
            "Triage Doctor",
            "Lab Analyst",
            "Primary Care Physician",
            "Endocrinologist",
            "Rheumatologist",
            "Diagnosis Synthesizer",
        ],
        "reject_agents": [
            "Cardiologist",
            "Gastroenterologist",
            "Nephrologist",
        ],
        "expect_python": True,
        "expected_in_output": [
            "MEDICAL ASSESSMENT REPORT",
            "thyroid",
            "anemia",
            "DISCLAIMER",
        ],
        "min_answer_length": 300,
        "purpose": "Validates multi-specialist routing: Triage → PCP → Endocrinologist "
                   "(HITL for antibodies) → Rheumatologist → Hematologist → Synthesizer.",
    },
    {
        "id": 2,
        "name": "P2: Cardiac with renal involvement",
        "mode": "full_diagnosis",
        "build_message": build_p2_message,
        "build_followup": build_p2_followup,
        "is_hitl": False,
        "expect_hitl_pause": True,  # Cardiologist should request echo/stress
        "expected_agents": [
            "Triage Doctor",
            "Lab Analyst",
            "Primary Care Physician",
            "Cardiologist",
            "Diagnosis Synthesizer",
        ],
        "reject_agents": [
            "Endocrinologist",
            "Rheumatologist",
            "Gastroenterologist",
        ],
        "expect_python": True,
        "expected_in_output": [
            "MEDICAL ASSESSMENT REPORT",
            "heart",
            "DISCLAIMER",
        ],
        "min_answer_length": 300,
        "purpose": "Validates cardiac routing: Triage → PCP → Cardiologist "
                   "(HITL for echo) → Nephrologist → Synthesizer.",
    },
    {
        "id": 3,
        "name": "P3: GI/Liver case (Hepatitis C)",
        "mode": "full_diagnosis",
        "build_message": build_p3_message,
        "build_followup": build_p3_followup,
        "is_hitl": False,
        "expect_hitl_pause": True,  # GI should request hepatitis serology
        "expected_agents": [
            "Triage Doctor",
            "Lab Analyst",
            "Primary Care Physician",
            "Gastroenterologist",
            "Diagnosis Synthesizer",
        ],
        "reject_agents": [
            "Endocrinologist",
            "Cardiologist",
            "Rheumatologist",
            "Nephrologist",
        ],
        "expect_python": True,
        "expected_in_output": [
            "MEDICAL ASSESSMENT REPORT",
            "liver",
            "DISCLAIMER",
        ],
        "min_answer_length": 300,
        "purpose": "Validates GI routing: Triage → PCP → Gastroenterologist "
                   "(HITL for serology/imaging) → Hematologist → Synthesizer.",
    },
]

HITL_TESTS = [
    {
        "id": 4,
        "name": "HITL: Vague complaint triggers triage questions",
        "mode": "hitl_only",
        "message": "I have been feeling unwell lately",
        "is_hitl": True,
        "expected_agents": ["Triage Doctor"],
        "reject_agents": [],
        "expect_python": False,
        "expected_in_output": [],
        "expected_pause_keywords": ["symptoms"],
        "min_answer_length": 0,
        "purpose": "Validates HITL: Vague complaint triggers Triage Doctor's "
                   "[NEEDS_INPUT] with clarifying questions about symptoms.",
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
    """Find the Medical Diagnosis Panel workflow by name."""
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


def run_patient_test(test_def: dict, workflow_id: int) -> dict:
    """Run a patient test with optional HITL multi-round flow.

    For patient tests (P1/P2/P3), the flow is:
      Round 0: Send initial message with symptoms + labs → may pause
      Round 1: If paused, send follow-up results → expect completion
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
        build_followup_fn = test_def.get("build_followup")
        if build_followup_fn:
            followup_msg = build_followup_fn()
            print(f"\n  --- ROUND 1: Providing follow-up results ---")
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
        # Specialist didn't pause — that's OK if the workflow still completed correctly
        print("  [INFO] Expected HITL pause but specialist proceeded without requesting additional tests")
        # This is a soft warning, not a failure — the LLM may have had enough info

    # ── Validate results ──

    # Check expected agents ran
    for agent in test_def.get("expected_agents", []):
        if agent not in all_agents:
            issues.append(f"Expected agent '{agent}' did not run")

    # GUARD RAIL: Check rejected agents were NOT called
    for agent in test_def.get("reject_agents", []):
        if agent in all_agents:
            issues.append(f"WRONG SPECIALIST: '{agent}' was called but should NOT have been for this patient")

    # Check completion
    if not final_result["completed"] and not final_result["was_paused"]:
        issues.append("Workflow neither completed nor paused")

    # If not HITL-only test, check final output
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


def run_hitl_test(test_def: dict, workflow_id: int) -> dict:
    """Run a simple HITL test (vague input → expect pause)."""
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


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Test the Medical Diagnosis Panel workflow",
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
        "--only-patients", action="store_true",
        help="Only run patient diagnosis tests (P1, P2, P3)",
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
            print(f"  python create_workflows.py --file workflows/22_medical_diagnosis.json")
            sys.exit(1)

    print(f"  Using workflow ID={workflow_id}")

    # Build test list
    tests_to_run = []

    if args.only_hitl:
        tests_to_run = HITL_TESTS[:]
    elif args.only_patients:
        tests_to_run = PATIENT_TESTS[:]
    elif args.test:
        all_tests = {t["id"]: t for t in PATIENT_TESTS + HITL_TESTS}
        for tid in args.test:
            if tid in all_tests:
                tests_to_run.append(all_tests[tid])
            else:
                print(f"[WARN] Test #{tid} not found")
    else:
        tests_to_run = PATIENT_TESTS + HITL_TESTS

    if not tests_to_run:
        print("[ERROR] No tests to run")
        sys.exit(1)

    print(f"\n{'#'*60}")
    print(f"  MEDICAL DIAGNOSIS WORKFLOW TEST SUITE")
    print(f"  Running {len(tests_to_run)} test(s)")
    print(f"{'#'*60}")

    # Run tests
    results = []
    for test_def in tests_to_run:
        if test_def["mode"] == "hitl_only":
            r = run_hitl_test(test_def, workflow_id)
        else:
            r = run_patient_test(test_def, workflow_id)
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
