#!/usr/bin/env python3
"""
Cybercrime Investigation Workflow — guard-rail test suite.

Mirrors test_insurance_claims.py: each case sends the mock data inline and asserts
the CORRECT drafters ran AND the WRONG ones did NOT (the fan-out guard-rail). The
always-run analysis agents (Extractor, Fraud-Ring Linker, Records & Registry Verifier,
Case Synthesizer) fire on every case; the discriminating signal is which DRAFTER runs.

  CC1  live golden-hour, isolated  -> Golden-Hour Freeze Drafter   (reject Refund, Charge-Sheet)
  CC2  mule ring, golden-hour gone -> Charge-Sheet Drafter         (reject Freeze, Refund)
  CC3  aged, funds frozen          -> Refund + Charge-Sheet        (reject Freeze)
  CC4  vague one-liner (HITL)      -> Extractor pauses [NEEDS_INPUT]

Usage:
  python test_cybercrime.py --key <ADMIN_KEY>                 # all cases
  python test_cybercrime.py --key <KEY> --test 1              # one case
  for t in 1 2 3 4; do python -u test_cybercrime.py --key <KEY> --test $t; sleep 45; done   # paced

Exit code 0 iff all selected cases pass.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from config import add_common_args, api, apply_common_args, stream_api

WORKFLOW_NAME = "Cybercrime Investigation"
CASES_DIR = Path(__file__).parent / "test_data" / "cybercrime"

# Distinctive header a drafter emits ONLY when it actually produces its document.
# (Its self-gated "NOT APPLICABLE ..." no-op does NOT contain these strings.) The guard
# rail is output-based + deterministic: even if the orchestrator over-calls a drafter,
# a wrong-stage drafter self-gates to a no-op, so the wrong document is never produced.
DRAFT_MARKERS = {
    "Golden-Hour Freeze Drafter": "freeze / lien-mark request",
    "Refund & MRM Petition Drafter": "refund / restoration petition",
    "Charge-Sheet Drafter": "charge-sheet skeleton",
}


# ── Data loading (flatten a case's CSVs to labelled text, like insurance) ────
def load_case_data(case_id: str) -> str:
    case_dir = CASES_DIR / case_id
    if not case_dir.exists():
        return ""
    parts = []
    for fpath in sorted(case_dir.iterdir()):
        if fpath.suffix == ".csv":
            parts.append(f"\n--- {fpath.stem} ---\n{fpath.read_text(encoding='utf-8').strip()}")
        elif fpath.suffix == ".json":
            data = json.loads(fpath.read_text(encoding="utf-8"))
            parts.append(f"\n--- {fpath.stem} ---\n{json.dumps(data, indent=2)}")
    return "\n".join(parts)


def build_cc1_message() -> str:
    return (
        "Please investigate this cyber-financial-fraud complaint end to end — triage/extract, check for a "
        "mule-account ring, verify records, and prepare whatever documents are appropriate for the officer.\n\n"
        "A citizen reported to the 1930 helpline just minutes ago that money was debited via UPI. The case data:\n"
        f"{load_case_data('CC1')}\n\n"
        "Extract the complaint card, decide the case stage, and route to the right drafter(s)."
    )


def build_cc2_message() -> str:
    return (
        "Please investigate this cyber-financial-fraud complaint end to end — triage/extract, cluster any "
        "mule-account ring, verify the accused, and prepare the appropriate documents for the officer.\n\n"
        "The victim lost Rs 9,40,000 to a 'digital arrest' fraud reported 4 days ago. The beneficiary mule "
        "account, the 40 linked/related complaints, and the mule-account and I4C suspect-registry data are all "
        "attached below (use them as the complaint record):\n"
        f"{load_case_data('CC2')}\n\n"
        "Cluster the ring, verify records, and route to the right drafter(s)."
    )


def build_cc3_message() -> str:
    return (
        "Please work up this cyber-financial-fraud case for filing — extract from the FIR, verify the accused, "
        "and prepare the appropriate documents for the officer.\n\n"
        "FIR 214/2026 is already registered, the accused is identified, and Rs 3,20,000 is already "
        "lien-marked/frozen with the bank. The FIR, the frozen-funds record, the verified-accused record, and the "
        "evidence checklist are attached below (use them as the case record):\n"
        f"{load_case_data('CC3')}\n\n"
        "Decide the case stage and route to the right drafter(s)."
    )


CASE_TESTS = [
    {
        "id": 1,
        "name": "CC1: Live UPI fraud, golden hour, isolated -> Freeze only",
        "build_message": build_cc1_message,
        "expected_agents": [
            "Cyber Complaint Extractor",
            "Fraud-Ring Linker",
            "Records & Registry Verifier",
            "Cyber Case Synthesizer",
        ],
        "produced": ["Golden-Hour Freeze Drafter"],
        "not_produced": ["Refund & MRM Petition Drafter", "Charge-Sheet Drafter"],
        "expected_in_output": ["disclaimer"],
        "min_answer_length": 200,
        "purpose": "Live golden-hour isolated fraud must PRODUCE only the golden-hour freeze; no charge-sheet, no refund.",
    },
    {
        "id": 2,
        "name": "CC2: Mule ring, golden hour expired -> Charge-Sheet",
        "build_message": build_cc2_message,
        "expected_agents": [
            "Cyber Complaint Extractor",
            "Fraud-Ring Linker",
            "Records & Registry Verifier",
            "Cyber Case Synthesizer",
        ],
        "produced": ["Charge-Sheet Drafter"],
        "not_produced": ["Golden-Hour Freeze Drafter", "Refund & MRM Petition Drafter"],
        "expected_in_output": ["ring", "disclaimer"],
        "min_answer_length": 200,
        "purpose": "A linked mule ring past the golden hour must PRODUCE the charge-sheet; no freeze (money gone), no refund (not recovered).",
    },
    {
        "id": 3,
        "name": "CC3: Aged case, funds frozen -> Refund + Charge-Sheet",
        "build_message": build_cc3_message,
        "expected_agents": [
            "Cyber Complaint Extractor",
            "Records & Registry Verifier",
            "Cyber Case Synthesizer",
        ],
        "produced": ["Charge-Sheet Drafter", "Refund & MRM Petition Drafter"],
        "not_produced": ["Golden-Hour Freeze Drafter"],
        "expected_in_output": ["disclaimer"],
        "min_answer_length": 200,
        "purpose": "An aged case with frozen funds must PRODUCE Refund + Charge-Sheet; NO golden-hour freeze (already frozen).",
    },
]

HITL_TESTS = [
    {
        "id": 4,
        "name": "CC4 (HITL): vague one-liner -> Extractor pauses for details",
        "message": (
            "Please investigate: a person called 1930 and said they lost some money to an online scam "
            "yesterday, but they don't remember the account, the amount, or any transaction reference."
        ),
        "expected_agents": ["Cyber Complaint Extractor"],
        "reject_agents": [
            "Golden-Hour Freeze Drafter",
            "Refund & MRM Petition Drafter",
            "Charge-Sheet Drafter",
        ],
        "expect_pause": True,
        "expected_pause_keywords": ["account", "amount"],
        "purpose": "With no usable identifiers the Extractor must pause with [NEEDS_INPUT]; no drafter should run.",
    },
    {
        "id": 5,
        "name": "CC5 (guard): described UPI-fraud complaint but NO data -> Extractor must pause, not fabricate",
        "message": (
            "Please investigate this cyber-fraud complaint (fraud_type: UPI fraud) about a citizen who lost "
            "money to an online scam. Triage/extract the complaint card, check for a mule-account ring, verify "
            "records, and prepare whatever documents are appropriate for the officer. "
            "(I don't have the beneficiary account/UPI, the amount, or any transaction/UTR reference yet.)"
        ),
        "expected_agents": ["Cyber Complaint Extractor"],
        "reject_agents": [
            "Golden-Hour Freeze Drafter",
            "Refund & MRM Petition Drafter",
            "Charge-Sheet Drafter",
        ],
        "expect_pause": True,
        "expected_pause_keywords": ["account"],
        "purpose": "Regression guard for the UI fabrication bug: a described-but-empty complaint (fraud_type + topic + instructions, but NO account/UPI/amount/UTR) must PAUSE with [NEEDS_INPUT] and must NOT fabricate a victim name or amount.",
    },
]


# ── Helpers (proven pattern from test_insurance_claims.py) ───────────────────
def _safe_print(text: str, **kwargs):
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"), **kwargs)


def find_workflow_id() -> int | None:
    resp = api("GET", "workflow")
    if resp.status_code != 200:
        print(f"[ERROR] Could not list workflows: {resp.status_code}")
        return None
    for w in resp.json():
        if w["name"] == WORKFLOW_NAME:
            return w["id"]
    return None


def create_chat_session(agent_id: int = 0) -> str | None:
    resp = api("POST", "converse/create-chat-session", {"agent_id": agent_id})
    if resp.status_code != 200:
        print(f"[ERROR] create chat session: {resp.status_code} {resp.text[:200]}")
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


def _validate_routing(test_def: dict, agents_run: list[str], issues: list[str]) -> None:
    for a in test_def.get("expected_agents", []):
        if a not in agents_run:
            issues.append(f"Expected agent '{a}' did not run")
    for a in test_def.get("reject_agents", []):
        if a in agents_run:
            issues.append(f"WRONG DRAFTER: '{a}' ran but should NOT have for this case")


def run_case_test(test_def: dict, workflow_id: int) -> dict:
    print(f"\n{'='*64}\nTEST #{test_def['id']}: {test_def['name']}\n  {test_def['purpose']}\n{'='*64}")
    issues = []
    message = test_def["build_message"]() if test_def.get("build_message") else test_def.get("message", "")
    sid = create_chat_session()
    if not sid:
        return {"id": test_def["id"], "name": test_def["name"], "status": "FAIL",
                "issues": ["no chat session"], "duration_s": 0, "agents_run": [], "python_executions": 0}

    r = run_workflow_stream(workflow_id, message, sid)
    if r["error"]:
        issues.append(f"stream error: {r['error']}")

    # always-run analysis agents must fire
    for a in test_def.get("expected_agents", []):
        if a not in r["agents_run"]:
            issues.append(f"expected agent '{a}' did not run")

    # PRODUCED: the right drafter(s) must emit their actual document
    for step in test_def.get("produced", []):
        out = r["step_outputs"].get(step, "").lower()
        if DRAFT_MARKERS[step] not in out:
            issues.append(f"expected '{step}' to PRODUCE its document ('{DRAFT_MARKERS[step]}') but it did not (ran={step in r['agents_run']})")

    # NOT PRODUCED (guard rail): wrong-stage drafter(s) must NOT emit a real document
    # (self-gated to a NOT-APPLICABLE no-op, or never invoked)
    for step in test_def.get("not_produced", []):
        out = r["step_outputs"].get(step, "").lower()
        if DRAFT_MARKERS[step] in out:
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
    print(f"  Python execs: {r['python_executions']} | final answer: {len(r['final_answer'])} chars | {r['duration_s']}s")
    for it in issues:
        print(f"  [ISSUE] {it}")
    print(f"  => {status}")
    return {"id": test_def["id"], "name": test_def["name"], "status": status, "issues": issues,
            "duration_s": r["duration_s"], "agents_run": r["agents_run"], "python_executions": r["python_executions"]}


def run_hitl_test(test_def: dict, workflow_id: int) -> dict:
    print(f"\n{'='*64}\nTEST #{test_def['id']}: {test_def['name']}\n  {test_def['purpose']}\n{'='*64}")
    issues = []
    sid = create_chat_session()
    r = run_workflow_stream(workflow_id, test_def["message"], sid)
    if r["error"]:
        issues.append(f"stream error: {r['error']}")
    _validate_routing(test_def, r["agents_run"], issues)
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
    return {"id": test_def["id"], "name": test_def["name"], "status": status, "issues": issues,
            "duration_s": r["duration_s"], "agents_run": r["agents_run"], "python_executions": 0}


def main():
    ap = argparse.ArgumentParser(description="Cybercrime workflow guard-rail tests")
    add_common_args(ap)
    ap.add_argument("--test", type=int, help="run only this case id")
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between cases (in-process pacing)")
    args = ap.parse_args()
    apply_common_args(args)

    wid = find_workflow_id()
    if wid is None:
        print(f"[ERROR] Workflow '{WORKFLOW_NAME}' not found. Deploy 33_cybercrime.json first.")
        return 1
    print(f"Workflow '{WORKFLOW_NAME}' id={wid}")

    all_defs = [(t, run_case_test) for t in CASE_TESTS] + [(t, run_hitl_test) for t in HITL_TESTS]
    if args.test:
        all_defs = [(t, fn) for t, fn in all_defs if t["id"] == args.test]
        if not all_defs:
            print(f"No case with id {args.test}")
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
