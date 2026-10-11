# CID Economic Offences & AHT workflow — mock test data

One folder per case; one CSV per source (all MOCK, no real victim identities). The status/type fields cue
the CASE TYPE and thus which drafter should PRODUCE its document (the guard rail in `test_cid.py`).

| Case | Type signal | Expected drafter | Rejected drafters |
|------|-------------|------------------|-------------------|
| CID1 | EOW deposit fraud; fund_trail_status=PENDING | Fund-Trail Report Drafter | AHT Victim-Rescue; Investigation |
| CID2 | AHTU rescue; victim_documentation_status=PENDING | AHT Victim-Rescue Report Drafter | Fund-Trail; Investigation |
| CID3 | investigation_status=COMPLETE + verified + trail annexed | Investigation Report Drafter | Fund-Trail; AHT Victim-Rescue |

CID4 (HITL) is a vague one-liner with NO data (inline in the test) -> the Extractor must pause [NEEDS_INPUT].

Always-run: Case Extractor, Entity & Fund-Flow Linker, Records Verifier, Case Synthesizer.
