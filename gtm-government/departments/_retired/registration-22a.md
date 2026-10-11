# Department Briefing — Registration & Stamps: Pre-Registration Scrutiny
### Section 22A prohibited-property · Encumbrance Certificate · Market-Value & Stamp-Duty (TS & AP)

_Revenue / Registration cluster. Wave-1 deep-dive. Sibling of the delivered "Prajavani" grievance copilot._
_Pipeline, unchanged: **EXTRACT → CHECK HISTORY → VERIFY RECORDS → ROUTE & DRAFT** — every output carries a
confidence score and a source citation, and **the Sub-Registrar signs.** AI is decision-**support**, never the gate._

Product mapping (as pitched to Revenue): **AI Agent = the scrutiny clerk** who reads the deed and pulls the
registers · **Workflow = the file's noting path** from clerk → Sub-Registrar → District Registrar · **Automation =
the typing** of the scrutiny sheet, the refusal note, the Section 47-A reference.

---

## 1. Positioning — offline, air-gapped, sovereign

VirtualAI runs **entirely inside the State Data Centre** on a **private open-weights LLM (Ollama)**. No deed, no
party PII, no transaction value, and — critically — **no page of the 22A prohibited-property register** ever leaves
government infrastructure. There are no cloud AI API calls.

Why this department, specifically, is the strongest air-gap case in the whole cluster:
- **Party PII at the point of the largest financial transaction of a citizen's life** — Aadhaar, PAN, names,
  addresses, photographs, thumb impressions, family and inheritance details captured at every registration.
- **Transaction values are market-moving and politically sensitive.** The live stream of *who is buying which
  survey number for how much* is exactly the data a cloud vendor should never see.
- **The 22A register is a map of vulnerability.** It lists which **government, endowment, wakf, assigned, and
  ceiling-surplus lands** are being probed for registration — i.e. which sovereign and temple lands encroachers
  are targeting *right now*. Streaming that to a third-party model is a corruption- and sovereignty-grade leak.

**Honesty qualifier:** "fully offline" is true **because the model weights are local**. A hosted model would break
the guarantee. We do not relabel a cloud call as "offline." This is on-prem inference on open weights, full stop.

---

## 2. The core recurring process

Under **Section 17 of the Registration Act, 1908**, sale, gift, mortgage and lease deeds are **compulsorily
registrable**. Before a Sub-Registrar admits any such deed, staff must perform **pre-registration scrutiny**:

1. **Read the deed** — parties, property (survey/plot no., village, mandal), extent, deed type, stated consideration.
2. **Check Section 22A** — is this parcel on the **prohibited-property register**? If yes, the SRO is **legally bound
   to refuse** — government/endowment/wakf/assigned/ceiling-surplus/court-disputed/public-policy land. No discretion.
3. **Read the Encumbrance Certificate (EC)** — the chain of registered charges (prior sales, mortgages, litigation)
   on Books 1 & 2, issued under **Section 57** of the Act (Form 15 = encumbrances found; Form 16 = nil).
4. **Fix the market value & stamp duty** — compare stated consideration to the **government market-value slab** for
   that SRO/village/classification, under the **AP Stamp (Prevention of Under-Valuation of Instruments) Rules, 1975**
   and the Market Value Guidelines Rules; flag under-valuation → refer to Collector under **Section 47-A**, Indian
   Stamp Act, 1899.

This runs **hundreds of thousands of times a year, per state.** Telangana alone processed **~14.5 lakh property
registrations** in a single fiscal year and now collects **~₹1,000 crore per month** in stamp & registration
revenue — a full-year figure crossing **₹12,000–15,000 crore.** Every rupee of that passes through step 4.

---

## 3. The problem — undervaluation and wrong-flagging are *pattern-recognition failures at scale*

Steps 2 and 4 are exactly the kind of task humans do badly by hand and machines do reliably: **match a survey number
against a messy register**, and **look up the right value in a large slab table.** The CAG audits read as a catalogue
of that failure:

- **~1 in 4 test-checked documents was under-assessed.** A CAG scrutiny of **1,456 registered documents** (Telangana,
  Revenue Sector audit for the year ended March 2021) found **under-assessment of ₹3.44 crore in 347 documents** —
  attributed explicitly to **"incorrect mapping of data, lack of a change-management system, and clerical errors."**
  That is a pattern-recognition failure named, in the auditor's own words.
- **Guideline value ignored, at scale.** In one set, **21 sale-deed instruments (May 2013–Mar 2015)** were valued at
  **₹14.60 crore against a guideline value of ₹29.63 crore** — half the true value — for a short-levy of
  **₹70.92 lakh** on those 21 documents alone.
