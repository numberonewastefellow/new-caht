# High Courts — Registry & Case Management
### Telangana High Court + Andhra Pradesh High Court · e-Filing scrutiny · Cause-list · Certified copies · Indexing & neutral citation

> _Judiciary cluster. The **highest-prestige, hardest-entry** file in the whole government map — and therefore
> pitched as the narrowest possible wedge. VirtualAI touches **only the Registry**: the clerical assembly line
> between a filing and the Bench — **scrutiny, objections, listing, copies, indexing.** It never touches the
> Bench's reasoning, never reads the merits, never drafts a judgment, never predicts an outcome. Same proven
> pipeline as the Revenue exemplars — **EXTRACT → CHECK HISTORY → VERIFY RECORDS → ROUTE & DRAFT**, every output
> with a confidence score and a source citation — but pointed at the **Registrar's desk, not the Judge's.**_
>
> _Product mapping, judiciary edition: **AI Agent = the scrutiny clerk / Stamp Reporter** who reads the filing and
> runs the checklist · **Workflow = the file's registry path** — e-filing → scrutiny → objections → registration →
> numbering → listing → (post-judgment) copying & indexing · **Automation = the typing** of the defect memo, the
> office note, the cause-list entry, the certified-copy index._
>
> _రిజిస్ట్రీ · లోపాల నివేదిక (అభ్యంతరాలు) · విచారణ జాబితా (కాజ్-లిస్ట్) · ధ్రువీకృత ప్రతులు · తీర్పుల సూచిక & న్యూట్రల్ సైటేషన్_

---

## 1. Positioning — offline, air-gapped, sovereign, and strictly clerical

VirtualAI runs **entirely inside government infrastructure** — the State Data Centre or the High Court's own server
room — on a **private open-weights LLM served locally via Ollama.** No filing, no litigant PII, no pre-pronouncement
draft, and no in-camera record ever leaves the court's perimeter. There are **no cloud AI API calls.**

Two reasons this department is, at once, the **strongest air-gap case** and the one demanding the **most disciplined
scope:**

- **The data is the most sensitive the state holds.** Pre-pronouncement **draft judgments** under embargo;
  **in-camera, POCSO, matrimonial, juvenile and sexual-offence** records where the litigant's or victim's identity is
  protected *by statute*; sealed-cover material; the entire litigation stream of a state. The single category of data
  that must **never** touch a third-party model is exactly what a court registry processes all day. A cloud AI vendor
  silently ingesting the nation's un-pronounced judgments is not a privacy risk — it is a **sovereignty breach.**
- **The Telangana High Court has *already made this exact choice.*** Its ICT stack is deliberately **Free and Open
  Source** — Ubuntu Linux, LibreOffice, PDFsam, Jitsi Meet, PostgreSQL, PHP/Java — precisely to reduce dependence on
  proprietary, telemetry-carrying software (e-Committee, Supreme Court of India). VirtualAI is not asking the court to
  change its posture; it is **the AI layer that respects the posture the court already adopted** — on-prem, open,
  auditable.

**Honesty qualifier:** "fully offline" is true **because the model weights are local.** A hosted model — however it
is branded — would break the guarantee. We do not relabel a cloud call as "offline." On-prem inference on open
weights, full stop.

**Scope qualifier, stated up front because it is the whole pitch:** VirtualAI is **registry/clerical
decision-support only.** It does **not** adjudicate, does **not** read or weigh the merits of a case, does **not**
draft judgments or orders, does **not** predict or recommend outcomes, and does **not** assist the Bench's judicial
reasoning. It helps the **Registry** do the Registry's own already-clerical work — scrutiny, listing, indexing,
copies — faster and more consistently. The Judge's function is untouched, by design.

---

## 2. The core recurring process — what the Registry actually does

Between the moment a case is e-filed and the moment it reaches a Judge, and again after judgment, the **Registry**
runs a fixed, high-volume, checklist-driven pipeline. None of it is adjudication; all of it is clerical scrutiny and
compilation:

