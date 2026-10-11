# VirtualAI for Cybercrime — Telangana Cyber Security Bureau (TGCSB) & AP Cybercrime Wing
### సైబర్ నేర దర్యాప్తు కోసం VirtualAI — మీ గోడలు దాటని ఎంటర్‌ప్రైజ్ AI
_Police / Home cluster · Wave-1 top-ranked beachhead (20/20). Decision-**support** only: EXTRACT → CHECK HISTORY → VERIFY RECORDS → ROUTE & DRAFT. Every output carries a **confidence score + source citation**. The officer always decides, signs with DSC, and can override in one click._

> **A note on the numbers below.** The Wave-1 seed carried "~Rs 850 cr refunds." On verification that figure is **wrong by an order of magnitude** — the underlying report is **Rs 85.05 crore** of court-ordered refunds (6,449 cases), the decimal lost in a headline slug. The correct, current, well-sourced figures are used throughout: **Rs 350 cr+ cumulative refunds facilitated** (Dec 2025) and **Rs 445.41 cr returned to 59,953 victims via Lok Adalats** (2026). We pitch measured reality, never inflated claims.

---

## 1. Positioning — గోడలు దాటని AI ("AI that never leaves your walls")

**Enterprise AI that never leaves your walls.** VirtualAI runs entirely inside the State Data Centre on a private, open-weights LLM (Ollama) — **air-gapped, sovereign, on-premise**. No victim PII, no bank/financial data, no live investigation intel is ever sent to a cloud AI service. It reads your own systems (NCRP, 1930/CFCFRMS, CCTNS/ICJS, the Suspect Registry) and drafts the clerical work an Investigating Officer does by hand today.

_Honest qualifier:_ the platform is **fully offline for all AI reasoning** — the model and every byte of case data sit on-prem. The only network calls it makes are to the **same government/bank rails the officer already uses** (the NCRP/CFCFRMS freeze API, the bank/PG endpoints) over the secure State network — never to an external or cloud AI API. "Fully offline" is delivered by the **local open-weights model**; take that away and you have a normal networked app. That distinction is the whole product.

**The mapping the client already knows** (from the Revenue "Prajavani" copilot):
- **AI Agent = the subject clerk** — a cyber-fraud copilot grounded in the Bureau's *own* records.
- **Workflow = the file's noting path** — the golden-hour → linkage → verification → charge-sheet journey.
- **Automation = the typing & compiling** — freeze requests, refund petitions, charge-sheets drafted for signature.

This is structurally **identical** to the proven Prajavani pipeline (Field Extractor → History/Duplicate Checker → Dharani Verifier → Router/Endorsement Drafter). We are re-pointing a working machine at cybercrime.

---

## 2. The core recurring process — ప్రధాన ప్రక్రియ

Every working day the Bureau runs the same loop, thousands of times:

> **A citizen loses money online → reports on 1930 / NCRP (cybercrime.gov.in) → a freeze request must reach the beneficiary bank inside the "golden hour" → the complaint is triaged, de-duplicated and assigned → the mule-account / transaction chain is traced across many complaints → the accused is verified against watchlists → funds are refunded via the Money Restoration Module → a charge-sheet is assembled under the IT Act + BNS.**

TGCSB is purpose-built for exactly this: it is **India's first Cyber Security Bureau** and the **first state to run a fully-functional 24×7 "1930" call centre** (established 31 May 2023; Director Shikha Goel, IPS). It operates seven cybercrime police stations, a dedicated Operations Wing for interstate cases, CyCaps/ICACCOPS tooling, and a Child Protection Unit. The AP Cybercrime Wing runs the **same national stack** (NCRP, 1930, I4C, CCTNS/ICJS) — so everything below is replicable in AP with no redesign.

---

## 3. The Problem — సమస్య (real, cited — framed as pattern-recognition failures)

Cyber-fraud is a **pattern-recognition problem at machine scale being fought at human speed.** The evidence:

