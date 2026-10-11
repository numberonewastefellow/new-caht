#!/usr/bin/env python3
"""
Generate mock test data for the Cybercrime Investigation workflow.

Creates test_data/cybercrime/{CC1,CC2,CC3}/*.csv — one CSV per data source, mirroring
the insurance CL1/CL2/CL3 pattern. The PRESENCE/ABSENCE of a source cues routing:
  CC1 (LIVE, isolated)      -> only a fresh single complaint, funds NOT_FROZEN  -> Golden-Hour Freeze only
  CC2 (RING, golden-hour gone) -> related complaints + mule accounts + registry hit, funds WITHDRAWN -> Charge-Sheet
  CC3 (aged, funds frozen)  -> existing FIR + frozen funds + verified accused -> Refund + Charge-Sheet
All data is MOCK. Re-run to regenerate.
"""
from pathlib import Path

BASE = Path(__file__).parent / "test_data" / "cybercrime"

FILES = {
    # ── CC1: fresh single UPI fraud, golden hour LIVE, isolated ──────────────
    "CC1/complaint_ncrp.csv": (
        "complaint_id,reported_at,minutes_since_txn,victim_name,victim_city,amount_inr,channel,beneficiary_upi,beneficiary_account,ifsc,fraudster_phone,utr,txn_time,funds_status,related_complaints_count\n"
        "NCRP-2026-0455123,2026-08-05T14:54,22,Ramesh Kumar,Hyderabad,180000,UPI,fraudster@ybl,50100123456,HDFC0000123,+918612345678,412345678901,2026-08-05T14:32,NOT_FROZEN,0\n"
    ),
    "CC1/victim_statement.csv": (
        "field,detail\n"
        "narrative,\"Received a call claiming bank KYC update. Was asked to share an OTP. Immediately Rs 1\\,80\\,000 was debited via UPI to fraudster@ybl in a single transaction.\"\n"
        "evidence,\"UPI app screenshot showing the debit at 14:32 today\"\n"
        "reported_via,\"1930 helpline, 22 minutes after the debit\"\n"
    ),
    "CC1/transaction_trail.csv": (
        "hop,from_party,to_account_or_upi,amount_inr,time,note\n"
        "1,Victim Ramesh Kumar,fraudster@ybl / 50100123456 HDFC,180000,2026-08-05T14:32,single hop; funds still sitting in beneficiary account; not yet withdrawn or frozen\n"
    ),

    # ── CC2: mule-account ring / digital arrest, golden hour EXPIRED ─────────
    "CC2/complaint_ncrp.csv": (
        "complaint_id,reported_at,days_since_txn,victim_name,victim_city,amount_inr,channel,beneficiary_account,ifsc,device_imei,funds_status,related_complaints_count,fraud_type\n"
        "NCRP-2026-0489777,2026-08-01,4,Sunitha Rao,Vijayawada,940000,IMPS,50200567890,ICIC0000567,356938035643809,WITHDRAWN,40,digital_arrest\n"
    ),
    "CC2/related_complaints.csv": (
        "complaint_id,beneficiary_account,device_imei,amount_inr,victim_city\n"
        "NCRP-2026-0489777,50200567890,356938035643809,940000,Vijayawada\n"
        "NCRP-2026-0489780,50200567890,356938035643809,210000,Guntur\n"
        "NCRP-2026-0489791,50200567890,356938035643809,155000,Hyderabad\n"
        "NCRP-2026-0489803,50300111222,356938035643809,320000,Warangal\n"
        "NCRP-2026-0489815,50300111222,356938035643809,88000,Nellore\n"
        "NCRP-2026-0489822,50200567890,356938035643809,430000,Visakhapatnam\n"
        "NCRP-2026-0489834,50200567890,356938035643809,120000,Kurnool\n"
        "NCRP-2026-0489849,50300111222,356938035643809,275000,Khammam\n"
        "NCRP-2026-0489850,50200567890,356938035643809,60000,Kadapa\n"
        "NCRP-2026-0489861,50200567890,356938035643809,510000,Tirupati\n"
        "NCRP-2026-0489870,50300111222,356938035643809,199000,Karimnagar\n"
        "NCRP-2026-0489888,50200567890,356938035643809,145000,Anantapur\n"
    ),
    "CC2/mule_accounts.csv": (
        "account,layer,holder_name,bank,linked_complaints\n"
        "50200567890,LAYER1,Ravi Teja (rented account),ICICI,28\n"
        "50300111222,LAYER2,Kiran Kumar (rented account),Axis,12\n"
    ),
    "CC2/suspect_registry.csv": (
        "account,upi,flag,record_id\n"
        "50200567890,,LAYER1_MULE_FLAGGED,SR-2026-90456\n"
        "50300111222,,LAYER2_MULE_FLAGGED,SR-2026-90461\n"
    ),
    "CC2/cdr_ipdr.csv": (
        "phone,device_imei,cell_tower,time,note\n"
        "+919812345678,356938035643809,VJA-042,2026-08-01T10:15,same device IMEI recurs across the ring complaints\n"
    ),

    # ── CC3: aged case, funds already frozen, refund + charge-sheet stage ────
    "CC3/existing_fir.csv": (
        "fir_no,police_station,district,date,sections,accused_name,arrest_date,stage,fraud_type\n"
        "214/2026,Cyber Crime PS,Hyderabad,2026-06-20,IT Act 66C/66D; BNS 318/319,Anil Mehta,2026-07-01,chargesheet_pending,investment_fraud\n"
    ),
    "CC3/frozen_funds.csv": (
        "account,ifsc,bank,amount_frozen_inr,frozen_on,status,victim_account,victim_bank\n"
        "50100123456,HDFC0000123,HDFC,320000,2026-06-25,LIEN_MARKED,60200999888,SBI\n"
    ),
    "CC3/accused_verified.csv": (
        "name,account,suspect_registry_record,cctns_antecedents,imei_status,verified\n"
        "Anil Mehta,50100123456,SR-2026-77001,1 prior FIR (cheating),blacklisted,YES\n"
    ),
    "CC3/evidence_checklist.csv": (
        "item,status\n"
        "FIR copy,OBTAINED\n"
        "Bank statements,OBTAINED\n"
        "CDR/IPDR,OBTAINED\n"
        "Section 63 BSA / 65B certificate,PENDING\n"
        "FSL cyber-forensics report,PENDING\n"
        "Seizure mahazar,OBTAINED\n"
    ),
}

