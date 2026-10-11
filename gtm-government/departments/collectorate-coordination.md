# District Collectorate — Coordination, Review & VIP-Reference Management
### Telangana & Andhra Pradesh · Weekly/monthly departmental review · MP/MLA/Minister references · Cross-department pendency & escalation

> _Revenue / Collectorate cluster. The **apex district file.** The District Collector is the district's single
> coordinating head — the officer who chairs the review of **20+ line departments**, answers every **MP / MLA /
> Minister reference** forwarded on a citizen's behalf, and carries the escalation of everything the departments
> below are late on. VirtualAI touches **only the coordination desk** — the reading, summarising, routing and
> drafting that surrounds the Collector's decision. It never decides which department is failing, never grades an
> officer, never signs a reply. Same proven pipeline as the Revenue exemplars — **EXTRACT → CHECK HISTORY → VERIFY
> RECORDS → ROUTE & DRAFT**, every output with a **confidence score and a source citation** — pointed at the
> **Collector's chamber, not the field.**_
>
> _Product mapping, Collectorate edition: **AI Agent = the subject clerk / superintendent** who reads the 20-department
> status feed and the day's tappal · **Workflow = the file's noting path** — reference inward → route to the line
> department → follow-up → reply · **Automation = the typing & compiling** of the review brief, the tasking letter,
> the VIP reply, and the meeting minutes._
>
> _This department is the **natural expansion of the deployed Prajavani copilot** — same Collector sponsor, one desk
> higher: from a single grievance stream up to the whole coordination-review-reference portfolio._
>
> _సమన్వయం · సమీక్షా సమావేశం · ప్రజాప్రతినిధుల సిఫారసులు (ఎంపీ/ఎమ్మెల్యే/మంత్రి) · శాఖల పెండెన్సీ & ఎస్కలేషన్_

---

## 1. Positioning — offline, air-gapped, sovereign, and strictly a coordination aide

VirtualAI runs **entirely inside government infrastructure** — the **State Data Centre** or the Collectorate's own
server room — on a **private open-weights LLM served locally via Ollama.** No VIP-reference letter, no candid
inter-department pendency assessment, no protocol/security file, and no disaster-response note ever leaves the
district's perimeter. There are **no cloud AI API calls.**

Why this department is one of the **strongest air-gap cases** in the whole government map:

- **The data is politically and security-sensitive by its nature.** A Collector's coordination desk holds the raw
  **references of every MP, MLA and Minister** in the district (each a named political principal writing on a named
  citizen's behalf); the Collector's own **frank assessment of which line department is lagging** and by how much;
  **VIP-visit protocol and security** arrangements; and, in the disaster-management role, live incident coordination.
  A cloud AI vendor silently ingesting a state's VIP correspondence and its districts' candid departmental
  scorecards is not a privacy nuisance — it is a **governance-sovereignty and political-security breach.**
- **The state has already chosen on-prem monitoring for this exact function.** Telangana's **TG-DMS "Collector
  Dashboard"** and **Prajavani-Praja Bhavan**, and Andhra Pradesh's **Real Time Governance Society (RTGS)** stack,
  are all **government-owned, on-premise** systems built and run by **CGG / the State**. VirtualAI is not asking the
  district to change posture; it is **the AI layer that respects the posture the state already adopted** — on-prem,
  government-hosted, auditable.

**Honesty qualifier:** "fully offline" is true **because the model weights are local.** A hosted model — however it
is branded — would break the guarantee. We do not relabel a cloud call as "offline." On-prem inference on open
weights, full stop.

**Scope qualifier, stated up front:** VirtualAI is **coordination decision-support only.** It does **not** decide
which department is failing, does **not** rate or rank officers, does **not** approve or reject a grievance, and does
**not** send a reply to any VIP. It reads the feeds and the references, assembles the brief, drafts the reply, and
**flags** the laggards — and the **Collector reviews, edits, and signs.** The apex officer's judgment is untouched,
by design.

---

## 2. The core recurring process — what the coordination desk actually does

The Collector is the **district's coordinating authority** — the Head of District administration under the **Board's
Standing Orders (BSO)** and, under **Section 25 of the Disaster Management Act, 2005**, the **Chairperson of the
District Disaster Management Authority (DDMA)**, the district's "planning, coordinating and implementing body"
(Section 30). Around that authority runs a fixed, high-volume, document-heavy cycle. None of it is field execution;
all of it is reading, compiling, routing and drafting:

1. **Weekly / monthly review-meeting preparation (the core job).** Before every departmental review, the Collectorate
   compiles the current status of **20+ line departments** — in Telangana literally the **87 parameters across 20
   departments** that **TG-DMS (the "Collector Dashboard")** tracks — into a **review brief**: what is on target,
   what is slipping, which SLAs are breached, which schemes are behind. After the meeting, staff draft the
   **minutes** and a **line-item action-tracker** with owners and deadlines.
2. **VIP-reference handling.** An **MP, MLA, Minister or Minister's office** forwards a citizen's petition to the
   Collector. Each such reference must be **entered in the inward/tappal register, routed to the correct line
   department, followed up, and replied to** — under the **CSMoP / DoPT** discipline that a communication from a
   people's representative is **acknowledged within 15 days and replied to within the next 15**, kept under "special
   watch" for speedy disposal.
3. **Pendency escalation.** When **Revenue, Housing, MeeSeva, Prajavani or Welfare** breaches its timeline, the
   Collector issues an **escalation / reminder note** to the line department and tracks it to closure — the recurring
   "why is this still pending" file.
4. **Protocol & disaster coordination.** VIP-visit arrangements and, in a disaster, the DDMA coordination stream —
   both document-heavy, both on sensitive material.

This cycle repeats **every week and every month, in every district** — 33 districts in Telangana, 26 in Andhra
Pradesh — and it is almost entirely **read-summarise-route-draft** work sitting on top of dashboards the state
already runs.

---

## 3. The problem — coordination friction as pattern-recognition failure, at scale

The numbers the Collector must coordinate are enormous, and the failure is not that the data is missing — the
dashboards hold it — but that **turning 20+ raw feeds into a coherent, prioritised, written review, and turning a
stack of unstructured VIP letters into correctly-routed, timely replies, is manual pattern-work that does not scale:**

- **The review surface is genuinely 20+ departments wide.** TG-DMS links **87 parameters from 20 departments** into
  the Collector Dashboard; of these, **22 are captured directly and 65 are dynamically pulled** from each
  department's own portal (CGG). Reading 87 live parameters and writing the *narrative* — "housing is on track,
  MeeSeva SLA is slipping in these three mandals, Prajavani pendency is up 18%" — is a synthesis task a **query
  cannot do**; a query returns 87 numbers, not a review.
- **Grievance volume is heavy and repeat-laden.** Telangana's **Prajavani-Praja Bhavan** system had, as of **9 Dec
  2024**, received **82,955 petitions**, of which **43,272 were classified as grievances**; **27,215 were resolved**
  and **16,057 remained pending** — and by **25 Feb 2025** the system had logged **91,313 grievances**. Every one
  carries a **30-day disposal clock** and lands, through the RDO-Monday channel, on the coordination desk.
- **The one-time outreach numbers show the true tail.** Telangana's **Praja Palana** outreach took **~1.30 crore
  applications** in ten days; **~70 lakh** of them were **land / Dharani-error** grievances, and of **3,49,514**
  applications routed for grievance resolution only **1,79,143** had been addressed at the review point — a live,
  cited illustration of how fast a coordination desk's backlog compounds when references arrive unstructured and must
  be read, classified and routed by hand.
- **VIP references carry a hard clock and a political cost for missing it.** Under **CSMoP** and the **DoPT
  Consolidated Guidelines on official dealings with Members of Parliament and State Legislatures**, an MP/MLA
  communication must be **acknowledged in 15 days and replied to in the next 15**, under "special watch." Nationally,
  the same discipline runs through **CPGRAMS**, where the redressal timeline was **cut from 30 to 21 days** (DARPG,
  Aug 2024) and where, even so, thousands of grievances age past 90 days. The failure mode is precisely a
  **pattern-recognition failure**: the letter that was mis-routed to the wrong department, the reference whose
  15-day acknowledgement slipped because it sat unread in a stack, the third letter this month on the same matter
  that nobody spotted as a duplicate.
- **Every one of these is a match a busy superintendent does by hand.** Which of 20 departments owns this citizen's
  ask? Is this reference a repeat of one already answered? Which three of 87 parameters are the ones the Collector
  must raise on Monday? Is this MP letter inside its 15-day window? These are exactly the tasks humans do
  inconsistently at volume and machines do reliably. **That gap — in the coordination desk, not the field — is the
  product.**

---

## 4. Where the time goes — the current coordination journey and its bottlenecks

| Stage | Who (Collectorate) | What happens | Bottleneck |
|---|---|---|---|
| Feed gathering | Superintendent / dashboard operator | Log into TG-DMS / department portals / Prajavani / MeeSeva; note the current numbers for 20+ departments | Data is *there* but scattered across portals; no single written picture |
| **Review-brief writing** | **Superintendent / PA to Collector** | Turn 87 parameters × 20 departments into a prioritised **narrative brief** for the review meeting | **The core bottleneck** — pure synthesis, done overnight by hand, inconsistent week to week |
| VIP-reference intake | Tappal / inward section | MP/MLA/Minister letter entered in the inward register; a citizen's ask buried in a forwarded, unstructured letter | Reading & classifying by hand; the 15-day acknowledgement clock starts here and is easy to miss |
| Routing | Coordination clerk | Decide which line department owns the ask; mark and forward the file | Mis-routing to the wrong department = a full cycle lost; repeats not detected |
| Follow-up & escalation | Coordination section | Chase the line department; draft reminder / escalation notes on SLA breaches | Manual chasing; no automatic "this reference is now overdue" flag |
| **Reply & tasking drafting** | **Superintendent** | Draft the VIP reply, the line-department tasking letter, the meeting minutes & action-tracker | Repetitive drafting; minutes lag the meeting by days; action-tracker owners drift |
| Sign-off | **Collector / Additional Collector** | Read, correct, **sign** (VIP replies often with **DSC**) | The one step that must stay human — and does |

The time is **not** in the Collector deciding — that is the apex officer's protected function and stays exactly where
it is. The time is in the **clerical layer around the decision**: gathering the feeds, writing the brief, reading and
routing the references, chasing the laggards, and typing the reply, the tasking letter and the minutes. That layer is
what VirtualAI compresses.

---

## 5. The solution — four named agents on the proven pipeline (coordination desk only)

Four decision-**support** agents, each returning a **confidence score + a citation to the exact source** (the
dashboard row, the paragraph of the MP's letter, the CPGRAMS/Prajavani ID, the department's own record). None of them
routes, escalates, or replies on its own: they assemble the coordination work; **the Collector / Additional Collector
reviews and signs.**

**The honest line — genuine AI vs a deterministic lookup (read this first).**
We are explicit about where the language model actually earns its place and where it does not:
- **Deterministic (a plain fetch — the LLM adds nothing here):** pulling the **87 TG-DMS parameters**, the
  **Prajavani pendency counts**, the **MeeSeva SLA-breach flags**, the **CPGRAMS overdue list**. These are database
  queries. A query returns numbers. VirtualAI does **not** reinvent the dashboard — it **reads** it, read-only, and
  shows the number with a link to its source row.
- **Genuine LLM (the language model is actually necessary):** **(a)** summarising **20+ department feeds** into a
  coherent, prioritised **narrative review brief** a Collector can read in five minutes — a query gives 87 numbers;
  only an LLM writes the *review*; **(b)** reading an **unstructured MP/MLA/Minister letter** — free-form prose, a
  citizen's ask embedded in a forwarding note — to **extract the ask and identify the correct line department**;
  **(c)** **drafting** the VIP-reference reply, the line-department tasking letter, and the meeting
  **minutes + action-tracker.** That is the summarisation-and-drafting layer sitting *on top of* the deterministic
  fetch — and it is the whole point.

**1 · Reference & Feed Reader — "సిఫారసు & ఫీడ్ పఠనం / Sipharasu-Pathanam" (EXTRACT).**
Two inputs, one clean output. From the **unstructured VIP letter** (a **typed / digital** forwarded petition — see
scope note) it extracts: **who forwarded it** (MP/MLA/Minister + constituency), **the citizen**, **the exact ask**,
**the apparent subject**, and **the date** that starts the 15-day clock. From the **structured dashboards** (TG-DMS,
Prajavani, MeeSeva) it pulls the current parameter values as-is. Produces a structured reference-sheet and a tidy
feed snapshot.
_Confidence + citation:_ each extracted field tagged to the paragraph of the letter or the dashboard row it came
from. **No Telugu handwritten OCR** — references are handled as **typed / digital** text; handwriting is explicitly
out of scope.

**2 · Pendency & History Checker — "పెండెన్సీ & చరిత్ర పరిశీలన / Pendency-Charitra" (CHECK HISTORY).**
Is this reference a **repeat** of one already logged or answered? Are there **prior references on the same matter or
from the same representative**? And, for the review: what is each department's **pendency history and SLA-breach
trend** (this is the deterministic fetch, assembled per-department). It links the duplicate chain and surfaces the
laggards so nothing is answered twice and nothing overdue is missed.
_Confidence + citation:_ the inward-register / Prajavani / CPGRAMS ID of each linked prior reference, and the source
row of every pendency figure.

**3 · Cross-Department Verifier — "శాఖల సరిపోలిక / Shakhala-Saripolika" (VERIFY RECORDS).**
The heart of the routing wedge. Verifies **which line department actually owns** the ask (Revenue, Housing, MeeSeva,
Welfare, Irrigation, Panchayat Raj, Education, Health…), cross-checks the reference against that department's **own
record** where it is readable, and flags **which items breach SLA** and are **escalation-worthy** for the review.
Catches the classic failure — a housing grievance mis-marked to Revenue — before a cycle is lost.
_Confidence + citation:_ the department mapping with the rule/parameter it rests on, and the exact record checked.

**4 · Review & Reply Drafter — "సమీక్ష & సమాధాన ముసాయిదా / Sameeksha-Musayida" (ROUTE & DRAFT).**
Assembles the clerical output for the officer to sign: the **narrative review-meeting brief** (the prioritised
20-department synthesis, bilingual); the **VIP-reference reply** back to the MP/MLA/Minister (bilingual, formatted
for **DSC** sign-off); the **line-department tasking / escalation letter**; and the **meeting minutes +
action-tracker** with owners and deadlines. **Automation compiles the Word / PDF / Excel; the Collector edits and
signs.**
_Confidence + citation:_ every line traceable to its upstream evidence — the dashboard row, the letter paragraph, the
prior reference.

Net effect: the review brief is written *before* the superintendent's night shift instead of during it; VIP
references are read, de-duplicated and correctly routed inside their 15-day window; SLA breaches surface themselves
for escalation; and the reply, tasking letter and minutes assemble as cited drafts the Collector edits and signs —
**all on the coordination side of the desk.**

---

## 6. Data sources — read-only, real systems

All access is **read-only**, against the state's own systems; the agents **never write** to a government record.

| Source | System | What it provides | Access |
|---|---|---|---|
| Departmental review | **TG-DMS "Collector Dashboard"** (CGG) | 87 parameters × 20 departments; flagship-scheme status | read-only |
| Grievances | **Prajavani-Praja Bhavan** (CGG) | citizen petitions, classification, disposal status, 30-day clock | read-only |
| Service delivery / SLA | **MeeSeva** (CGG/NIC) | service-request status and SLA-breach flags | read-only |
| Land / revenue | **Dharani** (TS) / land records (AP) | land-grievance context behind references | read-only |
| Central grievances | **CPGRAMS / PG Portal** | central references routed to the district, 21-day timeline | read-only |
| VIP correspondence | Collectorate **tappal / inward register**, **eOffice** (NIC) | the forwarded MP/MLA/Minister letters (typed/digital) | read-only |
| AP analogue | **RTGS Core Dashboard / CM Dashboard** (AP) | AP district review MIS across departments | read-only |
| Line-department portals | Housing / Welfare / Irrigation / etc., dynamically linked to TG-DMS | the 65 dynamically-linked parameters at source | read-only |

**Integration counterpart — the crux of the entry strategy.** The monitoring stack this brief sits on is
**government-owned and already built**: **CGG (Centre for Good Governance)** builds and runs TG-DMS, Prajavani and
MeeSeva for Telangana; **NIC** runs CPGRAMS and eOffice; **RTGS** runs the AP dashboards. This is exactly why the
pitch is a **coordination/clerical wedge, not a rebuild**: VirtualAI does **not** modify any of these systems — it
**reads** a scoped, read-only extract and produces drafts an officer signs. The pilot's first dependency is a
**data-access approval from the Collector (with CGG / NIC concurrence)** — governance, not code.

**Sequencing:** where live read-only APIs are not yet exposed, begin with a **nightly read-only extract** into the
Collectorate's own server (the day's dashboard snapshot, the Prajavani/CPGRAMS delta, the inward-reference feed),
then migrate to real-time read-only hooks as CGG/NIC provision them. The pipeline runs on either.

