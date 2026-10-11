# Revenue — Land Mutation & Record-of-Rights (ROR) Correction
### VirtualAI Department Briefing · Revenue / Collectorate cluster (TS & AP)

> _Wave-1 deep-dive of shortlist item #1 (score 19/20). This is the **closest sibling** to the already-built
> Prajavani grievance copilot — same Collector sponsor, same EXTRACT → CHECK → VERIFY → ROUTE & DRAFT pipeline,
> same on-prem stack — but a **distinct** file: land mutation and Record-of-Rights correction, not general
> grievances. Land is the highest-sovereignty, most litigation- and fraud-prone citizen dataset the department
> holds. Every candidate here runs on **already-digital registries** (Dharani/Bhu Bharati, Webland, MeeBhoomi),
> so there is **no Telugu handwritten OCR** — the AI reads structured records and typed/PDF deeds only._
>
> _భూమి రికార్డులు · పట్టాదారు పాస్‌పుస్తకం · మ్యుటేషన్ (దాఖిల్ ఖారిజ్) · రికార్డ్ ఆఫ్ రైట్స్ (RoR / 1-B) సవరణ_

---

## 1. Positioning — Sovereign, on-premise, officer-led

VirtualAI is an **offline, on-premise** decision-support platform. It runs a **private open-weights LLM via
Ollama** inside the department's own network — on the **State Data Centre** or a Collectorate server room — with
**no cloud AI APIs and no data egress**. Pattadar identities, family succession trees, Aadhaar-seeded
landholdings and prohibited-land politics never leave government infrastructure.

**"Fully offline" is qualified honestly:** full air-gap operation requires the **local LLM** (Ollama +
open-weights model) plus read-only connectors to the department's existing registries. No component calls out to
OpenAI, Google, or any hosted model. The exchange is deliberate: we trade the marginal quality of a frontier
cloud model for **absolute data sovereignty** — the only acceptable trade for land records.

The mental model mirrors the file itself:
- **AI Agent = the subject clerk (VRO / Revenue Inspector / dealing assistant)** — reads the deed, checks the register, drafts the noting.
- **Workflow = the file's noting path** — Tahsildar → RDO → Collector, with human-in-the-loop sign-off at each rung.
- **Automation = the typing & compiling** — the mutation order, the corrected 1-B, the passbook entry, the rejection endorsement.

Every AI output carries a **confidence score** and a **source citation** back to the exact survey number,
register row, or deed clause. **The officer always decides.**

---

## 2. The core recurring process

The department's land wing runs a small number of very high-volume, legally-loaded transactions on the
**Record of Rights (RoR / Form 1-B)** and the **pattadar passbook**:

1. **Mutation on succession / inheritance** (వారసత్వ మ్యుటేషన్) — a pattadar dies; the khata must pass to legal
   heirs. Inputs: **death certificate**, **Family Member / Legal-Heir Certificate (FMC)**, the deceased's
   **existing passbook**. Called **Dakhil Kharij** (దాఖిల్ ఖారిజ్) / name-transfer.
2. **Mutation on sale / gift / partition / court decree** — a registered deed changes ownership; the new owner
   needs a fresh khata and passbook. In Telangana's Dharani/Bhu Bharati model, **mutation is auto-initiated the
   moment the sale-deed is registered** (single-window), then approved by the RDO; in AP, **auto-mutation on
   registration** is live across all 26 districts.
3. **RoR / Pahani-1B correction grievances** — the register itself is wrong: **missing survey numbers**, **wrong
   land classification** (patta shown as assigned/government/endowment), **extent mismatch** (deed acreage ≠
   register acreage), **Part-B / prohibited-property entanglement** blocking any transaction.
4. **Chain-of-title assembly for a survey number** — reconstructing the ownership history across prior mutations,
   sada-bainama (informal-sale) regularisations, sub-divisions and litigation, to answer "who really owns this?"

These four map one-to-one onto the proven pipeline: **EXTRACT** the deed/application → **CHECK HISTORY** (prior
mutations, chain of title, prohibited list) → **VERIFY RECORDS** (deed vs RoR) → **ROUTE & DRAFT** the order.

---

## 3. The problem — pattern-recognition failures, at scale

Land record errors are, at root, **pattern-recognition failures** — a human clerk under a pendency mountain
failing to spot a mismatch, a duplicate, a wrong classification, or the correct correction channel. The public
record shows the cost:

