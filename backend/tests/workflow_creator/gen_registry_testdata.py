#!/usr/bin/env python3
"""
Mock test data for the High Court Registry Scrutiny workflow -> test_data/registry/{HC1,HC2,HC3}/*.csv.
Presence/absence + explicit status fields cue the REGISTRY STAGE and thus which drafter should PRODUCE:
  HC1 DEFECTIVE_FILING     (court fee short, welfare stamp + certified copy missing, index defect) -> Registry Objection Memo
  HC2 READY_FOR_LISTING    (all requisites complete, no defects, pending registration)             -> Registration & Listing Note
  HC3 JUDGMENT_FOR_HEADNOTE (a DISPOSED matter — judgment pronounced, operative portion present)   -> Draft Headnote
HC4 (HITL) is a vague one-liner with NO filing data -> the Extractor pauses [NEEDS_INPUT] (no CSV needed).
All data is MOCK. The Registry is CLERICAL ONLY — none of this touches the merits of any case.
"""
from pathlib import Path

BASE = Path(__file__).parent / "test_data" / "registry"

FILES = {
    # ── HC1: fresh filing with curable defects -> Registry Objection Memo ─────
    "HC1/filing.csv": (
        "field,value\n"
        "cause_title,Sharma vs State of Telangana\n"
        "case_type,Writ Petition (fresh filing)\n"
        "case_number,not yet numbered (under scrutiny)\n"
        "court,High Court for the State of Telangana\n"
        "filed_date,2026-07-28\n"
        "category,Writ - service matter\n"
        "prayer,Challenge to a departmental transfer order (clerical description only)\n"
        "disposition,UNDER SCRUTINY (fresh filing; no judgment pronounced)\n"
    ),
    "HC1/scrutiny_checklist.csv": (
        "item,status,rule\n"
        "Court fee,SHORT - paid Rs 500 but Rs 1000 required (deficit Rs 500),Court-fee schedule\n"
        "Welfare stamp on vakalatnama,MISSING,Advocates' Welfare Fund Act / vakalatnama rules\n"
        "Certified copy of impugned order,NOT ANNEXED,Appellate-side / e-Filing rules\n"
        "Index & pagination,DEFECTIVE - annexures not indexed and pages unnumbered,CPC Order VI/VII\n"
        "Cause-title format,OK,CPC Order VII\n"
        "Limitation,WITHIN TIME (filed on day 32 of a 90-day period),Limitation Act\n"
        "Affidavit,Sworn,e-Filing rules\n"
    ),
    "HC1/annexures.csv": (
        "annexure,description,indexed\n"
        "A,Copy of the transfer order under challenge,NO\n"
        "B,Representation submitted by the petitioner,NO\n"
    ),
    "HC1/prior_filings.csv": (
        "cnr,case_number,parties,impugned_order,note\n"
        "TSHC010000002026,-,No prior matter found for these parties,-,No connected matter on record\n"
    ),

    # ── HC2: clean, ready filing -> Registration & Listing Note ──────────────
    "HC2/filing.csv": (
        "field,value\n"
        "cause_title,Reddy vs Municipal Corporation of Hyderabad\n"
        "case_type,Writ Appeal (fresh filing)\n"
        "case_number,not yet numbered (pending registration)\n"
        "court,High Court for the State of Telangana\n"
        "filed_date,2026-07-30\n"
        "category,Writ Appeal - municipal / property\n"
        "prayer,Appeal against a single-judge order (clerical description only)\n"
        "disposition,PENDING REGISTRATION (fresh filing; no judgment pronounced)\n"
    ),
    "HC2/scrutiny_checklist.csv": (
        "item,status,rule\n"
        "Court fee,OK - Rs 2000 paid and sufficient for the stated valuation,Court-fee schedule\n"
        "Welfare stamp on vakalatnama,AFFIXED,Advocates' Welfare Fund Act / vakalatnama rules\n"
        "Certified copy of impugned order,ANNEXED,Appellate-side / e-Filing rules\n"
        "Index & pagination,OK - annexures indexed and pages numbered,CPC Order VI/VII\n"
        "Cause-title format,OK,CPC Order VII\n"
        "Limitation,WITHIN TIME (filed on day 20 of a 90-day period),Limitation Act\n"
        "Affidavit,Sworn,e-Filing rules\n"
        "Overall,NO DEFECTS - requisites complete; ready for registration and listing,-\n"
    ),
    "HC2/prior_filings.csv": (
        "cnr,case_number,parties,impugned_order,note\n"
        "TSHC010044552026,WP 3321/2026,Reddy vs Municipal Corporation of Hyderabad,Order dated 2026-05-10 in WP 3321/2026,Connected - same parties and the SAME impugned order; tag to be listed together\n"
        "TSHC010049992026,WP 3980/2026,Reddy vs Municipal Corporation of Hyderabad,Order dated 2026-05-10 in WP 3321/2026,Analogous - same parties challenging the same order\n"
    ),
    "HC2/citations_in_filing.csv": (
        "citation_string,type\n"
        "2023 INSC 210,Neutral citation (Supreme Court)\n"
        "(2019) 5 SCC 344,Reporter citation\n"
    ),

    # ── HC3: DISPOSED matter, judgment pronounced -> Draft Headnote ──────────
    "HC3/judgment.csv": (
        "field,value\n"
        "cause_title,Verma vs State of Andhra Pradesh\n"
        "case_number,Writ Petition No. 4412 of 2025\n"
        "court,High Court for the State of Andhra Pradesh\n"
        "disposition,DISPOSED - judgment pronounced in open court\n"
        "judgment_date,2026-06-15\n"
        "coram,Division Bench (Hon'ble the Chief Justice and Hon'ble Justice A. Rao)\n"
        "neutral_citation,to be assigned (YYYY APHC n family)\n"
        "subject,Service law - regularisation of daily-wage employees\n"
    ),
    "HC3/operative_portion.csv": (
        "para,text\n"
        "1,The petitioner challenged the denial of regularisation after 10 years of continuous daily-wage service.\n"
        "2,Holding: the Court held that continuous service beyond the sanctioned period entitles the employee to consideration for regularisation under the applicable scheme.\n"
        "3,Operative order: the writ petition is ALLOWED; the respondents are directed to consider the petitioner's case for regularisation within three months. No costs.\n"
    ),
    "HC3/catchwords_source.csv": (
        "keyword\n"
        "Service law\n"
        "Regularisation\n"
        "Daily-wage employee\n"
        "Continuous service\n"
    ),
}