- **The AP side is the same story.** CAG found short-levy of **₹1.24 crore** from under-valuation linked to Land
  Revenue classification, and a **₹5.98 crore** under-valuation from incorrect adoption of composite rates.
- **The macro leak.** Property under-valuation of **₹285.33 crore** in one audited set produced a consequent
  short-levy of **₹18.82 crore** in stamp duty and registration fee. Under-valuation is the standard method: the
  cash component is kept off the deed to suppress the recorded consideration.
- **The register itself misfires — both ways.** Since the 2020 Dharani migration, the **22A prohibited list ballooned
  from roughly 20 lakh acres to over 1 crore acres**, sweeping in **thousands of genuine patta lands** (valid
  Pattadar Passbooks, even approved layouts). This generated **60,000+ grievances** and forced a **high-level review
  committee in August 2025.** So the manual/register process produces *both* wrongful refusals of clean land *and*
  missed prohibited parcels — the two failure modes that pre-registration scrutiny exists to prevent.

Each of these is a case a diligent clerk *should* have caught by cross-checking a register or a slab table — and
didn't, because a human cannot pattern-match 14.5 lakh documents a year without error. **That gap is the product.**

---

## 4. Where the time goes — the current journey and its bottlenecks

**Citizen side:** book a slot on IGRS → pay stamp duty via **e-STAMPS** → travel to the SRO → present the deed.
The failure the citizen feels: a 22A refusal is discovered **at the counter, after** advance paid, stamp duty paid,
agreement signed, and travel spent — with recovery from the seller often meaning years of litigation.

**Officer side, per deed:**
- **Manual 22A cross-check.** Staff match the deed's survey number against the prohibited register by hand. Dharani's
  data is inconsistent (part-survey numbers, sub-divisions, spelling variants), so the match is slow and error-prone
  → false refusals of clean land **and** missed prohibited parcels.
- **Manual market-value lookup.** The clerk finds the applicable slab (village × classification × SRO) and eyeballs
  stated consideration against it. This is the exact step the CAG found failing in 347 of 1,456 documents.
- **Manual EC interpretation.** The EC is a dense list of prior registrations; reading out the live encumbrances,
  the chain, and any subsisting mortgage/litigation is skilled, slow, and inconsistent between clerks.
- **No standing second reader.** Volume + counter pressure means scrutiny quality tracks whoever is on the desk.

The time isn't in *registering* the deed — the CARD/IGRS data entry is already digital. The time (and the leakage)
is in the **judgement steps**: is this parcel prohibited, is this value honest, what does this EC actually say.

---

## 5. The solution — four named agents on the proven pipeline

Four decision-**support** agents, each returning a **confidence score + a citation to the exact source record.**
None of them registers or refuses anything: they assemble the scrutiny, the **Sub-Registrar decides and signs.**
(The statutory CARD auto-block on 22A stays exactly as it is — these agents are the *diligent second reader* that
catches what the register's survey-number matching and the clerk's eyeball miss.)

**1 · Deed Reader — "పత్ర సారం / Patra-Saara" (EXTRACT).**
Parses the presented deed and the e-STAMPS/CARD submission into structured fields: parties, deed type
(sale/gift/mortgage), survey/plot numbers, village-mandal, extent, boundaries, **stated consideration.**
_Confidence + citation:_ each field tagged to its source line in the deed. _(No handwriting OCR — these are
already-digital, typed submissions.)_

**2 · Prohibited-Property & Encumbrance Sentinel — "నిషేధిత రక్షకుడు / Nishedha-Rakshaka" (CHECK HISTORY).**
For every survey number and sub-division, checks the **Section 22A prohibited register** (CARD/Dharani), returning
**category** (govt / endowment / wakf / assigned / ceiling-surplus / disputed) and the **notification reference** —
and flags **part-parcel** overlaps the eyeball misses. In the same pass it **reads the EC (Form 15/16)** and states,
in plain language, the subsisting encumbrances, the chain, and any live mortgage/litigation.
_Confidence + citation:_ the exact 22A register/notification entry and the specific EC document numbers.

**3 · Market-Value & Under-Valuation Verifier — "విలువ సత్యం / Viluva-Satya" (VERIFY RECORDS).**
Resolves the correct **market-value slab** (SRO × village × land classification) and compares it to the stated
consideration. Emits the **under-valuation / stamp-duty-leakage flag** — the exact ₹-gap and the resulting
short-levy — and drafts the **Section 47-A reference to the Collector** when the gap crosses threshold. This is the
CFO agent: it directly attacks the leakage the CAG keeps documenting.
_Confidence + citation:_ the specific slab row (with its guideline value) and the computed differential.

