# Health — Aarogyasri Claim Pre-Authorization
### VirtualAI Department Briefing · Citizen-Service / Health Cluster (TS & AP)
_ఆరోగ్యశ్రీ — "వైద్యాధికారి నిర్ణయిస్తారు. ఎల్లప్పుడూ." (The medical auditor decides. Always.)_

**Client-facing one-liner:** An on-premise decision-support copilot for the Trust's pre-authorization and claim-adjudication doctors — it reads the hospital's pre-auth packet, checks the beneficiary's history, verifies the proposed package against the rate-card and clinical protocol, and drafts the approval / query / rejection note **for the medical auditor to sign**. Every output carries a **confidence score** and a **source citation**. It never approves, never denies, never touches emergency care — it only prepares the file faster and flags what a human should look at.

> **Accuracy note on the Wave-1 seed:** the seed line "~1,400 hospitals" conflates the **Rs 1,400 crore arrears** figure with the hospital count. The verified current Telangana network is **~477 empanelled hospitals** (~323 private under TANHA); Andhra Pradesh runs **~730+**. Corrected figures are used throughout this brief.

---

## 1. Positioning — Offline, air-gapped, sovereign

Aarogyasri / Dr YSR Aarogyasri–NTR Vaidya Seva handles the **protected health information (PHI) of nearly 1 crore of the poorest families** — diagnoses, ICD codes, ration/white-card identity, surgical histories, implant invoices, and hospital financials. This is the single most privacy-sensitive dataset in the state's citizen-service stack. It must **never leave state health infrastructure** to a cloud AI API.

VirtualAI is built for exactly this: a **private, open-weights LLM served locally via Ollama**, deployed **inside the Telangana State Data Centre (TSDC)** or the AP counterpart, **air-gapped** from the public internet. No diagnosis, no patient name, no hospital claim ever leaves the SDC perimeter.

- **"Fully offline" is qualified honestly:** the air-gapped guarantee holds **only because the LLM runs locally** on the department's own GPUs. There is no cloud model, no external API, no "cloud-as-offline" sleight of hand. If the model ran in a vendor cloud, the offline claim would be false — so it doesn't.
- Aligns with the **DPDP Act 2023** treatment of health data as sensitive personal data, and with MeitY data-localization expectations for citizen PHI.
- The map to the proven Revenue "Prajavani" exemplar: **AI Agent = the pre-auth desk analyst (subject clerk); Workflow = the case's noting path from Aarogyamithra → specialty panel doctor → Chief Medical Auditor; Automation = the typing & compiling of the approval / query / rejection letter and the settlement note.**

---

## 2. The core recurring process

The Trust runs the same high-volume loop, tens of thousands of times a month, in two linked stages:

**Stage A — Pre-authorization (before treatment; target turnaround < 24h TS / 12h AP).**
A patient with an Aarogyasri/white card reaches an empanelled **Network Hospital**. The hospital's **Aarogyamithra ("ఆరోగ్యమిత్ర" — Friend of Health)** at the reception kiosk verifies the beneficiary, and the **MEDCO (Medical Co-ordinator)** raises an **e-preauthorization** on the **ASRI 2.0** portal — uploading the **diagnosis + ICD code, the proposed package/procedure code** (from the ~1,835-procedure master), **investigation reports** (labs, imaging), a **clinical justification**, and a **cost estimate**. A **round-the-clock pre-auth wing of specialty panel doctors** reviews it and issues **approve / query / reject**. Only after approval does cashless treatment proceed.

**Stage B — Post-discharge claim adjudication + medical audit.**
After discharge the hospital submits the **claim packet** (discharge summary, operative notes, implant invoices, ICU records, outcome). The Trust's **medical auditors** scrutinize it against the approved pre-auth and the scheme rules, run **fraud / upcoding checks**, and settle, query, or reject. Payment is meant to flow via ECS within the **40-day MoU window** (a window frequently missed — see §3).

