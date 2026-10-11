# Aarogyasri Claim Pre-Authorization workflow — mock test data

One folder per case; one CSV per source (all MOCK / SYNTHETIC — no real PHI). The explicit
checklist/status fields cue the PRE-AUTH DECISION and thus which drafter should PRODUCE its
document (the guard rail in `test_aarogyasri.py`).

| Case | Decision signal | Expected drafter | Rejected drafters |
|------|-----------------|------------------|-------------------|
| AR1 | in-package + matches diagnosis + investigations complete + within benefit | Approval Note Drafter | Query Note; Rejection Note |
| AR2 | mandatory Knee X-ray report MISSING (curable); otherwise in order | Query Note Drafter | Approval Note; Rejection Note |
| AR3 | upcoding / package mismatch (major laparotomy for an appendicitis) | Rejection Note Drafter | Approval Note; Query Note |

The Extractor classifies with a STRICT PRIORITY ORDER (REJECT grounds first, then QUERY, then APPROVE),
so an upcoded case is a REJECT even though its docs are complete, and a merely-missing report is a QUERY.

Always-run: Preauth Extractor, History & Benefit Checker, Package & Upcoding Verifier, Synthesizer.
AR4 (HITL, no folder) is a vague one-liner in test_aarogyasri.py -> the Extractor must pause [NEEDS_INPUT].