README = """# High Court Registry Scrutiny workflow — mock test data

One folder per case; one CSV per source (all MOCK). The scrutiny/status fields cue the REGISTRY STAGE
and thus which drafter should PRODUCE its clerical document (the guard rail in `test_registry.py`).
The Registry is CLERICAL ONLY — none of this touches the merits of any case.

| Case | Stage signal | Expected drafter | Rejected drafters |
|------|--------------|------------------|-------------------|
| HC1 | fresh filing; court fee short + welfare stamp/certified copy missing + index defect | Defect Memo Drafter | Cause-List Entry; Judgment Headnote |
| HC2 | fresh filing; all requisites complete, NO defects, pending registration | Cause-List Entry Drafter | Defect Memo; Judgment Headnote |
| HC3 | DISPOSED matter; judgment pronounced + operative portion present | Judgment Headnote Drafter | Defect Memo; Cause-List Entry |
| HC4 | vague one-liner, no filing data (HITL) | (Extractor pauses [NEEDS_INPUT]) | all drafters |

Always-run: Filing Extractor, Connected-Matter Checker, Defect Verifier, Registry Synthesizer.
"""


def main():
    for rel, content in FILES.items():
        p = BASE / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (BASE / "README.md").write_text(README, encoding="utf-8")
    print(f"[OK] wrote {len(FILES)} CSVs + README under {BASE}")
    for case in ("HC1", "HC2", "HC3"):
        print(f"  {case}: {sorted(f.name for f in (BASE / case).iterdir())}")


if __name__ == "__main__":
    main()