1. **e-Filing scrutiny / defect reporting** (the core job). Every petition, appeal or SLP filed through the court's
   e-filing portal (`aphc.gov.in/efiling.php`, `tshc.gov.in`) is examined by the **Stamp Reporter / scrutiny clerk**
   against a checklist: correct and sufficient **court fee**; **index** and **pagination**; **cause-title** format;
   **vakalatnama** with the **welfare-fund / advocates'-welfare stamp**; **certified copy of the impugned order**
   annexed; **limitation** met; affidavit sworn; annexure legibility. Anything wrong → the case is put **"under
   objection"** and a **defect sheet** goes back to the advocate to cure before it can be numbered and listed.
2. **Registration & numbering.** Once defect-free, the filing is registered and assigned a case number and CNR.
3. **Cause-list preparation.** Numbered, ready matters are compiled into the daily **cause list** by category and
   roster — and **connected / analogous matters** (same parties, same impugned order) are tagged to be listed
   together.
4. **Certified-copy issuance.** After orders and judgments, the **copying (CD) section** issues **certified copies**
   to litigants on application.
5. **Post-judgment indexing.** For **already-pronounced, public** judgments, the reporting/indexing section prepares
   the **headnote, catchwords and index** and assigns the **neutral citation** (e.g. the `YYYY INSC n` family the
   Supreme Court launched in 2023, now being mirrored by High Courts) — a librarian's task, done **after** the Bench
   has spoken.

This runs **hundreds of thousands of times a year, per High Court.** It is the throat through which every one of the
**~2.46 lakh** cases pending at the AP High Court and **~2.45 lakh** at the Telangana High Court had to pass — and
through which every new filing still must.

---

## 3. The problem — registry friction as pattern-recognition failure, at scale

The backlog is enormous and old, and while the **Bench** clears cases, the **Registry** is where filings stall,
bounce and wait before a Judge ever sees them:

- **~60.6 lakh cases pending across the High Courts** (60,62,953 as of 14 July 2024, Law Ministry / NJDG) — with
  **Allahabad alone near 10 lakh.** Roughly **half of all High Court cases are more than five years old, and a
  quarter more than ten** (Data For India, on NJDG data); **71,204 cases have been pending over 30 years**, and
  **1,063 over 50 years** (Ministry of Law & Justice). The pendency is not just large — it is **aged**, and age
  compounds every registry lookup (connected matters, prior filings, chain of appeals) that a clerk must do by hand.
- **The e-filing "defect battle" is real, and it is a pattern-matching failure.** The clearest public illustration is
  the **Supreme Court's own Registry**: over **1,000 petitions filed between 2014–2020** were sent back to advocates
  to cure filing defects and were **threatened with dismissal** if not cured within the refiling window — the apex
  registry's standard cure period being **28 days**, extendable only on a condonation application (LiveLaw). The same
  mechanics operate at every High Court: a filing goes **under objection**, the advocate must cure within the days the
  registry sets (commonly **7–15**), and until every defect clears the matter **is not listed at all.** Multi-round
  scrutiny — court-fee short by a few rupees, a missing welfare stamp, a mis-paginated annexure — routinely costs a
  case **weeks before it is ever a case.**
- **Certified copies stall.** The rule-of-thumb is **3–7 working days**, but "in some courts, because of pendency, it
  might take around 30 days" — and because delay in obtaining a certified copy is **excluded under Section 12 of the
  Limitation Act**, every slow copy is a downstream appeal delayed. (The Telangana High Court recognised exactly this
  and, back in 2019, launched **CD-section software** to issue certified documents "instantaneously or at the
  earliest" from scanned digital case files — proof the department itself treats copy-turnaround as a problem worth
  automating.)
- **Every one of these is a checklist match a tired clerk does by hand.** Is the court fee correct for this valuation?
  Is the welfare stamp on the vakalatnama? Is the impugned order's certified copy annexed? Is this the third matter
  today between the same parties on the same order — i.e. a connected case that should be tagged? These are precisely
  the tasks humans do inconsistently at volume and machines do reliably. **That gap — in the Registry, not the
  courtroom — is the product.**

