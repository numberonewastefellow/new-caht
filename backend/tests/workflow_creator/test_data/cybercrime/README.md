# Cybercrime workflow — mock test data

One folder per case; one CSV per data source (all MOCK). Presence/absence of a source
cues which drafter the workflow should route to — the guard-rail in `test_cybercrime.py`.

| Case | Stage signal | Sources present | Expected drafter(s) | Rejected drafter(s) |
|------|--------------|-----------------|---------------------|---------------------|
| CC1  | funds NOT_FROZEN, 22 min old, 0 related | complaint, victim stmt, single-hop trail | Golden-Hour Freeze Drafter | Refund; Charge-Sheet |
| CC2  | funds WITHDRAWN, 4 days old, 40 related | complaint, related_complaints, mule_accounts, suspect_registry, cdr_ipdr | Charge-Sheet Drafter | Freeze; Refund |
| CC3  | funds LIEN_MARKED, FIR exists, accused verified | existing_fir, frozen_funds, accused_verified, evidence_checklist | Refund + Charge-Sheet | Freeze |

Always-run analysis agents (Extractor, Fraud-Ring Linker, Records & Registry Verifier, Case Synthesizer)
fire on every case. The discriminating signal is which DRAFTERS run.