Scale (verified): **TS ~99 lakh BPL families / ~2.84 crore individuals; ~477 network hospitals; 1,835 procedures; Rs 10 lakh cover.** **AP ~1.29 crore families; ~730+ hospitals; 3,000+ procedures; Rs 5 lakh cover** under the restored **Dr NTR Vaidya Seva** name (2024). Coverage since Aug 2024 in TS was **doubled Rs 5 → 10 lakh**, with **163 new procedures** (98 via PM-JAY + 65 state) and **1,375 procedures re-rated** (+20%), costing **~Rs 487.29 crore**.

---

## 3. The problem — every leak is a pattern-recognition failure

The scheme's losses and delays are, at root, **failures to spot a pattern in a document at speed** — precisely what decision-support is for. Cited public evidence:

- **Upcoding is a named, prosecuted fraud.** PM-JAY / NHA governs on a **zero-tolerance** stance against "up-coding of treatment packages/procedures," impersonation, and non-genuine claims. NHA's own AI freezes a claim for manual audit when a hospital bills a **"Major Surgery" but the record only supports a "Minor Procedure"** — the exact pattern a pre-auth reviewer must catch under a 24-hour clock. _(NHA / IndiaAI, PIB)_
- **Ghost and dead-patient claims.** A CAG audit found **Rs 6.97 crore paid on 3,903 claims for patients already recorded as dead** under AB-PMJAY — a de-duplication / cross-reference failure, not a clinical one. _(Deccan Herald / CAG)_
- **Fraud at national scale is real and material.** NHA's **National Anti-Fraud Unit (NAFU)** penalised **2,842 hospitals (Rs 114.06 crore)** in FY25-26, **de-empanelled 2,003**, suspended **839**, and **blocked Rs 678.47 crore of suspicious claims before payment**; separately **3.56 lakh claims worth Rs 643 crore** were rejected for fraud. _(Medical Dialogues; Deccan Herald)_
- **Local precedent in Telangana.** CID booked **17 private hospitals** for siphoning funds via **fabricated medical bills** (CM Relief Fund) — the same document-forgery vector that hits Aarogyasri claims. _(Deccan Herald)_
- **Turnaround pressure breeds error.** The MoU sets a **40-day** reimbursement window that is routinely blown; arrears reached **~Rs 1,400 crore**, triggering a **TANHA service suspension (Sept 2025)** across ~323 private hospitals. When queues back up, reviewers rush — and rushed review is where both wrongful rejections and missed upcoding happen. _(Siasat; Medical Dialogues)_

**The through-line:** upcoding, gender/package mismatch, once-only-procedure repeats, ghost patients, forged invoices, and incomplete packets are all **recognizable patterns in already-digital records**. A tireless copilot that flags them — and cites the rule — lets the medical auditor spend scarce minutes on judgment, not on hunting.

---

## 4. Where the time goes — the current journey and its bottlenecks

A single pre-auth today:

1. **Packet assembly (hospital side).** Aarogyamithra + MEDCO gather diagnosis, ICD, package code, investigations, cost estimate and upload to ASRI 2.0. **Bottleneck:** incomplete/inconsistent packets — a wrong package code, a missing mandatory investigation, an ICD that doesn't match the claimed procedure.
2. **Queue + triage (Trust side).** The packet lands in a shared queue and must be routed to the right **specialty panel doctor** (cardiology, oncology, nephrology, ortho…). **Bottleneck:** manual triage; emergencies and near-deadline cases are not always surfaced first.
3. **Clinical + eligibility review.** The panel doctor checks eligibility, benefit balance (Rs 10 lakh cap), package-vs-diagnosis appropriateness, and upcoding signals — **by hand, against a 1,835-line master and the rate card.** **Bottleneck:** cognitive load under a 24h/12h clock; only **one query** is allowed (AP: +6h), so a poorly-specified query wastes the single round-trip.
4. **Decision + letter.** Approve / query / reject, then draft the letter. **Bottleneck:** free-text drafting, inconsistent rule citations, bilingual phrasing done ad hoc.
5. **Post-discharge audit.** Same reviewers re-open the file against delivered treatment and invoices. **Bottleneck:** reconciling "approved vs delivered," spotting phantom procedures and invoice fraud across thousands of claims — the work that, when skipped, becomes the CAG finding.

