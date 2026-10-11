# ePASS Post-Matric Scholarship workflow - mock test data

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
