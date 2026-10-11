# Wave-1 Shortlist — Police / Home / Law-Enforcement (TS & AP)

_All use cases run on already-digital typed records (CCTNS/EeCOPS, NCRP, e-Prisons, verification portals, fire-NOC
forms) — NO Telugu handwritten OCR. Pipeline: EXTRACT → CHECK HISTORY → VERIFY → ROUTE & DRAFT; officer decides.
Cross-cutting "why offline" anchor: TSCOP police app was hacked + repeated TS police-data breaches → criminal-justice
AI must be air-gapped on-prem._

| # | Candidate | AI-fit | Offline | Prestige | Feasibility | Total |
|---|-----------|:--:|:--:|:--:|:--:|:--:|
| 1 | Cybercrime — TGCSB (TS) / AP Cybercrime | 5 | 5 | 5 | 5 | **20** |
| 2 | State Police — Investigation & Station Records (CCTNS/EeCOPS/ICJS) | 5 | 5 | 5 | 4 | **19** |
| 3 | Police Verification / Special Branch (passport, tenant, employee, arms, PCC) | 5 | 5 | 3 | 5 | **18** |
| 4 | Prisons & Correctional Services (e-Prisons) | 4 | 5 | 4 | 4 | **17** |
| 5 | CID — Economic Offences & Anti-Human-Trafficking | 4 | 5 | 4 | 3 | **16** |
| 6 | Fire & Emergency / SDRFS (TS SDRFS; AP Fire) — NOC scrutiny | 4 | 3 | 3 | 5 | **15** |
| 7 | Traffic Enforcement (e-Challan) | 3 | 2 | 3 | 4 | **12** |
| 8 | Disaster Management (APSDMA / TS) | 2 | 2 | 4 | 3 | **11** |

## 1. Cybercrime — TGCSB / AP Cybercrime — 20/20
- **Jobs:** NCRP petition triage/de-dup/assignment; 1930 "golden-hour" bank/PG freeze requests; mule-account & transaction-chain linking; PT-warrant tracking; refund-claim (MRM) drafting; IT Act/BNS charge-sheet assembly.
- **Systems:** NCRP (cybercrime.gov.in), 1930 helpline, I4C, TGCSB Money Restoration Module, CCTNS/ICJS.
- **Statute:** IT Act 2000; BNS/BNSS 2023; RBI/bank freeze SOPs.
- **AI-fit:** complaint-triage agent (extract accounts/UPI/URLs → cluster fraud rings → verify watchlists → route w/ confidence); golden-hour freeze-request automation; pattern-of-fraud linking; refund-order draft; charge-sheet draft.
- **Offline:** victim PII + bank data + live intel. **Best beachhead** — structurally identical to Prajavani copilot, hard ROI (funds frozen/refunded ~Rs 850cr cited).
- Sources: tgcsb.tspolice.gov.in; deccanherald.com; newsonair.gov.in.

## 2. State Police — Investigation & Station Records — 19/20
- TS = national frontrunner (~709 stations; first CCTNS-EeCOPS↔ICJS live integration; first digitally-signed FIR under new laws).
- **Jobs:** FIR/e-FIR/Zero-FIR intake; petition-enquiry; charge-sheet drafting under BNSS 60/90-day deadlines; repeat-complainant/accused linking; missing-person matching; case-diary notes; IPC→BNS mapping.
- **Systems:** CCTNS + EeCOPS, ICJS, TSCOP (facial recog), Hawk Eye, national missing-persons DB/UNIFY; AP appolice.gov.in + Dial-112 ERSS.
- **Statute:** BNS/BNSS/BSA 2023 (Sec 105 audio-video search/seizure; 176(3) forensics 7yr+; 173 e-FIR/Zero-FIR).
- **AI-fit:** charge-sheet drafting workflow (BNSS-deadline countdown, IPC→BNS mapping, cited); repeat-linking; BNSS-compliance checklist; missing-person matching; petition-enquiry drafting.
- Highest-volume flagship prize; bigger integration lift → feasibility 4.
- Sources: exhibition.skoch.in; thenewsminute.com; mha.gov.in.