Every one of these bottlenecks is document-reading and cross-referencing — **decision-support work, with a human decision at the end.**

---

## 5. The solution — four named agents on EXTRACT → CHECK → VERIFY → ROUTE & DRAFT

Four cooperating agents (extending the seeded **health agent**), each emitting a **confidence score + source citation** on every finding, each stopping short of the decision. They serve **both** pre-auth (Stage A) and post-discharge adjudication (Stage B).

**Agent 1 — Pre-Auth Reader & Completeness Check · "ముందస్తు అనుమతి రీడర్" · (EXTRACT).**
Reads the uploaded packet (diagnosis note, ICD, proposed package/procedure code, investigation reports, cost estimate). Extracts structured fields and runs **completeness + internal-consistency** checks: does the **ICD diagnosis match the claimed package code**? Are the **mandatory investigations** for that package present and legible? Is the cost estimate within the package's rate-card band? _Output: a structured case sheet + a "missing/mismatched items" list, each item citing the exact uploaded document and page. Confidence per field._

**Agent 2 — Beneficiary & Claim-History · "లబ్ధిదారు చరిత్ర" · (CHECK HISTORY).**
Checks card validity and family eligibility, **remaining annual benefit balance** against the Rs 10 lakh (TS) / Rs 5 lakh (AP) cap, and **prior claims**: is this a **repeat of a once-only procedure** (e.g., appendectomy, hysterectomy, same-eye cataract)? Recent same-hospital / same-beneficiary billing clusters? Any **deceased-beneficiary or duplicate-ID** flag (the CAG failure mode). _Output: eligibility + history summary with duplicate/anomaly flags, citing card record and prior claim IDs. Confidence per flag._

**Agent 3 — Package & Clinical Verification (Medical-Audit Copilot) · "ప్యాకేజీ సరిపోలిక" · (VERIFY RECORDS).**
The upcoding-defence layer. Cross-checks the proposed package against the **procedure master + rate card** and the scheme's **clinical protocol**: is the package **appropriate to the diagnosis and the investigations actually on file** (guarding against **major-billed-for-minor** upcoding)? **Gender/package mismatch**? Are the package's clinical pre-conditions met? Length-of-stay and cost within norms? For Stage B it reconciles **approved-vs-delivered** treatment and screens implant invoices. _Output: a ranked list of cited concerns — each tied to a specific master-entry or guideline clause — for the auditor to accept or override. **It surfaces; it never denies.** Confidence per concern._

**Agent 4 — Adjudication Routing & Drafting · "నిర్ణయ ముసాయిదా" · (ROUTE & DRAFT).**
Routes the case to the correct **specialty panel-doctor queue**, and **prioritizes emergencies and near-deadline cases** against the 24h/12h clock. Then **drafts, for the auditor to edit and sign**: the approval note; the **query letter** — enumerating exactly which documents/clarifications are needed so the single query round is used well; or the **rejection letter** with **cited scheme-rule reasons** — all in **bilingual Telugu/English**. _Output: a signature-ready draft (Word/PDF) with citations; the officer signs with **DSC**. Confidence on routing + draft-completeness._

_Guardrail baked in: Agent 3's flags are advisory inputs to a human. No agent can issue an approval or denial, and emergency-tagged cases are fast-tracked straight to a human reviewer — the AI never sits between a critically ill patient and care._

---

## 6. Data sources — read-only, real systems

**Read-only** connections to the systems the Trust already runs (the copilot reads; it never writes a decision back):

