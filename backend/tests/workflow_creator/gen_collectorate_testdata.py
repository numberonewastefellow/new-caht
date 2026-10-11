#!/usr/bin/env python3
"""
Mock test data for the District Collectorate Coordination workflow
-> test_data/collectorate/{CO1,CO2,CO3}/*.csv.

The explicit `item_type` field + the STRUCTURE of the tables cue the ITEM TYPE and thus which
drafter should PRODUCE:
  CO1 VIP_REFERENCE  (one MP letter forwarding a citizen's petition)          -> VIP Reference Reply
  CO2 SLA_OUTLIER    (one line-department SLA breach flagged for escalation)  -> Department Tasking Letter
  CO3 REVIEW_MEETING (agenda + MANY department feeds for the weekly review)   -> Weekly Review Brief
CO4 (HITL) is a vague one-liner with NO item/feed/agenda data -> the Extractor pauses [NEEDS_INPUT] (no CSV needed).

All data is MOCK. The Collectorate desk is COORDINATION DECISION-SUPPORT ONLY — none of this decides
which department is failing or grades any officer; the Collector reviews and signs.
"""
from pathlib import Path

BASE = Path(__file__).parent / "test_data" / "collectorate"

FILES = {
    # ── CO1: VIP/MP reference forwarded for reply -> VIP Reference Reply ──────
    "CO1/reference.csv": (
        "field,value\n"
        "item_type,VIP_REFERENCE\n"
        "inward_no,COLL/INW/2026/04412\n"
        "date_received,2026-07-30\n"
        "forwarded_by,Sri K. Ramesh Rao (Member of Parliament)\n"
        "constituency,Malkajgiri\n"
        "channel,MP reference letter forwarded to the District Collector (tappal / inward)\n"
        "citizen,Smt. Lakshmi Devi\n"
        "subject,Delayed sanction of a 2BHK housing-scheme unit\n"
        "ask,Requests early sanction and possession of the allotted 2BHK unit\n"
        "concerned_department,Housing (2BHK)\n"
        "clock_start,2026-07-30 (15-day CSMoP acknowledgement window)\n"
    ),
    "CO1/letter.csv": (
        "para_no,text\n"
        "1,From the office of Sri K. Ramesh Rao MP Malkajgiri — forwarding the enclosed representation of Smt. Lakshmi Devi for favourable and early consideration by the District Collector.\n"
        "2,The petitioner states that her 2BHK unit under the housing scheme was approved in principle but the final sanction and possession have been pending for over eight months.\n"
        "3,Requested to look into the matter and intimate the action taken to this office as well as to the petitioner.\n"
    ),
    "CO1/dept_action_status.csv": (
        "department,application_id,current_status,as_of,source_row\n"
        "Housing (2BHK),HSG-2BHK-2026-77120,Beneficiary verified; unit earmarked; final sanction order under processing at Mandal level,2026-07-29,TG-DMS Housing feed row 5\n"
    ),
    "CO1/prior_references.csv": (
        "reference_id,citizen,subject,representative,note\n"
        "COLL/INW/2026/04412,Smt. Lakshmi Devi,Delayed 2BHK sanction,Sri K. Ramesh Rao MP,Current reference (first on this matter)\n"
        "-,-,No earlier reference found for this citizen or subject,-,No duplicate on record\n"
    ),

    # ── CO2: single line-department SLA breach -> Department Tasking Letter ───
    "CO2/sla_feed.csv": (
        "field,value\n"
        "item_type,SLA_OUTLIER\n"
        "source,TG-DMS Collector Dashboard - SLA-breach flag (single outlier)\n"
        "department,MeeSeva\n"
        "parameter,Income-certificate service requests - SLA disposal\n"
        "mandal,Keesara\n"
        "sla_days,15\n"
        "days_elapsed,41\n"
        "status,BREACHED\n"
        "pending_count,318\n"
        "flagged_on,2026-08-03\n"
        "note,Single department outlier flagged for the Collector's escalation (not a full review)\n"
    ),
    "CO2/pendency_history.csv": (
        "month,department,pending_start,received,disposed,pending_end\n"
        "2026-05,MeeSeva (Keesara),120,540,510,150\n"
        "2026-06,MeeSeva (Keesara),150,560,480,230\n"
        "2026-07,MeeSeva (Keesara),230,600,512,318\n"
    ),
    "CO2/hod.csv": (
        "name,designation,department,note\n"
        "Sri P. Anjaneyulu,Mandal MeeSeva Manager / concerned Head of Department,MeeSeva (Keesara mandal),Officer to be tasked to clear the pendency\n"
    ),

    # ── CO3: weekly-review agenda + MANY department feeds -> Weekly Review Brief ──
    "CO3/agenda.csv": (
        "field,value\n"
        "item_type,REVIEW_MEETING\n"
        "source,Collector's weekly departmental review - agenda + multi-department status feeds\n"
        "meeting_date,2026-08-06\n"
        "chair,District Collector\n"
        "venue,Collectorate conference hall\n"
        "departments_to_review,Housing; MeeSeva; Prajavani; Welfare; Irrigation; Panchayat Raj\n"
        "scope,Full 6-department weekly review across the dashboard parameters\n"
    ),
    "CO3/department_feeds.csv": (
        "department,parameter,target,actual,status,sla_status,source_row\n"
        "Housing,2BHK units handed over (cumulative),1200,1180,ON TARGET,within SLA,TG-DMS row 5\n"
        "MeeSeva,Service requests disposed within SLA,95%,71%,SLIPPING,SLA breached in 3 mandals,TG-DMS row 12\n"
        "Prajavani,Grievances disposed within 30 days,90%,74%,SLIPPING,pendency up 18% vs last week,TG-DMS row 19\n"
        "Welfare,Scholarship disbursement,100%,98%,ON TARGET,within SLA,TG-DMS row 27\n"
        "Irrigation,Minor-irrigation tank desilting,80%,55%,SLIPPING,behind schedule,TG-DMS row 33\n"
        "Panchayat Raj,Gram Panchayat road works completed,75%,73%,ON TARGET,within SLA,TG-DMS row 41\n"
    ),
    "CO3/decision_points.csv": (
        "point,department,needs\n"
        "MeeSeva SLA slippage in 3 mandals,MeeSeva,Collector's direction on additional counters / staff\n"
        "Prajavani pendency up 18%,Prajavani,Collector's call on an escalation drive\n"
        "Irrigation desilting behind schedule,Irrigation,Collector's decision on re-tendering vs departmental execution\n"
    ),
}

