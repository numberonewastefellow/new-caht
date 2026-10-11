#!/usr/bin/env python3
"""
Re-scope the test-data description tags added by tag_test_files.py.

Problem it fixes: tag_test_files.py appended a "[Test suite: ... | Mock test data: ...]" tag to EVERY
gov agent, including internal STEP agents. That invited testing a step agent standalone (e.g. chatting
"WF Cyber2 Case Synthesizer" directly), which — having no upstream step outputs — fabricates a case.

This script:
  * STEP agents  (name starts with "WF <Dept> ")  -> strip the "[Test suite: ...]" tag and append
        "[Internal step of the '<Workflow>' workflow - run the workflow directly, not this agent standalone]"
  * WRAPPER agents (the workflow-named ones)       -> left untouched (they KEEP the test-data tag).

Full-body PATCH mirrors tag_test_files.py: preserves system_prompt, tools, starter_messages and the
per-agent gpt-4.1 model override. Idempotent (skips a step already carrying the internal-step note).

Usage: python fix_agent_tags.py --key <ADMIN_KEY> [--dry-run]
"""
import argparse
import sys

from config import add_common_args, api, apply_common_args

TESTSUITE_MARK = "[Test suite:"       # the tag added by tag_test_files.py
STEP_MARK = "[Internal step of"       # idempotency marker for this script

# (wrapper name, step-agent prefix). Order matters: "WF Cyber2 " BEFORE "WF Cyber " so the sequential
# steps are not swallowed by the original-Cybercrime rule.
WORKFLOWS = [
    ("Cybercrime Investigation (Sequential)", "WF Cyber2 "),
    ("Cybercrime Investigation", "WF Cyber "),
    ("State Police Charge-Sheet Investigation", "WF Police "),
    ("Directorate of Prosecutions Scrutiny", "WF Prosecution "),
    ("CID Economic Offences & AHT Investigation", "WF CID "),
    ("High Court Registry Scrutiny", "WF Registry "),
    ("Land Mutation & ROR Correction", "WF Land "),
    ("District Collectorate Coordination", "WF Collectorate "),
    ("Aarogyasri Claim Pre-Authorization", "WF Aarogyasri "),
    ("ePASS Post-Matric Scholarship Verification", "WF ePASS "),
]


def match_step(name: str):
    """Return the owning workflow name if `name` is a gov STEP agent, else None."""
    for wname, prefix in WORKFLOWS:
        if name.startswith(prefix):
            return wname
    return None


def strip_testsuite_tag(desc: str) -> str:
    idx = desc.find(TESTSUITE_MARK)
    return desc[:idx].rstrip() if idx != -1 else desc.rstrip()


def patch_desc(agent_id: int, new_desc: str) -> int:
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
        "llm_model_provider_override": a.get("llm_model_provider_override"),
        "llm_model_version_override": a.get("llm_model_version_override"),
    }
    return api("PATCH", f"agent/{agent_id}", body).status_code


def main():
    ap = argparse.ArgumentParser(description="Mark gov STEP agents as internal (not for standalone use)")
    add_common_args(ap)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    apply_common_args(args)

    resp = api("GET", "agent")
    if resp.status_code != 200:
        print(f"[ERROR] GET agent: {resp.status_code}")
        return 1
    agents = resp.json()

    fixed = skipped = failed = 0
    for a in agents:
        wname = match_step(a["name"])
        if not wname:
            continue  # not a gov step agent (wrappers and non-gov agents untouched)
        desc = a.get("description") or ""
        if STEP_MARK in desc:
            skipped += 1
            continue
        new_desc = strip_testsuite_tag(desc) + (
            f"  [Internal step of the '{wname}' workflow - run the workflow directly, "
            f"not this agent standalone]"
        )
        if args.dry_run:
            print(f"  [DRY] {a['name']:<44} -> internal-step note")
            fixed += 1
            continue
        code = patch_desc(a["id"], new_desc)
        if code == 200:
            print(f"  [OK] {a['name']:<44} -> {wname}")
            fixed += 1
        else:
            print(f"  [FAIL {code}] {a['name']}")
            failed += 1

    print(f"\n  fixed={fixed}  already-marked(skipped)={skipped}  failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