---

## 7. Sovereign by design

- **Where it runs.** Inside the district's perimeter — the **State Data Centre** or the Collectorate server room.
  Nothing egresses. This aligns with the state's own on-prem posture for TG-DMS, Prajavani and RTGS.
- **The model.** An **open-weights LLM served locally by Ollama.** No cloud inference, no vendor telemetry. Model
  updates arrive as vetted files, not API calls.
- **The workflow engine = the file's noting path.** Reference inward → route to line department → follow-up →
  reply/escalation, and feed-gather → review-brief → minutes → action-tracker — each encoded as a workflow with
  **mandatory human sign-off** at the Collector / Additional Collector step. The engine cannot self-route,
  self-escalate, or self-reply.
- **Immutable audit log.** Every extraction, every routing suggestion, every pendency flag, and every officer action
  is logged with its citation — an auditable trail for the Collector, the General Administration Department, and RTI.

The offline argument is not generic here: **the district's VIP correspondence, its candid departmental scorecards,
and its protocol/security and disaster-coordination files** are categories whose leakage carries political and
security consequences. Air-gapped, on-prem inference is the only posture consistent with that duty.

---

## 8. Accountability — "The officer decides. Always."

The Collector is the **single apex decider** of the district, and VirtualAI replaces that officer in **nothing:**

