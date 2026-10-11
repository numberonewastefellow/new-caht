# Directorate of Prosecutions Scrutiny — mock test data

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
