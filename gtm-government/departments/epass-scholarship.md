# Education / Welfare — ePASS Post-Matric Scholarship & Fee-Reimbursement (RTF) Verification
### VirtualAI Department Briefing · Citizen-Service Cluster (TS & AP) · SC / ST / BC / EBC / Minority & Disabled Welfare Departments
_ఉపకార వేతనం & ఫీజు రీయింబర్స్‌మెంట్ — "సంక్షేమ అధికారి నిర్ణయిస్తారు. ఎల్లప్పుడూ." (The welfare officer decides. Always.)_

**Client-facing one-liner:** An on-premise decision-support copilot for the scholarship **verification and sanctioning officers** of the welfare departments — it reads the student's ePASS / Jnanabhumi application, checks the caste and income certificates, verifies the **institution's genuineness** and the **course/fee cap**, screens for **duplicate applications, duplicate bank accounts, and fresh-vs-renewal defects**, and drafts the **sanction / defect-memo / rejection proceedings for the welfare officer to sign**. Every output carries a **confidence score** and a **source citation**. It never sanctions, never rejects, never releases a rupee of DBT — it only prepares the file faster and flags what a human should look at.

> **Accuracy note — the Rs 144.33 crore case is the CENTRAL scheme, not this portal.** The widely-reported **Rs 144.33 crore CBI scholarship scam (830 fake / partially-fake institutions across 21 states)** is the **Ministry of Minority Affairs / National Scholarship Portal (NSP)** pre-/post-matric scheme — a **Union-government sibling** of the state schemes. It is **not** the Telangana ePASS or AP Jnanabhumi portal. We flag this deliberately: the two overlap (the **same colleges** often draw both central NSP minority scholarships and state ePASS post-matric funds) and share **identical fraud vectors** — ghost institutions, fake beneficiaries, nodal-officer-plus-bank collusion — so the central case is cited here as **honest sibling evidence of the failure modes the state portal is exposed to**, never as a state-portal statistic. State-specific evidence (CAG findings, "food-and-bed" ghost enrollment, AP scheme misuse) is cited separately below.

---

## 1. Positioning — Offline, air-gapped, sovereign

The scholarship pipeline holds the **caste, income, Aadhaar, bank-account and academic records of lakhs of minor and young students** from the state's poorest SC / ST / BC / EBC / Minority and Disabled households. Caste and income data are among the most sensitive categories a government holds; here they are attached to **children's names, Aadhaar numbers and family bank accounts**. This dataset must **never leave state welfare infrastructure** for a cloud AI API — and the **fraud-detection heuristics themselves** (how the state spots a ghost college or a duplicate account) are exactly what an adversary would want, so they must stay **in-house**.

VirtualAI is built for this: a **private, open-weights LLM served locally via Ollama**, deployed **inside the State Data Centre**, **air-gapped** from the public internet. No student's caste, no income figure, no bank account, and no institution-scoring rule ever leaves the SDC perimeter.

- **"Fully offline" is qualified honestly:** the air-gapped guarantee holds **only because the LLM runs locally** on the department's own GPUs. There is no cloud model, no external API, no "cloud-as-offline" sleight of hand. If the model ran in a vendor cloud, the offline claim would be false — so it doesn't.
- Aligns with the **DPDP Act 2023** (caste, financial and children's data as sensitive personal data; heightened duty for minors' data) and MeitY data-localization expectations for citizen records.
- The map to the proven Revenue "Prajavani" exemplar: **AI Agent = the scholarship verification clerk (subject clerk); Workflow = the file's noting path from field/institution verification → verifying officer → sanctioning authority; Automation = the typing & compiling of the sanction proceedings, defect memo, or rejection order.**

---

## 2. The core recurring process

The welfare departments run the same high-volume sanction loop, **lakhs of times each academic cycle**, through the ePASS (TS) / Jnanabhumi (AP) portals:

1. **Apply / renew.** A student registers on **telanganaepass.cgg.gov.in** (TS) or **jnanabhumi.ap.gov.in** (AP) as a **Fresh** or **Renewal** applicant, selecting scheme, course and institution, and attaching **caste certificate, income certificate, admission/fee particulars, marks/attendance and an Aadhaar-seeded bank account**.
2. **e-KYC / biometric.** The applicant completes **biometric authentication at a MeeSeva centre** (AP additionally routes field checks through the **Village/Ward Secretariat and Volunteer** under **Navasakam**), binding the application to a verified Aadhaar identity.
3. **Verify.** The welfare officer verifies **caste + income + category eligibility**, **institution genuineness**, **course and fee within the sanctioned cap**, and — for renewals — **attendance and pass status**.
4. **Sanction / defect / reject.** The verifying officer and sanctioning authority clear, raise a defect, or reject the application against the scheme GOs.
5. **Pay by DBT.** Funds flow as **Direct Benefit Transfer** — **RTF (Reimbursement of Tuition Fee)** to the college and **MTF (Maintenance/Scholarship)** to the student — routed via the **Aadhaar Payment Bridge System (APBS / NPCI Mapper)** to the Aadhaar-seeded account.

Scale (verified): the **CGG-run TS ePASS handles ~7 lakh+ applications a year** across SC/ST/BC/EBC/Minority/Disabled Welfare departments. In **2025-26 the portal recorded ~6.84 lakh post-matric beneficiaries at ~Rs 1,291.8 crore** (plus pre-matric, Kalyana Lakshmi, Shaadi Mubarak and Overseas schemes on the same rails). **Income caps by category** (TS): **SC ≤ Rs 2.5 lakh · ST ≤ Rs 2.0 lakh · BC / EBC / Minority ≈ Rs 1.5 lakh (rural) / Rs 2.0 lakh (urban)**. Most courses draw **100% RTF**; self-financed courses are capped (e.g. **Rs 20,000 or actual, whichever is less**). Renewal requires **≥ 75% attendance per quarter**, now enforced by **Aadhaar-enabled biometric / facial-recognition attendance (AEBAS)**.

---

## 3. The problem — every leak is a pattern-recognition failure

The scheme's losses are, at root, **failures to spot a pattern in already-digital records at speed** — a ghost college, a fake income slab, a duplicate account, a phantom renewal — precisely what decision-support is for. Cited public evidence:

- **The central sibling scam is real, prosecuted and enormous.** The **Ministry of Minority Affairs** referred a **Rs 144.33 crore** fraud to the **CBI**, which registered its FIR (case filed **28 August 2024**) after Minister Smriti Irani flagged it in July 2023. Of **1,572 institutes** put to an **NCAER** evaluation on **NSP red flags** (6,055 were flagged in all), **830 institutions across 21 states were found non-operational, fake or partially fake** — over half of those checked (Assam 225, Karnataka 162, UP 154, Rajasthan 99, Chhattisgarh 62). The **modus operandi is exactly the state portal's exposure**: "collusion between institutions, applicants, institute nodal officers, district nodal officers, and bank officials, as scholarship amounts are directly credited to beneficiaries' bank accounts." Three central schemes have **disbursed nothing since 2022-23** while the probe drags; **193 FIRs**, only **~Rs 29 lakh** recovered. _(The News Minute; ThePrint; Swarajya)_
- **State CAG audits name the same failure classes.** CAG scrutiny of scholarship/fee-reimbursement spending records **diversion of scholarship funds, excess payment of scholarship, short/denied reimbursement, and scholarship paid to ineligible students** — every one a **cross-reference or eligibility-pattern miss**, not a policy fault. _(CAG audit reports, Telangana)_
- **"Food-and-bed courses" — ghost enrollment for the money.** Telangana had to roll out **Aadhaar-enabled biometric attendance (AEBAS)** and **facial-recognition attendance in ~430 junior colleges**, made **mandatory for promotion and for ePASS/fee-reimbursement**, precisely because colleges enrolled students who never attended ("food-and-bed courses") to draw RTF. The **75%-attendance-per-quarter** rule is the anti-phantom control the copilot must check on every renewal. _(Telangana Today; The News Minute)_
- **The scheme is big enough to be worth defrauding.** AP's Fee Reimbursement Scheme (post-matric) grew from **~Rs 2,000 crore (2008-09) to ~Rs 5,000 crore (2012-13)**, covering **~6 lakh professional students** (~1.5 lakh in engineering), and Wikipedia notes it "faced criticism due to the **misuse of the policy by some institutions**." Scale plus institutional discretion is the classic fraud surface. _(Wikipedia: Fee Reimbursement Scheme)_

**The through-line:** fake/de-recognized institution codes, income just under the category slab, the same bank account behind many "students," a fresh application that is really a duplicate, a renewal for a student who stopped attending — all are **recognizable patterns in structured records**. A tireless copilot that flags them — and cites the rule — lets the welfare officer spend scarce minutes on judgment, not on hunting.

---

