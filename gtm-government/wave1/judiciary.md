# Wave-1 Shortlist — Judiciary / Courts / Prosecution / Legal (TS & AP)

_Positioning guardrail: VirtualAI is registry/clerical/decision-SUPPORT only — EXTRACT → CHECK HISTORY →
VERIFY RECORDS → ROUTE & DRAFT, always with confidence scores + source citations. The judge/prosecutor/
Member-Secretary always decides. AI never adjudicates. Telugu handwritten OCR out of scope._

Ranking: Prosecutions (18) → High Courts (18) → District Judiciary (17) → Legal Services Authorities (17) → Legal Metrology (12).

## 1. Directorate of Prosecutions — TS (Hyderabad) & AP (Vijayawada) — 18/20
- **Mandate:** criminal prosecution for the State; scrutinise charge sheets; legal opinions. Under **Home Dept** (executive — easier sell than judiciary).
- **Jobs:** legal opinion on FIRs & draft charge sheets; charge-sheet (Sec.193 BNSS) defect/completeness checking (65B/forensic certs, sanction, seizure memos); case-brief/opening-address prep; undertrial records; appeal-worthiness opinions; prosecutor KPI/MIS.
- **Systems:** e-Prosecution (`eprosecution.gov.in`), ICJS (links CCTNS/e-Courts/e-Prisons/e-Forensics), `prosecution.telangana.gov.in`.
- **Statute:** Directorate under **Sec.20 BNSS 2023** (BNSS now mandates District Directorates); PPs/APPs under Sec.18–19 BNSS.
- **AI-fit:** charge-sheet scrutiny agent; legal-opinion drafter (cited); appeal-triage HITL; auto-draft scrutiny note/summons list/KPI MIS.
- **Offline:** FIR/charge-sheet/victim-witness PII + forensic reports = maximal air-gap justification.
- **Score:** AI-fit 5 · Offline 5 · Prestige 4 · Feasibility 4 = **18**. Closest analogue to the proven Revenue Prajavani copilot; **best first sale**.

## 2. High Courts — TS HC & AP HC (Registry & Case Management) — 18/20
- **Jobs:** e-filing defect/scrutiny reporting (court-fee, index, vakalatnama, annexures); cause-list prep; certified copies; judgment headnoting/neutral-citation tagging; precedent/connected-matter chaining; paper-book compilation.
- **Systems:** CIS 3.x, e-filing (`aphc.gov.in/efiling`, `tshc.gov.in`), NJDG/HC-NJDG, NSTEP, neutral-citation portals. TS HC runs open-source (Ubuntu/LibreOffice/PostgreSQL).
- **AI-fit:** e-filing defect-checker; citation-anchored case-file summarisation; judgment-indexing automation; connected-matter/precedent agent.
- **Offline:** pre-publication draft judgments, in-camera/POCSO/matrimonial, litigant PII.
- **Score:** AI-fit 5 · Offline 5 · Prestige 5 · Feasibility 3 (independent judiciary; e-Committee/NIC stack) = **18**. Highest prestige, hardest entry — enter as registry/clerical support only.

## 3. District & Sessions Courts — District Judiciary TS & AP — 17/20
- **Jobs:** e-filing defect-checking at scale; cause-list churn; bail/remand/notice/summons drafting; limitation/missing-doc checks; NJDG pendency returns; UTRC undertrial-review packs.
- **Systems:** CIS 3.x, NJDG (district), e-filing, NSTEP, Virtual Courts, e-Sewa Kendras, ICJS.
- **AI-fit:** registry defect+limitation agent; cause-list/bundling automation; order/notice drafting copilot (template-grounded, never a bail recommendation); undertrial-review summariser.
- **Score:** AI-fit 5 · Offline 5 · Prestige 4 · Feasibility 3 = **17**. Highest raw document volume; same stack-control constraint.

## 4. State & District Legal Services Authorities — TSLSA, APSLSA + DLSAs — 17/20
- **Mandate:** free legal aid (Art.39-A) + Lok Adalat/Permanent Lok Adalat. APSLSA: 1 HCLSC, 13 DLSAs, 13 mediation centres, 145 MLSCs — high volume, largely manual. Autonomous statutory body (strong social mandate, low resistance).
- **Jobs:** legal-aid application intake + Sec.12 eligibility scrutiny; panel-advocate assignment; Lok Adalat case bundling (National Lok Adalat disposes lakhs in a day); award/settlement-deed drafting; legal literacy; RTI.
- **Systems:** NALSA portals (`telangana.nalsa.gov.in`, `andhrapradesh.nalsa.gov.in`), LSAMS, e-Courts integration, UMANG.
- **Statute:** Legal Services Authorities Act 1987 (Sec.12, 19–22, 22B–22E); NALSA Regs 2010 (Reg.7 scrutiny).
- **AI-fit:** eligibility-triage agent; Lok Adalat bundling workflow (cheque-bounce/MACT/matrimonial/utility recovery) + auto-draft notices/settlement templates; award automation; multilingual legal-literacy/RTI copilot.
- **Score:** AI-fit 5 · Offline 4 · Prestige 4 · Feasibility 4 = **17**. **Easiest beachhead** — autonomous, mass mandate, manual workflows.

## 5. Legal Metrology — TS & AP — 12/20
- **Jobs:** license issuance/renewal; verification & stamping certs; inspection reports; compounding notices; complaint intake.
- **Systems:** `lm.telangana.gov.in`, AP district LM portals, national eMaap.
- **Statute:** Legal Metrology Act 2009 + Packaged Commodities Rules 2011.
- **Score:** AI-fit 4 · Offline 2 · Prestige 2 · Feasibility 4 = **12**. **Weakest offline case** (public/commercial data) — de-prioritise.

### GTM read
- **Best first sale:** Directorate of Prosecutions (executive dept, nascent digitisation, huge doc load, strongest air-gap case; Prajavani-analogue).
- **Easiest beachhead:** Legal Services Authorities (autonomous, manual, high visibility).
- **Highest prestige / hardest:** Courts (HC + District) — registry/clerical wedge only.
- **De-prioritise:** Legal Metrology.