---

## 4. Where the time goes — the current registry journey and its bottlenecks

| Stage | Who (Registry) | What happens | Bottleneck |
|---|---|---|---|
| e-Filing intake | Advocate → e-filing portal | Petition uploaded (typed PDFs), court fee paid, vakalatnama & annexures attached | Uploaded with defects the filer can't see; feedback only after scrutiny |
| **Scrutiny / defect report** | **Stamp Reporter / scrutiny clerk** | Manual checklist: court fee, index, pagination, cause-title, welfare stamp, certified copy of impugned order, limitation, affidavit | **The core bottleneck** — slow, inconsistent between clerks; one missed line = another round |
| Objection & cure | Registry ↔ advocate | Defect sheet issued; advocate re-files; re-scrutinised | Multi-round ping-pong; **7–15 day** cure windows; matter **not listed** until clear |
| Registration & numbering | Registry | Case numbered, CNR assigned, entered in CIS | Re-keying; connected matters not yet linked |
| Listing / cause list | Court officer / listing branch | Compile daily cause list by roster; tag connected/analogous matters | Connected-matter chaining done from memory; misses cause avoidable adjournments |
| Certified copies | Copying (CD) section | Issue certified copies on application after orders/judgment | Manual assembly & indexing; **up to ~30 days** under load |
| Post-judgment indexing | Reporting / ILR section | Headnote, catchwords, index, **neutral-citation** tag for a **pronounced** judgment | Manual editorial work; backlog delays reportability and searchability |

The time is **not** in the Judge deciding — that is the Bench's protected function and stays exactly where it is. The
time is in the **clerical layer around the decision**: reading the filing against a checklist, chasing defects,
compiling the list, cutting the copy, indexing the judgment. Notably, the **Telangana High Court already runs OCR** to
convert scanned **typed** case files into searchable text and to extract **petitioner names and prayer text**
(e-Committee) — so the department has itself established that structured extraction from its own typed documents is
appropriate and useful. VirtualAI extends that established practice into a full scrutiny-and-compilation assistant.

---

## 5. The solution — four named agents on the proven pipeline (Registry only)

Four decision-**support** agents, each returning a **confidence score + a citation to the exact source** (the page of
the filing, the rule number, the CNR of the connected matter). None of them registers, objects, lists, or issues
anything on its own: they assemble the clerical work; **the Registrar / Stamp Reporter reviews and signs.** Every one
of them stops at the courtroom door — none reads the merits, none touches the Bench.

**1 · Filing Reader — "దాఖలు పఠనం / Daakhalu-Pathanam" (EXTRACT).**
Parses the e-filed bundle — **already-typed PDFs**, exactly the material the court's own OCR pipeline already handles —
into structured fields: **cause-title, parties, category, prayer, court-fee paid, index, page count, vakalatnama +
welfare stamp, list of annexures, limitation dates, affidavit.** Produces a clean filing sheet.
_Confidence + citation:_ each field tagged to its page/line in the filing. **No Telugu handwritten OCR** — these are
typed e-filings and scanned typed documents; handwriting is explicitly out of scope.

**2 · Connected-Matter & Citation Checker — "అనుబంధ వ్యవహారాలు / Anubandha-Vyavaharam" (CHECK HISTORY).**
For **listing and scrutiny** purposes only: finds **connected / analogous matters** (same parties, same impugned
order, transfer/tag candidates) and prior filings by the same litigant, so the listing branch can chain them; and
**verifies the citations in the filing** are real and correctly formatted (neutral-citation `YYYY INSC n` / HC
equivalents, reporter cites). It **does not** opine on which precedent governs, does **not** research the merits, and
does **not** advise the Bench — it flags *connections and citation hygiene* the registry needs for listing.
_Confidence + citation:_ the CNR / case number of each connected matter and the exact citation string checked.

