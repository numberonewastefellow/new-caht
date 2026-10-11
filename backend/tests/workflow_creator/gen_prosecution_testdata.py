#!/usr/bin/env python3
"""
Mock test data for the Directorate of Prosecutions Scrutiny workflow
  -> test_data/prosecution/{PR1,PR2,PR3}/*.csv.
Presence/absence + explicit status fields cue the SCRUTINY VERDICT and thus which drafter PRODUCES:
  PR1 FIT_FOR_TRIAL           (complete + sufficient)                 -> Fit-for-Trial Opinion
  PR2 RETURN_FOR_RECTIFICATION (curable gaps: no sanction / no Sec 63 cert / missing statements) -> Return-for-Rectification Memo
  PR3 WEAK_CASE               (paperwork complete BUT evidence insufficient) -> Weak-Case Opinion
All data is MOCK. Statutes: BNSS 2023 (Sec 193 report, Sec 218 sanction, Sec 230 supply), BSA 2023
(Sec 63 electronic-evidence certificate), BNS 2023 (offence sections).
"""
from pathlib import Path

BASE = Path(__file__).parent / "test_data" / "prosecution"

FILES = {
    # ── PR1: complete + sufficient -> Fit-for-Trial Opinion ──────────────────
    "PR1/chargesheet.csv": (
        "cc_no,court,fir_no,police_station,district,offence,ipc_sections,bns_sections,accused,accused_public_servant,chargesheet_indexed,evidence_strength\n"
        "210/2026,II Addl. Sessions Court Cyberabad,128/2026,Cyberabad PS,Cyberabad,Robbery with weapon,IPC 392,BNS 309,Suresh Reddy,NO,YES (Sec 193(8)),STRONG\n"
    ),
    "PR1/completeness.csv": (
        "checklist_item,status\n"
        "Charge-sheet indexed (Sec 193(8)),PRESENT\n"
        "Sec 180/183 witness statements,ALL ATTACHED (3 of 3)\n"
        "Sec 63 BSA e-evidence certificate (CCTV),PRESENT - dual-signed with hash value\n"
        "Sec 176(3) forensic/FSL report,PRESENT\n"
        "Sec 218 BNSS sanction,NA (accused is not a public servant)\n"
        "Chain of custody / seizure memos,INTACT\n"
        "Sufficiency of evidence,SUFFICIENT - reasonable prospect of conviction\n"
        "Overall scrutiny,COMPLETE AND FIT FOR TRIAL\n"
    ),
    "PR1/witnesses.csv": (
        "name,role,statement_sec180_attached,summary\n"
        "Mahesh,Complainant/victim,YES,Robbed at knife-point; identifies the accused and the recovered chain\n"
        "Anil,Eyewitness,YES,Saw the accused snatch the chain and flee; corroborates the victim\n"
        "Constable Rao,Recovery/seizing officer,YES,Recovered the stolen chain and weapon from the accused\n"
    ),
    "PR1/evidence.csv": (
        "exhibit,type,sec63_certificate,forensic_result\n"
        "CCTV footage of the market lane,electronic,PRESENT (dual-signed + SHA-256 hash),Shows the accused at the scene\n"
        "Gold chain + knife,material object (MO-210/2026),NA,FSL: chain matches the victim's description; fingerprints on knife match accused\n"
    ),

    # ── PR2: curable procedural gaps -> Return-for-Rectification Memo ─────────
    "PR2/chargesheet.csv": (
        "cc_no,court,fir_no,police_station,district,offence,ipc_sections,bns_sections,accused,accused_public_servant,chargesheet_indexed,evidence_strength\n"
        "077/2026,Special Court for PC Act Hyderabad,077/2026,Panjagutta PS,Hyderabad,Criminal breach of trust by public servant,IPC 409,BNS 316(5),Imran Khan (Revenue clerk),YES,YES,SOUND (strong once cured)\n"
    ),
    "PR2/completeness.csv": (
        "checklist_item,status\n"
        "Charge-sheet indexed (Sec 193(8)),PRESENT\n"
        "Sec 180/183 witness statements,PARTIAL - 2 of 5 statements MISSING (witnesses W3, W4)\n"
        "Sec 63 BSA e-evidence certificate (phone dump),MISSING - phone-dump exhibit relied on but NO certificate\n"
        "Sec 176(3) forensic/FSL report,PRESENT\n"
        "Sec 218 BNSS sanction,MISSING - accused is a public servant; sanction NOT obtained\n"
        "Chain of custody / seizure memos,INTACT\n"
        "Sufficiency of evidence,SOUND IF CURED - documentary evidence is strong; defects are procedural and curable\n"
        "Overall scrutiny,RETURN FOR RECTIFICATION - curable defects must be cured before filing\n"
    ),
    "PR2/witnesses.csv": (
        "name,role,statement_sec180_attached,summary\n"
        "Ramesh,Complainant,YES,Reported the misappropriation of funds by the clerk\n"
        "Auditor Rao,Departmental auditor,YES,Audit shows the shortfall traced to the accused's ledger\n"
        "W3 (cashier),Material witness,NO - MISSING,Statement not recorded/attached\n"
        "W4 (bank official),Material witness,NO - MISSING,Statement not recorded/attached\n"
    ),
    "PR2/evidence.csv": (
        "exhibit,type,sec63_certificate,forensic_result\n"
        "Seized mobile phone dump (WhatsApp records),electronic,MISSING - no Sec 63 BSA certificate,Content extracted but inadmissible without the certificate\n"
        "Ledger + audit report,documentary,NA,Shows the misappropriation; strong documentary proof\n"
    ),
    "PR2/prior_opinions.csv": (
        "opinion_id,fir_no,note\n"
        "OP-2025-3312,412/2025,Similar PC Act case returned for want of Sec 218 sanction; cured and later convicted\n"
    ),

    # ── PR3: paperwork complete BUT evidence insufficient -> Weak-Case Opinion ─
    "PR3/chargesheet.csv": (
        "cc_no,court,fir_no,police_station,district,offence,ipc_sections,bns_sections,accused,accused_public_servant,chargesheet_indexed,evidence_strength\n"
        "041/2026,XIV Metropolitan Magistrate Court,041/2026,Gachibowli PS,Cyberabad,Voluntarily causing hurt,IPC 323,BNS 115,Ravi Varma,NO,YES,INSUFFICIENT\n"
    ),
    "PR3/completeness.csv": (
        "checklist_item,status\n"
        "Charge-sheet indexed (Sec 193(8)),PRESENT\n"
        "Sec 180/183 witness statements,ALL ATTACHED (paperwork is complete)\n"
        "Sec 63 BSA e-evidence certificate,NA (no electronic evidence relied on)\n"
        "Sec 176(3) forensic/FSL report,PRESENT\n"
        "Sec 218 BNSS sanction,NA (accused is not a public servant)\n"
        "Chain of custody / seizure memos,INTACT\n"
        "Sufficiency of evidence,INSUFFICIENT - sole eyewitness retracted; no recovery; medical inconclusive; NO reasonable prospect of conviction\n"
        "Overall scrutiny,WEAK CASE - advise against filing / further investigation (paperwork complete, evidence substantively weak)\n"
    ),
    "PR3/witnesses.csv": (
        "name,role,statement_sec180_attached,summary\n"
        "Kiran,Complainant/victim,YES,Alleges he was beaten; but no independent corroboration\n"
        "Sole eyewitness (Latha),Eyewitness,YES,RETRACTED - has since filed an affidavit stating she did not witness the incident (turned hostile)\n"
    ),
    "PR3/evidence.csv": (
        "exhibit,type,sec63_certificate,forensic_result\n"
        "Medical/wound certificate,documentary,NA,Simple abrasions; INCONCLUSIVE - cannot establish who caused them or link the accused\n"
        "Alleged weapon,material object,NA,NOT RECOVERED - no seizure; no forensic link to the accused\n"
    ),
}

