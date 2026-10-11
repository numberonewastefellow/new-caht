#!/usr/bin/env python3
"""
Append ONE "upload the case file" starter to each gov workflow WRAPPER agent, so the UI can demo
the file-upload flow (attach the case documents) ALONGSIDE the existing quick-demo starters.

Why this is safe / agent-config only:
- Full-body PATCH mirrors tag_test_files.py: preserves system_prompt, task_prompt, tools, labels,
  the EXISTING starter_messages, and the per-agent gpt-4.1 model override (llm_model_version_override).
- Only starter_messages is changed (one appended object). No prompt/logic/model change. Idempotent:
  re-running skips any wrapper that already has an upload starter (name begins with the paperclip mark).

The new starter is a THIN request that NAMES the case documents and expects an attachment:
  * clicked WITH files -> the workflow's Extractor reads the inlined file text and runs end-to-end;
  * clicked WITHOUT files -> the Extractor's existing anti-fabrication HITL asks which files to upload.

Usage:
  python add_file_upload_starter.py --key <ADMIN_KEY> --only "District Collectorate Coordination"   # one
  python add_file_upload_starter.py --key <ADMIN_KEY>                                                # all
  python add_file_upload_starter.py --key <ADMIN_KEY> --dry-run
"""
import argparse
import sys

from config import add_common_args, api, apply_common_args

UPLOAD_MARK = "\U0001F4CE Upload"  # paperclip; idempotency marker on the starter NAME

# Common tail appended to every message: names the pause behaviour so a no-file click demos HITL.
_NOFILE = (
    " If I have NOT attached the documents, do not guess or invent any details — pause and tell me "
    "exactly which files to upload."
)

# wrapper agent name -> (starter name, starter message). Message lists the case docs for THAT workflow
# (mirrors the files in backend/tests/workflow_creator/test_data/<dept>/<case>/).
UPLOAD_STARTERS = {
    "Cybercrime Investigation": (
        "\U0001F4CE Upload complaint & investigate",
        "Please investigate this cybercrime complaint. I am attaching the case file — the NCRP "
        "complaint, the victim's statement and the transaction/money trail (plus the mule-account list, "
        "related complaints and CDR/IPDR if it is a fraud ring). Extract the complaint, link any ring, "
        "verify records, and prepare the officer's case file with the right drafts." + _NOFILE,
    ),
    "Cybercrime Investigation (Sequential)": (
        "\U0001F4CE Upload complaint & investigate",
        "Please investigate this cybercrime complaint. I am attaching the case file — the NCRP "
        "complaint, the victim's statement and the transaction/money trail (plus the mule-account list, "
        "related complaints and CDR/IPDR if it is a fraud ring). Extract the complaint, link any ring, "
        "verify records, and prepare the officer's case file with the right drafts." + _NOFILE,
    ),
    "State Police Charge-Sheet Investigation": (
        "\U0001F4CE Upload charge-sheet & scrutinise",
        "Please scrutinise this charge-sheet before filing. I am attaching the case file — the FIR, "
        "the case diary, the BNSS compliance sheet, the witness list and the seizure memo. Extract the "
        "case, check antecedents, verify BNSS compliance, and prepare the appropriate document." + _NOFILE,
    ),
    "Directorate of Prosecutions Scrutiny": (
        "\U0001F4CE Upload charge-sheet & scrutinise",
        "Please scrutinise this police charge-sheet for filing. I am attaching the file — the "
        "charge-sheet, the evidence-completeness sheet, the witness list and the evidence inventory. "
        "Extract the case skeleton, check completeness, verify sufficiency and the sections, and prepare "
        "the appropriate prosecution document." + _NOFILE,
    ),
    "CID Economic Offences & AHT Investigation": (
        "\U0001F4CE Upload case & investigate",
        "Please investigate this economic-offence / AHT case. I am attaching the file — the FIR, the "
        "depositor/victim list, the bank statements and the shell-entity list. Extract the case, map the "
        "entities and fund flow, verify records, and prepare the appropriate report." + _NOFILE,
    ),
    "High Court Registry Scrutiny": (
        "\U0001F4CE Upload filing & scrutinise",
        "Please scrutinise this filing for the High Court Registry. I am attaching the papers — the "
        "filing/petition, its annexures, the scrutiny checklist and any connected/prior filings (or the "
        "judgment + operative portion for a headnote). Extract the filing, check connected matters, verify "
        "defects, and prepare the appropriate clerical output." + _NOFILE,
    ),
    "Land Mutation & ROR Correction": (
        "\U0001F4CE Upload application & process",
        "Please process this land mutation / RoR item. I am attaching the file — the application, the "
        "registered deed, the RoR (1-B), the chain of title (and the prohibited-property list / passbook if "
        "relevant). Extract the application, check the chain of title, verify the record, and prepare the "
        "appropriate order/memo." + _NOFILE,
    ),
    "District Collectorate Coordination": (
        "\U0001F4CE Upload reference & coordinate",
        "Please handle this coordination item for the Collector. I am attaching the case file — the "
        "reference/intake sheet, the department action-status feed, the forwarding letter and the "
        "prior-reference (duplicate) check. Extract the intake sheet, verify the owning department and its "
        "status, and prepare the appropriate coordination document." + _NOFILE,
    ),
    "Aarogyasri Claim Pre-Authorization": (
        "\U0001F4CE Upload preauth & review",
        "Please pre-authorise this Aarogyasri claim. I am attaching the packet — the e-preauth request, "
        "the benefit/eligibility record, the package master/rate card and the mandatory-investigation "
        "checklist. Extract the case, verify eligibility and benefit balance, check the package for "
        "upcoding, and prepare the appropriate note (patient data is mock)." + _NOFILE,
    ),
    "ePASS Post-Matric Scholarship Verification": (
        "\U0001F4CE Upload application & verify",
        "Please verify this post-matric scholarship application. I am attaching the file — the "
        "application, the caste/income certificates, the institution (U-DISE/AISHE) record, the bank "
        "details and the duplicate/ghost screening. Extract the application, screen for duplicates, verify "
        "eligibility and the institution, and prepare the appropriate proceedings." + _NOFILE,
    ),
    "Insurance Claims Investigation": (
        "\U0001F4CE Upload claim & investigate",
        "Please investigate this insurance claim. I am attaching the file — the FNOL intake, the policy "
        "declarations, the loss/investigation report, the contractor estimates, the room-by-room damage "
        "inventory and the prior-claims history. Triage the claim, assess damage, verify coverage, check for "
        "red flags, and produce a settlement recommendation." + _NOFILE,
    ),
}