- The Collector decides **which department is failing** and how hard to push it; VirtualAI only **assembles the cited
  pendency picture.** The scorecard is the officer's read, not the machine's verdict.
- The Collector decides **the reply to a VIP reference** and **signs it** (often with **DSC**); VirtualAI only hands
  over a **cited draft** in the correct format and language.
- The Collector decides **the agenda, the minutes and the action-tracker**; VirtualAI only **drafts** them for edit.

Every flag is a **confidence score plus a source citation** the officer opens in one click; a flag the officer
disagrees with is overridden, and the override is logged.

**What VirtualAI will NOT do — stated as a hard boundary, not a disclaimer:**
- it will **not** rate, rank, or score any officer or department — it reports the numbers, the officer judges;
- it will **not** approve, reject, or dispose of any grievance or reference;
- it will **not** send any reply, tasking letter, or escalation on its own — every outbound act is a human's;
- it will **not** decide protocol, security, or disaster-response actions — it drafts and flags, the Collector
  commands;
- it will **not** auto-route a reference to a department without the officer's confirmation.

**Decision-support, strictly coordination, strictly the Collector's desk** — the same accountability contract that
made the Revenue Prajavani copilot acceptable, now extended one desk higher to the officer who already reviewed it.

---

## 9. Projected impact — illustrative, to be *measured* in the pilot

