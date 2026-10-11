# High Court Registry Scrutiny workflow — mock test data

One folder per case; one CSV per source (all MOCK). The scrutiny/status fields cue the REGISTRY STAGE
and thus which drafter should PRODUCE its clerical document (the guard rail in `test_registry.py`).
The Registry is CLERICAL ONLY — none of this touches the merits of any case.

| Case | Stage signal | Expected drafter | Rejected drafters |
|------|--------------|------------------|-------------------|
| HC1 | fresh filing; court fee short + welfare stamp/certified copy missing + index defect | Defect Memo Drafter | Cause-List Entry; Judgment Headnote |
| HC2 | fresh filing; all requisites complete, NO defects, pending registration | Cause-List Entry Drafter | Defect Memo; Judgment Headnote |
| HC3 | DISPOSED matter; judgment pronounced + operative portion present | Judgment Headnote Drafter | Defect Memo; Cause-List Entry |
| HC4 | vague one-liner, no filing data (HITL) | (Extractor pauses [NEEDS_INPUT]) | all drafters |

Always-run: Filing Extractor, Connected-Matter Checker, Defect Verifier, Registry Synthesizer.
