# VirtualAI for the CID — Economic Offences Wing & Anti-Human-Trafficking Unit (TS CID / AP CID)
### ఆర్థిక నేరాలు & మానవ అక్రమ రవాణా దర్యాప్తు కోసం VirtualAI — మీ గోడలు దాటని ఎంటర్‌ప్రైజ్ AI

**Cluster:** Police / Home / Law-Enforcement (Telangana CID & Andhra Pradesh CID)
**Wave-1 rank:** #5 of 8 (16/20) — AI-fit 4 · Offline 5 · Prestige 4 · Feasibility 3
**Matching VirtualAI build (nearest seed):** the seeded Police FIR / BNS / BNSS / CCTNS agent, re-pointed at multi-document economic-fraud bundling and AHTU rescue documentation.
**Exemplar to point at:** the Revenue **Prajavani** grievance copilot (on-prem; officer signs with DSC) — same four-stage pipeline, a heavier document per case.

> **అధికారే నిర్ణయిస్తారు. ఎల్లప్పుడూ. / The officer decides. Always.**
> VirtualAI reads seized records, links entities and drafts the report. It never attaches a property, never files a charge-sheet, never confirms a victim–trafficker link, never identifies a victim, never signs. Every output carries a **confidence score**, a **source citation**, a **one-click override**, and an **immutable audit entry**.

---

## 1. Positioning — గోడలు దాటని AI ("AI that never leaves your walls")