- **National scale.** In 2024, citizens filed **22.68 lakh** cybercrime incidents on NCRP (**+42%** YoY) and lost **Rs 22,845.73 crore** — up from Rs 7,465 cr (2023) and Rs 2,290 cr (2022). [MHA/Parliament reply, via Prokerala]
- **Telangana is the epicentre.** NCRB *Crime in India 2024* records **Telangana with the highest cybercrime rate in the country — over 70 cases per lakh population**, ahead of Karnataka and Maharashtra. TGCSB's own 2024 Annual Report: **1,14,174 complaints (+18%)**, losses up **140%** to **Rs 1,866.90 crore**, **24,643 FIRs**. Hyderabad is worst-hit; salaried private employees are the most-targeted victims. ["Digital arrest" fraud spiked exponentially.]
- **The recognition failure #1 — the golden hour is missed.** If a freeze request reaches the bank within minutes, success is **>60%**; wait two hours and the money is layered onward, cashed out, or converted to crypto. Every minute an officer spends *re-typing* account numbers off a complaint is a minute the money is moving.
- **The recognition failure #2 — rings look like isolated complaints.** The same mule account, UPI handle, phone or device recurs across dozens of complaints, but each lands as a separate file. As of Jan 2026 the I4C **Suspect Registry** had flagged **27.37 lakh Layer-1 mule accounts** and helped prevent **Rs 9,518 cr** — the connective tissue exists nationally, but locally the links are found by hand, if at all.
- **The recognition failure #3 — cases collapse at charge-sheet.** Nationally the cybercrime **chargesheeting rate is ~18%**, and of 1.67 lakh cases (2020-22) only **1.6% ended in conviction** (0–2% across states). Telangana's chargesheeting rate (~20.9%) leads most states but still means **~4 in 5 cases never reach a complete charge-sheet.** The bottleneck is clerical assembly — sections, seizure memos, 65B certificates, bank trails — not investigative will.

**None of this is a "work harder" problem. It is a "surface the pattern, draft the paperwork, free the officer to decide" problem** — exactly what decision-support AI is for.

---

## 4. Where the time goes — సమయం ఎక్కడ పోతుంది (current journey, bottlenecks marked)

| # | Step today | Who | Bottleneck |
|---|-----------|-----|-----------|
| 1 | Victim calls 1930 / files on NCRP; free-text complaint captured | Call-taker | Details buried in prose; UPI/account/IFSC must be hand-picked out ⛔ **golden-hour clock already running** |
| 2 | Officer drafts & sends the bank/PG freeze ("Put-on-Hold") request | IO / 1930 desk | ⛔ **Manual re-typing** of account/wallet IDs — minutes lost while funds move |
| 3 | Complaint triaged, de-duplicated, assigned to a cybercrime PS/IO | Supervisor | ⛔ **Duplicates & rings missed** — same mule seen as many unrelated files |
| 4 | IO reconstructs the money trail across complaints & bank statements | IO | ⛔ **Manual layering analysis** — slow, error-prone, doesn't scale to 1.1 lakh/yr |
| 5 | Accused accounts/numbers/IMEIs checked vs registries & antecedents | IO | ⛔ **Serial lookups** across NCRP, Suspect Registry, CEIR, CCTNS |
| 6 | Interstate arrest → accused brought back on **transit (PT) warrant** | Ops Wing | Coordination & warrant paperwork across states |
| 7 | Refund petition drafted for court / **Money Restoration Module** | IO / Legal | ⛔ **Repetitive petition drafting**, one case at a time |
| 8 | Charge-sheet assembled under IT Act + BNS with all annexures | IO | ⛔ **Days of clerical assembly**; sections/65B/seizure gaps → case collapses |

Steps 1-2 (golden hour), 3-4 (linkage), 5 (verification) and 7-8 (drafting) are precisely the four clerical stages VirtualAI compresses.

---

## 5. The Solution — పరిష్కారం: a 4-agent workflow (EXTRACT → CHECK HISTORY → VERIFY → ROUTE & DRAFT)

Four named agents, each output carrying **confidence + citation**, mirroring the Prajavani copilot one-for-one:

**① Field Extractor** — _సంగ్రహకర్త_ · **EXTRACT**
Parses each incoming 1930/NCRP complaint and pulls structured entities out of the free text: victim details, accused **UPI IDs, bank accounts, IFSC, wallet IDs, phone numbers, URLs, crypto addresses, transaction IDs, amounts, timestamps**. Emits a clean "complaint card" in seconds. → _Output: structured card, per-field confidence, cited to the NCRP complaint ID._