README = """# Cybercrime workflow — mock test data

One folder per case; one CSV per data source (all MOCK). Presence/absence of a source
cues which drafter the workflow should route to — the guard-rail in `test_cybercrime.py`.

| Case | Stage signal | Sources present | Expected drafter(s) | Rejected drafter(s) |
|------|--------------|-----------------|---------------------|---------------------|
| CC1  | funds NOT_FROZEN, 22 min old, 0 related | complaint, victim stmt, single-hop trail | Golden-Hour Freeze Drafter | Refund; Charge-Sheet |
| CC2  | funds WITHDRAWN, 4 days old, 40 related | complaint, related_complaints, mule_accounts, suspect_registry, cdr_ipdr | Charge-Sheet Drafter | Freeze; Refund |
| CC3  | funds LIEN_MARKED, FIR exists, accused verified | existing_fir, frozen_funds, accused_verified, evidence_checklist | Refund + Charge-Sheet | Freeze |

Always-run analysis agents (Extractor, Fraud-Ring Linker, Records & Registry Verifier, Case Synthesizer)
fire on every case. The discriminating signal is which DRAFTERS run.
"""


def main():
    for rel, content in FILES.items():
        p = BASE / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (BASE / "README.md").write_text(README, encoding="utf-8")
    print(f"[OK] wrote {len(FILES)} CSVs + README under {BASE}")
    for case in ("CC1", "CC2", "CC3"):
        files = sorted(f.name for f in (BASE / case).iterdir())
        print(f"  {case}: {files}")


if __name__ == "__main__":
    main()
