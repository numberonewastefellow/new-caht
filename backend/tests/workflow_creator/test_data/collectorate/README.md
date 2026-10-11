# District Collectorate Coordination workflow — mock test data

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