- **ASRI 2.0 hospital/Trust portal** — live pre-auth and claim transactions. `aarogyasri.telangana.gov.in` · `rajivaarogyasri.telangana.gov.in/ASRI2.0/portal` (TS); `drntrvaidyaseva.ap.gov.in` (AP).
- **Package & Procedure Master + Rate Card** — the ~1,835-procedure catalogue (TS) / 3,000+ (AP) with clinical pre-conditions and package rates (the ground truth for Agent 3).
- **Beneficiary / eligibility DB** — white/ration card, PM-JAY beneficiary DB, **ABHA/Ayushman card** under the **Ayushman Bharat PM-JAY Aarogyasri** convergence (~1.3 crore beneficiaries; portability across ~22,000 hospitals nationally).
- **Empanelled-hospital master + panel-doctor directory** (routing targets).
- **Prior pre-auth / claims history warehouse** (duplicate & anomaly checks).
- **NHA Transaction Management System (TMS)** for converged PM-JAY claims.
- **Hospital-uploaded clinical documents** (diagnosis, investigations, discharge summary, implant invoices) in the document store — **typed/structured digital records only; no Telugu handwritten OCR.**

**Integration counterpart & cadence:** a **read-only DB replica / API gateway** inside the SDC. **Nightly extract** of slow-moving master data (package master, rate card, empanelment list, beneficiary eligibility) into the air-gapped store, **then live read-only APIs** for per-case, real-time pre-auth/claim status. **No PHI ever leaves the SDC**; the LLM reads local copies only.

---

## 7. Sovereign by design

- **Hosting:** the **Telangana State Data Centre (TSDC)** — an **ISO 27001:2022**-certified facility (220 racks, 481 servers, 4,000+ VMs, 16 PB storage, 10 Gbps), already the government cloud for Health and other departments via SWAN/NICNET — or the AP State Data Centre counterpart. VirtualAI deploys **inside this perimeter.**
- **Model:** a **private open-weights LLM served locally via Ollama** on department GPUs. No external API call, ever. This is what makes the offline claim true.
- **Workflow engine:** the case's noting path — Aarogyamithra/MEDCO submission → specialty panel doctor → **Chief Medical Auditor (Chair, Empanelment & Disciplinary Committee)** — runs as an explicit **human-in-the-loop** workflow with officer sign-off gates.
- **Audit log:** an **immutable, append-only** record of every AI suggestion, every confidence score, every citation, and **every officer decision (accept / override / edit)** — so the Trust, the CEO (an IAS officer), and CAG can reconstruct exactly why any case went the way it did. The AI's advice is logged **as advice**, distinct from the human ruling.

Data governance frame: **PHI of ~1 crore poor families — diagnoses, patient identity, hospital financials — physically never leaves state health infrastructure.** That is the whole reason this department is a maximal offline case.

---

## 8. Accountability — "The officer decides. Always."

_"వైద్యాధికారి నిర్ణయిస్తారు. ఎల్లప్పుడూ."_

- The **medical auditor / specialty panel doctor** is the decision-maker. The AI **ranks, cites, and drafts** — nothing more. There is **no auto-approve and no auto-deny.**
- **The AI never denies care.** Agent 3's upcoding/anomaly flags are **advisory**; false positives are expected and the auditor **overrides freely**, with the override logged. A flag is a prompt to look, not a verdict.
- **Emergencies bypass the AI** to immediate human review — no clinical clock is ever spent waiting on a model.
- **Every rejection or query carries a named human auditor's signature and DSC.** The citation the AI supplies is there to make the human's reasoning faster and more defensible — not to substitute for it.
- Clinical and scheme rules are treated conservatively: where a package/protocol interpretation is ambiguous, the agent **flags for human judgment rather than guessing**, and says so in its confidence note.

---

## 9. Projected impact — illustrative, to be baselined in the pilot

We do **not** claim numbers we haven't measured. The following are **illustrative hypotheses to baseline in Week 1–2 and then report against measured reality, not against these figures:**