**3 · Defect & Compliance Verifier — "లోపాల పరిశీలన / Lopala-Parisheelana" (VERIFY RECORDS).**
The heart of the wedge. Runs the extracted filing against the **e-filing rules and scrutiny checklist** (Model
e-Filing Rules 2021 as adopted; the HC's Appellate-Side / e-filing rules; **CPC Order IV/VI/VII**; the court-fee
schedule): is the **court fee** correct for the stated valuation; is the **welfare stamp** on the vakalatnama; is the
**certified copy of the impugned order** annexed; are **index/pagination/cause-title** compliant; is **limitation**
met. Emits a **draft defect sheet** — each defect named against the exact rule it violates.
_Confidence + citation:_ the specific rule/Order and the offending page. This is the agent that attacks the
multi-round defect ping-pong directly.

**4 · Registry Drafter — "రిజిస్ట్రీ ముసాయిదా / Registry-Draft" (ROUTE & DRAFT).**
Assembles the clerical output for the officer to sign: the **objection/defect memo** (bilingual) back to the advocate;
the **office note**; the **cause-list entry** routed to the correct roster/category with connected matters tagged; the
**certified-copy cover-and-index** for the copying section; and — for an **already-pronounced, public judgment** — a
**draft headnote, catchwords, index and neutral-citation tag** for the reporting section. **Automation compiles the
Word/PDF; the Registrar edits and signs.**
_Confidence + citation:_ every line traceable to the upstream evidence. The headnote is an editorial summary of a
judgment the Bench has **already delivered in open court** — indexing, never authoring.

Net effect: the advocate learns of a defect **in one pass instead of three**, the cause list's connected-matter
tagging stops leaking avoidable adjournments, certified copies assemble themselves for the clerk to certify, and
pronounced judgments get indexed and neutral-cited without a reporting backlog — **all on the registry side of the
line.**

---

## 6. Data sources — read-only, real systems

All access is **read-only**, against the court's own systems; the agents **never write** to a record of the court.

| Source | System | What it provides | Access |
|---|---|---|---|
| Case & filing data | **CIS** (eCourts case-management stack, High Court version) | filing, registration, scrutiny status, listing, disposal | read-only |
| e-Filings | **e-Filing portals** — `aphc.gov.in/efiling.php`, `tshc.gov.in` | the typed petition bundle, court fee, annexures, vakalatnama | read-only |
| Pendency & case age | **NJDG / HC-NJDG** (`njdg.ecourts.gov.in`) | pendency, age buckets, category counts, disposal | read-only |
| Process service | **NSTEP** | summons/notice service status (for listing readiness) | read-only |
| Judgments & citations | HC judgment repository + **neutral-citation** index | pronounced, public judgments for indexing/headnoting | read-only |
| Copies & litigant services | **Certified-copy / CD-section software**, **e-Sewa Kendra**, **Justice Clock** | copy applications, litigant-facing status | read-only |