**4 · Scrutiny-Note Drafter — "పరిశీలన ముసాయిదా / Parishilana-Draft" (ROUTE & DRAFT).**
Assembles the one-page **scrutiny sheet**: a clear **CLEAR / REFER / REFUSE** recommendation with every flag and its
citation; auto-drafts the **refusal note** (quoting the 22A category and notification) or the **47-A undervaluation
reference**; and routes it up the noting path to the Sub-Registrar / District Registrar.
_Confidence + citation:_ the recommendation is a summary of the upstream evidence, each line traceable. **Automation
compiles the Word/PDF; the officer edits and signs.**

Net effect: the citizen can be warned of a 22A problem **before** paying, the honest-value question is answered the
same way every time, and the leakage in step 4 gets a standing auditor instead of a tired clerk.

---

## 6. Data sources — read-only, real systems

All access is **read-only**, against the department's own live systems; the agents **never write** to a source of record.

| Source | System | What it provides | Access |
|---|---|---|---|
| Deed & registration data | **CARD** / **IGRS** (registration.telangana.gov.in · registration.ap.gov.in) | parties, survey nos, extent, deed type, consideration | read-only |
| Prohibited property | **Section 22A register** (CARD) · **Dharani / Bhu Bharati** prohibited-property search | 22A categories + notifications; land classification | read-only |
| Encumbrances | **EC index** — Books 1 & 2 (Sec 57) | prior registered charges, mortgages, litigation | read-only |
| Market value | **Market-Value Guidelines** slabs (SRO/village) | guideline value per classification | read-only |
| Duty paid | **e-STAMPS** | stamp duty / registration fee paid | read-only |

**Integration counterpart:** the systems that must open the read-only hooks are built and run by **CGG (Centre for
Good Governance)** — the agency behind CARD and the IGRS portals for both states — and **NIC** (Dharani/land-record
stack). The pilot's first dependency is a data-access MoU with CGG, not new code.

**Sequencing:** where live APIs are not yet exposed, start with a **nightly read-only extract** into the State Data
Centre (deed feed, 22A register snapshot, market-value slabs, EC index), **then** migrate to real-time read-only APIs
as CGG provisions them. The pipeline is built to run on either.

---

## 7. Sovereign by design

- **State Data Centre.** All inference and all data stay on TS/AP SDC hardware in Hyderabad. Nothing egresses.
- **On-prem open-weights model.** Private LLM served locally via **Ollama** — no cloud AI API, no vendor telemetry.
- **Workflow engine = the noting path.** The clerk → Sub-Registrar → District Registrar route is modelled as a
  workflow with **mandatory human sign-off** at the registering-officer step. The engine cannot self-approve.
- **Immutable audit log.** Every extraction, every register lookup, every value comparison, and every officer
  decision is logged with its citation — an auditable trail for CAG, the DIG (Registration), and RTI.

The offline argument is not generic here: the three data classes this department handles — **party PII, transaction
values, and the 22A vulnerability map** — are precisely the categories that must never touch a third-party model.

---

## 8. Accountability — the officer decides. Always.

The AI **never registers, never refuses, never refers.** It reads, cross-checks, computes, and drafts — then hands the
Sub-Registrar a cited scrutiny sheet. Statutory power under Sections 22A / 47-A / 57 stays exactly where the law puts
it: with the registering officer and the Collector. Every recommendation is a **confidence score plus a source
citation the officer can open and verify in one click.** A flag the officer disagrees with is overridden in the note,
with the override logged. **Decision-support, not decision-making** — the same discipline that let Revenue trust the
Prajavani copilot.

---

## 9. Projected impact — illustrative, to be *measured* in the pilot

These are **hypotheses we baseline in Week 1–2 and report against measured reality — not claims.** We will publish the
before/after from the pilot SROs, not a brochure number.

- **Under-valuation catch-rate.** Baseline: the CAG-observed miss rate (347 under-assessed in 1,456 = ~24% of
  test-checked documents). Target: the Verifier surfaces a flag on materially every case the slab table would catch,
  so the officer chooses to refer — *measured as agreement with a manual re-audit of the same deeds.*
- **Wrongful 22A refusals.** Baseline: the part-parcel/spelling-variant false-flag rate at the pilot SROs. Target:
  fewer clean-land refusals *and* fewer missed prohibited parcels than the manual survey-number match — *measured
  against a ground-truth sample.*
- **Scrutiny turnaround.** Baseline: minutes-per-deed for 22A + market-value + EC by hand. Target: a cited scrutiny
  sheet ready before the officer opens the file — *measured, per SRO.*
- **Revenue integrity (the CFO line).** Stamp-duty leakage recovered via 47-A references the tool surfaced —
  *reported as rupees referred and rupees realised, audited, not projected.*

We commit to the number the pilot produces. If a hypothesis doesn't hold, that's in the report too.

---

## 10. The 12-week pilot

