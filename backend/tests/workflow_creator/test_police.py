#!/usr/bin/env python3
"""
State Police Charge-Sheet Workflow — guard-rail test suite.

Same deterministic pattern as test_cybercrime.py: each drafter self-gates by CASE STAGE, and the
test asserts on what each drafter actually PRODUCED (a distinctive header) captured per-step, so
orchestrator over-calling is harmless.

  SP1 ready + compliant + in deadline      -> Charge-Sheet Report (BNSS Sec 193)
  SP2 mandatory Sec 176(3)/105 step missing -> Compliance Deficiency Memo
  SP3 day 88/90 + FSL pending (incomplete)  -> Default-Bail Risk Alert (Sec 187)
  SP4 vague one-liner (HITL)                -> Extractor pauses [NEEDS_INPUT]

Usage: python test_police.py --key <KEY> [--test N] ; pace cases with an external sleep.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from config import add_common_args, api, apply_common_args, stream_api

WORKFLOW_NAME = "State Police Charge-Sheet Investigation"
CASES_DIR = Path(__file__).parent / "test_data" / "police"

DRAFT_MARKERS = {
    "Charge-Sheet Drafter": "charge-sheet report (bnss sec 193)",
    "Compliance Deficiency Memo Drafter": "compliance deficiency memo",
    "Default-Bail Risk Drafter": "default-bail risk alert",
}


def load_case_data(case_id: str) -> str:
    case_dir = CASES_DIR / case_id
    if not case_dir.exists():
        return ""
    parts = []
    for fpath in sorted(case_dir.iterdir()):
        if fpath.suffix == ".csv":
            parts.append(f"\n--- {fpath.stem} ---\n{fpath.read_text(encoding='utf-8').strip()}")
        elif fpath.suffix == ".json":
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(json.loads(fpath.read_text(encoding='utf-8')), indent=2)}")
    return "\n".join(parts)


def build_sp1_message() -> str:
    return (
        "Please work up this police case for filing — extract the case skeleton, check antecedents, verify BNSS "
        "compliance and the charge-sheet deadline, and prepare the appropriate document for the officer.\n\n"
        "The investigation is complete and the case file is attached:\n"
        f"{load_case_data('SP1')}\n\n"
        "Decide the case readiness stage and route to the right drafter."
    )


def build_sp2_message() -> str:
    return (
        "Please work up this police case — extract the skeleton, check antecedents, verify BNSS compliance, and "
        "prepare the appropriate document for the officer.\n\n"
        "This is a 7-year-plus offence and the case file is attached:\n"
        f"{load_case_data('SP2')}\n\n"
        "Decide the case readiness stage and route to the right drafter."
    )


def build_sp3_message() -> str:
    return (
        "Please work up this police case URGENTLY — extract the skeleton, verify the charge-sheet deadline, and "
        "prepare the appropriate document for the officer.\n\n"
        "The custody clock is nearly expired and the case file is attached:\n"
        f"{load_case_data('SP3')}\n\n"
        "Decide the case readiness stage and route to the right drafter."
    )


CASE_TESTS = [
    {
        "id": 1,
        "name": "SP1: ready + compliant + in deadline -> Charge-Sheet",
        "build_message": build_sp1_message,
        "expected_agents": ["Case-File Extractor", "Antecedents & Linkage", "BNSS Compliance & Section-Mapping Verifier", "Case Synthesizer"],
        "produced": ["Charge-Sheet Drafter"],
        "not_produced": ["Compliance Deficiency Memo Drafter", "Default-Bail Risk Drafter"],
        "expected_in_output": ["disclaimer"],
        "min_answer_length": 200,
        "purpose": "A complete, compliant, in-deadline case must PRODUCE only the Sec 193 charge-sheet.",
    },
    {
        "id": 2,
        "name": "SP2: mandatory forensic/AV step missing -> Deficiency Memo",
        "build_message": build_sp2_message,
        "expected_agents": ["Case-File Extractor", "Antecedents & Linkage", "BNSS Compliance & Section-Mapping Verifier", "Case Synthesizer"],
        "produced": ["Compliance Deficiency Memo Drafter"],
        "not_produced": ["Charge-Sheet Drafter", "Default-Bail Risk Drafter"],
        "expected_in_output": ["disclaimer"],
        "min_answer_length": 200,
        "purpose": "A 7yr+ case missing the Sec 176(3)/105 step must PRODUCE a deficiency memo; NO charge-sheet (premature).",
    },
    {
        "id": 3,
        "name": "SP3: deadline critical + FSL pending -> Default-Bail Alert",
        "build_message": build_sp3_message,
        "expected_agents": ["Case-File Extractor", "Antecedents & Linkage", "BNSS Compliance & Section-Mapping Verifier", "Case Synthesizer"],
        "produced": ["Default-Bail Risk Drafter"],
        "not_produced": ["Charge-Sheet Drafter", "Compliance Deficiency Memo Drafter"],
        "expected_in_output": ["disclaimer"],
        "min_answer_length": 200,
        "purpose": "A case at day 88/90 with FSL pending must PRODUCE a default-bail risk alert; NO charge-sheet (can't complete in time).",
    },
]

HITL_TESTS = [
    {
        "id": 4,
        "name": "SP4 (HITL): vague one-liner -> Extractor pauses",
        "message": "Please prepare a charge-sheet. Someone said there was a case the other day but I don't have the FIR number, the offence sections, or the accused details.",
        "expected_agents": ["Case-File Extractor"],
        "reject_agents": ["Charge-Sheet Drafter", "Compliance Deficiency Memo Drafter", "Default-Bail Risk Drafter"],
        "expect_pause": True,
        "expected_pause_keywords": ["fir"],
        "purpose": "With no FIR/offence/accused the Extractor must pause with [NEEDS_INPUT]; no drafter should run.",
    },
    {
        "id": 5,
        "name": "SP5 (guard): described robbery charge-sheet but NO data -> Extractor must pause, not fabricate",
        "message": (
            "Please prepare a charge-sheet for a robbery case (offence: robbery). Extract the case skeleton, "
            "check antecedents, verify BNSS compliance and the charge-sheet deadline, and prepare the "
            "appropriate document for the officer. "
            "(I don't have the FIR number, the exact offence sections, the accused details, or the arrest date yet.)"
        ),
        "expected_agents": ["Case-File Extractor"],
        "reject_agents": ["Charge-Sheet Drafter", "Compliance Deficiency Memo Drafter", "Default-Bail Risk Drafter"],
        "expect_pause": True,
        "expected_pause_keywords": ["fir"],
        "purpose": "Regression guard for the UI fabrication bug: a described-but-empty case (offence type + topic + instructions, but NO FIR number / accused / arrest date / case-diary data) must PAUSE with [NEEDS_INPUT] and must NOT fabricate an FIR number, accused name, or date.",
    },
]


def _safe_print(text: str, **kwargs):
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"), **kwargs)


def find_workflow_id() -> int | None:
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"[ERROR] list workflows: {resp.status_code}")
        return None
    for w in resp.json():
        if w["name"] == WORKFLOW_NAME:
            return w["id"]
    return None


def create_chat_session(agent_id: int = 0) -> str | None:
    resp = api("POST", "converse/create-chat-session", {"agent_id": agent_id})
    if resp.status_code != 200:
        print(f"[ERROR] create session: {resp.status_code} {resp.text[:200]}")
        return None
    return str(resp.json().get("chat_session_id", "")) or None


def run_workflow_stream(workflow_id: int, message: str, chat_session_id: str | None = None) -> dict:
    result = {
        "agents_run": [], "was_paused": False, "pause_text": "", "final_answer": "",
        "completed": False, "python_executions": 0, "files_generated": [],
        "error": None, "duration_s": 0, "all_text": "", "step_outputs": {},
    }
    body = {"message": message}
    if chat_session_id:
        body["chat_session_id"] = chat_session_id
    start = time.time()
    resp = stream_api("POST", f"workflow/{workflow_id}/run", body)
    if resp.status_code != 200:
        result["error"] = f"HTTP {resp.status_code}: {resp.text[:400]}"
        result["duration_s"] = round(time.time() - start, 1)
        return result

    in_final = False
    current_step = None
    final_parts, all_parts = [], []
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
                step = obj.get("step_name", "?")
                current_step = step
                if step not in result["agents_run"]:
                    result["agents_run"].append(step)
                _safe_print(f"\n  [STEP] {step}")
            elif ptype == "workflow_step_delta":
                c = obj.get("content", "")
                if c:
                    all_parts.append(c)
                    if current_step:
                        result["step_outputs"][current_step] = result["step_outputs"].get(current_step, "") + c
            elif ptype == "workflow_pause_for_input":
                result["was_paused"] = True
                result["pause_text"] = obj.get("questions", "")
                _safe_print(f"  [PAUSED] {obj.get('step_name','?')}: {result['pause_text'][:200]}")
            elif ptype == "python_tool_start":
                result["python_executions"] += 1
            elif ptype == "python_tool_delta":
                result["files_generated"].extend(obj.get("file_ids", []))
            elif ptype == "message_start":
                in_final = True
            elif ptype == "message_delta":
                c = obj.get("content", obj.get("delta", ""))
                if c:
                    if in_final:
                        final_parts.append(c)
                    all_parts.append(c)
            elif ptype == "stop":
                result["completed"] = True
        except json.JSONDecodeError:
            pass

    result["final_answer"] = "".join(final_parts)
    result["all_text"] = "".join(all_parts)
    result["duration_s"] = round(time.time() - start, 1)
    return result


def run_case_test(test_def: dict, workflow_id: int) -> dict:
    print(f"\n{'='*64}\nTEST #{test_def['id']}: {test_def['name']}\n  {test_def['purpose']}\n{'='*64}")
    issues = []
    message = test_def["build_message"]()
    sid = create_chat_session()
    if not sid:
        return {"id": test_def["id"], "name": test_def["name"], "status": "FAIL", "issues": ["no chat session"], "duration_s": 0, "agents_run": []}

    r = run_workflow_stream(workflow_id, message, sid)
    if r["error"]:
        issues.append(f"stream error: {r['error']}")
    for a in test_def.get("expected_agents", []):
        if a not in r["agents_run"]:
            issues.append(f"expected agent '{a}' did not run")
    for step in test_def.get("produced", []):
        if DRAFT_MARKERS[step] not in r["step_outputs"].get(step, "").lower():
            issues.append(f"expected '{step}' to PRODUCE its document ('{DRAFT_MARKERS[step]}') but it did not (ran={step in r['agents_run']})")
    for step in test_def.get("not_produced", []):
        if DRAFT_MARKERS[step] in r["step_outputs"].get(step, "").lower():
            issues.append(f"WRONG DRAFT: '{step}' produced '{DRAFT_MARKERS[step]}' but must NOT at this stage")
    if not r["completed"] and not r["was_paused"]:
        issues.append("workflow neither completed nor paused")
    combined = (r["final_answer"] + " " + r["all_text"]).lower()
    for kw in test_def.get("expected_in_output", []):
        if kw.lower() not in combined:
            issues.append(f"output missing keyword: '{kw}'")
    if len(r["final_answer"]) < test_def.get("min_answer_length", 0):
        issues.append(f"final answer too short ({len(r['final_answer'])} < {test_def['min_answer_length']})")

    drafted = [s for s in DRAFT_MARKERS if DRAFT_MARKERS[s] in r["step_outputs"].get(s, "").lower()]
    status = "PASS" if not issues else "FAIL"
    print(f"\n  Agents run: {r['agents_run']}")
    print(f"  Drafts PRODUCED: {drafted}")
    print(f"  final answer: {len(r['final_answer'])} chars | {r['duration_s']}s")
    for it in issues:
        print(f"  [ISSUE] {it}")
    print(f"  => {status}")
    return {"id": test_def["id"], "name": test_def["name"], "status": status, "issues": issues, "duration_s": r["duration_s"], "agents_run": r["agents_run"]}


def run_hitl_test(test_def: dict, workflow_id: int) -> dict:
    print(f"\n{'='*64}\nTEST #{test_def['id']}: {test_def['name']}\n  {test_def['purpose']}\n{'='*64}")
    issues = []
    sid = create_chat_session()
    r = run_workflow_stream(workflow_id, test_def["message"], sid)
    if r["error"]:
        issues.append(f"stream error: {r['error']}")
    for a in test_def.get("expected_agents", []):
        if a not in r["agents_run"]:
            issues.append(f"expected agent '{a}' did not run")
    for a in test_def.get("reject_agents", []):
        if a in r["agents_run"]:
            issues.append(f"WRONG: '{a}' ran but should NOT have")
    if test_def.get("expect_pause") and not r["was_paused"]:
        issues.append("expected a HITL pause ([NEEDS_INPUT]) but the workflow did not pause")
    if r["was_paused"]:
        low = r["pause_text"].lower()
        for kw in test_def.get("expected_pause_keywords", []):
            if kw.lower() not in low:
                issues.append(f"pause prompt missing keyword: '{kw}'")
    status = "PASS" if not issues else "FAIL"
    print(f"\n  Agents run: {r['agents_run']} | paused: {r['was_paused']}")
    for it in issues:
        print(f"  [ISSUE] {it}")
    print(f"  => {status}")
    return {"id": test_def["id"], "name": test_def["name"], "status": status, "issues": issues, "duration_s": r["duration_s"], "agents_run": r["agents_run"]}


def main():
    ap = argparse.ArgumentParser(description="State Police charge-sheet workflow guard-rail tests")
    add_common_args(ap)
    ap.add_argument("--test", type=int)
    ap.add_argument("--sleep", type=float, default=0.0)
    args = ap.parse_args()
    apply_common_args(args)

    wid = find_workflow_id()
    if wid is None:
        print(f"[ERROR] Workflow '{WORKFLOW_NAME}' not found. Deploy 34_police_chargesheet.json first.")
        return 1
    print(f"Workflow '{WORKFLOW_NAME}' id={wid}")

    all_defs = [(t, run_case_test) for t in CASE_TESTS] + [(t, run_hitl_test) for t in HITL_TESTS]
    if args.test:
        all_defs = [(t, fn) for t, fn in all_defs if t["id"] == args.test]
        if not all_defs:
            print(f"No case id {args.test}")
            return 1

    results = []
    for i, (t, fn) in enumerate(all_defs):
        results.append(fn(t, wid))
        if args.sleep and i < len(all_defs) - 1:
            time.sleep(args.sleep)

    print(f"\n{'='*64}\nSUMMARY")
    passed = sum(1 for r in results if r["status"] == "PASS")
    for r in results:
        tag = "[OK]" if r["status"] == "PASS" else "[FAIL]"
        extra = "" if r["status"] == "PASS" else "  " + "; ".join(r["issues"])
        print(f"  {tag} #{r['id']} {r['name'][:52]:<52} {r['duration_s']}s{extra}")
    print(f"\n  Total: {len(results)} | {passed} passed | {len(results)-passed} failed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