**② History & Duplicate Checker (Fraud-Ring Linker)** — _చరిత్ర & నకిలీ తనిఖీ_ · **CHECK HISTORY**
Matches those entities against the corpus of prior complaints/FIRs and **clusters everything that shares a mule account / UPI / phone / device / URL into one ring**; flags duplicates; reconstructs the **transaction-layering chain**. Turns 40 "isolated" complaints into one ring with one accused set. → _Output: linkage graph, confidence, cited to each matched complaint/FIR ID._

**③ Records Verifier (Suspect-Registry / CCTNS Verifier)** — _రికార్డుల ధృవీకరణ_ · **VERIFY RECORDS**
Cross-checks accused accounts/numbers/IMEIs against the **I4C Suspect Registry, CEIR, CCTNS antecedents, prior FIRs and the jurisdiction master**; confirms bank/PG details for the freeze and which cybercrime PS owns the case. → _Output: verified match report, confidence, cited to the registry record._

**④ Router & Drafter (Golden-Hour / Refund / Charge-sheet Draftsman)** — _రూటింగ్ & ముసాయిదా_ · **ROUTE & DRAFT**
From verified data, drafts the four documents that eat the IO's day:
- the **golden-hour bank/PG freeze / lien-marking request** (ready to approve in seconds),
- the **assignment note** to the correct PS/IO,
- the **MRM refund claim / court petition**,
- the **charge-sheet skeleton** citing **IT Act §66C (identity theft) / §66D (cheating by personation)** with **BNS §318 (cheating), §319 (cheating by personation), §111 (organised crime)** and a 65B/seizure-memo checklist.
→ _Every draft carries confidence + citation. The officer reviews, edits, signs (DSC). AI never sends the freeze or files the charge-sheet on its own._

---

## 6. Department data sources (read-only) — శాఖ డేటా వనరులు

VirtualAI **reads**, it does not write to systems of record. Real systems, named precisely:

| System | Owner / rail | Used by |
|--------|--------------|---------|
| **NCRP** — National Cyber Crime Reporting Portal (cybercrime.gov.in) | I4C / MHA | ① ② |
| **1930 helpline / CFCFRMS** — Citizen Financial Cyber Fraud Reporting & Mgmt System | I4C | ①, freeze rail (④) |
| **I4C platforms** — **Suspect Registry**, **Samanvay**, **Sahyog**, **GRM** | I4C | ② ③ |
| **Money Restoration Module (MRM)** + **e-Zero FIR** | NCRP / I4C | ④ |
| **CCTNS / ICJS** — Crime & Criminal Tracking; Inter-operable Criminal Justice System | NCRB / NIC | ③ ④ |
| **CEIR** — Central Equipment Identity Register (IMEI) | DoT | ③ |
| **TGCSB tooling** — CyCaps, ICACCOPS; district jurisdiction master | TGCSB | ② ③ |

**Integration counterpart:** the Bureau does not expose these to us directly — integration is brokered through **I4C** (NCRP/CFCFRMS/Suspect Registry/MRM), **NIC** (CCTNS/ICJS), and the state's **CGG (Centre for Good Governance)** e-gov team.

**Pattern — nightly extract, then live APIs.** A **nightly read-only extract** pulls the slow-moving corpus (prior complaints/FIRs, Suspect-Registry snapshot, CCTNS antecedents, jurisdiction masters) into the on-prem store for agents ② and ③. For the **time-critical golden hour**, agent ④ uses the **live NCRP/CFCFRMS freeze API and bank/PG endpoints** — the same rails the officer uses today. Nothing about the AI leaves the building; only the freeze instruction travels, exactly as it does now.

---

## 7. Sovereign by design — సార్వభౌమ నిర్మాణం

- **State Data Centre, air-gapped.** Runs on Telangana/AP's own infrastructure — no public cloud, no external AI API.
- **Private open-weights model (Ollama).** The LLM weights live on-prem; prompts and case data never traverse the internet.
- **Agent workflow engine on-prem.** The four-agent pipeline, the confidence scoring, the citation store — all inside the perimeter.
- **Full audit log.** Every extraction, match, draft, officer edit and override is logged immutably — who saw what, when, and on what source.

