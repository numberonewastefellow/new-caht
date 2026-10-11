#!/usr/bin/env python3
"""
Mock test data for the Land Mutation & ROR Correction workflow -> test_data/land/{LM1,LM2,LM3}/*.csv.
Presence/absence + explicit fields cue the CASE TYPE and thus which drafter should PRODUCE:
  LM1 MUTATION_CLEAN       (deed extent == RoR extent, patta, no 22A, no dispute) -> Mutation Order
  LM2 MUTATION_DISCREPANCY (extent mismatch + Sec 22A Part-B + rival claim)        -> Objection & Requisition Memo
  LM3 ROR_CORRECTION       (clerical name/khata/extent typo in the existing 1-B)   -> RoR Correction Order
All data is MOCK. Survey numbers, names, khatas and document numbers are fictitious.
"""
from pathlib import Path

BASE = Path(__file__).parent / "test_data" / "land"

FILES = {
    # ── LM1: clean transfer, deed == RoR, patta, no 22A/dispute -> Mutation Order ──
    "LM1/application.csv": (
        "application_no,application_type,survey_no,sub_division,village,mandal,district,transferee,correction_request_flag,dispute_flag\n"
        "APP-LM1-2026,Mutation on registered Sale Deed,124,2,Kondapur,Serilingampally,Ranga Reddy,Rajeshwari Devi,NO,NO\n"
    ),
    "LM1/deed.csv": (
        "document_no,deed_type,transferor,transferee,deed_extent_acres,consideration_rs,registration_date\n"
        "DOC-4821/2026,Sale Deed,Narsimha Rao,Rajeshwari Devi,2.00,4500000,2026-06-15\n"
    ),
    "LM1/ror_1b.csv": (
        "survey_no,sub_division,khata_no,recorded_pattadar,ror_extent_acres,classification,section_22A_flag\n"
        "124,2,KH-1180,Narsimha Rao,2.00,Patta,N\n"
    ),
    "LM1/chain_of_title.csv": (
        "sequence,year,event,owner,document_no,litigation\n"
        "1,2005,Original patta granted,Narsimha Rao,PB-1180,None\n"
        "2,2026,Sale to Rajeshwari Devi (mutation pending),Rajeshwari Devi,DOC-4821/2026,None\n"
    ),

    # ── LM2: transfer that cannot be mutated (extent mismatch + Part-B + rival claim) -> Objection Memo ──
    "LM2/application.csv": (
        "application_no,application_type,survey_no,sub_division,village,mandal,district,transferee,correction_request_flag,dispute_flag\n"
        "APP-LM2-2026,Mutation on registered Sale Deed,88,1,Ibrahimpatnam,Ibrahimpatnam,Ranga Reddy,Suresh Kumar,NO,YES\n"
    ),
    "LM2/deed.csv": (
        "document_no,deed_type,transferor,transferee,deed_extent_acres,consideration_rs,registration_date\n"
        "DOC-5533/2026,Sale Deed,Anjaneyulu,Suresh Kumar,3.00,3200000,2026-07-10\n"
    ),
    "LM2/ror_1b.csv": (
        "survey_no,sub_division,khata_no,recorded_pattadar,ror_extent_acres,classification,section_22A_flag\n"
        "88,1,KH-0770,Anjaneyulu,2.20,Prohibited (Part-B),Y\n"
    ),
    "LM2/prohibited_list.csv": (
        "survey_no,sub_division,village,reason,section\n"
        "88,1,Ibrahimpatnam,Assigned land - Part-B prohibited property,Sec 22A\n"
    ),
    "LM2/chain_of_title.csv": (
        "sequence,year,event,owner,document_no,litigation\n"
        "1,2010,Assigned patta (conditional),Anjaneyulu,PB-0770,None\n"
        "2,2024,Rival claim by legal heir Ramulamma,Ramulamma,RCCMS-2024-441,PENDING (Revenue Court)\n"
    ),

    # ── LM3: clerical error in the existing 1-B, no transfer -> RoR Correction Order ──
    "LM3/application.csv": (
        "application_no,application_type,survey_no,sub_division,village,mandal,district,applicant,correction_request_flag,dispute_flag\n"
        "APP-LM3-2026,Record-of-Rights (1-B) Clerical Correction,205,3,Shamirpet,Shamirpet,Medchal-Malkajgiri,Lakshmi Narayana,YES,NO\n"
    ),
    "LM3/ror_1b.csv": (
        "survey_no,sub_division,khata_no,recorded_pattadar,ror_extent_acres,classification,section_22A_flag\n"
        "205,3,KH-1234,Lakshmi Narayan,1.50,Patta,N\n"
    ),
    "LM3/correction_request.csv": (
        "field,recorded_value,correct_value,proof_document\n"
        "pattadar_name,Lakshmi Narayan,Lakshmi Narayana,Pattadar Passbook PB-9021\n"
        "khata_no,KH-1234,KH-1243,Pattadar Passbook PB-9021\n"
        "extent_acres,1.50,1.05,Registered Sale Deed DOC-2011/778\n"
    ),
    "LM3/passbook.csv": (
        "document_no,pattadar_name,khata_no,survey_no,sub_division,extent_acres\n"
        "PB-9021,Lakshmi Narayana,KH-1243,205,3,1.05\n"
    ),
}

README = """# Land Mutation & ROR Correction workflow — mock test data

One folder per case; one CSV per source (all MOCK). The application/RoR fields cue the CASE TYPE
and thus which drafter should PRODUCE its document (the guard rail in `test_land.py`).

| Case | Type signal | Expected drafter | Rejected drafters |
|------|-------------|------------------|-------------------|
| LM1 | deed extent == RoR (2.00), Patta, Sec 22A N, no dispute | Mutation Order Drafter | Objection Memo; RoR Correction |
| LM2 | deed 3.00 vs RoR 2.20, Part-B / Sec 22A Y, rival claim | Objection Memo Drafter | Mutation Order; RoR Correction |
| LM3 | clerical name/khata/extent typo in existing 1-B, no transfer | RoR Correction Drafter | Mutation Order; Objection Memo |

Key LM2 vs LM3 disambiguation: LM2 is a TRANSFER (sale deed) that conflicts with the register ->
objection; LM3 is NOT a transfer, just a clerical correction of the existing record proven by the
original passbook -> correction order.

Always-run: Application Extractor, Chain-of-Title Checker, Record Verifier, Synthesizer.
LM4 (in test_land.py, no CSVs): a vague one-liner -> the Extractor pauses with [NEEDS_INPUT].
"""


def main():
    for rel, content in FILES.items():
        p = BASE / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (BASE / "README.md").write_text(README, encoding="utf-8")
    print(f"[OK] wrote {len(FILES)} CSVs + README under {BASE}")
    for case in ("LM1", "LM2", "LM3"):
        print(f"  {case}: {sorted(f.name for f in (BASE / case).iterdir())}")


if __name__ == "__main__":
    main()