- **66% of all civil suits in India relate to land or property**, and land-related matters are **60–70% of all
  civil litigation** (NCAER / NIPFP). Roughly **25% of Supreme Court cases** involve land, ~30% of those land
  acquisition; the average land-acquisition dispute **pends ~20 years**. Land is India's single largest source
  of litigation, and the register error is usually where it starts. [NIPFP WP-349; ThePrint]
- Telangana's **Dharani** portal — launched 2020 as an integrated records-plus-registration single window —
  accumulated **6.46 lakh pending grievances by December 2023**, with rigid architecture and no proper correction
  path. [The News Minute]
- Dharani offered **33 separate correction modules, each with a ₹1,000 fee** — and **lakhs of applications were
  rejected because applicants (and clerks) picked the wrong module.** Choosing the channel was itself the failure
  point. [The News Minute]
- The **prohibited-property (Part-B) list ballooned from ~20 lakh acres to over 1 crore acres** (of Telangana's
  ~2.5 crore acres). Privately-owned patta land was frozen as "assigned" or "prohibited," blocking sale and
  registration outright; **60,000+ grievances** concern this misclassification alone. Courts had to intervene
  repeatedly — e.g. *S. Mukund Reddy v. State of Telangana* (2024), *G. Sathyanarayana v. State of Telangana*
  (2021). [Assetly; court records]
- **9 lakh+ sada-bainama** (informal-sale) regularisation applications were left pending under Dharani. [The News Minute]
- When **Bhu Bharati** opened village-level **Revenue Sadassulu** (రెవెన్యూ సదస్సులు) in mid-2025, **8.5 lakh+
  applications** poured in to fix long-pending land disputes — a direct measure of the un-cleared backlog. [NewsOnAir, Prasar Bharati]

Each of these is a place where a **second reader that never tires** — cross-checking deed against register,
flagging the mismatch, and naming the correct channel — changes the outcome.

---

## 4. Where the time goes — the current journey & its bottlenecks

A single succession mutation or 1-B correction today travels a slow, manual noting path:

| Stage | Who | What happens | Bottleneck |
|---|---|---|---|
| Intake | MeeSeva / Bhu Bharati counter | Citizen files with death cert + FMC + old passbook, or a correction petition | Wrong module / missing document → later rejection |
| Scrutiny | VRO / Revenue Inspector / dealing clerk | Manually pull the survey number's RoR (1-B), Pahani/Adangal, prior mutations, prohibited list | Register spread across modules; chain-of-title reconstructed by hand |
| Field / history check | Tahsildar office | Verify extent, classification, heirs, encumbrance; check pending litigation (RCCMS) | No single view; duplicates & overlaps missed |
| Decision & drafting | Tahsildar → RDO → Collector | Draft mutation order / correction endorsement / rejection; route by land value | **RDO < ₹5 lakh, Collector ≥ ₹5 lakh** thresholds; hand-typed orders; queue |
| Output | Bhu Bharati / Webland | Update RoR, issue new passbook | Re-keying; transcription error re-enters the register |

The **FMC / legal-heir certificate** alone takes **15–30 days** (MRO route) and a court **succession certificate
3–6 months**; the mutation then queues behind it. Under Dharani, a routine error had **no administrative remedy
at all** — the citizen was pushed to **civil court**, feeding the 66% litigation figure. Bhu Bharati's reform
explicitly **decentralised** this (Tahsildar → RDO → Collector → Land Tribunal), but the **clerical load of
reading, cross-checking and drafting still lands on an overstretched revenue officer.** That clerical layer is
exactly what VirtualAI absorbs.

---

## 5. The solution — four named agents on EXTRACT → CHECK → VERIFY → ROUTE & DRAFT

Four grounded copilots, each producing a **confidence score + source citation**, chained as a human-in-the-loop
workflow. They **support** the decision; they never make it.

**Agent 1 — Field Extractor** (`EXTRACT`) · _the intake clerk_
Reads the registered **sale/gift/partition deed**, the **succession application**, or the **RoR-correction
petition** plus attachments (death certificate, FMC/legal-heir certificate, old passbook, EC). Pulls **survey /
sub-division number, extent, boundaries, pattadar & party names, deed type, consideration, document number**.
Because every source is a **digital registry or typed/registered PDF**, this is structured extraction — **no
handwritten Telugu OCR**. _Output:_ a clean, field-tagged case sheet, each field cited to its document line.

