#!/usr/bin/env python3
"""
Mock test data for the Aarogyasri Claim Pre-Authorization workflow -> test_data/aarogyasri/{AR1,AR2,AR3}/*.csv.
Explicit, unambiguous checklist/status fields cue the PRE-AUTH DECISION and thus which drafter should PRODUCE:
  AR1 APPROVE  (in-package, matches diagnosis, investigations complete, within benefit) -> Approval Note
  AR2 QUERY    (mandatory Knee X-ray report missing; otherwise in order, curable)       -> Query Memo
  AR3 REJECT   (upcoding: major laparotomy billed for an appendicitis -> appendectomy)  -> Rejection Note
All patient data is MOCK / SYNTHETIC (no real PHI, no real names/IDs).
"""
from pathlib import Path

BASE = Path(__file__).parent / "test_data" / "aarogyasri"

FILES = {
    # ── AR1: clean, in-package, within benefit -> Approval Note ───────────────
    "AR1/preauth.csv": (
        "field,value\n"
        "preauth_id,PA-AR-2026-1001\n"
        "beneficiary_card,ASRI-XXXX-1001 (mock)\n"
        "patient,Patient A (mock; 58M)\n"
        "diagnosis,Acute ST-elevation myocardial infarction (STEMI)\n"
        "icd_code,I21.0\n"
        "proposed_package_code,AS-CARD-012\n"
        "proposed_package_name,PTCA with single drug-eluting stent\n"
        "specialty,Cardiology\n"
        "cost_estimate,90000\n"
        "investigations_uploaded,ECG; Troponin-I; Coronary Angiogram\n"
        "clinical_justification,Single-vessel LAD occlusion on angiogram; primary PCI indicated\n"
        "emergency,NO\n"
        "doc_completeness,COMPLETE\n"
    ),
    "AR1/master.csv": (
        "package_code,package_name,specialty,rate_min,rate_max,mandatory_investigations,diagnosis_appropriate_for\n"
        "AS-CARD-012,PTCA with single drug-eluting stent,Cardiology,80000,95000,ECG|Troponin-I|Coronary Angiogram,STEMI / single-vessel coronary block (I21.x)\n"
        "AS-CARD-020,CABG (coronary bypass surgery),Cardiac Surgery,140000,160000,ECG|Troponin-I|Coronary Angiogram,Triple-vessel disease (I25.x)\n"
    ),
    "AR1/benefit.csv": (
        "field,value\n"
        "beneficiary_card,ASRI-XXXX-1001 (mock)\n"
        "card_valid,YES\n"
        "beneficiary_status,ALIVE\n"
        "annual_cover,1000000\n"
        "benefit_used,150000\n"
        "benefit_balance,850000\n"
        "prior_same_procedure,NONE\n"
        "duplicate_or_deceased_flag,NONE\n"
        "beneficiary_eligible,YES\n"
    ),
    "AR1/checklist.csv": (
        "field,value\n"
        "package_in_master,YES (AS-CARD-012)\n"
        "package_matches_diagnosis,YES (PTCA appropriate for STEMI I21.0)\n"
        "mandatory_investigations,ALL_PRESENT (ECG + Troponin-I + Coronary Angiogram uploaded)\n"
        "upcoding_flag,NONE\n"
        "cost_within_rate_band,YES (90000 within 80000-95000)\n"
        "benefit_sufficient,YES (balance 850000 >= cost 90000)\n"
        "beneficiary_eligible,YES\n"
        "documentation,COMPLETE\n"
        "emergency,NO\n"
    ),

    # ── AR2: mandatory investigation report missing (curable) -> Query Memo ───
    "AR2/preauth.csv": (
        "field,value\n"
        "preauth_id,PA-AR-2026-1002\n"
        "beneficiary_card,ASRI-XXXX-1002 (mock)\n"
        "patient,Patient B (mock; 64F)\n"
        "diagnosis,Primary osteoarthritis of knee (bilateral; right worse)\n"
        "icd_code,M17.0\n"
        "proposed_package_code,AS-ORTHO-045\n"
        "proposed_package_name,Total Knee Replacement (unilateral)\n"
        "specialty,Orthopaedics\n"
        "cost_estimate,120000\n"
        "investigations_uploaded,CBC; Renal Function Test  (weight-bearing Knee X-ray report NOT uploaded)\n"
        "clinical_justification,Advanced OA; failed conservative management\n"
        "emergency,NO\n"
        "doc_completeness,INCOMPLETE (mandatory weight-bearing Knee X-ray report missing)\n"
    ),
    "AR2/master.csv": (
        "package_code,package_name,specialty,rate_min,rate_max,mandatory_investigations,diagnosis_appropriate_for\n"
        "AS-ORTHO-045,Total Knee Replacement (unilateral),Orthopaedics,110000,130000,Weight-bearing Knee X-ray|CBC|Renal Function Test,Primary osteoarthritis of knee (M17.x)\n"
    ),
    "AR2/benefit.csv": (
        "field,value\n"
        "beneficiary_card,ASRI-XXXX-1002 (mock)\n"
        "card_valid,YES\n"
        "beneficiary_status,ALIVE\n"
        "annual_cover,1000000\n"
        "benefit_used,100000\n"
        "benefit_balance,900000\n"
        "prior_same_procedure,NONE\n"
        "duplicate_or_deceased_flag,NONE\n"
        "beneficiary_eligible,YES\n"
    ),
    "AR2/checklist.csv": (
        "field,value\n"
        "package_in_master,YES (AS-ORTHO-045)\n"
        "package_matches_diagnosis,YES (TKR appropriate for primary OA knee M17.0)\n"
        "mandatory_investigations,MISSING (weight-bearing Knee X-ray report not uploaded; CBC + RFT present)\n"
        "upcoding_flag,NONE\n"
        "cost_within_rate_band,YES (120000 within 110000-130000)\n"
        "benefit_sufficient,YES (balance 900000 >= cost 120000)\n"
        "beneficiary_eligible,YES\n"
        "documentation,INCOMPLETE_CURABLE (one mandatory report missing; otherwise in order)\n"
        "emergency,NO\n"
    ),

    # ── AR3: upcoding / package mismatch (major-billed-for-minor) -> Rejection Note ──
    "AR3/preauth.csv": (
        "field,value\n"
        "preauth_id,PA-AR-2026-1003\n"
        "beneficiary_card,ASRI-XXXX-1003 (mock)\n"
        "patient,Patient C (mock; 34M)\n"
        "diagnosis,Acute appendicitis\n"
        "icd_code,K35.80\n"
        "proposed_package_code,AS-SURG-118\n"
        "proposed_package_name,Major exploratory laparotomy\n"
        "specialty,General Surgery\n"
        "cost_estimate,85000\n"
        "investigations_uploaded,Ultrasound abdomen (confirms appendicitis); CBC\n"
        "clinical_justification,Right iliac fossa pain; USG confirms uncomplicated appendicitis\n"
        "emergency,NO\n"
        "doc_completeness,COMPLETE\n"
    ),
    "AR3/master.csv": (
        "package_code,package_name,specialty,rate_min,rate_max,mandatory_investigations,diagnosis_appropriate_for\n"
        "AS-SURG-072,Appendectomy (laparoscopic),General Surgery,28000,32000,Ultrasound abdomen|CBC,Acute appendicitis (K35.x)\n"
        "AS-SURG-118,Major exploratory laparotomy,General Surgery,80000,90000,CT abdomen|CBC|documented exploratory indication,Peritonitis / bowel obstruction / abdominal trauma (NOT uncomplicated appendicitis)\n"
    ),
    "AR3/benefit.csv": (
        "field,value\n"
        "beneficiary_card,ASRI-XXXX-1003 (mock)\n"
        "card_valid,YES\n"
        "beneficiary_status,ALIVE\n"
        "annual_cover,1000000\n"
        "benefit_used,200000\n"
        "benefit_balance,800000\n"
        "prior_same_procedure,NONE\n"
        "duplicate_or_deceased_flag,NONE\n"
        "beneficiary_eligible,YES\n"
    ),
    "AR3/checklist.csv": (
        "field,value\n"
        "package_in_master,YES (AS-SURG-118 exists, but is not the diagnosis-appropriate package)\n"
        "package_matches_diagnosis,NO (diagnosis acute appendicitis maps to AS-SURG-072 Appendectomy ~30000, NOT AS-SURG-118 Major laparotomy ~85000)\n"
        "mandatory_investigations,ALL_PRESENT (USG + CBC support an appendectomy)\n"
        "upcoding_flag,FLAGGED (major-billed-for-minor: costlier laparotomy proposed for an appendectomy indication)\n"
        "cost_within_rate_band,YES-BUT-WRONG-PACKAGE (85000 is within the laparotomy band, but the laparotomy is the wrong package)\n"
        "benefit_sufficient,YES\n"
        "beneficiary_eligible,YES\n"
        "documentation,COMPLETE\n"
        "emergency,NO\n"
    ),
}