**Integration counterpart — and the crux of the entry strategy.** Unlike Revenue (where CGG/NIC own the registries),
the judiciary stack is governed by the **e-Committee of the Supreme Court of India** and built/run on **NIC's eCourts
platform (CIS)**. This is a nationally-controlled, standardised system — which is exactly why the pitch is a
**registry/clerical wedge, not a rebuild.** Note the version reality precisely: **High Courts run the CIS High-Court
core; the district judiciary is on CIS 3.x with e-Filing 3.0** (AP's district e-Filing v3.0 rollout is dated 2026).
VirtualAI does **not** modify CIS; it **reads** a scoped, read-only extract and produces drafts an officer signs. The
pilot's first dependency is a **data-access approval from the High Court Registrar (with e-Committee/NIC concurrence)**
— governance, not code.

**Sequencing:** where live read-only CIS APIs are not exposed, begin with a **nightly read-only extract** into the
court's own server (filing metadata, scrutiny status, cause-list feed, pronounced-judgment corpus), then migrate to
real-time read-only hooks as NIC provisions them. The pipeline runs on either.

---

## 7. Sovereign by design

- **Where it runs.** Inside the court's perimeter — the **State Data Centre** or the High Court server room. Nothing
  egresses. This aligns with the Telangana High Court's own **FOSS, on-prem** ICT posture.
- **The model.** An **open-weights LLM served locally by Ollama.** No cloud inference, no vendor telemetry. Model
  updates arrive as vetted files, not API calls.
- **The workflow engine = the registry path.** e-Filing → scrutiny → objection/cure → registration → listing →
  copying/indexing, encoded as a workflow with **mandatory human sign-off** at the Stamp Reporter / Registrar step.
  The engine cannot self-approve, self-object, or self-list.
- **Immutable audit log.** Every extraction, every checklist match, every connected-matter flag, and every officer
  action is logged with its citation — an auditable trail for the Registrar, the High Court's Computer Committee, and
  RTI.

The offline argument is not generic here: **draft judgments under embargo, in-camera/POCSO/matrimonial records, and
the litigant PII of an entire state** are categories the law itself shields. Air-gapped, on-prem inference is the only
posture consistent with that duty.

---

## 8. Accountability — the Registrar decides on the file; the Judge decides the case. The AI decides nothing.

This department has **two** deciders, and VirtualAI replaces **neither:**

- On the **registry** side, the **Registrar / Deputy Registrar / Stamp Reporter** decides whether a filing is in
  order, what the defect is, how the matter is listed, and whether a copy issues. VirtualAI hands them a **cited draft
  defect sheet / cause-list entry / copy index** — they review, correct, and sign. Every flag is a **confidence score
  plus a source citation** the officer opens in one click; a flag they disagree with is overridden, and the override
  is logged.
- On the **judicial** side, the **Judge** decides the case. VirtualAI does **not** cross this line at all.

**What VirtualAI will NOT do — stated as a hard boundary, not a disclaimer:**
- it will **not** read, weigh, or summarise the **merits** of a pending case;
- it will **not** draft **judgments or orders**, and will **not** suggest how a matter should be decided;
- it will **not** **predict outcomes**, score parties, or rank a Judge's options;
- it will **not** auto-reject, auto-register, or auto-list — every registry action is a human's;
- it will **not** touch draft/un-pronounced judgments except where a Judge's own staff explicitly, optionally use it
  as an offline typing/formatting aid inside the air-gap — never as a drafter of reasoning.

**Decision-support, strictly clerical, strictly registry** — the same accountability contract that made the Revenue
Prajavani copilot acceptable, held to an even tighter line because the institution demands it.

---

## 9. Projected impact — illustrative, to be *measured* in the pilot

These are **hypotheses we baseline in Week 1–2 and report against measured reality — not claims.** We publish the
before/after from the pilot registry sections, not a brochure number.

- **First-pass defect detection.** Baseline: the current share of filings that bounce **more than once** through
  scrutiny at the pilot HC. Target: the Verifier surfaces materially every checklist defect on the **first** pass, so
  the advocate cures in one round — *measured as agreement with a manual re-scrutiny of the same filings.*
- **Scrutiny turnaround.** Baseline: minutes-per-filing for the manual court-fee + index + vakalatnama + limitation
  check. Target: a cited draft defect sheet ready before the Stamp Reporter opens the file — *measured, per section.*
- **Connected-matter capture.** Baseline: the rate at which connected/analogous matters are *missed* at listing today.
  Target: fewer missed links, and the avoidable adjournments they cause — *measured against a ground-truth sample.*
- **Certified-copy turnaround.** Baseline: current days-to-issue in the CD section. Target: pre-assembled, pre-indexed
  copies for the clerk to certify — *reported in days saved, audited.*
- **Indexing throughput.** Baseline: the reporting section's backlog for headnoting/neutral-citation tagging of
  **pronounced** judgments. Target: draft headnotes waiting for editorial sign-off — *measured as judgments indexed
  per week.*

We commit to the number the pilot produces. If a hypothesis doesn't hold, that is in the report too.

---

## 10. The 12-week pilot

Bounded to **one or two registry sections** of a single High Court, read-only throughout, nowhere near the Bench.

| Weeks | Phase | Outcome |
|---|---|---|
| **1–2** | Access + baseline | Registrar's read-only data-access approval (e-Committee/NIC concurrence); nightly extract into the court server; **measure current multi-round-defect / scrutiny-turnaround / copy-turnaround baseline** in the pilot sections |
| **3–6** | Build | Stand up the four agents on the read-only extract; tune court-fee/welfare-stamp/limitation checks and connected-matter matching against real, already-processed filings |
| **7–10** | **Shadow mode** | AI produces the defect sheet / cause-list tags / copy index in parallel; the Stamp Reporter and CD section work as usual; **measure agreement** vs officer + re-scrutiny; **no live effect** |
| **11–12** | Supervised live | Registry officers use the cited drafts in the pilot sections; **report against the Week 1–2 baseline**; go/no-go for wider registry rollout |

Scope discipline: **no** Telugu handwritten OCR (typed e-filings only); **no** image generation; **no**
cloud-as-offline; **no** merits, judgments, or outcome prediction — **ever**. One High Court, the scrutiny + copying
sections, to start.

---

## 11. Bilingual by default — Telugu / English

The court works in English and Telugu; the litigant reads Telugu. Every registry-facing surface is bilingual:

- **Officer defect sheet** labels in Telugu + English: **కోర్టు రుసుము (Court Fee)**, **వకాలత్‌నామా (Vakalatnama)**,
  **సంక్షేమ ముద్ర (Welfare Stamp)**, **సూచిక & పేజీల వరుస (Index & Pagination)**, **కాజ్ శీర్షిక (Cause-Title)**,
  **కాలపరిమితి (Limitation)**, **ధ్రువీకృత ప్రతి (Certified Copy)**.
- **Litigant-facing defect / copy notices** — *"మీ దాఖలులో లోపాలు ఉన్నాయి — కోర్టు రుసుము సరిపోలేదు"* ("your filing has
  defects — court fee is short") — delivered in plain Telugu with an English gloss, so the litigant understands the
  objection without a translator.
- **Cause-list and certified-copy indexes** generated bilingually, matching the terminology already live on the
  Telangana and AP High Court portals and e-Sewa Kendras — nothing in the UI is a neologism to registry staff.

Everything the litigant sees stays **traceable, in their own language, and signed by a human officer** — and every
judicial decision remains, wholly and only, the Judge's.

---

## Sources (public)

**Pendency & case-age (the Problem)**
- Law Ministry / NJDG — over 60 lakh cases pending in High Courts (60,62,953 as of 14 July 2024), LiveLaw — https://www.livelaw.in/top-stories/over-4-crore-cases-pending-in-trial-courts-more-than-60-lakh-backlogs-in-high-courts-law-ministry-233926
- Nearly 60 lakh pending in HCs, Allahabad ~10 lakh (India Today NE) — https://www.indiatodayne.in/national/story/nearly-60-lakh-cases-pending-in-high-courts-of-india-69000-in-supreme-court-510004-2023-02-09
- Telangana HC pendency ~2.45 lakh with case-type breakdown; 2024 disposal 72,182 vs filing 70,623 (Deccan Chronicle) — https://www.deccanchronicle.com/southern-states/telangana/telangana-hc-disposal-rate-improves-but-pendency-remains-high-1875523
- High Court case-age: ~50% older than 5 years, ~25% older than 10 years (Data For India, on NJDG) — https://www.dataforindia.com/pendency/
- 80,000+ HC cases pending over 30 years (Business Standard) — https://www.business-standard.com/india-news/10000-sc-cases-pending-over-10-years-80000-hc-cases-over-30-years-126080300335_1.html
- Analyzing HC-NJDG data — pendency structure (arXiv 2307.10615) — https://ar5iv.labs.arxiv.org/html/2307.10615
- NJDG High-Court dashboard (live pendency, incl. AP HC ~2,46,464) — https://njdg.ecourts.gov.in/hcnjdg_v2/

**The e-filing "defect battle" & registry rules**
- Supreme Court to dismiss 1,000+ cases (2014–2020) if filing defects not cured in 4 weeks; 28-day refiling window (LiveLaw) — https://www.livelaw.in/top-stories/supreme-court-to-dismiss-over-1000-cases-filed-between-2014-2020-if-filing-defects-are-not-cured-within-4-weeks-212617
- Model Rules for e-Filing (e-Committee, Supreme Court of India) — https://ecommitteesci.gov.in/document/model-rules-for-e-filing/
- E-Filing Rules of the High Court of Delhi 2021 (representative rules) — https://www.legitquest.com/act/e-filing-rules-of-the-high-court-of-delhi-2021/C22C
- Delhi High Court — List of Common Objections (defect catalogue) — https://www.delhihighcourt.nic.in/web/faqs/list-of-common-objections
- High Court of Andhra Pradesh — e-Filing portal & rules (AP Gazette No. 3295) — https://aphc.gov.in/efiling.php · https://aphc.gov.in/docs/e-Filing%20Rules_gazette.pdf

**Systems (official) & registry function**
- Case Information System (CIS) — scrutiny/registration/listing modules; HC vs district versions (Justice Definitions Project) — https://jdc-definitions.wikibase.wiki/wiki/Case_Information_System_(CIS)
- Case Management through CIS 3.0 (eCourts manual) — https://ecourts.gov.in/ecourts2.0//static/manuals/Case%20Management%20through%20CIS%203.0.pdf
- NSTEP — National Service and Tracking of Electronic Processes (e-Committee) — https://ecommitteesci.gov.in/nstep/
- e-Sewa Kendra — litigant services incl. certified copies & e-filing assistance (e-Committee) — https://ecommitteesci.gov.in/service/e-sewa-kendra/
- Certified copies — HC copying rules, Chapter 17 "Preparation and Supply of Copies" (Delhi HC, representative) — https://delhihighcourt.nic.in/files/2024-04/courtrulefile_pue0w9a6.pdf

**Neutral citation & indexing**
- Supreme Court launches Phase 1 of the Neutral Citation System (`YYYY INSC n`); HC adoption (Bar & Bench) — https://www.barandbench.com/news/litigation/supreme-court-launches-phase-1-of-neutral-citation-system
- Supreme Court Press Note on neutral citations, 23 Feb 2023 — https://images.assettype.com/barandbench/2023-02/5621c99f-0540-432a-94ea-4a975b6405a8/PRESS_NOTE_23_Feb_2023.pdf

**Telangana High Court's own tech posture (the alignment argument)**
- TSHC e-Initiatives — FOSS stack (Ubuntu/LibreOffice/PDFsam/Jitsi/PostgreSQL/PHP-Java), OCR extraction, CD-section certified-copy software (2019), auto advocate-wise cause lists (e-Committee) — https://ecommitteesci.gov.in/division/technical-initiatives-and-achievements-of-the-high-court-for-the-state-of-telangana/
- TSHC — Adopting Open Source Software in the State Judiciary (e-Committee) — https://ecommitteesci.gov.in/project/adopting-open-source-software-in-the-state-judiciary/

**Statutes & rules referenced:** Code of Civil Procedure, 1908 — Order IV (institution of suits), Order VI
(pleadings), Order VII (plaint & rejection) · Court-fees legislation (Court Fees Act, 1870 / AP Court Fees and Suits
Valuation Act, 1956) · Model e-Filing Rules 2021 (e-Committee, SCI) · High Court Appellate-Side / e-Filing Rules
(TS & AP) · Section 12, Limitation Act, 1963 (exclusion of certified-copy time).

_Note on figures: AP HC ~2,46,464 and TS HC ~2.45 lakh are NJDG figures (AP reported to Parliament, ~March 2025);
the "1,000+ cases / 28-day cure" is the **Supreme Court Registry's** own defect enforcement, cited here as the
sharpest public illustration of the pan-court e-filing defect problem, not as an AP/TS-specific event. The verified
national case-age figure is "~half older than 5 years, ~a quarter older than 10" (NJDG via Data For India); we do not
assert an unverified "% over 3 years."_