def _safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(text.encode(enc, "replace").decode(enc, "replace"))


def patch_starters(agent_id: int, starters: list) -> int:
    a = api("GET", f"agent/{agent_id}").json()
    body = {
        "name": a["name"],
        "description": a.get("description") or "",
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
        "starter_messages": starters,
        "users": [], "groups": [], "hierarchy_node_ids": [],
        "document_ids": [], "knowledge_file_ids": [],
        # PRESERVE the model override (else the PATCH resets it to the global default)
        "llm_model_provider_override": a.get("llm_model_provider_override"),
        "llm_model_version_override": a.get("llm_model_version_override"),
    }
    return api("PATCH", f"agent/{agent_id}", body).status_code


def main():
    ap = argparse.ArgumentParser(description="Append an upload-the-file starter to gov workflow wrappers")
    add_common_args(ap)
    ap.add_argument("--only", help="exact wrapper name to target (e.g. 'District Collectorate Coordination')")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    apply_common_args(args)

    resp = api("GET", "agent")
    if resp.status_code != 200:
        print(f"[ERROR] GET agent: {resp.status_code}")
        return 1
    agents = resp.json()

    added = skipped = failed = 0
    for a in agents:
        name = a["name"]
        if name not in UPLOAD_STARTERS:
            continue
        if args.only and name != args.only:
            continue
        starters = list(a.get("starter_messages") or [])
        if any((s.get("name") or "").startswith(UPLOAD_MARK) for s in starters):
            skipped += 1
            continue
        sname, smsg = UPLOAD_STARTERS[name]
        new_starters = starters + [{"name": sname, "message": smsg}]
        if args.dry_run:
            _safe_print(f"  [DRY] {name}: +1 upload starter (now {len(new_starters)})")
            added += 1
            continue
        code = patch_starters(a["id"], new_starters)
        if code == 200:
            _safe_print(f"  [OK] {name:<46} -> {len(new_starters)} starters")
            added += 1
        else:
            _safe_print(f"  [FAIL {code}] {name}")
            failed += 1

    print(f"\n  added={added}  already-had(skipped)={skipped}  failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