**Agent 2 — History & Duplicate Checker** (`CHECK HISTORY`) · _the register memory_
Assembles the **chain of title** for the survey number: prior mutations, sada-bainama regularisations,
sub-divisions, prior grievances/appeals, and **pending revenue-court or civil litigation**. Flags **duplicate or
overlapping claims** and checks the **prohibited-property (Part-B) list**. _Output:_ a chronological title
history with duplicate/litigation risk flags, each event cited to its register entry.

**Agent 3 — Records Verifier** (`VERIFY RECORDS`) · _the Bhu Bharati / Webland cross-checker_
Cross-checks the extracted deed against the live **RoR (1-B) / Pahani-Adangal**: **extent match** (deed vs
register), **classification** (patta vs assigned vs prohibited vs endowment), **survey-number existence**,
**pattadar name match**, and **encumbrance**. Surfaces the four canonical error patterns — **missing survey
number, wrong classification, extent mismatch, Part-B entanglement**. _Output:_ a verification verdict with a
mismatch list and a confidence score per check.

**Agent 4 — Router & Endorsement Drafter** (`ROUTE & DRAFT`) · _the noting clerk_
Names the **correct channel** — the right mutation type, the right correction category, and the right **appeal
tier by land value** (Tahsildar → RDO **< ₹5 lakh** → Collector **≥ ₹5 lakh** → Land Tribunal, per Bhu Bharati's
timelines: RDO within 60 days, Collector within a further 30). Then drafts the **mutation order, corrected 1-B
endorsement, requisition-for-missing-documents, or reasoned rejection note**, each with a **risk flag**. This
kills the single biggest Dharani failure — **applicants picking the wrong module and being rejected.** _Output:_
a ready-to-sign draft in the officer's queue.

