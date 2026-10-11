# Wave-1 Shortlist — Other Citizen-Service & Admin (TS & AP)
_Typed/structured digital inputs only — no Telugu handwritten OCR. Pipeline: EXTRACT → CHECK HISTORY → VERIFY
→ ROUTE & DRAFT; officer decides._

| # | Candidate | AI-fit | Offline | Prestige | Feasibility | Total |
|---|-----------|:--:|:--:|:--:|:--:|:--:|
| 1 | Health — Aarogyasri claim pre-authorization (TS / AP NTR Vaidya Seva) | 5 | 5 | 5 | 4 | **19** |
| 2 | Education — ePASS post-matric scholarship / fee-reimbursement verification | 5 | 4 | 4 | 5 | **18** |
| 3 | Municipal — TS-bPASS building-permission defect-check (GHMC/CDMA; AP DTCP) | 5 | 3 | 4 | 4 | **16** |
| 4 | Civil Supplies — Food-Security/ration-card eligibility & de-dup (ePDS/GSWS) | 4 | 4 | 4 | 4 | **16** |
| 5 | Transport/RTA — Sarathi/Vahan licence, permit & challan-appeal | 4 | 3 | 4 | 4 | **15** |
| 6 | Finance/Treasury — bill pre-audit & pension (IFMIS/e-Kuber) | 4 | 4 | 3 | 4 | **15** |
| 7 | Health — Drugs Control Administration licensing (ONDLS) | 4 | 3 | 3 | 4 | **14** |
| 8 | Agriculture — Rythu Bharosa scheme-eligibility triage | 4 | 3 | 4 | 3 | **14** |

- **1. Aarogyasri Pre-Auth** ★ — ~99L BPL families, ~1,400 hospitals, 1,835 procedures; TS cleared Rs 1,779cr FY24-25. Pre-auth (<24h) + post-discharge claim adjudication + fraud/upcoding. Systems: aarogyasri.telangana.gov.in (ASRI 2.0), drntrvaidyaseva.ap.gov.in; PM-JAY convergence. AI: extract pre-auth packet → check prior claims/benefit balance → verify package vs 1,835-master + rate card → draft approve/query/reject w/ cited rule. **PHI of 1cr families = maximal offline case.**
- **2. ePASS Scholarship** — lakhs/cycle; active fraud (CBI FIR minority-scam; ghost institutions; ~Rs 144cr loss). Verify caste/income caps, course-fee caps, institution vs live U-DISE, duplicate detection. Systems: telanganaepass.cgg.gov.in, AP Jnanabhumi/navasakam, MeeSeva certs, DBT. **Textbook verify+defect-check; feasibility 5.**
- **3. TS-bPASS Building Permission** — instant-approval/single-window scrutiny; setback/FAR/zoning; occupancy cert. Systems: tsbpass/tgbpass.telangana.gov.in, GHMC, CDMA. Statute: TS-bPASS Act 2020. AI: extract plan+NOCs → verify rule compliance → draft defect/shortfall or sanction w/ cited rule.
- **4. PDS/Ration eligibility & de-dup** — FSC applications, eKYC, income/land/govt-employee exclusion, bogus-card detection at crore scale. Systems: epds/civilsupplies.telangana.gov.in (AePDS+ePoS), GSWS. Statute: NFSA 2013. HITL essential (livelihood consequences).
- **5-8:** Transport/RTA licence+challan-appeal (15); Treasury bill pre-audit/pension (15, whole-of-govt financial data); Drugs Control licensing (14); Rythu Bharosa L1→L2→L3 eligibility (14, GIS land-use checks limit feasibility).

**Standouts: #1 Aarogyasri + #2 ePASS.** Fast-follows: #3 TS-bPASS, #4 PDS.