- **Cleaner packets, fewer wasted query rounds** — Agent 1's completeness check aims to cut incomplete/inconsistent submissions so the single allowed query round is rarely wasted. _(Baseline: current query/re-submission rate.)_
- **More consistent on-time approvals** — faster triage + drafting aims to help more cases clear inside the **24h (TS) / 12h (AP)** target. _(Baseline: current % within target.)_
- **Earlier upcoding / anomaly capture** — Agent 3 aims to surface major-for-minor, gender/package mismatch, once-only repeats and ghost-patient flags **before** payment, in the spirit of NHA's Rs 678 cr pre-payment blocks — but we will report **only what this deployment actually flags and what auditors confirm.** _(Baseline: current audit catch-rate.)_
- **Faster, better-cited letters** — bilingual approval/query/rejection drafts aim to reduce drafting time and standardize rule citation. _(Baseline: current drafting time per case.)_

**The honesty commitment:** every metric above gets a **measured baseline in the pilot**, and monthly reporting compares against that baseline — we report the truth the pilot produces, not the promise on this page.

---

## 10. The 12-week pilot

- **Weeks 1–2 — Baseline & access.** Read-only API/replica into ASRI 2.0 (or Dr NTR Vaidya Seva) inside the SDC; ingest package master + rate card; **measure current turnaround, query-rate, and audit catch-rate** on a defined case stream. Stand up the local LLM + audit log.
- **Weeks 3–5 — Agents 1 & 2 (EXTRACT + CHECK), shadow mode.** Pre-auth reader + beneficiary/history run alongside human reviewers on live cases; outputs shown to auditors but **not acted on**. Tune to the state's package master and card DB.
- **Weeks 6–8 — Agent 3 (VERIFY) + Agent 4 drafts.** Package/clinical verification and bilingual draft letters, still human-signed; calibrate confidence thresholds with the Chief Medical Auditor; suppress noisy false positives.
- **Weeks 9–11 — Supervised live on one specialty + post-discharge audit sample.** Pick one high-volume specialty (e.g., cardiology or ortho) for supervised assist; extend Agent 3 to a **retrospective post-discharge audit sample** to test upcoding detection against known-good cases.
- **Week 12 — Measured readout.** Report **actual** deltas vs the Week-1 baseline (turnaround, wasted-query reduction, confirmed audit flags), the officer-override rate, and a go/no-go for scale-out. **Scope excludes:** any auto-decisioning, any Telugu handwritten OCR, any image generation, any cloud model.

---

## 11. Bilingual — Telugu / English touches