**Why air-gapped is non-negotiable here — the anchor:** In just ten days (**29 May–7 June 2024**) Telangana Police suffered **three data breaches** — the facial-recognition **TSCOP** app, the **HawkEye** citizen app, and the SMS-delivery service were all compromised by threat actor "**Adm1nFr1end**." Root cause: the vendor (WinC IT Services) had **hard-coded API passwords in plaintext over HTTP**. Leaked data included offender records, gun licences, and the names/photos/postings of officers from the **ACB, Intelligence, Greyhounds and Home Guards**. TSCOP was pulled offline. **This is the case study for why cyber-investigation AI — holding victim PII, bank data, informant identities and live intel — must be air-gapped, on-prem, and never wired to a cloud AI service.**

---

## 8. Accountability — జవాబుదారీతనం: "The officer decides. Always." (నిర్ణయం అధికారిదే. ఎల్లప్పుడూ.)

- AI **never** decides, freezes, refunds, closes, or signs. It **drafts and flags**.
- Every output shows a **confidence score** (_విశ్వాస స్కోరు_) and a **source citation** (_మూలాధార ఉల్లేఖనం_) — no unsourced assertion ever reaches an officer.
- **One-click override** on every suggestion; the officer's edit is the record.
- **HITL sign-off is mandatory** at each gate — freeze dispatch, assignment, refund petition, charge-sheet filing all require an officer's approval and DSC.
- **Everything is logged.** The audit trail is the accountability guarantee, not a dashboard afterthought.

This is decision-**support**. The Bureau's authority, discretion and legal responsibility are untouched.

---

## 9. Projected impact — అంచనా ప్రభావం (honest & illustrative)

> **Illustrative only — not a claim.** These are directional targets. Actuals are **baselined in weeks 1-2 of the pilot on the Bureau's own data, and we report against measured reality, not against this table.**

| Metric | Today (baseline set in pilot) | With VirtualAI (target to measure) |
|--------|------|------|
| Time to a ready-to-approve **golden-hour freeze** draft | manual minutes of re-typing | **seconds** → more complaints hit the bank inside the 60-min window |
| Share of 1930 complaints frozen **within** the golden hour | baseline TBD | measurable lift |
| Complaint triage, **de-dup & ring-linking** | hours; links often missed | **minutes**; rings auto-clustered with citations |
| **Charge-sheet** first-draft assembly (sections, 65B, seizure) | days | **hours**, with a completeness checklist |
| **Chargesheeting rate** (Telangana ~20.9% baseline) | as-is | measured improvement over pilot window |
| Officer review load per complaint | full manual read | reduced, **100% cited** for fast verification |

Grounding reality check: TGCSB already froze **Rs 244.56 cr**, refunded **Rs 176.71 cr to 17,411 victims in 2024**, and has facilitated **Rs 350 cr+ cumulative** refunds and **Rs 445.41 cr via Lok Adalats**. The pilot's job is to move each of these curves by shrinking the clerical time between "victim reports" and "officer acts."

---

## 10. The 12-week pilot — 12-వారాల పైలట్

- **Weeks 1-2 — Baseline (బేస్‌లైన్).** Instrument the current flow on real (consented, in-perimeter) cases: golden-hour dispatch time, de-dup hit-rate, charge-sheet assembly time, chargesheeting rate. **Measure before we touch anything.**
- **Weeks 3-8 — Shadow (షాడో).** All four agents run alongside officers, drafting silently. Officers compare AI drafts to their own; we tune extraction accuracy, linkage precision and citation quality. **No AI output reaches a bank or a court.**
- **Weeks 9-12 — Assisted live (సహాయక ప్రత్యక్ష).** Agents draft; **officers approve/override/sign**. Golden-hour freeze drafts, MRM petitions and charge-sheet skeletons go live *under human sign-off only*. Report measured deltas vs the week-1 baseline.

**What we need from the Bureau:** a nominated sponsor (SP/DSP-rank) and 3-5 IOs; read-only access brokered via **I4C / NIC / CGG** to a scoped case set; space on the **State Data Centre**; and sign-off on the audit/HITL policy. **What we do not need:** any data to leave the building.

---

## 11. Bilingual touches — ద్విభాషా లేబుళ్లు (Telugu / English glossary)

| English | తెలుగు (Telugu) |
|---------|------|
| Cyber crime | సైబర్ నేరం |
| The officer decides. Always. | నిర్ణయం అధికారిదే. ఎల్లప్పుడూ. |
| Data never leaves your walls | డేటా మీ గోడలు దాటదు |
| Golden hour | సువర్ణ ఘడియ (Golden Hour) |
| Complaint | ఫిర్యాదు |
| Victim | బాధితుడు |
| Refund | తిరిగి చెల్లింపు (Refund) |
| Confidence score | విశ్వాస స్కోరు |
| Source citation | మూలాధార ఉల్లేఖనం |
| Freeze request | నిలిపివేత అభ్యర్థన |

