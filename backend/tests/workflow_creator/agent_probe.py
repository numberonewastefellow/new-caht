#!/usr/bin/env python3
"""
agent_probe.py — test individual workflow agents in ISOLATION (agent-first TDD).

Sends one message straight to a single agent (no workflow orchestration) via the
non-streaming chat path and checks the reply's structure. Use this to get each
agent's prompt right BEFORE wiring the full workflow, and to re-verify after edits.

    python agent_probe.py --key <ADMIN_KEY>                 # run all probes, paced
    python agent_probe.py --key <KEY> --agent "Extractor"   # substring filter
    python agent_probe.py --key <KEY> --sleep 8             # inter-probe pacing (default 6s)

Exit code 0 iff every selected probe passes. Reusable across departments — just
extend PROBES with your agent names + expectations.
"""
import argparse
import sys
import time
from urllib.parse import urljoin

import requests

from config import CONFIG, add_common_args, api, apply_common_args, headers


def send_to_agent(agent_id: int, message: str, timeout: int = 300) -> dict:
    """One-shot: create a session bound to agent_id and send message (non-streaming)."""
    url = urljoin(CONFIG["base_url"] + "/", "api/converse/send-chat-message")
    body = {
        "message": message,
        "chat_session_info": {"agent_id": agent_id},
        "stream": False,
    }
    resp = requests.post(url, headers=headers(), json=body, timeout=timeout)
    if resp.status_code != 200:
        return {"_http": resp.status_code, "_text": resp.text[:400], "answer": ""}
    return resp.json()


_agent_ids: dict[str, int] = {}


def resolve_agents() -> dict[str, int]:
    if not _agent_ids:
        r = api("GET", "agent")
        if r.status_code == 200:
            for a in r.json():
                _agent_ids[a["name"]] = a["id"]
    return _agent_ids


# ── Probe definitions ────────────────────────────────────────────────────────
# Each: agent (exact name), label, message, and checks:
#   contains        = ALL of these case-insensitive substrings must appear
#   status_complete = require 'STATUS: COMPLETE'
#   needs_input     = require the reply to START with [NEEDS_INPUT]
#   min_len         = minimum answer length

_REG_EXTRACT = (
    "\n\n--- suspect_registry (I4C) ---\n"
    "account,upi,flag,record_id\n"
    "50100123456,fraudster@ybl,LAYER1_MULE_FLAGGED,SR-2026-88123\n"
)
_RELATED = (
    "\n\n--- related_complaints ---\n"
    "complaint_id,beneficiary_account,upi,amount\n"
    "NCRP-2026-0455123,50100123456,fraudster@ybl,180000\n"
    "NCRP-2026-0455777,50100123456,fraudster@ybl,240000\n"
    "NCRP-2026-0456001,50100123456,scammer@okaxis,95000\n"
)

PROBES = [
    {
        "agent": "WF Cyber Complaint Extractor",
        "label": "extractor / live golden-hour",
        "message": (
            "Investigate this 1930/NCRP complaint. NCRP-2026-0455123, reported 22 minutes ago. "
            "Victim Ramesh K, Hyderabad lost Rs 1,80,000 via UPI to fraudster@ybl, beneficiary "
            "A/C 50100123456 HDFC IFSC HDFC0000123, fraudster phone +918612345678, UTR 412345678901 "
            "at 14:32 today. Money not yet frozen. Screenshot only."
        ),
        "contains": ["complaint card", "case stage", "recommended drafters", "golden"],
        "status_complete": True,
        "min_len": 200,
    },
    {
        "agent": "WF Cyber Complaint Extractor",
        "label": "extractor / HITL sparse",
        "message": "A woman says she lost some money to an online scam yesterday but doesn't remember any account, amount, or transaction details.",
        "needs_input": True,
        "min_len": 30,
    },
    {
        "agent": "WF Cyber Fraud-Ring Linker",
        "label": "linker / ring found",
        "message": (
            "Complaint card: seed NCRP-2026-0455123, beneficiary A/C 50100123456, UPI fraudster@ybl, "
            "amount 180000. Cluster against the related complaints and reconstruct the layering." + _RELATED
        ),
        "contains": ["ring found", "50100123456"],
        "status_complete": True,
        "min_len": 150,
    },
    {
        "agent": "WF Cyber Records Verifier",
        "label": "verifier / registry hit",
        "message": (
            "Verify accused beneficiary A/C 50100123456 / UPI fraudster@ybl for NCRP-2026-0455123 "
            "(victim in Hyderabad). Resolve the owning cyber PS and the bank nodal for a freeze." + _REG_EXTRACT
        ),
        "contains": ["suspect registry", "accused verified"],
        "status_complete": True,
        "min_len": 150,
    },
    {
        "agent": "WF Cyber Golden-Hour Freeze Drafter",
        "label": "freeze drafter",
        "message": (
            "Verified: beneficiary A/C 50100123456 @ HDFC (IFSC HDFC0000123), Rs 1,80,000 fraudulently "
            "credited 25 minutes ago, NCRP-2026-0455123, owning PS Cyber Crime PS Hyderabad. Draft the "
            "golden-hour freeze request."
        ),
        "contains": ["freeze", "lien", "50100123456"],
        "status_complete": True,
        "min_len": 150,
    },
    {
        "agent": "WF Cyber Refund Petition Drafter",
        "label": "refund drafter",
        "message": (
            "FIR 214/2026. Rs 3,20,000 already lien-marked/frozen at HDFC A/C 50100123456. Victim account "
            "beneficiary Ramesh K A/C 60200999888 SBI. Court-ordered refund pending. Draft the MRM/court "
            "restoration petition."
        ),
        "contains": ["refund", "petition"],
        "status_complete": True,
        "min_len": 150,
    },
    {
        "agent": "WF Cyber Charge-Sheet Drafter",
        "label": "charge-sheet drafter",
        "message": (
            "Verified cyber-fraud case FIR 214/2026, PS Cyber Crime Hyderabad. Accused Anil M (verified, "
            "Layer-1 mule A/C 50100123456), arrested 2026-07-01. UPI cheating-by-personation, part of a "
            "40-complaint ring. Bank statements + CDR obtained; 65B certificate pending. Draft the charge-sheet skeleton."
        ),
        "contains": ["charge-sheet", "66c", "66d", "bns", "65b"],
        "status_complete": True,
        "min_len": 250,
    },
    {
        "agent": "WF Cyber Case Synthesizer",
        "label": "synthesizer",
        "message": (
            "Assemble the case file. Stage LIVE_GOLDEN_HOUR; ring ISOLATED; accused not yet verified; funds not "
            "frozen. Drafts produced upstream: a Golden-Hour Freeze Request. Owning PS: Cyber Crime PS Hyderabad."
        ),
        "contains": ["case file", "disclaimer", "assignment"],
        "status_complete": True,
        "min_len": 150,
    },
]