## 3. Police Verification / Special Branch — 18/20
- **Jobs:** passport PV (residence+criminal check → clear/adverse to PSK), tenant verification (Hawk Eye), employee PVC, arms-license antecedents, PCC. Repetitive, form-driven, already digital.
- **Systems:** pvc.tspolice.gov.in, Hawk Eye, Passport Seva integration, Special Branch criminal index, CCTNS antecedent lookup.
- **Statute:** Passports Act 1967; Arms Act 1959; BNSS 172 / tenant-info notifications.
- **AI-fit:** near-perfect loop — extract applicant → check FIR/antecedents → verify CCTNS/SB index → draft clear/adverse report w/ confidence + flagged hits. **Highest feasibility → best low-risk technical pilot.**
- Sources: pvc.tspolice.gov.in; delhipolice.gov.in; godigit.com.

## 4. Prisons & Correctional Services (e-Prisons) — 17/20
- **Jobs:** admission/release docs; undertrial-review & BNSS Sec 479 first-timer-release eligibility; remission/premature-release calc; parole/furlough proposals; e-Mulaqat; court-production (PT-warrant) scheduling.
- **Systems:** e-Prisons (ICJS jail pillar), e-Mulaqat, Prison-Court Video Linkage; AP apprisons.gov.in.
- **Statute:** BNSS Sec 479; Prisons Act 1894 → AP Prisons & Correctional Services Bill 2026.
- **AI-fit:** undertrial-review workflow (extract custody+charges → check BNSS 479/max-sentence → verify court orders via ICJS → draft release-eligibility list/bail memo for Supdt/DLSA); remission calc; parole draft; court-production scheduling. Strong humanitarian/decongestion impact.
- Sources: ecommitteesci.gov.in/e-prison; deccanchronicle.com; AP Prisons Bill 2026 (PRS).

## 5. CID — Economic Offences & Anti-Human-Trafficking — 16/20
- **Jobs:** multi-doc economic-fraud case bundling (chit-fund/Ponzi/land-fraud); AHTU victim/rescue docs; inter-state coordination; complaint scrutiny.
- **Systems:** cid.tspolice.gov.in; CCTNS/ICJS; EOW registries.
- **Statute:** BNS/BNSS; Immoral Traffic (Prevention) Act 1956; Prize Chits & Money Circulation Act 1978.
- Lower feasibility (heterogeneous, lower-volume cases). Sources: cid.tspolice.gov.in.

## 6. Fire & Emergency / SDRFS — 15/20
- **Jobs:** fire-NOC application scrutiny (NBC + TS Fire Services Act, 60-day clock); 5-yr NOC renewals; post-incident reports; compliance records.
- **Systems:** tsfire.cgg.gov.in; NBC; TG-bPASS linkage.
- **Statute:** Telangana Fire Services Act 1999; National Building Code.
- **AI-fit:** NOC-scrutiny workflow (extract plan+certs → check prior NOC → verify NBC clause checklist → draft NOC/deficiency memo w/ cited clauses). **Very high feasibility, low data-sensitivity → clean self-contained "second vertical" pilot.**
- Sources: uattsfire.cgg.gov.in; TS Fire NOC/NBC docs.

## 7-8 (de-prioritise)
- **Traffic e-Challan (12):** issuance already automated; residual value = accident-report drafting, 12-point repeat-offender notes, court-challan bundling. Weak offline case.
- **Disaster Management (11):** forecasting already AI'd (AP + IIT-GN flood alerts); only back-office relief-claim/damage-report drafting fits; weak offline (public data).

### GTM read
Lead with **#1 Cybercrime** (Prajavani-identical, hungry high-prestige customer, hard ROI, airtight offline). **#3 Police Verification** = cleanest technical proof-of-concept. **#2 State Police charge-sheet/BNSS** = highest-prestige prize, bigger lift. **#6 Fire-NOC** = strong low-friction second vertical.