## 4. Where the time goes — the current journey and its bottlenecks

A single application today:

1. **Application assembly (student side).** Register on ePASS/Jnanabhumi, attach caste + income certificates, admission/fee particulars, marks/attendance, Aadhaar-seeded bank account. **Bottleneck:** avoidable defects — wrong category, income certificate that doesn't match the caste category's cap, mismatched course/institution, un-seeded bank account — a large share of rejections are for these fixable errors.
2. **e-KYC / field verification.** Biometric at MeeSeva; in AP, Village/Ward-Secretariat + Volunteer field check under Navasakam. **Bottleneck:** manual matching of certificate data to the identity and to category income limits.
3. **Institution genuineness check.** Verify the college is real, recognized and affiliated, and that its **AISHE / U-DISE+ / NCVT code** is valid and live. **Bottleneck:** this is the single most fraud-critical step and the hardest to do by hand across thousands of institutions — the exact gap the central scam exploited.
4. **Eligibility + fee-cap verification.** Category income slab, course eligibility, RTF/MTF within the sanctioned rate/cap. **Bottleneck:** cross-referencing each case against GO fee schedules and category thresholds manually.
5. **Duplicate / renewal screening.** Same Aadhaar/name/DOB applying twice; **one bank account behind many students**; a "fresh" claim that is a disguised renewal; a renewal for a **student below the attendance/pass bar**. **Bottleneck:** duplicate and cluster detection across lakhs of rows is precisely what humans cannot do at the console — and where the CAG "excess/ineligible payment" findings come from.
6. **Sanction + proceedings.** Approve, raise a defect memo, or reject; draft the order; DBT release. **Bottleneck:** free-text drafting, inconsistent GO citation, ad-hoc bilingual phrasing.

Every one of these bottlenecks is document-reading and cross-referencing — **decision-support work, with a human decision at the end.**

---

## 5. The solution — four named agents on EXTRACT → CHECK → VERIFY → ROUTE & DRAFT

Four cooperating agents, each emitting a **confidence score + source citation** on every finding, each stopping short of the decision.

**Agent 1 — Application & Document Reader · "దరఖాస్తు రీడర్" · (EXTRACT).**
Reads the submitted application and its attachments (caste certificate, income certificate, admission/fee particulars, marks/attendance, bank details). Extracts structured fields and runs **completeness + internal-consistency** checks: does the **selected category match the caste certificate**? Is the **income figure within that category's cap** (SC ≤ 2.5L / ST ≤ 2.0L / BC-EBC-Min ~1.5–2.0L)? Is the **course eligible** and the **institution one on record**? Is the **bank account Aadhaar-seeded**? _Output: a structured case sheet + a "missing/mismatched/defect" list, each item citing the exact document and field. Confidence per field._

**Agent 2 — Applicant & Duplicate History · "లబ్ధిదారు చరిత్ర & నకిలీ తనిఖీ" · (CHECK HISTORY).**
Screens for the fraud patterns humans can't see at the console: **duplicate applications** (same Aadhaar / name+DOB / certificate number across the cycle or across ePASS↔Jnanabhumi), **duplicate bank accounts** (one account receiving DBT for many "students," or agent/institution accounts), **fresh-vs-renewal integrity** (a "fresh" claim that is really a renewal; prior-year sanction history), and for renewals the **attendance (≥75%/quarter, AEBAS) and pass/promotion status**. _Output: an eligibility + history summary with de-duplication and cluster flags, citing the prior application IDs, account/Aadhaar links and attendance record. Confidence per flag._

**Agent 3 — Institution & Eligibility Verification (Fraud-Defence Copilot) · "సంస్థ & అర్హత ధృవీకరణ" · (VERIFY RECORDS).**
The ghost-institution defence layer — the control the central scam defeated. Cross-checks the claimed institution against the **AISHE (higher-ed) / U-DISE+ (school) / NCVT (vocational) code registry, affiliation and recognition status**: is the institution **genuine, operational, affiliated and not de-recognized or blacklisted**? Is its code **valid and not a duplicate / reused / lapsed code**? Then verifies the **course and RTF/MTF amount against the GO fee schedule and category cap**, and re-confirms the **income slab**. _Output: a ranked list of cited concerns — each tied to a specific code-registry entry, affiliation record or fee-schedule GO clause — for the officer to accept or override. **It surfaces; it never rejects.** Confidence per concern._

