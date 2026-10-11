#!/usr/bin/env python3
"""
Mock test data for the CID Economic Offences & AHT workflow -> test_data/cid/{CID1,CID2,CID3}/*.csv.
Presence/absence + explicit status/type fields cue the CASE TYPE and thus which drafter should PRODUCE:
  CID1 ECONOMIC_OFFENCE   (deposit/Ponzi fraud, seized statements, fund-trail PENDING) -> Fund-Trail Report
  CID2 HUMAN_TRAFFICKING  (rescue op, victims, traffickers, documentation PENDING)     -> AHT Victim-Rescue Report
  CID3 READY_TO_FILE      (investigation COMPLETE, accused verified, trail annexed)     -> Consolidated Investigation Report
All data is MOCK. No real victim identities.
"""
from pathlib import Path

BASE = Path(__file__).parent / "test_data" / "cid"

FILES = {
    # ── CID1: economic-offence, fund-trail PENDING -> Fund-Trail Report ───────
    "CID1/fir.csv": (
        "cr_no,wing,police_station,district,date,offence,sections,scheme,establishment,total_collected_inr,depositors_count,accused,investigation_status,fund_trail_status\n"
        "41/2026,Economic Offences Wing (EOW),CID PS,Hyderabad,2026-05-14,Deposit / investment (Ponzi) fraud,BNS 318 / 316,Sunrise Fixed-Return Plan,Sunrise Fincorp,450000000,1240,Prakash Rao (MD),UNDER_INVESTIGATION,PENDING (not yet reconstructed)\n"
    ),
    "CID1/depositors.csv": (
        "depositor_id,name,amount_inr,deposit_date,receipt_no,branch\n"
        "D-1001,Ramesh Kumar,500000,2025-11-02,SF-1001,Ameerpet\n"
        "D-1002,Ramesh Kumr,500000,2025-11-02,SF-1044,Ameerpet\n"   # variant spelling — de-dup target
        "D-1003,Lakshmi Devi,300000,2025-11-10,SF-1102,Dilsukhnagar\n"
        "D-1004,Syed Imran,750000,2025-12-01,SF-1210,Ameerpet\n"
        "D-1005,Venkata Rao,250000,2025-12-05,SF-1288,Kukatpally\n"
    ),
    "CID1/bank_statements.csv": (
        "txn_id,from_account,to_account,amount_inr,date,note\n"
        "T-01,Depositors (various),SF-COLLECT-50100111 HDFC,1800000,2025-12-06,Deposits pooled into collection account\n"
        "T-02,SF-COLLECT-50100111 HDFC,BRIGHT-VENTURES-50200222 ICICI,1500000,2025-12-08,Transfer to shell entity (layer 1)\n"
        "T-03,BRIGHT-VENTURES-50200222 ICICI,APEX-HOLDINGS-50300333 AXIS,1200000,2025-12-11,Onward layering to second shell\n"
        "T-04,APEX-HOLDINGS-50300333 AXIS,Property purchase (villa Kompally),900000,2025-12-20,Exit into real estate (attachable)\n"
    ),
    "CID1/shell_entities.csv": (
        "entity,type,director,account,mca_status\n"
        "Bright Ventures Pvt Ltd,Shell,Prakash Rao,50200222 ICICI,Unregistered / vanishing\n"
        "Apex Holdings LLP,Shell,K. Naidu (dummy director),50300333 AXIS,Struck off\n"
    ),

    # ── CID2: human-trafficking, documentation PENDING -> AHT Victim-Rescue ───
    "CID2/fir.csv": (
        "cr_no,wing,police_station,district,date,offence,sections,operation_ref,victims_count,accused_count,investigation_status,victim_documentation_status\n"
        "88/2026,Anti-Human-Trafficking Unit (AHTU),CID PS,Rangareddy,2026-06-21,Human trafficking / commercial sexual exploitation,BNS 143 / ITPA,OP-VIMUKTHI-2026-07,6,4,ONGOING,PENDING (victims not yet documented; network not linked)\n"
    ),
    "CID2/victims.csv": (
        "victim_code,age,gender,source_location,destination_location,rescued_from\n"
        "V-1,17,F,Malkangiri (Odisha),Hyderabad,Brothel - Mehdipatnam\n"   # minor -> POCSO
        "V-2,22,F,Jharkhand,Hyderabad,Brothel - Mehdipatnam\n"
        "V-3,19,F,West Bengal,Hyderabad,Bonded labour - Katedan\n"
        "V-4,20,F,Assam,Hyderabad,Brothel - Mehdipatnam\n"
        "V-5,16,F,Malkangiri (Odisha),Hyderabad,Brothel - Mehdipatnam\n"   # minor -> POCSO
        "V-6,24,F,Chhattisgarh,Hyderabad,Bonded labour - Katedan\n"
    ),
    "CID2/accused.csv": (
        "accused_id,name,role,location,note\n"
        "A-1,Saleem,Brothel operator (destination),Mehdipatnam,Runs the destination premises\n"
        "A-2,Ravi Munda,Broker (source),Malkangiri,Recruits from source district\n"
        "A-3,Sunita,Handler / transporter,Vijayawada,Moves victims along the route\n"
        "A-4,Unknown financier,Financier,-,Suspected funder — to be identified by officer\n"
    ),
    "CID2/operations.csv": (
        "op_ref,date,location,victims_recovered,accused_arrested,note\n"
        "OP-VIMUKTHI-2026-07,2026-06-20,Mehdipatnam & Katedan,6,3,Joint AHTU raid; V-1 and V-5 appear age minor - age-determination pending\n"
    ),

    # ── CID3: investigation COMPLETE + verified -> Consolidated Investigation Report ──
    "CID3/fir.csv": (
        "cr_no,wing,police_station,district,date,offence,sections,accused,investigation_status,accused_verified,fund_trail_status,chargesheet_status,ready_to_file\n"
        "12/2026,Economic Offences Wing (EOW),CID PS,Hyderabad,2026-01-08,Chit-fund misappropriation,BNS 316 / 318,Mohan Das (proprietor),COMPLETE,YES,RECONSTRUCTED_AND_ANNEXED,DUE,YES\n"
    ),
    "CID3/investigation_summary.csv": (
        "item,status\n"
        "Extraction of seized records,DONE\n"
        "Entity & fund-flow linkage,DONE (Annexure-A)\n"
        "Records verification & antecedents,DONE\n"
        "Fund-trail reconstruction,COMPLETE - annexed as Annexure-A\n"
        "Depositor de-duplication,DONE (2140 -> 2088 unique)\n"
        "BSA Sec 63 e-evidence certificate,OBTAINED\n"
        "Prosecution sanction,OBTAINED\n"
        "Charge-sheet,DUE - to be filed within 15 days\n"
    ),
    "CID3/accused.csv": (
        "accused_id,name,role,antecedents,status\n"
        "A-1,Mohan Das,Proprietor,Prior CR 233/2019 (chit default) - VERIFIED,Chargesheet-ready\n"
        "A-2,Girish Das,Manager / signatory,No prior - VERIFIED,Chargesheet-ready\n"
    ),
}