README = """# Directorate of Prosecutions Scrutiny — mock test data

One folder per case; one CSV per source (all MOCK). The completeness/sufficiency fields cue the
SCRUTINY VERDICT and thus which drafter should PRODUCE its document (the guard rail in `test_prosecution.py`).

| Case | Verdict signal | Expected drafter | Rejected drafters |
|------|----------------|------------------|-------------------|
| PR1 | complete + sufficient (statements, Sec 63 cert, forensic all present; strong) | Fit-for-Trial Opinion Drafter | Return-Memo; Weak-Case |
| PR2 | curable gaps: no Sec 218 sanction, no Sec 63 cert, 2 statements missing (evidence sound if cured) | Return-Memo Drafter | Fit-for-Trial; Weak-Case |
| PR3 | paperwork COMPLETE but evidence INSUFFICIENT (sole witness retracted, no recovery, medical inconclusive) | Weak-Case Opinion Drafter | Fit-for-Trial; Return-Memo |

The distinguisher: PR2 is INCOMPLETE-but-curable (procedural), PR3 is COMPLETE-but-substantively-weak.

Always-run: Case Extractor, Evidence Completeness Checker, Sufficiency & Section Verifier, Synthesizer.
PR4 (in test_prosecution.py, no data dir): a vague one-liner -> the Extractor pauses [NEEDS_INPUT].
"""


def main():
    for rel, content in FILES.items():
        p = BASE / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (BASE / "README.md").write_text(README, encoding="utf-8")
    print(f"[OK] wrote {len(FILES)} CSVs + README under {BASE}")
    for case in ("PR1", "PR2", "PR3"):
        print(f"  {case}: {sorted(f.name for f in (BASE / case).iterdir())}")


if __name__ == "__main__":
    main()
