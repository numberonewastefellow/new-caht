#!/usr/bin/env python3
"""
Mock test data for the ePASS Post-Matric Scholarship workflow -> test_data/epass/{EP1,EP2,EP3}/*.csv.
Explicit status fields cue the VERIFICATION DECISION and thus which drafter should PRODUCE:
  EP1 SANCTION  (within cap, certs valid, genuine institution, no flags)        -> Sanction Proceedings
  EP2 QUERY     (income cert EXPIRED + bank not Aadhaar-seeded; both FIXABLE)   -> Defect/Query Memo
  EP3 REJECT    (income OVER cap + de-recognised institution + duplicate app)   -> Rejection Proceedings
All data is MOCK/SYNTHETIC — no real names, IDs, or Aadhaar numbers (Aadhaar shown masked).
"""
from pathlib import Path

BASE = Path(__file__).parent / "test_data" / "epass"

FILES = {
    # -- EP1: clean, within cap, genuine institution -> Sanction Proceedings --
    "EP1/application.csv": (
        "app_id,portal,type,scheme,year,applicant,category,course,institution,udise_aishe_code,claimed_rtf,claimed_mtf\n"
        "EPX-2026-1001,ePASS,Fresh,Post-Matric RTF+MTF,2025-26,Applicant-A (mock),SC,B.Tech CSE,Sri Sai Degree & PG College (mock),U36010112345,35000,12000\n"
    ),
    "EP1/certificates.csv": (
        "cert_type,cert_no,detail,status\n"
        "Caste certificate,CC-SC-MOCK-1001,Category SC matches application,VALID\n"
        "Income certificate,IC-MOCK-1001,Annual family income Rs 1;80;000,VALID (current year)\n"
        "Income vs cap,,Income Rs 1;80;000 vs SC cap Rs 2;50;000,WITHIN CAP\n"
    ),
    "EP1/institution.csv": (
        "institution,udise_aishe_code,recognised,affiliation,blacklisted,code_status\n"
        "Sri Sai Degree & PG College (mock),U36010112345,YES,ACTIVE,NO,VALID\n"
    ),
    "EP1/bank.csv": (
        "account,aadhaar_ref,aadhaar_seeded,duplicate_account\n"
        "MOCKACCT10001,XXXX-XXXX-1001,YES,NO\n"
    ),
    "EP1/screening.csv": (
        "check,result,detail\n"
        "Duplicate application,NO,No prior application this cycle for this Aadhaar/certs\n"
        "Duplicate bank account,NO,Account not linked to other students\n"
        "Ghost/phantom enrolment,NO,Fresh applicant; NA\n"
        "Renewal attendance,NA,Fresh application (attendance not applicable)\n"
    ),

    # -- EP2: fixable documentation defects -> Defect/Query Memo --------------
    "EP2/application.csv": (
        "app_id,portal,type,scheme,year,applicant,category,course,institution,udise_aishe_code,claimed_rtf,claimed_mtf\n"
        "EPX-2026-1002,ePASS,Fresh,Post-Matric RTF+MTF,2025-26,Applicant-B (mock),BC,B.Com,Government Degree College (mock),U36020254321,20000,8000\n"
    ),
    "EP2/certificates.csv": (
        "cert_type,cert_no,detail,status\n"
        "Caste certificate,CC-BC-MOCK-1002,Category BC matches application,VALID\n"
        "Income certificate,IC-MOCK-1002,Issued 2023-24 - validity lapsed for 2025-26,EXPIRED (FIXABLE - re-obtain current MeeSeva income certificate)\n"
        "Income vs cap,,Income Rs 1;40;000 vs BC cap Rs 2;00;000,WITHIN CAP\n"
    ),
    "EP2/institution.csv": (
        "institution,udise_aishe_code,recognised,affiliation,blacklisted,code_status\n"
        "Government Degree College (mock),U36020254321,YES,ACTIVE,NO,VALID\n"
    ),
    "EP2/bank.csv": (
        "account,aadhaar_ref,aadhaar_seeded,duplicate_account\n"
        "MOCKACCT10002,XXXX-XXXX-1002,NO (SEEDING PENDING - FIXABLE),NO\n"
    ),
    "EP2/screening.csv": (
        "check,result,detail\n"
        "Duplicate application,NO,No prior application this cycle\n"
        "Duplicate bank account,NO,Account not linked to other students\n"
        "Ghost/phantom enrolment,NO,Fresh applicant; NA\n"
        "Renewal attendance,NA,Fresh application (attendance not applicable)\n"
    ),

    # -- EP3: hard disqualifiers -> Rejection Proceedings --------------------
    "EP3/application.csv": (
        "app_id,portal,type,scheme,year,applicant,category,course,institution,udise_aishe_code,claimed_rtf,claimed_mtf\n"
        "EPX-2026-1003,Jnanabhumi,Fresh,Post-Matric RTF+MTF,2025-26,Applicant-C (mock),BC,B.Tech,Phantom Institute of Technology (mock),U36099999999,90000,20000\n"
    ),
    "EP3/certificates.csv": (
        "cert_type,cert_no,detail,status\n"
        "Caste certificate,CC-BC-MOCK-1003,Category BC matches application,VALID\n"
        "Income certificate,IC-MOCK-1003,Annual family income Rs 3;20;000,VALID (figure over cap)\n"
        "Income vs cap,,Income Rs 3;20;000 vs BC cap Rs 2;00;000,OVER CAP (HARD - ineligible)\n"
    ),
    "EP3/institution.csv": (
        "institution,udise_aishe_code,recognised,affiliation,blacklisted,code_status\n"
        "Phantom Institute of Technology (mock),U36099999999,NO (DE-RECOGNISED),LAPSED,YES,INVALID/BLACKLISTED\n"
    ),
    "EP3/bank.csv": (
        "account,aadhaar_ref,aadhaar_seeded,duplicate_account\n"
        "MOCKACCT99999,XXXX-XXXX-1003,YES,YES (one account receiving DBT for 6 other students)\n"
    ),
    "EP3/screening.csv": (
        "check,result,detail\n"
        "Duplicate application,YES,Same Aadhaar/certs already sanctioned under prior app EPX-2025-0777\n"
        "Duplicate bank account,YES,MOCKACCT99999 linked to 6 other students (cluster)\n"
        "Ghost/phantom enrolment,YES,Renewal attendance 40% (below 75%/quarter) - phantom enrolment\n"
        "Renewal attendance,40%,Below the 75%/quarter AEBAS bar\n"
    ),
}