README = """# CID Economic Offences & AHT workflow — mock test data

One folder per case; one CSV per source (all MOCK, no real victim identities). The status/type fields cue
the CASE TYPE and thus which drafter should PRODUCE its document (the guard rail in `test_cid.py`).

| Case | Type signal | Expected drafter | Rejected drafters |
|------|-------------|------------------|-------------------|
| CID1 | EOW deposit fraud; fund_trail_status=PENDING | Fund-Trail Report Drafter | AHT Victim-Rescue; Investigation |
| CID2 | AHTU rescue; victim_documentation_status=PENDING | AHT Victim-Rescue Report Drafter | Fund-Trail; Investigation |
| CID3 | investigation_status=COMPLETE + verified + trail annexed | Investigation Report Drafter | Fund-Trail; AHT Victim-Rescue |

CID4 (HITL) is a vague one-liner with NO data (inline in the test) -> the Extractor must pause [NEEDS_INPUT].

Always-run: Case Extractor, Entity & Fund-Flow Linker, Records Verifier, Case Synthesizer.
"""


def main():
    for rel, content in FILES.items():
        p = BASE / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (BASE / "README.md").write_text(README, encoding="utf-8")
    print(f"[OK] wrote {len(FILES)} CSVs + README under {BASE}")
    for case in ("CID1", "CID2", "CID3"):
        print(f"  {case}: {sorted(f.name for f in (BASE / case).iterdir())}")


if __name__ == "__main__":
    main()