The CID holds two of the most sensitive data classes a state possesses: **trafficking-victim identities** (rescued women and children, their statements, their locations) and **financial-crime intelligence** (seized bank statements, depositor lists, the fund-trails of live economic-fraud investigations). Neither can sit behind a cloud AI API — and Telangana already learned why. Between **29 May and 7 June 2024**, apps run by the Telangana Police suffered **three data breaches** in ten days — the **TSCOP** facial-recognition app and the **Hawk Eye** citizen app among them; leaked records were offered for sale for as little as **USD 150**, the root cause being a vendor that had **hard-coded API passwords in plaintext over HTTP** ([The Cyber Express](https://thecyberexpress.com/tscop-app-cyberattack-telangana-police/); [The South First](https://thesouthfirst.com/telangana/telangana-police-take-down-tscop-after-breach-but-questions-galore-on-data-cops-keep/)).

VirtualAI is built for exactly this constraint:

- **On-premise, air-gapped** — runs inside the State Data Centre / NIC facility or the CID's own server room. Case files, seized statements and victim records never leave government infrastructure.
- **Private open-weights LLM via Ollama** — no OpenAI, no Gemini, no cloud inference. **Fully-offline operation is possible precisely because the model is local**; every token of a seized bank statement is reasoned over on the department's own hardware.
- **Decision-support only** — the investigating officer stays the decision-maker at every step (see §8).

*Honesty note:* "Fully offline" is a property of the **local model**. If the CID ever chose a hosted model, that guarantee would not hold. VirtualAI's design assumption is the local open-weights model, and everything below is scoped to that. There is **no Telugu handwritten OCR, no image generation, and no cloud fallback**.

**The mapping the client already knows** (from the Revenue Prajavani copilot): **AI Agent = the subject clerk / dealing assistant** on the file; **Workflow = the file's noting path** from seizure to charge-sheet; **Automation = the typing & compiling** of the fund-trail report and the attachment proposal. This is structurally the **same machine** — pointed at a smaller number of far larger files.

---

## 2. The core recurring process — ప్రధాన ప్రక్రియ

The CID's specialised wings — **Economic Offences, General Offences, Child & Women Protection, Protection of Civil Rights and Cyber Crimes** ([Telangana CID](https://cid.tspolice.gov.in/)) — run two document-heavy loops that dominate officer time:

**Economic-fraud investigation (EOW):**
> A deposit / chit-fund / Ponzi / land-fraud complaint is received → the establishment's records are **seized** (ledgers, agent registers, bank statements, deposit receipts, app/CRM exports) → an officer reads them into a picture of **who deposited how much, collected by whom, routed where** → the **fund-trail** is reconstructed across dozens of accounts and shell entities → **property is attached** under the Depositors Act to protect victims → a charge-sheet is assembled under the BNS + the deposit/chit statutes.

The EOW's own remit spans "financial frauds and misappropriation, counterfeit currency, frauds by non-banking finance companies, banking frauds, multi-level-marketing cases, vanishing companies, and money-circulation schemes" ([Telangana CID EOW](https://cid.tspolice.gov.in/cid/ecooffenses/Economic-Offenses)).

**Anti-Human-Trafficking (AHTU):**
> A rescue / source-complaint comes in → victims are **rescued and documented** (age-determination, victim statements, medical records) → victims, accused traffickers, brokers and locations are **linked across operations** → an **inter-state coordination memo** goes to the source/destination district → a charge-sheet is filed under BNS §143 + the Immoral Traffic (Prevention) Act.

Telangana runs functional AHTUs in **all 31 police districts / commissionerates** ([Telangana Today](https://telanganatoday.com/telangana-cracks-whip-on-human-trafficking)). The AP CID runs the identical wing structure on the same national CCTNS/ICJS stack — so everything below is replicable in AP with no redesign.

---

## 3. The Problem — సమస్య (real, cited — framed as pattern-recognition failures)

These are not "work harder" problems. They are **document-comprehension and cross-document-linking problems** being solved by hand, one seized carton at a time.

- **The mega-case scale is inhuman to read by hand.** The **Falcon Invoice Discounting** scam — worked by the Telangana CID — collected about **Rs 4,215 crore from 7,056 depositors** through a fake invoice-discounting app floating deals in the names of reputed MNCs; **4,065 victims** were cheated of **Rs 792 crore** alone; three cases were registered under **BNS §§316(2)/318(4)/61(2) and §5 of the Telangana Protection of Depositors Act 1999** at the EOW PS Cyberabad and transferred to CID, with **11 accused (including a chartered accountant) arrested** and **8+ more cases across India** ([The News Minute](https://www.thenewsminute.com/telangana/telangana-cid-arrests-falcon-coo-in-rs-4215-crore-scam); [The South First](https://thesouthfirst.com/telangana/telangana-cid-arrest-two-more-in-the-rs-4215-crore-falcon-invoice-discounting-scam/)). Reconstructing that trail means reading **thousands of transaction lines and depositor records** by hand.
- **The old mega-cases never end.** **AgriGold** collected **over Rs 7,000 crore from ~32 lakh depositors** across six states before collapsing in 2014; the AP CID attached its real estate under the **AP Protection of Depositors Act 1999**, and the ED has since **restituted Rs 3,950 crore** of assets to victims (Special PMLA Court, 2025) — a decade-long fund-trail and asset-mapping exercise still running ([The420](https://the420.in/ed-restitutes-rs-3950-crore-agri-gold-ponzi-victims-hyderabad-pmla/); [Lawful Legal](https://lawfullegal.in/agrigold-chit-fund-scam-in-south-indiaa-massive-scam-that-duped-millions/)).
- **Economic-offence cases are cheating-and-forgery at scale.** NCRB *Crime in India 2022* recorded **1,70,901 forgery/cheating/fraud (FCF) cases** and **21,814 criminal-breach-of-trust cases**, with cheating and forgery ~93% of the economic-offence total — high registration, chronically **low conviction and high pendency** ([Drishti IAS on NCRB 2022](https://www.drishtiias.com/daily-updates/daily-news-analysis/ncrbs-crime-in-india-2022-report)).
- **Trafficking cases are lost at conviction — a linkage/evidence failure.** Telangana registered the **highest number of human-trafficking cases in India in 2024 (423 cases; 812 persons rescued)** ([Telangana Today, NCRB 2024](https://telanganatoday.com/ncrb-data-shows-telangana-tops-in-human-trafficking-cases-conviction-rate-remains-low)). Yet in 2023, of **336 cases and 607 victims, 1,058 were arrested and 873 chargesheeted — but only 9 convicted, a 3.7% conviction rate** ([Deccan Chronicle](https://www.deccanchronicle.com/southern-states/telangana/telangana-ranks-third-in-human-trafficking-1907275)). Cases collapse because victim statements, medical records and cross-operation links are not stitched into a coherent, cited narrative in time.

Each of these is a **pattern-recognition and synthesis failure** — precisely what a tireless, fully-cited assistant is suited to catch, so the officer can spend scarce hours **deciding**, not **collating**.

---

## 4. Where the time goes — సమయం ఎక్కడ పోతుంది (current journey, bottlenecks marked)

| # | Step today | Who | Bottleneck |
|---|-----------|-----|-----------|
| 1 | Seized records read into a picture — ledgers, agent registers, **bank statements, deposit receipts, app/CRM exports**, victim statements | IO / dealing staff | ⛔ **Manual reading of thousands of pages/lines**; the single biggest time sink |
| 2 | Depositors / victims de-duplicated across many complaints and branches | IO | ⛔ **Same person appears under name/spelling variants** across files — merged by hand or missed |
| 3 | Accused firms, directors, agents checked for antecedents & regulated-entity status | IO | ⛔ **Serial lookups** across CCTNS, prior FIRs, MCA, RBI lists |
| 4 | **Fund-trail reconstructed** — deposits → collection accounts → shell entities → property | IO | ⛔ **Semantic layering across accounts where keys don't match**; error-prone, doesn't scale to 7,056 depositors |
| 5 | Property-attachment proposal drafted under the Depositors Act | IO / Legal | ⛔ **Repetitive schedule-building** linking each asset to seized-money proof |
| 6 | Inter-state / inter-agency coordination memo drafted (source & destination districts, ED/FIU) | IO | ⛔ **Manual memo assembly**, one counterpart at a time |
| 7 | **Investigation report / charge-sheet** synthesised from all of the above under the correct statutes | IO | ⛔ **Weeks of clerical assembly**; sections/annexure gaps → case collapses at trial |

Steps 1–2 (read & de-dup), 3 (antecedents), 4–5 (fund-trail & attachment) and 6–7 (memo & report) are the four clerical stages VirtualAI compresses.

---

## 5. The Solution — పరిష్కారం: four named agents (EXTRACT → CHECK HISTORY → VERIFY → ROUTE & DRAFT)

Each agent produces a **confidence score** and a **source citation** on every output — nothing is asserted without pointing to the exact seized-document page/line, record ID or statute section it came from.

**① Seized-Document & Statement Extractor** — _సంగ్రహకర్త_ · **EXTRACT**
Reads the **machine-readable** seized record — bank/PG statement PDFs and Excel exports, typed/printed deposit ledgers and agent registers, app/CRM data dumps, e-filed complaint narratives, WhatsApp text exports, and typed victim/witness statements — and emits a **structured case skeleton**: depositors/victims, agents, amounts, dates, account numbers, IFSC, scheme names, branches. For AHTU: victims, ages, accused, brokers, source/destination locations, dates.
→ _Output: structured records, per-field confidence, each field cited back to the source page/line._ **Scope guardrail:** typed/printed and digital records only — **handwritten seized ledgers must be digitised/transcribed by staff first; there is no Telugu handwritten OCR.**

**② Antecedents & Registry Check** — _పూర్వ చరిత్ర & నమోదు తనిఖీ_ · **CHECK HISTORY**
Checks accused persons, firms, directors and agents against **CCTNS antecedents, prior FIRs/charge-sheets across districts and states, MCA/vanishing-company status and RBI regulated-entity lists**; and semantically **de-duplicates depositor/victim complaints** that describe the same person or the same scheme under different spellings.
→ _Output: an antecedents/duplication report, confidence, cited to each matched record ID._

**③ Fund-Trail & Entity Linker** — _నిధి-మార్గం & అనుసంధానం_ · **VERIFY RECORDS**
The linkage brain. Performs the **semantic linking across many documents where exact keys don't match** — connecting victims ↔ deposit receipts ↔ collection/mule accounts ↔ agents ↔ shell entities ↔ attached property, and reconstructing the **layering chain** across bank statements. For AHTU: links victims ↔ rescue operations ↔ accused ↔ locations across separate case files to expose a **network, not isolated rescues**.
→ _Output: a fund-trail / linkage graph, confidence per edge, cited to each source document. **AI proposes the link; the officer confirms it.**_

**④ Investigation-Report & Charge-Sheet Draftsman** — _దర్యాప్తు నివేదిక & అభియోగ పత్రం_ · **ROUTE & DRAFT**
**Synthesises** the multi-document fund-trail into the long-form work products that eat weeks:
- the **property-attachment proposal** under the **Telangana / AP Protection of Depositors Act 1999 (Sec 3)**, with a victim-restitution schedule;
- the **inter-state / ED–FIU coordination memo**;
- the **charge-sheet** under **BNS §318 (cheating), §316 (criminal breach of trust), §111 (organised crime), §61 (conspiracy)** with the **Banning of Unregulated Deposit Schemes Act 2019**, the **Prize Chits & Money Circulation Schemes (Banning) Act 1978** and the **Chit Funds Act 1982** — or, for AHTU, **BNS §143/§144 (trafficking / exploitation of a trafficked person)** with the **Immoral Traffic (Prevention) Act 1956** and **POCSO 2012**.
→ _Every draft carries confidence + citation. The officer reviews, edits, and signs with DSC. AI never attaches property or files the charge-sheet on its own._

> The four together are the **CID Case-Bundling Workflow**: EXTRACT the seized record → CHECK history & de-dup → VERIFY the fund-trail/network → ROUTE & DRAFT for the officer's signature.

### Honest note — where this is genuine LLM value vs a deterministic lookup

This department was chosen because its **genuine-AI density is high** — but we are explicit about which is which:

- **Genuine LLM, hard to do any other way:** ① **reading unstructured seized bank statements, typed ledgers, complaint narratives and WhatsApp exports into structured transactions and entities**; ③ **semantic linking of victims / mule-accounts / agents / shell entities across hundreds of documents where names and keys never match exactly**; ④ **synthesising a coherent, cited fund-trail into the long investigation report / charge-sheet**. Reasoning over messy natural-language and tabular evidence at volume is exactly what the model is for.
- **Deterministic lookup, and we say so:** ② the **antecedent / regulated-entity checks against CCTNS, MCA and RBI lists** are ordinary structured queries. The LLM adds only **fuzzy name-matching** on top; it is not doing anything magical there, and we do not price it as if it were.

### Feasibility caveat — read this honestly

CID cases are **heterogeneous and far lower-volume** than a citizen counter service (Prajavani or 1930 handle thousands of near-identical transactions a day; the EOW/AHTU runs a **smaller number of very large, document-heavy investigations**). So the ROI here is **not throughput — it is per-case leverage**: compressing the months of manual fund-trail reconstruction and report assembly on a single mega-case (Falcon = 7,056 depositors; AgriGold = 32 lakh) into weeks. That is why this ranks #5 on feasibility (3/5) but remains a compelling second-wave vertical: **the leverage per case is very high.**

---

## 6. Department data sources (read-only) — శాఖ డేటా వనరులు

VirtualAI **reads**; it does not write to any system of record. Real systems, named precisely:

| System | Owner / rail | Used by |
|--------|--------------|---------|
| **CCTNS + EeCOPS** — FIR, case diary, charge-sheet modules | SCRB / NCRB / NIC | ① ② ④ |
| **ICJS** pillars — e-Courts, e-Prosecution, **e-Forensics (FSL)** | NCRB / NIC | ② ④ |
| **CID / EOW case registries** + seized-evidence store (bank-statement PDFs/Excel, digitised ledgers, app/CRM exports) | TS/AP CID | ① ③ |
| **AHTU rescue documentation** — victim statements, age-determination, medical records | CID Child & Women Protection / **Women Safety Wing** | ① ③ |
| **MCA21** (company/director), **RBI regulated-entity lists** (fuzzy check only) | MCA / RBI | ② |
| **PMLA / ED–FIU** attachment & restitution records (read-only coordination) | ED / FIU-IND | ③ ④ |

**Integration counterparts:** the **State Crime Records Bureau (SCRB)** as CCTNS state nodal, with **NIC / NCRB** for ICJS connectivity and any read-API clearance; the **Women Safety Wing / Dept. of Women & Child Welfare** for AHTU records.

**Pattern — nightly extract, then read-only APIs.** Begin with a **nightly read-only extract** of the slow-moving corpus (case registries, CCTNS antecedents, seized-document store) into the air-gapped VirtualAI box — lowest integration risk, zero change to live systems. Graduate to **read-only APIs** where NIC/CCTNS permits. **VirtualAI never writes to CCTNS.**

---

## 7. Sovereign by design — సార్వభౌమ నిర్మాణం

- **Hosting:** inside the **Telangana State Data Centre / NIC Hyderabad** (BRKR Bhavan; **ISO 27001:2022** certified) or the CID's own server room — on-prem, air-gapped ([NIC Telangana Data Centres](https://tg.nic.in/en/service/data-centres/)).
- **Model:** on-prem **open-weights LLM via Ollama** — no cloud AI API; inference on department hardware.
- **Workflow engine:** VirtualAI Workflows orchestrate EXTRACT→CHECK→VERIFY→ROUTE&DRAFT with **officer sign-off gates**.
- **Audit log:** every extract, link proposal, confidence score, citation, officer edit, override and sign-off is written to an **immutable audit trail** — court-defensible provenance for every drafted line and every proposed fund-trail edge.

**Why air-gapped is non-negotiable here — the anchor:** in ten days in mid-2024 Telangana Police suffered three app data breaches with data sold for as little as USD 150, root-caused to plaintext API passwords over HTTP ([The Cyber Express](https://thecyberexpress.com/tscop-app-cyberattack-telangana-police/)). An AI that holds **trafficking-victim identities and live financial-crime intelligence** must live **inside the wire**. Telangana was also the **first state to live-integrate CCTNS (EeCOPS) with ICJS** ([SKOCH](https://exhibition.skoch.in/beacon-of-hope/police-computer-services-and-standardization/)) — the read-only rails already exist inside government.

---

## 8. Accountability — జవాబుదారీతనం: "The officer decides. Always." (అధికారే నిర్ణయిస్తారు. ఎల్లప్పుడూ.)

- **AI never decides, attaches, links, closes or signs.** It does **not** attach property, does **not** file a charge-sheet, does **not** confirm a fund-trail edge, does **not** identify a victim, does **not** send a coordination memo.
- **Every output carries four things:** a **confidence score** (_విశ్వాస స్కోరు_), a **source citation** (_మూలాధార ఉల్లేఖనం_), a **one-click officer override**, and an **audit-log entry**.
- **Human-in-the-loop is mandatory.** A low-confidence extraction, an ambiguous entity link, or a missing statutory element **pauses the workflow** for officer input before it can advance. Victim-identity handling is confirmed by the officer, never asserted by the model.
- **The officer signs.** As with Telangana's move to **digitally-signed records under the new criminal laws**, the final attachment proposal and charge-sheet are reviewed, edited and **signed by the IO with a Digital Signature Certificate**. VirtualAI produces the first draft; the officer produces the decision.

This is decision-**support**. The CID's authority, discretion and legal responsibility are untouched.

---

## 9. Projected impact — అంచనా ప్రభావం (honest & illustrative)

> **Illustrative directions of travel — not guarantees.** Each is **baselined in Week 1 of the pilot on the CID's own case**, and we **report against measured reality, not marketing claims.** Given the low-volume/high-leverage nature of CID work, the honest headline metric is **per-case time**, not case throughput.

- **Fund-trail reconstruction time** — from months of manual reading toward a weeks-scale, fully-cited draft trail on a mega-case.
- **Depositor/victim de-duplication** — more duplicate and variant-spelling complaints merged, fewer double-counts in the victim schedule.
- **Attachment-proposal & charge-sheet assembly** — from weeks of clerical synthesis toward a same-week reviewable first draft with a completeness checklist.
- **Trafficking-network linkage** — more cross-operation links surfaced (and cited) per case, supporting the evidence chain that today collapses at a **3.7% conviction rate**.
- **Officer review load** — reduced, and **100% cited** so verification is fast rather than a re-read from scratch.

Each is a **measurable metric with a Week-1 baseline and a Week-12 assisted-live comparison** on the pilot case.

---

## 10. The 12-week pilot — 12-వారాల పైలట్: Baseline → Shadow → Assisted-Live

**Scope:** one live economic-fraud mega-case bundle (a chit-fund / deposit-fraud case with seized bank statements and depositor records) **plus** one AHTU district's rescue caseload, with one CID nodal officer and one PP/legal reviewer.

| Phase | Weeks | What happens |
|---|---|---|
| **Baseline** (బేస్‌లైన్) | 1–3 | Stand up the air-gapped box; ingest a **nightly read-only extract** of the pilot case's seized-document store and CCTNS antecedents; **instrument the current process** — measure fund-trail reconstruction time, de-dup hit-rate, report-assembly time. No AI in the officers' loop yet. |
| **Shadow** (షాడో) | 4–8 | The four agents run **in parallel, out of the officers' way**. Compare AI extractions, links and drafts against officer output; **calibrate confidence scores**; tune to TS/AP CID SOPs, the deposit/chit statutes and BNS section set. **No AI output reaches a court.** |
| **Assisted-Live** (సహాయక ప్రత్యక్ష) | 9–12 | Officers use the AI draft as their **first draft** — review, edit, and **sign with DSC**. Attachment proposals, coordination memos and charge-sheet skeletons go live **under human sign-off only**. Measure deltas vs the Week-1 baseline. **Officer always decides.** |

**What we need from the CID:** a nominated **nodal sponsor (SP/DSP-rank)**; **read-only data-extract clearance** brokered via **SCRB / NIC** to a scoped case set; on-prem space on the **State Data Centre**; the department's current **charge-sheet and attachment-proposal SOPs** for tuning; and sign-off on the audit/HITL policy. **What we do not need:** any data to leave the building.

---

## 11. Bilingual by default — ద్విభాషా లేబుళ్లు (Telugu / English glossary)

| English | తెలుగు (Telugu) |
|---------|------|
| The officer decides. Always. | అధికారే నిర్ణయిస్తారు. ఎల్లప్పుడూ. |
| Data never leaves your walls | డేటా మీ గోడలు దాటదు |
| Economic offence | ఆర్థిక నేరం |
| Depositor / Victim | డిపాజిటర్ / బాధితుడు |
| Chit fund / Deposit scheme | చిట్ ఫండ్ / డిపాజిట్ పథకం |
| Fund-trail | నిధి-మార్గం |
| Attachment of property | ఆస్తి జప్తు |
| Human trafficking | మానవ అక్రమ రవాణా |
| Rescue | రక్షణ / విముక్తి |
| Charge-sheet | అభియోగ పత్రం |
| Confidence score | విశ్వాస స్కోరు |
| Source citation | మూలాధార ఉల్లేఖనం |

_Section titles above carry Telugu subheads; the officer-facing UI ships bilingual labels for every action button and every confidence/citation badge. Telugu support is for UI, drafting and display over already-typed digital records, using the local open-weights model — **no handwritten OCR, no image generation, no cloud fallback.**_

---

## Sources (public)

1. Telangana CID — home & wing structure (Economic Offences, General Offences, Child & Women Protection, Protection of Civil Rights, Cyber Crimes): https://cid.tspolice.gov.in/
2. Telangana CID — Economic Offences Wing remit (financial frauds, NBFC/banking fraud, MLM, vanishing companies, money-circulation schemes): https://cid.tspolice.gov.in/cid/ecooffenses/Economic-Offenses
3. Falcon Invoice Discounting scam — Rs 4,215 cr from 7,056 depositors; CID arrests; BNS + TS Depositors Act (The News Minute): https://www.thenewsminute.com/telangana/telangana-cid-arrests-falcon-coo-in-rs-4215-crore-scam
4. Falcon scam — 4,065 victims / Rs 792 cr; BNS §§316(2)/318(4)/61(2) + §5 TS Depositors Act; EOW Cyberabad → CID; 8+ cases (The South First): https://thesouthfirst.com/telangana/telangana-cid-arrest-two-more-in-the-rs-4215-crore-falcon-invoice-discounting-scam/
5. Rs 70 cr chit-fund scam — TS CID; IPC + TS Depositors Act + Chit Funds Act + RBI Act (Hans India): https://www.thehansindia.com/telangana/telangana-cid-cracks-70-crore-chit-fund-scam-four-arrested-950810
6. AgriGold — ED restitutes Rs 3,950 cr to victims; AP CID attachment under AP Depositors Act; PMLA (The420): https://the420.in/ed-restitutes-rs-3950-crore-agri-gold-ponzi-victims-hyderabad-pmla/
7. AgriGold — Rs 7,000 cr from ~32 lakh depositors across six states (Lawful Legal): https://lawfullegal.in/agrigold-chit-fund-scam-in-south-indiaa-massive-scam-that-duped-millions/
8. NCRB *Crime in India 2022* — economic offences: 1,70,901 FCF, 21,814 CBT; cheating/forgery ~93% (Drishti IAS): https://www.drishtiias.com/daily-updates/daily-news-analysis/ncrbs-crime-in-india-2022-report
9. NCRB 2024 — Telangana highest human-trafficking cases (423; 812 rescued); 2023 conviction 3.7% (Telangana Today): https://telanganatoday.com/ncrb-data-shows-telangana-tops-in-human-trafficking-cases-conviction-rate-remains-low
10. Human trafficking 2023 — TS 336 cases / 607 victims / 1,058 arrested / 873 chargesheeted / 9 convicted (Deccan Chronicle): https://www.deccanchronicle.com/southern-states/telangana/telangana-ranks-third-in-human-trafficking-1907275
11. AHTUs in all 31 TS districts/commissionerates; enforcement drive (Telangana Today): https://telanganatoday.com/telangana-cracks-whip-on-human-trafficking
12. Telangana CID — Women Protection Cell / Child & Women Protection wing (missing/abandoned children, ITPA): https://cid.tspolice.gov.in/cid/womenandchild/Women-Protection-Cell
13. Banning of Unregulated Deposit Schemes Act, 2019 (official; 3–10 yrs imprisonment, fine up to 2× collected) — India Code: https://www.indiacode.nic.in/handle/123456789/11641
14. Andhra Pradesh Protection of Depositors of Financial Establishments Act, 1999 (official; adopted by Telangana) — India Code: https://www.indiacode.nic.in/handle/123456789/16102?locale=en
15. Prize Chits and Money Circulation Schemes (Banning) Act, 1978 (official) — India Code: https://www.indiacode.nic.in/handle/123456789/1628?view_type=browse
16. BNS §143 — Trafficking of person (RI 7–10 yrs); §144 exploitation of a trafficked person: https://devgan.in/bns/section/143/
17. MHA — Anti-Human-Trafficking Units scheme (comprehensive AHTU framework): https://www.mha.gov.in/sites/default/files/Scheme-AHTU-SS-271011.pdf
18. TSCOP / Hawk Eye breach — three breaches in ten days (May–Jun 2024); data sold for USD 150; plaintext API passwords over HTTP (The Cyber Express; The South First): https://thecyberexpress.com/tscop-app-cyberattack-telangana-police/ ; https://thesouthfirst.com/telangana/telangana-police-take-down-tscop-after-breach-but-questions-galore-on-data-cops-keep/
19. Telangana first to integrate CCTNS (EeCOPS) with ICJS (SKOCH): https://exhibition.skoch.in/beacon-of-hope/police-computer-services-and-standardization/
20. Telangana State Data Centre / NIC (ISO 27001:2022; on-prem hosting): https://tg.nic.in/en/service/data-centres/

_Statutes named: Bharatiya Nyaya Sanhita 2023 (§318 cheating, §316 criminal breach of trust, §111 organised crime, §61 conspiracy, §143/§144 trafficking); Bharatiya Nagarik Suraksha Sanhita 2023; Banning of Unregulated Deposit Schemes Act 2019; Telangana / AP Protection of Depositors of Financial Establishments Act 1999; Prize Chits and Money Circulation Schemes (Banning) Act 1978; Chit Funds Act 1982; Prevention of Money-Laundering Act 2002; Immoral Traffic (Prevention) Act 1956; POCSO 2012. AP parallel: AP CID runs the identical wing structure on the same CCTNS/ICJS stack — replicable without redesign._