README = """# District Collectorate Coordination workflow — mock test data

One folder per case; one CSV per source (all MOCK). The explicit `item_type` field + the STRUCTURE
of the tables cue the ITEM TYPE and thus which drafter should PRODUCE its coordination document
(the guard rail in `test_collectorate.py`). The desk is COORDINATION DECISION-SUPPORT ONLY —
none of this decides which department is failing or grades an officer; the Collector reviews and signs.

| Case | Item-type signal | Expected drafter | Rejected drafters |
|------|------------------|------------------|-------------------|
| CO1 | VIP_REFERENCE — one MP letter forwarding a citizen's petition | VIP Reply Drafter | Tasking Letter; Review Brief |
| CO2 | SLA_OUTLIER — one line-department SLA breach flagged for escalation | Tasking Letter Drafter | VIP Reply; Review Brief |
| CO3 | REVIEW_MEETING — agenda + MANY department feeds for the weekly review | Review Brief Drafter | VIP Reply; Tasking Letter |
| CO4 | vague one-liner, no item/feed/agenda data (HITL) | (Extractor pauses [NEEDS_INPUT]) | all drafters |

Always-run: Intake Extractor, Pendency & SLA Checker, Status Verifier, Coordination Synthesizer.
"""


def main():
    for rel, content in FILES.items():
        p = BASE / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (BASE / "README.md").write_text(README, encoding="utf-8")
    print(f"[OK] wrote {len(FILES)} CSVs + README under {BASE}")
    for case in ("CO1", "CO2", "CO3"):
        print(f"  {case}: {sorted(f.name for f in (BASE / case).iterdir())}")


if __name__ == "__main__":
    main()