README = """# ePASS Post-Matric Scholarship workflow - mock test data

One folder per case; one CSV per source (all MOCK/SYNTHETIC - no real names/IDs/Aadhaar). The status
fields cue the VERIFICATION DECISION and thus which drafter should PRODUCE its document (the guard rail
in `test_epass.py`).

| Case | Decision signal | Expected drafter | Rejected drafters |
|------|-----------------|------------------|-------------------|
| EP1 | within cap + certs valid + genuine institution + no flags | Sanction Order Drafter | Query Note; Rejection Order |
| EP2 | income cert EXPIRED + bank not Aadhaar-seeded (both fixable), income within cap, institution genuine | Query Note Drafter | Sanction Order; Rejection Order |
| EP3 | income OVER cap + de-recognised/blacklisted institution + duplicate application/account + ghost | Rejection Order Drafter | Sanction Order; Query Note |

EP4 (HITL, no files): a vague one-liner with no application/certificate/institution data -> Extractor pauses [NEEDS_INPUT].

Always-run: Application Extractor, Duplicate & Ghost Checker, Eligibility & Institution Verifier, Synthesizer.
(Rupee figures use ';' as the thousands separator so they don't collide with the CSV comma delimiter.)
"""


def main():
    for rel, content in FILES.items():
        p = BASE / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (BASE / "README.md").write_text(README, encoding="utf-8")
    print(f"[OK] wrote {len(FILES)} CSVs + README under {BASE}")
    for case in ("EP1", "EP2", "EP3"):
        print(f"  {case}: {sorted(f.name for f in (BASE / case).iterdir())}")


if __name__ == "__main__":
    main()