The workflow **pauses for officer sign-off** at Tahsildar / RDO / Collector as the file's value dictates
(mirroring the department's own hierarchy). The Automation layer then **compiles** the approved order into the
register format for the officer to push.

---

## 6. Data sources — read-only, real systems

VirtualAI reads the department's **existing** registries; it writes nothing back autonomously. Integration is via
the state's own e-governance builders — **CGG (Centre for Good Governance)** for Telangana, **NIC / APCFSS** for
Andhra Pradesh — using a **nightly extract into a read-only mirror, then live read-only APIs** where available.

**Telangana**
- **Bhu Bharati** portal (RoR / 1-B, pattadar passbook, 6 modules) — the current system of record, replacing Dharani.
- **Dharani** legacy data (prohibited-property / Part-B list, prior mutations, historical RoR) — for chain-of-title.
- **Registration (IGRS / CARD)** — registered deeds, Encumbrance Certificate (EC), document numbers; the single-window mutation trigger.
- **MeeSeva** — FMC / legal-heir certificate and death-certificate records.
- **RCCMS** (Revenue Courts) — pending appeals / land-litigation flags.

**Andhra Pradesh**
- **Webland (CCLA)** — authoritative backend land-records database, Chief Commissioner of Land Administration, Mangalagiri.
- **MeeBhoomi** (మీ భూమి) — citizen RoR: **Adangal** (crop/land-use) and **1-B** (title), passbook, mutation status; ~4.42 crore records.
- **Auto-mutation-on-registration** feed — live across all 26 districts.

**Integration counterparts:** CGG (TS) and NIC/APCFSS (AP) own the connectors; VirtualAI consumes read-only.
Nothing is written to a register without an **officer's authenticated action**.

---

## 7. Sovereign by design

- **Where it runs:** the **Telangana / AP State Data Centre**, or a Collectorate server — inside the government
  perimeter, behind the department firewall.
- **The model:** an **open-weights LLM served locally by Ollama**. No cloud inference; the weights sit on state
  disk. Model updates arrive as vetted files, not API calls.
- **The workflow engine:** the noting path (Tahsildar → RDO → Collector → Tribunal) encoded as a human-in-the-loop
  workflow, with configurable value thresholds matching the Bhu Bharati Act.
- **The audit log:** every extraction, every cross-check, every draft and every officer decision written to an
  **immutable, timestamped audit trail** — reviewable by vigilance, CAG, or a court.

**Why sovereignty is non-negotiable here:** land ownership is the **most litigation- and fraud-prone,
politically sensitive citizen dataset** the state holds — Aadhaar-seeded pattadar identities, family succession,
prohibited-land classifications with direct market and political value. A single leak or tamper is a land scam.
This dataset cannot touch a cloud model. VirtualAI is built so it never has to.

---

## 8. Accountability — "The officer decides. Always."

> **అధికారే నిర్ణయిస్తారు. ఎప్పుడూ.** — _The officer decides. Always._

VirtualAI is **decision-support, not decision-making.** It reads, cross-checks, and drafts; the **Tahsildar, RDO
or Collector signs** — with a **Digital Signature Certificate (DSC)** where the workflow requires it, exactly as
in the Prajavani exemplar. The AI's job is to make the officer **faster and better-informed**, never to
pre-empt them:

- Every claim is **cited** to a survey number, register row, or deed clause the officer can open.
- Every output carries a **confidence score**; low-confidence items are flagged **for human attention**, not
  auto-passed.
- The officer can **override any draft**, and the override is logged.
- The AI **never writes to the RoR** — it prepares; the officer commits.

This is the same accountability contract that made the Revenue Prajavani copilot acceptable to the Collectorate,
carried intact onto a higher-stakes file.

---

## 9. Projected impact — honest and illustrative

> _These figures are **illustrative, not promised.** We **baseline every metric in the pilot's first two weeks**
> and then report VirtualAI against **measured reality, not marketing claims.** The department's own numbers, not
> ours, decide whether the pilot succeeds._

Plausible, pilot-testable directions of impact (to be confirmed against baseline):

- **Faster scrutiny:** the manual pull-and-cross-check of RoR, Pahani, prior mutations and the prohibited list —
  minutes-to-hours per file — compressed to a **pre-assembled, cited case sheet** waiting for the officer.
- **Fewer wrong-channel rejections:** by **naming the correct correction module / mutation type / appeal tier**,
  the agent attacks the exact Dharani failure that rejected *lakhs* of applications.
- **Earlier error-catching:** extent mismatch, wrong classification and Part-B entanglement flagged **at intake**,
  before a file travels the full noting path and comes back.
- **Litigation deflected:** cleaner administrative correction (now possible under Bhu Bharati's decentralised
  tiers) that resolves at Tahsildar/RDO/Collector instead of feeding the **66%-of-civil-litigation** land docket.
- **Backlog throughput:** measurable movement on the kind of queue that stood at **6.46 lakh grievances** and drew
  **8.5 lakh Revenue-Sadassulu applications**.

We commit to the **method**, not a headline percentage: measure the baseline, deploy, re-measure, report the delta.

---

## 10. The 12-week pilot

A bounded, low-risk proof on a single revenue division, read-only throughout.

- **Weeks 1–2 — Baseline & access.** Stand up VirtualAI on a State Data Centre / Collectorate node with the local
  Ollama model. With CGG/NIC, open **read-only** extracts of Bhu Bharati / Webland RoR, registration EC, MeeSeva
  FMC. **Measure current cycle-time, rejection rate and backlog** for succession mutation and 1-B correction.
- **Weeks 3–5 — Extract + Verify.** Deploy Agents 1 & 3 (Field Extractor, Records Verifier) on **historical,
  already-decided** files; tune extent/classification/name-match against known outcomes.
- **Weeks 6–8 — History + Route/Draft.** Add Agents 2 & 4 (chain-of-title, router/drafter). Wire the
  Tahsildar → RDO → Collector workflow with the **₹5 lakh** threshold and Bhu Bharati timelines. Officers review
  drafts in a **shadow queue** — AI drafts, human decides, nothing auto-commits.
- **Weeks 9–11 — Supervised live.** A named set of officers use the copilot on **live** succession-mutation and
  RoR-correction files, signing every output. Confidence-score calibration and audit-log review with vigilance.
- **Week 12 — Report against baseline.** Present measured deltas (cycle-time, wrong-channel rejections,
  errors-caught-at-intake) vs the Week-1 baseline. Go / no-go on expansion to registration pre-scrutiny (22A/EC)
  and Collectorate coordination — the natural next files.

**Success criteria** are set **with** the department in Week 1 and judged on **its** numbers.

---

## 11. Bilingual touches — Telugu / English

The copilot speaks the register's own language. Interface, drafts and citations render in **Telugu and English**,
using the exact terms officers and citizens use:

- **భూమి** (land) · **సర్వే నంబరు** (survey number) · **విస్తీర్ణం** (extent) · **ఖాతా** (khata)
- **పట్టాదారు పాస్‌పుస్తకం** (pattadar passbook) · **రికార్డ్ ఆఫ్ రైట్స్ / 1-B** · **పహాణీ / అడంగల్** (Pahani / Adangal)
- **మ్యుటేషన్ · దాఖిల్ ఖారిజ్** (mutation · dakhil kharij) · **వారసత్వం** (succession) · **సదా బైనామా** (sada bainama)
- **నిషేధిత భూములు / పార్ట్-B** (prohibited lands / Part-B) · **మరణ ధ్రువీకరణ పత్రం** (death certificate) · **వారసుల ధ్రువీకరణ పత్రం** (legal-heir / FMC)
- **తహసీల్దార్ · ఆర్డీవో · కలెక్టర్ · భూ ట్రిబ్యునల్** (Tahsildar · RDO · Collector · Land Tribunal)

Draft orders generate in the **official bilingual format** the register already uses; citizen-facing endorsements
carry a **plain-Telugu summary** of what was decided and why. Echoing the state's own promise —
**మీ భూమి, మీ హక్కు** (_your land, your right_) — every decision stays **traceable, in the citizen's language, and
signed by a human officer.**

---

## Sources

- The Telangana Bhu Bharati (Record of Rights in Land) Act, 2024 — **Act 1 of 2025** (primary statute, PRS India): https://prsindia.org/files/bills_acts/acts_states/telangana/2025/Act1of2025TS.pdf
- Bhu Bharati vs Dharani — grievance redressal, decentralisation (The News Minute): https://www.thenewsminute.com/telangana/how-is-bhu-bharati-telanganas-new-land-records-system-different-from-dharani
- Two-tier / multi-tier appeal system, RDO ₹5 lakh threshold, 60/30-day timelines (The Hans India): https://www.thehansindia.com/news/cities/hyderabad/2-tier-appeal-system-in-bhu-bharati-for-resolving-farmers-grievances-966606
- 8.5 lakh+ Revenue Sadassulu applications (NewsOnAir / Prasar Bharati, official): https://www.newsonair.gov.in/over-8-5-lakh-applications-received-during-telanganas-revenue-sadassulu-under-bhu-bharati-act
- Bhu Bharati land-record errors, Part-B misclassification, ~1 crore acres, court cases (Assetly): https://assetlyhq.com/blog/bhu-bharati-land-record-errors-check-correct-telangana/
- Characterising land & property litigation — 66% / pendency (NIPFP Working Paper 349/2021): https://nipfp.org.in/media/medialibrary/2022/06/WP_349_2021.pdf
- Land disputes clog courts — 60–70% civil litigation (ThePrint): https://theprint.in/opinion/indian-courts-clogged-with-land-disputes-because-laws-keep-conflicting-each-other/254033/
- Bhu Bharati — Application for Succession (official user manual): https://bhubharati.telangana.gov.in/assets/images/userManuals/Application_for_Succession.pdf
- Telangana Registration — mutation procedure (official): https://registration.telangana.gov.in/mutationProcedure.htm
- Webland AP / CCLA land records: https://www.squareyards.com/blog/webland-ap-land-records-andhra-pradesh-lrid
- MeeBhoomi AP — Adangal & 1-B, auto-mutation, ~4.42 cr records (Landeed): https://web.landeed.com/andhra-pradesh/adangal
- Centre for Good Governance (CGG), Telangana e-gov build partner: https://www.cgg.gov.in/
- Dharani → Bhu Bharati strategic shift (Landeed): https://www.landeed.com/post/dharani-to-bhu-bharati---a-strategic-shift

**Statutes referenced:** Telangana Bhu Bharati (Record of Rights in Land) Act, 2024 (Act 1 of 2025) · Telangana
Rights in Land and Pattadar Pass Books Act, 2020 (repealed) · Andhra Pradesh Rights in Land and Pattadar Pass
Books Act, 1971 · AP/Telangana Survey and Boundaries Act, 1923 · Registration Act, 1908 (incl. Sec. 22A
prohibited-property).
