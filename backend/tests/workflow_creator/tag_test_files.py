#!/usr/bin/env python3
"""
Append the owning workflow's test-suite + mock-data paths to each gov-workflow agent's
description (so the UI shows which agent belongs to which test files). Description-only;
preserves the system_prompt, tools, labels, starter_messages, and the gpt-4.1 model
override. Idempotent (won't double-append). No prompt/logic changes, no test runs.

    python tag_test_files.py --key <ADMIN_KEY>
"""
import argparse
import sys

from config import add_common_args, api, apply_common_args

MARK = "[Test suite:"  # idempotency marker

# (exact workflow/wrapper name, step-agent prefix, test file, mock-data folder).
# Order matters: the more-specific "WF Cyber2 " rule is BEFORE "WF Cyber " so the
# sequential agents don't get matched by the original Cybercrime rule.
WORKFLOWS = [
    ("Cybercrime Investigation (Sequential)", "WF Cyber2 ", "test_cybercrime_seq.py", "test_data/cybercrime/"),
    ("Cybercrime Investigation", "WF Cyber ", "test_cybercrime.py", "test_data/cybercrime/"),
    ("State Police Charge-Sheet Investigation", "WF Police ", "test_police.py", "test_data/police/"),
    ("Directorate of Prosecutions Scrutiny", "WF Prosecution ", "test_prosecution.py", "test_data/prosecution/"),
    ("CID Economic Offences & AHT Investigation", "WF CID ", "test_cid.py", "test_data/cid/"),
    ("High Court Registry Scrutiny", "WF Registry ", "test_registry.py", "test_data/registry/"),
    ("Land Mutation & ROR Correction", "WF Land ", "test_land.py", "test_data/land/"),
    ("District Collectorate Coordination", "WF Collectorate ", "test_collectorate.py", "test_data/collectorate/"),
    ("Aarogyasri Claim Pre-Authorization", "WF Aarogyasri ", "test_aarogyasri.py", "test_data/aarogyasri/"),
    ("ePASS Post-Matric Scholarship Verification", "WF ePASS ", "test_epass.py", "test_data/epass/"),
]

BASE = "backend/tests/workflow_creator/"


def ref_suffix(test_file: str, folder: str) -> str:
    return f"  [Test suite: {BASE}{test_file}  |  Mock test data: {BASE}{folder}]"


def match(name: str):
    for wname, prefix, tf, folder in WORKFLOWS:
        if name == wname or name.startswith(prefix):
            return tf, folder
    return None


def patch_agent(agent_id: int, new_desc: str) -> int:
    a = api("GET", f"agent/{agent_id}").json()
    body = {
        "name": a["name"],
        "description": new_desc,
        "system_prompt": a.get("system_prompt") or "",
        "task_prompt": a.get("task_prompt") or "",
        "num_chunks": a.get("num_chunks", 0),
        "is_public": a.get("is_public", True),
        "recency_bias": a.get("recency_bias", "base_decay"),
        "llm_filter_extraction": a.get("llm_filter_extraction", False),
        "llm_relevance_filter": a.get("llm_relevance_filter", False),
        "replace_base_system_prompt": a.get("replace_base_system_prompt", True),
        "datetime_aware": a.get("datetime_aware", True),
        "document_set_ids": a.get("document_set_ids", []),
        "tool_ids": sorted(t["id"] for t in a.get("tools", [])),
        "label_ids": sorted(l["id"] for l in a.get("labels", [])),
        "starter_messages": a.get("starter_messages", []),
        "users": [], "groups": [], "hierarchy_node_ids": [],
        "document_ids": [], "knowledge_file_ids": [],
        # PRESERVE the model override (else the PATCH would reset it to the global default)
        "llm_model_provider_override": a.get("llm_model_provider_override"),
        "llm_model_version_override": a.get("llm_model_version_override"),
    }
    return api("PATCH", f"agent/{agent_id}", body).status_code


def main():
    ap = argparse.ArgumentParser(description="Tag gov agents with their test-file paths")
    add_common_args(ap)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    apply_common_args(args)

    resp = api("GET", "agent")
    if resp.status_code != 200:
        print(f"[ERROR] GET agent: {resp.status_code}")
        return 1
    agents = resp.json()

    tagged = skipped = failed = 0
    for a in agents:
        m = match(a["name"])
        if not m:
            continue
        tf, folder = m
        desc = a.get("description") or ""
        if MARK in desc:
            skipped += 1
            continue
        new_desc = desc + ref_suffix(tf, folder)
        if args.dry_run:
            print(f"  [DRY] {a['name']}  +=  {ref_suffix(tf, folder).strip()}")
            tagged += 1
            continue
        code = patch_agent(a["id"], new_desc)
        if code == 200:
            print(f"  [OK] {a['name']:<44} -> {tf}")
            tagged += 1
        else:
            print(f"  [FAIL {code}] {a['name']}")
            failed += 1

    print(f"\n  tagged={tagged}  already-tagged(skipped)={skipped}  failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
