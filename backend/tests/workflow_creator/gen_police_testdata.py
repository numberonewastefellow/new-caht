#!/usr/bin/env python3
"""
Mock test data for the State Police Charge-Sheet workflow -> test_data/police/{SP1,SP2,SP3}/*.csv.
Presence/absence + explicit status fields cue the CASE STAGE and thus which drafter should PRODUCE:
  SP1 CHARGESHEET_READY  (complete, compliant, in deadline)      -> Charge-Sheet
  SP2 COMPLIANCE_GAP     (Sec 176(3) forensic + Sec 105 AV missing) -> Compliance Deficiency Memo
  SP3 DEADLINE_CRITICAL  (day 88/90, FSL pending, incomplete)    -> Default-Bail Risk Alert
All data is MOCK.
"""
from pathlib import Path

BASE = Path(__file__).parent / "test_data" / "police"

FILES = {
    # ── SP1: ready, compliant, within deadline -> Charge-Sheet ───────────────
    "SP1/fir.csv": (
        "fir_no,police_station,district,date,offence,ipc_sections,accused,accused_status,arrest_date,victim,punishment_years,investigation_status\n"
        "128/2026,Cyberabad PS,Cyberabad,2026-06-27,Theft of two-wheeler,IPC 379,Suresh Reddy,arrested,2026-06-28,Mahesh,3,COMPLETE\n"
    ),
    "SP1/compliance.csv": (
        "item,status\n"
        "Investigation,COMPLETE\n"
        "Sec 105 audio-video of seizure,DONE\n"
        "Sec 176(3) forensic visit,NA (offence under 7 years)\n"
        "FSL report,NA\n"
        "Custody day,40\n"
        "Deadline limit (days),90\n"
    ),
    "SP1/case_diary.csv": (
        "entry_no,date,note\n"
        "1,2026-06-28,Accused apprehended; stolen two-wheeler recovered and seized under mahazar (audio-video recorded)\n"
        "2,2026-07-05,Witness statements recorded under Sec 180 BNSS; ownership documents collected\n"
    ),
    "SP1/witnesses.csv": (
        "name,role,statement_summary\n"
        "Mahesh,Complainant/owner,Reported the theft and identified the recovered vehicle\n"
        "Constable Rao,Seizing officer,Recovered and seized the vehicle from the accused\n"
        "Anil,Panch witness,Witnessed the seizure mahazar\n"
    ),
    "SP1/seizure.csv": (
        "item,muddemal_no,custody\n"
        "Hero Splendor two-wheeler TS09XX1234,MO-128/2026,Malkhana\n"
    ),

    # ── SP2: mandatory compliance step missing -> Deficiency Memo ────────────
    "SP2/fir.csv": (
        "fir_no,police_station,district,date,offence,ipc_sections,accused,accused_status,arrest_date,victim,punishment_years,investigation_status\n"
        "077/2026,Panjagutta PS,Hyderabad,2026-07-19,Robbery with weapon,IPC 392,Imran Khan,arrested,2026-07-20,Latha,10,NEARLY_COMPLETE\n"
    ),
    "SP2/compliance.csv": (
        "item,status\n"
        "Investigation,NEARLY_COMPLETE\n"
        "Sec 105 audio-video of seizure,NOT_DONE\n"
        "Sec 176(3) forensic visit,NOT_DONE (REQUIRED - offence punishable 7 years or more)\n"
        "FSL report,NOT_DONE\n"
        "Custody day,16\n"
        "Deadline limit (days),90\n"
    ),
    "SP2/case_diary.csv": (
        "entry_no,date,note\n"
        "1,2026-07-20,Accused arrested; cash and weapon seized but seizure NOT recorded on audio-video\n"
        "2,2026-07-28,Statements recorded; forensic team was not deputed to the scene\n"
    ),
    "SP2/prior_firs.csv": (
        "fir_no,police_station,accused,offence,note\n"
        "512/2024,Panjagutta PS,Imran Khan,IPC 392 robbery,Same accused - prior robbery case (repeat offender)\n"
    ),

    # ── SP3: deadline nearly expired + investigation incomplete -> Default-Bail Alert ──
    "SP3/fir.csv": (
        "fir_no,police_station,district,date,offence,ipc_sections,accused,accused_status,arrest_date,victim,punishment_years,investigation_status\n"
        "041/2026,Gachibowli PS,Cyberabad,2026-05-09,Grievous hurt with dangerous weapon,IPC 326,Ravi Varma,arrested,2026-05-10,Kiran,10,INCOMPLETE\n"
    ),
    "SP3/compliance.csv": (
        "item,status\n"
        "Investigation,INCOMPLETE\n"
        "Sec 105 audio-video of seizure,DONE\n"
        "Sec 176(3) forensic visit,DONE\n"
        "FSL report,PENDING (not yet received)\n"
        "Custody day,88\n"
        "Deadline limit (days),90\n"
        "Deadline date,2026-08-08\n"
        "Days left,2\n"
    ),
    "SP3/case_diary.csv": (
        "entry_no,date,note\n"
        "1,2026-05-10,Accused arrested; weapon seized (audio-video recorded); forensic team deputed\n"
        "2,2026-07-30,FSL report still awaited; charge-sheet cannot be completed until it arrives\n"
    ),
}

README = """# State Police Charge-Sheet workflow — mock test data

One folder per case; one CSV per source (all MOCK). The compliance/status fields cue the CASE STAGE
and thus which drafter should PRODUCE its document (the guard rail in `test_police.py`).

| Case | Stage signal | Expected drafter | Rejected drafters |
|------|--------------|------------------|-------------------|
| SP1 | complete + Sec105 done + Sec176(3) NA + day 40/90 | Charge-Sheet Drafter | Deficiency Memo; Default-Bail |
| SP2 | Sec176(3) forensic + Sec105 AV NOT done (10yr offence) | Compliance Deficiency Memo Drafter | Charge-Sheet; Default-Bail |
| SP3 | day 88/90 + FSL pending + investigation incomplete | Default-Bail Risk Drafter | Charge-Sheet; Deficiency Memo |

Always-run: Case-File Extractor, Antecedents & Linkage, BNSS Compliance & Section-Mapping Verifier, Case Synthesizer.
"""


def main():
    for rel, content in FILES.items():
        p = BASE / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (BASE / "README.md").write_text(README, encoding="utf-8")
    print(f"[OK] wrote {len(FILES)} CSVs + README under {BASE}")
    for case in ("SP1", "SP2", "SP3"):
        print(f"  {case}: {sorted(f.name for f in (BASE / case).iterdir())}")


if __name__ == "__main__":
    main()
