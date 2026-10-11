#!/usr/bin/env python3
"""
Cybercrime Investigation (Sequential) — guard-rail test suite.

Tests the SEQUENTIAL re-build of the Cybercrime workflow (gen_cyber2_workflow.py /
42_cyber2.json), the sibling of the original llm_decision "Cybercrime Investigation".

Same deterministic pattern as test_police.py / test_registry.py: all 7 steps run every
case, each drafter SELF-GATES on the Extractor's RECOMMENDED DRAFTERS line (forced
gate-check preamble), and the test asserts on what each drafter actually PRODUCED — a
distinctive document HEADER captured per-step from the SSE stream — so orchestrator/engine
over-firing is harmless (a wrong-stage drafter's name-free no-op never trips the marker).

  CC1  live golden-hour, isolated  -> Golden-Hour Freeze Request      (reject Refund, Charge-Sheet)
  CC2  mule ring, golden-hour gone -> Charge-Sheet Skeleton           (reject Freeze, Refund)
  CC3  aged, funds frozen          -> Refund Petition + Charge-Sheet  (reject Freeze)
  CC4  vague one-liner (HITL)      -> Extractor pauses [NEEDS_INPUT]

Reuses the existing mock data in test_data/cybercrime/{CC1,CC2,CC3}.

Usage: python test_cybercrime_seq.py --key <KEY> [--test N] ; pace cases with an external sleep.
Exit code 0 iff all selected cases pass.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from config import add_common_args, api, apply_common_args, stream_api

WORKFLOW_NAME = "Cybercrime Investigation (Sequential)"
CASES_DIR = Path(__file__).parent / "test_data" / "cybercrime"

# Each marker is the drafter's real document HEADER, verified (see _verify_markers) to be
# NOT a substring of any drafter STEP NAME (which the forced GATE CHECK line echoes) and
# NOT a substring of another drafter's header. Captured per-step, so a wrong-stage drafter's
# name-free "NOT APPLICABLE ..." no-op never trips these.
DRAFT_MARKERS = {
    "Golden-Hour Freeze Drafter": "freeze / lien-mark request",
    "Refund Petition Drafter": "refund / restoration petition",
    "Charge-Sheet Drafter": "charge-sheet skeleton",
}

# Drafter step names as they appear in the workflow (used to prove marker != name).
_DRAFTER_STEP_NAMES = list(DRAFT_MARKERS.keys())

# Always-run analysis/synthesis steps (fire on every case in sequential mode).
_ANALYSIS_STEPS = ["Complaint Extractor", "Fraud-Ring Linker", "Records Verifier", "Case Synthesizer"]


def _verify_markers() -> list[str]:
    """Guard against the #1 failure mode: a marker being a substring of any drafter step name
    (which the GATE CHECK preamble echoes) or of another drafter's marker. Empty == OK."""
    problems = []
    names_lc = [n.lower() for n in _DRAFTER_STEP_NAMES]
    markers = {k: v.lower() for k, v in DRAFT_MARKERS.items()}
    for step, marker in markers.items():
        for nm in names_lc:
            if marker in nm:
                problems.append(f"marker '{marker}' is a substring of step name '{nm}'")
        for other_step, other_marker in markers.items():
            if other_step != step and marker in other_marker:
                problems.append(f"marker '{marker}' is a substring of another marker '{other_marker}'")
    return problems


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
        "expected_agents": _ANALYSIS_STEPS,
        "produced": ["Golden-Hour Freeze Drafter"],
        "not_produced": ["Refund Petition Drafter", "Charge-Sheet Drafter"],
        "expected_in_output": ["disclaimer"],
        "min_answer_length": 200,
        "purpose": "Live golden-hour isolated fraud must PRODUCE only the golden-hour freeze; no charge-sheet, no refund.",
    },
    {
        "id": 2,
        "name": "CC2: Mule ring, golden hour expired -> Charge-Sheet",
        "build_message": build_cc2_message,
        "expected_agents": _ANALYSIS_STEPS,
        "produced": ["Charge-Sheet Drafter"],
        "not_produced": ["Golden-Hour Freeze Drafter", "Refund Petition Drafter"],
        "expected_in_output": ["ring", "disclaimer"],
        "min_answer_length": 200,
        "purpose": "A linked mule ring past the golden hour must PRODUCE the charge-sheet; no freeze (money gone), no refund (not recovered).",
    },
    {
        "id": 3,
        "name": "CC3: Aged case, funds frozen -> Refund + Charge-Sheet",
        "build_message": build_cc3_message,
        "expected_agents": _ANALYSIS_STEPS,
        "produced": ["Charge-Sheet Drafter", "Refund Petition Drafter"],
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
        "expected_agents": ["Complaint Extractor"],
        "reject_agents": [
            "Golden-Hour Freeze Drafter",
            "Refund Petition Drafter",
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
        "expected_agents": ["Complaint Extractor"],
        "reject_agents": [
            "Golden-Hour Freeze Drafter",
            "Refund Petition Drafter",
            "Charge-Sheet Drafter",
        ],
        "expect_pause": True,
        "expected_pause_keywords": ["account"],
        "purpose": "Regression guard for the UI fabrication bug: a described-but-empty complaint (fraud_type + topic + instructions, but NO account/UPI/amount/UTR) must PAUSE with [NEEDS_INPUT] and must NOT fabricate a victim name or amount.",
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
    print(f"  Python execs: {r['python_executions']} | final answer: {len(r['final_answer'])} chars | {r['duration_s']}s")
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
    ap = argparse.ArgumentParser(description="Cybercrime (Sequential) workflow guard-rail tests")
    add_common_args(ap)
    ap.add_argument("--test", type=int)
    ap.add_argument("--sleep", type=float, default=0.0)
    args = ap.parse_args()
    apply_common_args(args)

    marker_problems = _verify_markers()
    if marker_problems:
        print("[ERROR] DRAFT_MARKERS failed the marker!=name self-check:")
        for p in marker_problems:
            print(f"  - {p}")
        return 1

    wid = find_workflow_id()
    if wid is None:
        print(f"[ERROR] Workflow '{WORKFLOW_NAME}' not found. Deploy 42_cyber2.json first.")
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
