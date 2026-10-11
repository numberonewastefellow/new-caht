# Department Briefing — State Police: Investigation, Station Records & Charge-Sheet Drafting under the New Criminal Codes

**Cluster:** Police / Home / Law-Enforcement (Telangana Police & Andhra Pradesh Police)
**Wave-1 rank:** #2 of 8 (19/20) — highest-prestige flagship prize
**Matching VirtualAI agent (seeded):** Police FIR / BNS / BNSS / CCTNS agent
**Exemplar to point at:** Prajavani grievance copilot (on-prem, officer signs with DSC) — same pipeline, different department.

> **అధికారే నిర్ణయిస్తారు. ఎల్లప్పుడూ. / The officer decides. Always.**
> VirtualAI drafts, links and flags. It never registers an FIR, never files a charge-sheet, never signs, never closes a case. Every output carries a confidence score, a source citation, a one-click override, and an immutable audit entry.

---

## 1. Positioning — Offline, Air-Gapped, Sovereign

FIRs, victim and witness identities, informant details, case diaries and live-investigation material are the **most sensitive class of state data there is**. They cannot sit behind a cloud AI API, and Telangana already knows why: between **29 May and 7 June 2024, apps run by the Telangana Police suffered three data breaches** — the **TSCOP** facial-recognition app leaked offender records, police gun licences, and officer names, designations, photographs and station affiliations, and the **Hawk Eye** app was breached the same week; the data was offered for sale for as little as **USD 150** before the hacker was arrested ([The Cyber Express](https://thecyberexpress.com/tscop-app-cyberattack-telangana-police/); [Internet Freedom Foundation](https://internetfreedom.in/three-telangana-police-data-breaches/)).

VirtualAI is built for exactly this constraint:

- **On-premise, air-gapped** — runs inside the State Data Centre / NIC facility or the SCRB server room. Case data never leaves government infrastructure.
- **Private open-weights LLM via Ollama** — no OpenAI, no Gemini, no cloud inference. **Fully-offline operation is possible precisely because the model is local**; the reasoning happens on the department's own hardware.
- **Decision-support only** — the officer stays the decision-maker at every step (see §8).

*Honesty note:* "Fully offline" is a property of the **local model**. If a department ever chose a hosted model, that offline guarantee would not hold. VirtualAI's design assumption is the local open-weights model, and everything below is scoped to that.

---

## 2. The Core Recurring Process — the file's noting path

Every station runs the same investigation lifecycle, thousands of times a year, now under the **new criminal codes** (BNS / BNSS / BSA 2023, in force **1 July 2024**):

1. **Intake** — FIR / e-FIR / Zero-FIR registered in CCTNS-EeCOPS under **BNSS Sec 173**.
2. **Investigation** — case diary (CD) entries, witness statements, panchanamas, seizure memos, arrest memos, medico-legal and **FSL/forensic** reports.
3. **Compliance under new law** — mandatory **audio-video recording of search & seizure (BNSS Sec 105)**; mandatory **forensic-expert visit for offences punishable by 7 years or more (BNSS Sec 176(3))**.
4. **Charge-sheet drafting** — the police report under **BNSS Sec 193**, assembled from the CD, statements, documents and forensics, with the **correct BNS/BNSS sections**.
5. **Scrutiny & filing** — Public Prosecutor scrutiny, then filing into court through the **ICJS** pillars.

Map to VirtualAI: **AI Agent = the subject clerk / diary writer; Workflow = the noting path from FIR to charge-sheet; Automation = the typing and compiling of the charge-sheet itself.**

---

## 3. The Problem — pattern-recognition failures, not effort failures

Investigating officers are not short on diligence; they are short on **bandwidth to catch every pattern** across dozens of simultaneous case files. The national numbers are a portrait of exactly that:

- **~29.2% of IPC cases remained pending investigation at year-end** (up from 28% the year before) — NCRB *Crime in India 2023* ([Drishti IAS summary](https://www.drishtiias.com/daily-updates/daily-news-analysis/crime-in-india-2023-report)). Roughly **1 in 4 to 1 in 3 cases never gets closed within the year.**
- **Charge-sheeting rate ~72.7%** — about **1 in 4 true cases never reaches a charge-sheet at all** (NCRB 2023, same source).
- **IPC conviction rate ~54%** — nearly half of *decided* cases fail, very often on **procedural and evidentiary gaps** a checklist would have caught.
- **Crimes against women: ~26.5% conviction, ~53% cases pending** — NCRB 2022 ([Drishti IAS](https://www.drishtiias.com/daily-updates/daily-news-analysis/ncrbs-crime-in-india-2022-report); [Tribune](https://www.tribuneindia.com/news/chandigarh/ncrb-report-2022-53-per-cent-cases-of-crime-against-women-left-pending-568799)).
- **2.88 crore criminal cases pending in district & subordinate courts** (of 5.19 crore total), ~20,580 judges, ~2,200 cases per judge ([NewsOnAir / NJDG](https://www.newsonair.gov.in/over-5-19-cr-cases-pending-in-indian-courts-govt-implements-fast-track-courts-to-address-backlog)). Every weak or late charge-sheet feeds this backlog.

Each of these is a **pattern-recognition failure** that a tireless assistant is well suited to catch:

- A **section mis-mapped** (the entire penal code was renumbered on 1 July 2024 — IPC had 511 sections, BNS has 358, and *no* section keeps its old number; e.g. IPC 302 → **BNS 103**, IPC 420 → **BNS 318**, IPC 376 → **BNS 65**) ([LawSikho IPC↔BNS table](https://lawsikho.com/blog/ipc-to-bns-conversion-table/)).
- A **60/90-day charge-sheet deadline missed** — under **BNSS Sec 187(2)** the accused then acquires an **absolute right to default bail** ([RestTheCase](https://restthecase.com/knowledge-bank/maximum-time-limit-to-file-charge-sheet-in-india); [Bar & Bench](https://www.barandbench.com/view-point/overview-criminal-investigations-and-trials-bnss-bns-bsa-part-ii)).
- A **repeat offender not linked** across FIRs / stations.
- A **mandatory forensic (Sec 176(3)) or audio-video (Sec 105) step skipped**, weakening the case at trial.

---

## 4. Where the Time Goes — current journey & bottlenecks

| Step | What the officer does today | Bottleneck |
|---|---|---|
| Section selection | Manually maps offence to the **new BNS/BNSS** sections, often from memory or a printed conversion sheet | Renumbered code (1 Jul 2024); straddle cases (offence before, charge-sheet after) are error-prone |
| Deadline tracking | Tracks the **60/90-day custody clock** manually across 30–50+ live cases | Missed clocks → **default bail** leakage |
| Antecedents / linkage | Recalls prior FIRs and repeat accused from memory or ad-hoc CCTNS look-ups | Cross-station patterns and repeat complainants slip through |
| Compliance | Remembers to trigger Sec 105 AV recording and Sec 176(3) forensic visit | Skipped steps discovered only at PP scrutiny or in court |
| Charge-sheet drafting | **Manually copy-compiles** the Sec 193 report from CD, statements, seizure lists, FSL — over days | Slow, inconsistent, the single biggest time sink |
| Missing persons / UIDB | Manual comparison against records | Matches against the national database rarely attempted at station level |

The charge-sheet itself — assembling and typing the BNSS Sec 193 report with correct sections, witness lists, document lists and property statements — is where **days disappear**.

---

## 5. The Solution — four named agents on EXTRACT → CHECK → VERIFY → ROUTE & DRAFT

Each agent produces a **confidence score** and a **source citation** on every output. Nothing is asserted without pointing to the exact CD page, statement, FSL report line, or statute section it came from.

### Agent 1 — **Case-File Extractor** (EXTRACT) · *కేసు-సార విశ్లేషణ*
Reads the already-digital record — FIR/e-FIR, case diary, witness statements, panchanamas, seizure & arrest memos, medico-legal and FSL reports in CCTNS-EeCOPS — and produces a **structured case skeleton**: accused, victims, witnesses, offence sections, incident/arrest dates, and the **custody clock start**.
*Cites:* every extracted field back to its source document/page. *Confidence:* per field, low-confidence fields flagged for officer entry. **Typed records only — no handwritten Telugu OCR.**

### Agent 2 — **Antecedents & Linkage** (CHECK HISTORY) · *పూర్వ చరిత్ర & అనుసంధానం*
Checks the accused/complainant against prior FIRs and charge-sheets across CCTNS; surfaces **repeat-complainant / repeat-accused** patterns and **modus-operandi links** — matched on **text/record attributes only** (name, address, phone, MO description, offence section), **never biometrics or facial recognition**.
*Cites:* the matching FIR numbers / record IDs. *Confidence:* ranked candidate list — **AI proposes the links, the officer confirms**.

### Agent 3 — **BNSS Compliance & Section-Mapping Verifier** (VERIFY RECORDS) · *BNSS నిబంధనల పరిశీలన*
The compliance brain. Maps **IPC → BNS/BNSS** sections; runs a **BNSS checklist** — Sec 105 audio-video of search/seizure done? Sec 176(3) forensic visit done for 7yr+ offences? — and runs the **Sec 193 deadline countdown**, raising a **default-bail risk alarm (Sec 187)** as the 60/90-day clock nears.
*Cites:* the exact BNS/BNSS section text and the missing-step rule. *Confidence:* mapping confidence per section; ambiguous mappings routed to the PP.

### Agent 4 — **Charge-Sheet Drafter & Router** (ROUTE & DRAFT) · *అభియోగ పత్రం రూపకల్పన*
Assembles the **BNSS Sec 193 charge-sheet** — cited sections, list of witnesses, list of documents, property/seizure statement, forensic annexures — plus **case-diary progress notes** and **station petition-enquiry reports**. Routes the draft to the **IO → SHO → SDPO/PP** for scrutiny and sign-off.
*Cites:* each paragraph back to CD/statement/FSL evidence. *Confidence:* whole-document readiness score; low scores or missing mandatory steps force a **human-in-the-loop pause** before the draft can advance.

> The four together are the **Charge-Sheet Workflow**: EXTRACT the file → CHECK the history → VERIFY compliance & deadlines → ROUTE & DRAFT for the officer's signature. It mirrors the seeded **police FIR/BNS/BNSS/CCTNS agent** and the proven Prajavani pattern.

---

## 6. Data Sources — read-only, real systems

**Read-only from live state systems (no write-back — the officer enters the final into CCTNS):**

- **CCTNS + EeCOPS** (Telangana's crime investigation & prosecution app) — FIR, case diary, charge-sheet modules.
- **ICJS** — Interoperable Criminal Justice System pillars: **e-Courts, e-Prisons, e-Forensics (FSL), e-Prosecution**. Telangana is the **first state to live-integrate CCTNS (EeCOPS) with ICJS** with electronic exchange between pillars ([SKOCH](https://exhibition.skoch.in/beacon-of-hope/police-computer-services-and-standardization/)).
- **CCTNS / EeCOPS** case & record search + **ICJS** links (e-Courts / e-Prisons / e-Forensics) — **read-only text/record lookup only; no facial recognition, biometric matching, or surveillance analytics**.
- **Andhra Pradesh:** [citizen.appolice.gov.in](https://citizen.appolice.gov.in/) citizen e-FIR / View-FIR services (on CCTNS) and **AP-112 ERSS** ([112.gov.in](https://112.gov.in/)).

**Integration counterpart:** the **State Crime Records Bureau (SCRB)** as CCTNS state nodal, with **NIC / NCRB** for ICJS connectivity and any read API clearance.

**Nightly-extract-then-APIs approach:** begin with **nightly read-only extracts** from the CCTNS/EeCOPS database into the air-gapped VirtualAI box (lowest integration risk, zero change to live systems); graduate to **read-only APIs** where NIC/CCTNS permits. VirtualAI never writes to CCTNS.

---

## 7. Sovereign by Design

- **Hosting:** inside the **Telangana State Data Centre / NIC Hyderabad** (BRKR Bhavan, **ISO 27001:2022 certified**, ~481 servers, 4000+ VMs, 16 PB storage) or the SCRB server room — on-prem, air-gapped ([NIC Telangana Data Centres](https://tg.nic.in/en/service/data-centres/)). Telangana was the **first state in India to launch a Data Centres Policy**.
- **Model:** on-prem **open-weights LLM via Ollama** — no cloud AI API; inference on department hardware.
- **Workflow engine:** VirtualAI Workflows orchestrate EXTRACT→CHECK→VERIFY→ROUTE&DRAFT with **officer sign-off gates**.
- **Audit log:** every extract, suggestion, confidence score, citation, officer edit, override and sign-off is written to an **immutable audit trail** — court-defensible provenance for every drafted line.

This is the on-prem answer to the TSCOP/Hawk Eye breach lesson: the AI that touches FIRs and victim identities lives **inside the wire**.

---

## 8. Accountability — "The officer decides. Always."

**అధికారే నిర్ణయిస్తారు. ఎల్లప్పుడూ.**

- **AI never decides, closes, or signs.** It does **not** register FIRs, does **not** file charge-sheets, does **not** confirm an identity match, does **not** grant or deny anything.
- **Every output carries four things:** a **confidence score**, a **source citation**, a **one-click officer override**, and an **audit-log entry**.
- **Human-in-the-loop is mandatory.** Low confidence, an ambiguous section mapping, or a missing Sec 105 / Sec 176(3) step **pauses the workflow** for officer input before it can advance.
- **The officer signs.** As with Telangana's **first digitally-signed FIR under the new laws** ([The News Minute](https://www.thenewsminute.com/telangana/telangana-police-registers-first-fir-with-digital-signature-under-new-criminal-laws)), the final charge-sheet is reviewed, edited and **signed by the IO/SHO with a Digital Signature Certificate**. VirtualAI produces the first draft; the officer produces the decision.

---

## 9. Projected Impact — illustrative, to be baselined in the pilot

> These are **illustrative directions of travel, not guarantees.** Each is **baselined in Week 1 of the pilot**, and we **report against measured reality, not marketing claims.**

- **Charge-sheet drafting time** — from days of manual compilation toward a same-day reviewable first draft.
- **Default-bail leakage** — fewer missed **60/90-day clocks** because the Sec 193 countdown and Sec 187 alarm are always on.
- **Compliance rate** — higher proportion of files with Sec 105 (AV) and Sec 176(3) (forensic) steps completed *before* PP scrutiny.
- **Section-mapping accuracy** — fewer IPC→BNS/BNSS errors on straddle cases.
- **Repeat-offender & missing-person linkage** — more cross-station patterns surfaced per week.

Every one of these is a **measurable metric with a Week-1 baseline and a Week-12 assisted-live comparison** in the pilot commissionerate/district.

---

## 10. The 12-Week Pilot — Baseline → Shadow → Assisted-Live

**Scope:** one pilot unit (e.g. a Hyderabad-city zone or an AP district), 1–2 stations plus the SCRB nodal, one PP reviewer.

| Phase | Weeks | What happens |
|---|---|---|
| **Baseline** | 1–3 | Stand up the air-gapped box; ingest **nightly read-only CCTNS/EeCOPS extract**; **instrument the current process** — measure charge-sheet cycle time, deadline misses, compliance-step completion, linkage hit-rate. No AI in the officers' loop yet. |
| **Shadow** | 4–8 | The four agents draft **in parallel, out of the officers' way**. Compare AI drafts and section mappings against officer output; **calibrate confidence scores**; tune to Telangana/AP SOPs and the BNS/BNSS section set. |
| **Assisted-Live** | 9–12 | Officers use the AI draft as their **first draft** — review, edit, and **sign with DSC**. Measure time saved, compliance uplift and deadline-miss reduction against the Week-1 baseline. **Officer always decides.** |

**What's needed from the department:**
- A **nodal sponsor** (SP/DCP) + **SCRB** engagement.
- **Read-only data-extract clearance** from CCTNS/NIC (nightly extract to start).
- **On-prem server** (or a State Data Centre VM) for the air-gapped box + Ollama model.
- **1–2 pilot stations** and **one PP/legal reviewer**.
- The department's current **BNS/BNSS mapping sheet and charge-sheet SOPs** for tuning.

---

## 11. Bilingual by Default — Telugu / English

- **Interface and drafts in both Telugu and English.** Charge-sheets and enquiry reports are drafted in the **language of the court record**; the IO's working interface can run in Telugu.
- **Bilingual section labels** — e.g. *అభియోగ పత్రం (Charge-Sheet / BNSS Sec 193)*, *ప్రథమ సమాచార నివేదిక (FIR / BNSS Sec 173)*, *విశ్వసనీయత స్కోరు (Confidence Score)*.
- **Standing tagline in the UI:** **అధికారే నిర్ణయిస్తారు. ఎల్లప్పుడూ. — The officer decides. Always.**
- **Scope guardrail:** Telugu support is for **UI, drafting and display over already-typed digital records**, using the local open-weights model's language ability. There is **no Telugu handwritten OCR, no image generation, and no cloud fallback** — the system reads structured CCTNS/EeCOPS text and drafts against it, on-prem.

---

## Sources

- Telangana first digitally-signed FIR under new laws; CID 24×7 investigation support centre — [The News Minute](https://www.thenewsminute.com/telangana/telangana-police-registers-first-fir-with-digital-signature-under-new-criminal-laws)
- Telangana first state to integrate CCTNS (EeCOPS) with ICJS; links police stations to trial courts — [SKOCH Exhibition](https://exhibition.skoch.in/beacon-of-hope/police-computer-services-and-standardization/)
- BNSS charge-sheet 60/90-day limits & default bail (Sec 187/193) — [RestTheCase](https://restthecase.com/knowledge-bank/maximum-time-limit-to-file-charge-sheet-in-india); [Bar & Bench](https://www.barandbench.com/view-point/overview-criminal-investigations-and-trials-bnss-bns-bsa-part-ii)
- BNSS Sec 105 (audio-video search/seizure) & Sec 176(3) (forensics 7yr+) — [LiveLaw](https://www.livelaw.in/articles/recording-of-search-and-seizure-electronic-mode-section-105-bnss-281366)
- BNSS Sec 173 (e-FIR & Zero-FIR; in force 1 Jul 2024) — [EBC Webstore](https://blog.ebcwebstore.com/zero-fir-e-fir-bnss-section-173/)
- IPC → BNS section renumbering (511→358; 302→103, 420→318, 376→65) — [LawSikho](https://lawsikho.com/blog/ipc-to-bns-conversion-table/)
- NCRB *Crime in India 2023* — 29.2% pending investigation, 72.7% charge-sheeting, 54% IPC conviction — [Drishti IAS](https://www.drishtiias.com/daily-updates/daily-news-analysis/crime-in-india-2023-report)
- NCRB *Crime in India 2022* — crimes against women conviction/pendency — [Drishti IAS](https://www.drishtiias.com/daily-updates/daily-news-analysis/ncrbs-crime-in-india-2022-report); [Tribune](https://www.tribuneindia.com/news/chandigarh/ncrb-report-2022-53-per-cent-cases-of-crime-against-women-left-pending-568799)
- Court backlog 5.19 crore / 2.88 crore criminal cases (NJDG) — [NewsOnAir](https://www.newsonair.gov.in/over-5-19-cr-cases-pending-in-indian-courts-govt-implements-fast-track-courts-to-address-backlog)
- TSCOP + Hawk Eye breaches (May–Jun 2024; sold for USD 150) — [The Cyber Express](https://thecyberexpress.com/tscop-app-cyberattack-telangana-police/); [Internet Freedom Foundation](https://internetfreedom.in/three-telangana-police-data-breaches/)
- ICJS (Inter-operable Criminal Justice System) / Digital Police portal — [MHA](https://digitalpolice.gov.in/)
- AP citizen e-FIR services & AP-112 ERSS — [citizen.appolice.gov.in](https://citizen.appolice.gov.in/); [112.gov.in](https://112.gov.in/)
- Telangana State Data Centre / NIC (ISO 27001:2022; on-prem hosting) — [NIC Telangana](https://tg.nic.in/en/service/data-centres/)