These are **hypotheses we baseline in Week 1–2 and report against measured reality — not claims.** We publish the
before/after from the pilot district, not a brochure number.

- **Review-brief turnaround.** Baseline: hours the superintendent spends assembling the 20-department review brief
  today. Target: a cited draft brief ready before the night shift — *measured in hours saved and in the Collector's
  own rating of the brief's usefulness.*
- **VIP-reference acknowledgement within the 15-day window.** Baseline: the current share of MP/MLA/Minister
  references acknowledged inside the CSMoP 15-day window. Target: fewer missed windows because every reference is
  read, dated and routed on intake — *measured against the inward register.*
- **Correct first-routing.** Baseline: the rate at which references are mis-routed to the wrong line department
  today. Target: fewer mis-routes and the lost cycles they cause — *measured against a ground-truth sample.*
- **Duplicate detection.** Baseline: repeat references answered twice or chased twice today. Target: the History
  Checker links the duplicate chain — *measured as duplicates caught vs a manual audit.*
- **Minutes & action-tracker latency.** Baseline: days between a review meeting and its circulated minutes today.
  Target: a draft minutes + action-tracker ready the same day — *measured in days.*

We commit to the number the pilot produces. If a hypothesis doesn't hold, that is in the report too.

---

## 10. The 12-week pilot