def check(ans: str, p: dict) -> list[str]:
    issues = []
    low = ans.lower()
    if p.get("needs_input"):
        if not ans.lstrip().startswith("[NEEDS_INPUT]"):
            issues.append("expected reply to START with [NEEDS_INPUT]")
    for sub in p.get("contains", []):
        if sub.lower() not in low:
            issues.append(f"missing substring: {sub!r}")
    if p.get("status_complete") and "status: complete" not in low:
        issues.append("missing 'STATUS: COMPLETE'")
    if len(ans) < p.get("min_len", 0):
        issues.append(f"answer too short ({len(ans)} < {p['min_len']})")
    return issues


def main():
    ap = argparse.ArgumentParser(description="Probe individual workflow agents")
    add_common_args(ap)
    ap.add_argument("--agent", help="substring filter on agent name/label")
    ap.add_argument("--sleep", type=float, default=6.0, help="seconds between probes (rate-limit pacing)")
    args = ap.parse_args()
    apply_common_args(args)

    ids = resolve_agents()
    probes = PROBES
    if args.agent:
        f = args.agent.lower()
        probes = [p for p in PROBES if f in p["agent"].lower() or f in p["label"].lower()]
    if not probes:
        print("No probes matched filter.")
        return 1

    results = []
    for i, p in enumerate(probes):
        aid = ids.get(p["agent"])
        print(f"\n=== [{i+1}/{len(probes)}] {p['label']}  ->  {p['agent']} (id={aid}) ===")
        if aid is None:
            print("  [FAIL] agent not found on server")
            results.append((p["label"], False, "agent not found"))
            continue
        t0 = time.time()
        resp = send_to_agent(aid, p["message"])
        dt = round(time.time() - t0, 1)
        if "_http" in resp:
            print(f"  [FAIL] HTTP {resp['_http']}: {resp.get('_text','')[:200]}")
            results.append((p["label"], False, f"HTTP {resp['_http']}"))
            continue
        ans = resp.get("answer") or ""
        err = resp.get("error_msg")
        if err:
            print(f"  [WARN] error_msg: {err}")
        issues = check(ans, p)
        status = "PASS" if not issues else "FAIL"
        print(f"  {status} in {dt}s | answer {len(ans)} chars")
        print("  --- answer (first 600 chars) ---")
        print("  " + ans[:600].replace("\n", "\n  "))
        if issues:
            for it in issues:
                print(f"  [ISSUE] {it}")
        results.append((p["label"], not issues, "; ".join(issues)))
        if i < len(probes) - 1:
            time.sleep(args.sleep)

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    for label, ok, note in results:
        print(f"  [{'OK' if ok else 'FAIL'}] {label}" + (f"  -- {note}" if note else ""))
    print(f"\n  Total: {len(results)} | {passed} passed | {len(results)-passed} failed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
