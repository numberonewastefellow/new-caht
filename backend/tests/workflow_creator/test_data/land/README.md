# Land Mutation & ROR Correction workflow — mock test data

One folder per case; one CSV per source (all MOCK). The application/RoR fields cue the CASE TYPE
and thus which drafter should PRODUCE its document (the guard rail in `test_land.py`).

| Case | Type signal | Expected drafter | Rejected drafters |
|------|-------------|------------------|-------------------|
| LM1 | deed extent == RoR (2.00), Patta, Sec 22A N, no dispute | Mutation Order Drafter | Objection Memo; RoR Correction |
| LM2 | deed 3.00 vs RoR 2.20, Part-B / Sec 22A Y, rival claim | Objection Memo Drafter | Mutation Order; RoR Correction |
| LM3 | clerical name/khata/extent typo in existing 1-B, no transfer | RoR Correction Drafter | Mutation Order; Objection Memo |

Key LM2 vs LM3 disambiguation: LM2 is a TRANSFER (sale deed) that conflicts with the register ->
objection; LM3 is NOT a transfer, just a clerical correction of the existing record proven by the
original passbook -> correction order.

Always-run: Application Extractor, Chain-of-Title Checker, Record Verifier, Synthesizer.
LM4 (in test_land.py, no CSVs): a vague one-liner -> the Extractor pauses with [NEEDS_INPUT].