| Weeks | Phase | Outcome |
|---|---|---|
| **1–2** | Access + baseline | CGG read-only MoU; nightly extract into SDC; **measure the current miss/turnaround baseline** at 1–2 pilot SROs |
| **3–6** | Build | Stand up the four agents on the read-only extract; tune 22A matching and slab resolution against real deeds |
| **7–10** | **Shadow mode** | AI produces the scrutiny sheet in parallel; officer works as usual; **measure agreement** vs officer + re-audit; no live effect |
| **11–12** | Supervised live | Officers use the cited scrutiny sheet in 1–2 SROs; **report against the Week 1–2 baseline**; go/no-go for district rollout |

Scope discipline: **no** Telugu handwritten OCR, **no** image generation, **no** cloud-as-offline. Already-digital
registries only. One district, two SROs, two deed types (sale + gift) to start.

---

## 11. Bilingual by default — Telugu / English

The department and its citizens work in Telugu; the officer's file works in both. Every surface is bilingual:

- **Officer scrutiny sheet** labels and headings in Telugu + English: **నిషేధిత ఆస్తులు (Prohibited Properties / 22A)**,
  **మార్కెట్ విలువ (Market Value)**, **భారాల ధ్రువీకరణ పత్రం (Encumbrance Certificate)**,
  **తక్కువ విలువ కట్టడం (Under-valuation)**, **రిజిస్ట్రేషన్ (Registration)**.
- **Citizen-facing pre-check warning** — *"ఈ సర్వే నంబర్ 22A నిషేధిత జాబితాలో ఉంది"* ("this survey number is on the 22A
  prohibited list") — delivered **before** the citizen pays advance and stamp duty, in Telugu with an English gloss.
- **Draft refusal / 47-A notes** generated bilingually, so the officer edits in the language the file will be read in.

Terminology follows the terms already live on the IGRS/Dharani portals, so nothing in the UI is a neologism to staff.

---

## Sources (public)

**Statute & rules**
- Registration Act, 1908 (India Code, full text) — https://www.indiacode.nic.in/bitstream/123456789/15937/1/the_registration_act,1908.pdf
- Section 57, Registration Act, 1908 (EC / inspection of Books 1 & 2) — https://indiankanoon.org/doc/9115/
- AP Stamp (Prevention of Under-Valuation of Instruments) Rules, 1975 — https://indiankanoon.org/doc/112429831/
- Section 47-A, Indian Stamp Act (Collector's power to re-determine market value) — https://www.lawyersclubindia.com/articles/sec-47-a-of-indian-stamp-act-in-india-18081.asp

**CAG audit findings (the Problem)**
- CAG, Telangana Revenue Sector, year ended March 2021 — Ch. III, Stamp Duty & Registration Fee (1,456 docs / 347 under-assessed / ₹3.44 cr) — https://cag.gov.in/uploads/download_audit_report/2021/Chapter-3-065cdaf4454f7c8.08280988.pdf
- CAG, Telangana Report No. 6 of 2020 (Revenue Sector, 2018-19) — https://cag.gov.in/webroot/uploads/download_audit_report/2020/AR%20(RS)%202018-19%20ENGLISH-0605b2ee924e189.72864101.pdf
- CAG, Registration & Stamps chapter, 2025 (Ch. IV) — https://cag.gov.in/uploads/download_audit_report/2025/7.--CHAPTER-IV,-REGISTRATION-&amp-STAMP-069ac62bdef26f1.21070935.pdf
- Citizen Matters — "Undervaluation of properties: crores lost in stamp duty, registration fees" (₹285.33 cr → ₹18.82 cr) — https://citizenmatters.in/property-undervaluation-crores-lost-in-stamp-duty-registration-fees/

**Systems (official) & context**
- IGRS Telangana — Registration & Stamps Dept portal — https://registration.telangana.gov.in/
- Dharani — Prohibited Property search — https://dharani.telangana.gov.in/prohibitedPropertySearchAgri
- Prohibited Properties u/s 22A, Govt of AP (district notice example, West Godavari) — https://westgodavari.ap.gov.in/prohibited-properties-u-s-22a-registration/
- Telangana Today — stamp & registration revenue (~₹12,364 cr prior year; ~14.5 lakh registrations; ~₹1,000 cr/month) — https://telanganatoday.com/telangana-revenue-from-stamp-duty-and-registration-to-cross-rs-15000-crore

_Note on figures: the ₹671.48 cr in the 2018-19 report is the Revenue-Sector aggregate across seven departments, not
registration alone; the registration-specific anchors above (₹3.44 cr / 347 of 1,456; ₹70.92 lakh / 21 docs; the AP
₹1.24 cr and ₹5.98 cr cases) are the sharp, on-theme figures for the pitch._