**Agent 4 — Sanction Routing & Drafting · "మంజూరు ముసాయిదా" · (ROUTE & DRAFT).**
Routes the case to the correct **verifying officer / sanctioning authority queue** and **prioritizes deadline-bound and renewal cases** against the cycle calendar. Then **drafts, for the officer to edit and sign**: the **sanction proceedings**; the **defect memo** — enumerating exactly which documents/clarifications are needed so the student's re-submission is used well; or the **rejection order** with **cited GO / category-rule reasons** — all in **bilingual Telugu/English**. _Output: a signature-ready draft (Word/PDF) with citations; the officer signs with **DSC** before any DBT release. Confidence on routing + draft-completeness._

_Guardrail baked in: Agent 3's institution/eligibility flags are advisory inputs to a human. No agent can sanction, reject, or trigger a DBT payment, and every flag is a prompt to look — false positives are expected and the officer overrides freely, with the override logged._

---

## 6. Data sources — read-only, real systems

**Read-only** connections to the systems the departments already run (the copilot reads; it never writes a decision or a payment back):

- **TS ePASS** — `telanganaepass.cgg.gov.in` · `tgepass.cgg.gov.in` (application, verification, sanction and DBT transactions; run by the **Centre for Good Governance**).
- **AP Jnanabhumi** — `jnanabhumi.ap.gov.in` — and **Navasakam** — `navasakam.ap.gov.in` (Village/Ward-Secretariat + Volunteer field-verification layer; caste/income certificates certified via the Secretariat and District Collector).
- **MeeSeva** — source-of-truth for **caste and income certificates** and **biometric e-KYC** at the application stage.
- **Institution registries** — **AISHE** (higher-ed, Ministry of Education), **U-DISE+** (schools), **NCVT** (vocational), plus **AICTE / UGC affiliation and recognition** status — the ground truth for Agent 3's genuineness check.
- **DBT / APBS** — the **NPCI Aadhaar-Mapper** (one Aadhaar ↔ one active account) for RTF-to-college and MTF-to-student release status and duplicate-account signals.
- **AEBAS / facial-recognition attendance** feeds (renewal attendance ≥75%/quarter; pass/promotion status).
- **Prior-cycle application & sanction warehouse** (fresh-vs-renewal and duplicate/cluster checks).
- **Uploaded documents** (certificates, admission/fee receipts, marks memos) in the document store — **typed/structured digital records only; no Telugu handwritten OCR** (scanned handwriting is routed to a human, never machine-read).

**Integration counterpart & cadence:** a **read-only DB replica / API gateway** inside the SDC, built with the portal's own e-governance owner — **CGG for Telangana ePASS**, the **AP e-governance / NIC stack for Jnanabhumi–Navasakam**. **Nightly extract** of slow-moving masters (institution + code registry, affiliation/recognition lists, category income limits, GO fee schedules, blacklist) into the air-gapped store, **then live read-only APIs** for per-case, real-time application/sanction/DBT status. **No student caste, income or bank data ever leaves the SDC**; the LLM reads local copies only.

---

## 7. Sovereign by design

- **Hosting:** the **State Data Centre** — the **Telangana State Data Centre (TSDC)**, an ISO 27001:2022-certified government facility already serving welfare and other departments over SWAN/NICNET, or the **AP State Data Centre** counterpart. VirtualAI deploys **inside this perimeter.**
- **Model:** a **private open-weights LLM served locally via Ollama** on department GPUs. No external API call, ever. This is what makes the offline claim true — and it also keeps the **fraud-detection heuristics off any vendor's servers.**
- **Workflow engine:** the file's noting path — application → **field / institution verification → verifying officer → sanctioning authority** → DBT release — runs as an explicit **human-in-the-loop** workflow with officer sign-off gates before any payment.
- **Audit log:** an **immutable, append-only** record of every AI suggestion, every confidence score, every citation, and **every officer decision (sanction / defect / reject / override)** — so the department, the Director/Commissioner (Welfare) and CAG can reconstruct exactly why any application went the way it did. The AI's advice is logged **as advice**, distinct from the human ruling.

Data-governance frame: **caste, income, Aadhaar and bank data of lakhs of minor and young students — physically never leaves state welfare infrastructure.** That, plus keeping the fraud heuristics in-house, is the whole reason this department is a maximal offline case.

---

## 8. Accountability — "The officer decides. Always."

_"సంక్షేమ అధికారి నిర్ణయిస్తారు. ఎల్లప్పుడూ."_