_Section titles above carry Telugu subheads; the officer-facing UI ships bilingual labels for every action button and every confidence/citation badge._

---

## Sources (public)
1. TGCSB — About Us (established 31 May 2023; India's first Cyber Security Bureau; first 24×7 1930 centre): https://tgcsb.tspolice.gov.in/about-us/
2. TGCSB Annual Report 2024 (1,14,174 complaints; Rs 1,866.90 cr loss; 24,643 FIRs; Rs 176.71 cr refunded; Rs 244.56 cr frozen): https://tgcsb.tspolice.gov.in/wp-content/uploads/2024/12/Annual-Report-2024-TGCSB.pdf
3. NCRB *Crime in India 2024* — Telangana highest cybercrime rate (>70/lakh); 1.01 lakh cases, +17% (via Drishti IAS): https://www.drishtiias.com/daily-updates/daily-news-analysis/ncrbs-crime-in-india-2024-report
4. India 2024 NCRP totals — 22.68 lakh incidents, Rs 22,845.73 cr lost (Centre/MHA reply): https://www.prokerala.com/news/articles/a1703249.html
5. CFCFRMS / 1930 — Rs 11,158 cr saved across 32.80 lakh complaints (to 30.06.2026), PIB/newsonair: https://www.newsonair.gov.in/over-rs-7000-crore-saved-through-citizen-financial-cyber-fraud-reporting-and-management-system/
6. Golden hour mechanics — >60% freeze success in first minutes; Mumbai 1930 saved ~Rs 202 cr (The420): https://the420.in/mumbai-1930-cyber-helpline-saves-202-crore-2025/
7. Mule accounts & layering explainer (Business Standard): https://www.business-standard.com/finance/news/what-are-mule-accounts-cybercrime-banking-layer-india-fraud-rbi-126062400855_1.html
8. I4C Suspect Registry — 27.37 lakh mule accounts, Rs 9,518 cr prevented (The420): https://the420.in/10-states-mule-account-hotspots-i4c/
9. Money Restoration Module + Rs 445.41 cr via Lok Adalats; e-Zero FIR (Siasat): https://www.siasat.com/telangana-leads-country-in-cybercrime-refund-modules-tgcsb-3513196/
10. Court-ordered refunds Rs 85.05 cr / 6,449 cases — the real figure behind the "8505" slug (Deccan Chronicle): https://www.deccanchronicle.com/southern-states/telangana/tgcsb-helps-cyberfraud-victims-get-back-rs-8505-crore-1814551
11. Rs 350 cr+ cumulative refunds; 2.44 lakh complaints; 58,244 FIRs (The Hawk): https://www.thehawk.in/news/india/telangana-cyber-security-bureau-facilitated-rs-350-crore-refund-to-victims
12. Interstate arrests brought back on **transit warrants** — Gujarat/Surat operation (Prokerala): https://www.prokerala.com/news/articles/a1634038.html
13. TSCOP / HawkEye breach — three breaches, 29 May–7 Jun 2024, "Adm1nFr1end" (The South First): https://thesouthfirst.com/telangana/telangana-police-take-down-tscop-after-breach-but-questions-galore-on-data-cops-keep/
14. Breach root cause — plaintext API passwords over HTTP (The News Minute): https://www.thenewsminute.com/telangana/how-inadequate-security-checks-led-to-massive-data-breach-in-telangana-police-app
15. Cybercrime conviction ~1.6% over two years (Tribune, on NCRB/Parliament data): https://www.tribuneindia.com/news/delhi/only-1-6-conviction-rate-in-2-yrs-amid-surge-in-cybercrime-cases

_Statutes named: Information Technology Act 2000 (§43, §66, §66C, §66D, §67); Bharatiya Nyaya Sanhita 2023 (§318, §319, §111); Bharatiya Nagarik Suraksha Sanhita 2023 (§173 e-FIR/Zero-FIR; transit warrants). AP parallel: AP Cybercrime Wing on the identical NCRP/1930/I4C/CCTNS-ICJS stack — replicable without redesign._
