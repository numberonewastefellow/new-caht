# State Police Charge-Sheet workflow — mock test data

One folder per case; one CSV per source (all MOCK). The compliance/status fields cue the CASE STAGE
and thus which drafter should PRODUCE its document (the guard rail in `test_police.py`).

| Case | Stage signal | Expected drafter | Rejected drafters |
|------|--------------|------------------|-------------------|
| SP1 | complete + Sec105 done + Sec176(3) NA + day 40/90 | Charge-Sheet Drafter | Deficiency Memo; Default-Bail |
| SP2 | Sec176(3) forensic + Sec105 AV NOT done (10yr offence) | Compliance Deficiency Memo Drafter | Charge-Sheet; Default-Bail |
| SP3 | day 88/90 + FSL pending + investigation incomplete | Default-Bail Risk Drafter | Charge-Sheet; Deficiency Memo |

Always-run: Case-File Extractor, Antecedents & Linkage, BNSS Compliance & Section-Mapping Verifier, Case Synthesizer.