Bounded to **one Collectorate** — ideally the **existing Prajavani-copilot sponsor district**, so the pitch lands on
a desk that has already seen the product work — read-only throughout, nowhere near field execution.

| Weeks | Phase | Outcome |
|---|---|---|
| **1–2** | Access + baseline | Collector's read-only data-access approval (CGG / NIC concurrence); nightly extract into the Collectorate server; **measure current review-brief turnaround / VIP-acknowledgement-within-15-days / mis-routing / minutes-latency baseline** |
| **3–6** | Build | Stand up the four agents on the read-only extract; tune the 20-department summarisation, the VIP-letter extraction, and the department-routing map against real, already-processed references |
| **7–10** | **Shadow mode** | AI produces the review brief / reference routing / draft replies in parallel; the coordination section works as usual; **measure agreement** vs officer + a manual audit; **no live effect** |
| **11–12** | Supervised live | Coordination staff use the cited drafts; the Collector signs; **report against the Week 1–2 baseline**; go/no-go for wider rollout across the district and to neighbouring Collectorates |

Scope discipline: **no** Telugu handwritten OCR (typed/digital references only); **no** image generation; **no**
cloud-as-offline; **no** officer/department scoring, grievance disposal, or auto-sent replies — **ever**. One
Collectorate, the coordination desk, to start.

---

## 11. Bilingual by default — Telugu / English

The Collectorate works in English and Telugu; the citizen and often the representative read Telugu. Every
coordination surface is bilingual:

- **Review-brief and dashboard labels** in Telugu + English: **సమీక్ష (Review)**, **పెండెన్సీ (Pendency)**,
  **గడువు మీరిన (SLA-breached)**, **శాఖ (Department)**, **చర్యల నివేదిక (Action-tracker)**, **సిఫారసు (Reference)**,
  **గడువు (Deadline)**.
- **VIP-reference replies and citizen intimations** — *"మీ సిఫారసు అందింది; సంబంధిత శాఖకు పంపబడింది — 15 రోజుల్లో
  సమాధానం"* ("your reference is received and routed to the concerned department — reply within 15 days") — drafted in
  plain Telugu with an English gloss, so both the representative and the citizen read it without a translator.
- **Meeting minutes and tasking letters** generated bilingually, matching the terminology already live on TG-DMS,
  Prajavani and the RDO-Monday channel — nothing in the UI is a neologism to Collectorate staff.

Everything the citizen and the representative see stays **traceable, in their own language, and signed by a human
officer** — and every coordination decision remains, wholly and only, the Collector's.

---

## Sources (public)

**The review surface — TG-DMS "Collector Dashboard" (Telangana)**
- Centre for Good Governance — Telangana State District Monitoring System (TG-DMS): 87 parameters from 20 departments, 22 directly captured + 65 dynamically linked, launched 25 Oct 2017 at Rangareddy Collectorate — https://www.cgg.gov.in/it_project/telangana-state-district-monitoring-system/