README = """# Aarogyasri Claim Pre-Authorization workflow — mock test data

One folder per case; one CSV per source (all MOCK / SYNTHETIC — no real PHI). The explicit
checklist/status fields cue the PRE-AUTH DECISION and thus which drafter should PRODUCE its
document (the guard rail in `test_aarogyasri.py`).

| Case | Decision signal | Expected drafter | Rejected drafters |
|------|-----------------|------------------|-------------------|
| AR1 | in-package + matches diagnosis + investigations complete + within benefit | Approval Note Drafter | Query Note; Rejection Note |
| AR2 | mandatory Knee X-ray report MISSING (curable); otherwise in order | Query Note Drafter | Approval Note; Rejection Note |
| AR3 | upcoding / package mismatch (major laparotomy for an appendicitis) | Rejection Note Drafter | Approval Note; Query Note |

The Extractor classifies with a STRICT PRIORITY ORDER (REJECT grounds first, then QUERY, then APPROVE),
so an upcoded case is a REJECT even though its docs are complete, and a merely-missing report is a QUERY.

Always-run: Preauth Extractor, History & Benefit Checker, Package & Upcoding Verifier, Synthesizer.
AR4 (HITL, no folder) is a vague one-liner in test_aarogyasri.py -> the Extractor must pause [NEEDS_INPUT].
"""


def main():
    for rel, content in FILES.items():
        p = BASE / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (BASE / "README.md").write_text(README, encoding="utf-8")
    print(f"[OK] wrote {len(FILES)} CSVs + README under {BASE}")
    for case in ("AR1", "AR2", "AR3"):
        print(f"  {case}: {sorted(f.name for f in (BASE / case).iterdir())}")


if __name__ == "__main__":
    main()