- The **verifying officer / sanctioning authority** is the decision-maker. The AI **ranks, cites, and drafts** — nothing more. There is **no auto-sanction and no auto-reject**, and the AI **never releases a DBT payment.**
- **Fraud flags are advisory.** Agent 2's duplicate-account and Agent 3's ghost-institution flags are **prompts to verify**, not verdicts; false positives are expected and the officer **overrides freely**, with the override logged. A genuine student is never denied by a model.
- **Every sanction, defect or rejection carries a named human officer's signature and DSC.** The citation the AI supplies makes the human's reasoning faster and more defensible — not automatic.
- Category, income-slab and fee-cap rules are treated conservatively: where a GO or affiliation status is ambiguous, the agent **flags for human judgment rather than guessing**, and says so in its confidence note.

---

## 9. Projected impact — illustrative, to be baselined in the pilot

We do **not** claim numbers we haven't measured. The following are **illustrative hypotheses to baseline in Week 1–2 and then report against measured reality, not against these figures:**

- **Fewer avoidable rejections** — Agent 1's completeness/consistency check aims to cut defective submissions (wrong category, income-over-cap, un-seeded account) so students aren't rejected for fixable errors. _(Baseline: current rejection-for-defect rate.)_
- **Earlier ghost-institution / duplicate capture** — Agents 2 and 3 aim to surface fake or de-recognized institution codes, duplicate applications, one-account-many-students clusters and phantom renewals **before** DBT — in the spirit of the NSP red-flag approach, but we report **only what this deployment actually flags and what officers confirm.** _(Baseline: current audit catch-rate / CAG-finding classes.)_
- **Faster verification throughput** — automated cross-referencing aims to help officers clear more genuine applications inside the cycle window. _(Baseline: current cases-per-officer-day and cycle backlog.)_
- **Faster, better-cited orders** — bilingual sanction/defect/rejection drafts aim to reduce drafting time and standardize GO citation. _(Baseline: current drafting time per case.)_

**The honesty commitment:** every metric above gets a **measured baseline in the pilot**, and monthly reporting compares against that baseline — we report the truth the pilot produces, not the promise on this page.

---

## 10. The 12-week pilot

- **Weeks 1–2 — Baseline & access.** Read-only API/replica into ePASS (or Jnanabhumi) inside the SDC; ingest the institution + code registry, GO fee schedules and category income limits; **measure current rejection-for-defect rate, verification throughput and known audit-finding classes** on a defined application stream. Stand up the local LLM + audit log.
- **Weeks 3–5 — Agents 1 & 2 (EXTRACT + CHECK), shadow mode.** Application reader + duplicate/history screening run alongside human verifiers on live cases; outputs shown but **not acted on**. Tune to the state's certificate formats, category caps and account/Aadhaar data.
- **Weeks 6–8 — Agent 3 (VERIFY) + Agent 4 drafts.** Institution-genuineness and eligibility/fee-cap verification plus bilingual draft proceedings, still human-signed; calibrate confidence thresholds with the verifying officer; suppress noisy false positives.
- **Weeks 9–11 — Supervised live on one category/district + retrospective fraud sample.** Pick one high-volume category or district for supervised assist; run Agent 3 over a **retrospective sample against known audit findings / de-recognized-institution lists** to test ghost-institution and duplicate detection.
- **Week 12 — Measured readout.** Report **actual** deltas vs the Week-1 baseline (defect-rejection reduction, confirmed fraud/duplicate flags, throughput), the officer-override rate, and a go/no-go for scale-out. **Scope excludes:** any auto-sanction or auto-reject, any DBT release by AI, any Telugu handwritten OCR, any image generation, any cloud model.

---

## 11. Bilingual — Telugu / English touches