**Grievance volume & the coordination load (the Problem)**
- Centre for Good Governance — Prajavani-Praja Bhavan, effective Grievance Redressal System — https://www.cgg.gov.in/it_project/prajavani-praja-bhavan-effective-grievance-redressal-system-2/
- Prajavani — Centralized Public Grievance Redress & Monitoring System, Telangana (30-day disposal), National Government Services Portal — https://services.india.gov.in/service/detail/prajavani-service-centralized-public-grievance-redress-and-monitoring-system-telangana
- Prajavani figures (82,955 petitions / 43,272 grievances / 27,215 resolved / 16,057 pending as of 9 Dec 2024; 91,313 by 25 Feb 2025), The Hans India — https://www.thehansindia.com/telangana/prajavani-in-tg-now-at-grassroots-level-1070781
- Prajavani at revenue-division level every Monday, Siasat — https://www.siasat.com/telangana-to-hold-prajavani-program-at-revenue-division-level-every-monday-3462715/
- Praja Palana: 70 lakh of 1.3 crore applications were Dharani/land grievances, Deccan Chronicle — https://www.deccanchronicle.com/southern-states/telangana/telangana-70-lakh-of-13-crore-praja-palana-plaints-on-dharani-errors-1812757
- Praja Palana review: 3,49,514 grievance-resolution applications, 1,79,143 addressed (Cabinet sub-committee), Prokerala — https://www.prokerala.com/news/articles/a1496359.html

**VIP / MP-MLA references — the 15-day discipline (CSMoP / DoPT)**
- PIB — Timely acknowledgement and responses to MP correspondence under CSMoP (acknowledge within 15 days, reply within the next 15) — https://www.pib.gov.in/PressReleasePage.aspx?PRID=2100784
- DoPT — Consolidated Guidelines on official dealings between the Administration and Members of Parliament and State Legislatures — https://www.gconnect.in/orders-in-brief/conduct-rules/official-dealings-administration-members-parliament-state-legislatures.html
- Central Secretariat Manual of Office Procedure (CSMOP), 13th edition, DARPG — https://darpg.gov.in/sites/default/files/CSMOP-13_1_0.pdf
- DARPG — Compilation of Guidelines for Redress of Public Grievances — https://darpg.gov.in/sites/default/files/Guidelines_PG_Redress.pdf

**National grievance benchmark — CPGRAMS**
- DARPG — CPGRAMS Monthly Report, States/UTs (November 2024) — https://darpg.gov.in/sites/default/files/2024-11-01-state.pdf
- Streamlining Grievance Redressal — a year of progress on CPGRAMS (timeline cut 30→21 days, Aug 2024 guidelines), DevDiscourse — https://www.devdiscourse.com/article/law-order/3794641-streamlining-grievance-redressal-a-year-of-progress-on-cpgrams

**Andhra Pradesh analogue — Real Time Governance Society (RTGS)**
- Real Time Governance Society — CM/Core Dashboard, 33+ departments, 13 district centres + 1 state centre (formed 6 Sept 2017), Wikipedia — https://en.wikipedia.org/wiki/Real_Time_Governance_Society
- RTGS — Real Time Governance State Center (official) — https://rtgs.ap.gov.in/

**Statutory basis of the Collector's coordinating authority**
- The Disaster Management Act, 2005 — Section 25 (District Collector as Chairperson, DDMA) and Section 30 (DDMA as district planning/coordinating/implementing body), NDMA — https://ndmindia.mha.gov.in/ndmi/images/The%20Disaster%20Management%20Act,%202005.pdf
- Andhra Pradesh Board of Revenue Standing Orders (BSO) — the Collector as Head of District administration — https://www.latestlaws.com/bare-acts/state-acts-rules/andhra-pradesh-state-laws/andhra-pradesh-board-of-revenue-standing-orders-collection-of-revenue/
- Department of Revenue, Government of AP (CCLA) — district administration & Collector's role — https://ccla.ap.gov.in/CCLA/Website/DepartmentProfile.aspx

_Note on figures: Telangana Prajavani counts (82,955 / 43,272 / 27,215 / 16,057; 91,313) are as reported by The Hans
India on the dates stated and reflect Praja Bhavan's own running totals, not a fixed annual figure; the Praja Palana
"~1.3 crore / ~70 lakh Dharani" figures are the state's one-time December-outreach totals, cited as an illustration
of the coordination tail, not a steady-state monthly load. The "87 parameters × 20 departments" and the launch date
are CGG's own published description of TG-DMS. The 15-day acknowledgement / 15-day reply discipline is the CSMoP /
DoPT rule for correspondence from Members of Parliament and State Legislatures, applied by analogy to the district's
MP/MLA/Minister references._