- **Beneficiary-facing letters** (query / rejection / approval intimation) drafted in **Telugu and English side-by-side**, so the patient's family reads the reason in their own language while the file keeps the English record.
- **Agent + UI labels in Telugu:** ఆరోగ్యశ్రీ (Aarogyasri), ఆరోగ్యమిత్ర (Aarogyamithra), ముందస్తు అనుమతి (pre-authorization), వైద్య తనిఖీ (medical audit), లబ్ధిదారు (beneficiary), ప్యాకేజీ (package).
- **Reviewer console** operable in Telugu or English; confidence notes and citations rendered bilingually on request.
- **Constraint honored:** all Telugu is **typed/rendered digital text** — the system does **not** attempt Telugu handwritten OCR. Scanned handwritten notes are routed to a human, never machine-read.
- Tagline for the deck: **"ఆరోగ్యశ్రీకి ఒక నమ్మకమైన సహాయకుడు — నిర్ణయం మాత్రం వైద్యుడిదే."** _(A trustworthy assistant for Aarogyasri — but the decision stays the doctor's.)_

---

## Sources (public, verifiable)

**Scheme scale, coverage & finances (TS):**
- Rs 1,779 cr cleared, Rs 95–100 cr/month, 99 L families, cover doubled 5→10 L — NewsMeter: https://newsmeter.in/top-stories/aarogyasri-row-telangana-govt-says-rs-1779-crore-dues-cleared-urges-hospitals-to-continue-services-755151
- Rs 100 cr/month release — Medical Buyer: https://medicalbuyer.co.in/telangana-to-release-rs-100-crore-per-month-for-aarogyasri/
- Cover enhanced to Rs 10 lakh — The Hans India: https://www.thehansindia.com/telangana/telangana-govt-enhances-aarogyasri-coverage-to-rs-10-lakh-843316
- 163 procedures added → 1,835 total (98 PM-JAY + 65 state) — NewsOnAir: https://www.newsonair.gov.in/telangana-govt-announced-addition-of-163-medical-procedures-to-states-ravij-aarogyasree-health-scheme

**Hospital network & arrears:**
- Rs 1,400 cr arrears, TANHA suspension, ~323 hospitals — Siasat: https://www.siasat.com/aarogyasri-services-suspended-in-telangana-over-arrears-of-rs-1400-cr-3272316/
- 477 hospitals / 87% running — Siasat: https://www.siasat.com/majority-hospitals-in-telangana-running-aarogyasri-services-despite-strike-govt-3272616/
- 40-day MoU window, corporate hospital counts — Medical Dialogues: https://medicaldialogues.in/state-news/telangana/unpaid-dues-aarogyasri-empanelled-hospitals-facing-financial-strain-137243

**Pre-auth process & scheme workflow:**
- AP pre-auth 12h (query +6h → 18h), round-the-clock panel doctors — Govt of AP / NTR Vaidya Seva functions: https://www.ysraarogyasri.ap.gov.in/ntr-vaidya-seva-functions
- Aarogyamithra role, kiosk, e-preauth — Law Insider: https://www.lawinsider.com/dictionary/aarogyamithra
- Dr YSR Aarogyasri Scheme Guidelines (5th ed.) PDF: https://www.govtschemes.in/sites/default/files/2023-01/Dr.%20YSR%20Aarogyasri%20Scheme%20Guidelines.pdf
- Official portals: https://aarogyasri.telangana.gov.in/ · https://drntrvaidyaseva.ap.gov.in/

**Fraud, upcoding & AI audit (national precedent):**
- NHA AI auto-adjudication (major-for-minor freeze, gender/package mismatch) — IndiaAI: https://indiaai.gov.in/news/the-government-of-india-uses-ai-ml-to-detect-potential-frauds-under-ab-pmjay
- Anti-fraud system for AB-PMJAY — PIB: https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=1847423
- NAFU: 2,842 hospitals penalised (Rs 114.06 cr), 2,003 de-empanelled, Rs 678.47 cr blocked — Medical Dialogues: https://medicaldialogues.in/news/health/hospital-diagnostics/ayushman-bharat-fraud-national-health-authority-slaps-rs-114-crore-penalty-on-2842-hospitals-175384
- 3.56 L claims / Rs 643 cr rejected for fraud — Deccan Herald: https://www.deccanherald.com/india/356-lakh-claims-worth-rs-643-cr-rejected-for-frauds-under-ayushman-bharat-scheme-3442492
- CAG: Rs 6.97 cr paid on claims for dead patients — Deccan Herald: https://www.deccanherald.com/health/healthcare/rs-697-crore-was-paid-to-dead-patients-under-pmjay-cag-2649876
- Telangana CID: 17 hospitals booked, fabricated bills — Deccan Herald: https://www.deccanherald.com/amp/story/india%2Ftelangana%2F17-private-hospitals-booked-for-siphoning-off-cm-relief-funds-through-fake-documents-in-telangana-3164566

**PM-JAY convergence:**
- Ayushman Bharat PM-JAY Aarogyasri, ~1.3 cr beneficiaries, 22,000 hospitals portability — Telangana Today: https://telanganatoday.com/convergence-of-aarogyasri-ayushman-bharat-to-benefit-1-3-cr-people-in-ts-nha
- TS implements AB PM-JAY (MoU with NHA) — BioSpectrum: https://www.biospectrumindia.com/news/16/18726/telangana-implements-ayushman-bharat-pm-jay-scheme.html

**Scheme history & sovereign hosting:**
- Launched 01.04.2007 (YSR); Trust under Health Dept, CM chair, IAS CEO — National Govt Services Portal: https://services.india.gov.in/service/detail/scheme-of-rajiv-aarogyasri-health-care-trust-telangana
- Telangana State Data Centre (ISO 27001:2022; 481 servers; 16 PB) — ITE&C Dept: https://it.telangana.gov.in/initiatives/sdc/