- **Student-facing letters** (defect memo / rejection / sanction intimation) drafted in **Telugu and English side-by-side**, so the family reads the reason in their own language while the file keeps the English record.
- **Agent + UI labels in Telugu:** ఉపకార వేతనం (scholarship), ఫీజు రీయింబర్స్‌మెంట్ (fee reimbursement), కుల ధృవీకరణ పత్రం (caste certificate), ఆదాయ ధృవీకరణ పత్రం (income certificate), సంస్థ ధృవీకరణ (institution verification), పునరుద్ధరణ (renewal), హాజరు (attendance), మంజూరు (sanction), తిరస్కరణ (rejection), లబ్ధిదారు (beneficiary).
- **Officer console** operable in Telugu or English; confidence notes and citations rendered bilingually on request.
- **Constraint honored:** all Telugu is **typed/rendered digital text** — the system does **not** attempt Telugu handwritten OCR. Scanned handwritten notes are routed to a human, never machine-read.
- Tagline for the deck: **"విద్యార్థికి ఒక నమ్మకమైన సహాయకుడు — నిర్ణయం మాత్రం అధికారిదే."** _(A trustworthy assistant for the student — but the decision stays the officer's.)_

---

## Sources (public, verifiable)

**State portals, scheme mechanics & scale (TS ePASS / CGG):**
- ePASS — Centre for Good Governance project page (departments served, workflow, 2025-26 beneficiaries/outlay): https://www.cgg.gov.in/it_project/electronic-payment-and-application-system-for-scholarships-epass/
- TS ePASS official portal: https://telanganaepass.cgg.gov.in/ · https://tgepass.cgg.gov.in/homeServicePMSPreReg
- Post-matric RTF/MTF components, category income limits (SC 2.5L / ST 2.0L / BC-EBC-Min 1.5–2.0L), self-financed cap — TeachersBadi guidelines: https://teachersbadi.in/telangana-fee-reimbursement-guidelines-ts-post-matrict-scholoarship-scheme-guidelines/
- ePASS eligibility & income conditions — Buddy4Study: https://www.buddy4study.com/article/telangana-epass

**AP Jnanabhumi / Navasakam & AP scheme history:**
- Jnanabhumi portal (SC/ST/OBC/EBC/Kapu/Minority; Ward-Secretariat certs; MeeSeva biometric): https://jnanabhumi.ap.gov.in/
- Navasakam (village/ward-secretariat + volunteer verification): http://navasakam.ap.gov.in
- Fee Reimbursement Scheme — history, scale (Rs 2,000 cr → Rs 5,000 cr; ~6 lakh students), documented institutional misuse, Aadhaar from 2013-14 — Wikipedia: https://en.wikipedia.org/wiki/Fee_Reimbursement_Scheme

**Fraud, ghost enrollment & audit (state-level):**
- CAG audit finding classes — diversion, excess payment, ineligible-student payment, short reimbursement — CAG (Telangana) audit reports: https://cag.gov.in/mab/telangana/en/audit-report/details/46238
- "Food-and-bed courses" → facial-recognition attendance in 430 junior colleges — Telangana Today: https://telanganatoday.com/no-more-food-and-bed-courses-telangana-varsities-to-launch-facial-recognition-based-attendance
- Aadhaar-enabled biometric attendance (AEBAS) mandatory for ePASS/fee-reimbursement, 75%/quarter — The News Minute: https://www.thenewsminute.com/telangana/telangana-enforces-aadhaar-enabled-biometric-attendance-students-168896
- Telangana Education Commission red-flags fee-reimbursement — The South First: https://thesouthfirst.com/telangana/telangana-education-commission-raises-red-flag-over-fee-reimbursement-stresses-reforms/

**Central sibling scam (Ministry of Minority Affairs / NSP — NOT the state portal; cited as sibling evidence):**
- CBI FIR, Rs 144.33 cr, 830 fake institutions / 21 states, nodal-officer + bank collusion — The News Minute: https://www.thenewsminute.com/news/cbi-registers-fir-rs-14433-crore-minority-scholarship-scam-181698
- 1,572 evaluated / 830 fake / 6,055 red-flagged; state distribution; NCAER evaluation — Swarajya: https://swarajyamag.com/news-brief/minority-scholarship-scam-union-ministry-reports-rs-144-crore-loss-from-exchequer-swindled-by-830-fake-institutions-cbi-files-case
- Scheme frozen since 2022-23; three schemes (pre-/post-matric/merit-cum-means); 193 FIRs, Rs 29 lakh recovered — ThePrint: https://theprint.in/india/education/govts-minority-scholarship-scheme-frozen-3-yrs-as-probe-into-fraud-meanders-students-pay-price/2877988/

**Institution genuineness & DBT rails:**
- NSP institution KYC — AISHE / U-DISE+ / NCVT code validation, nodal-officer Aadhaar — Buddy4Study: https://www.buddy4study.com/article/how-to-register-your-institute-on-the-nsp
- Institute KYC registration (official) — NSP: https://nsp.gov.in/IVER/instEKYCRegistrationIndex
- DBT via Aadhaar Payment Bridge / NPCI Mapper (one Aadhaar ↔ one account) — Buddy4Study Aadhaar seeding: https://www.buddy4study.com/article/aadhaar-seeding
