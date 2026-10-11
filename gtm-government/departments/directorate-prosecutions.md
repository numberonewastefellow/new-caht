# Department Briefing — Directorate of Prosecutions (Telangana, Hyderabad · Andhra Pradesh, Vijayawada)
### న్యాయ దర్యాప్తు కోసం VirtualAI — మీ గోడలు దాటని ఎంటర్‌ప్రైజ్ AI

**Cluster:** Judiciary / Legal — but the Directorate sits under the **Home Department** (executive), which makes this an *easier institutional sell* than the judiciary proper.
**Statutory anchor:** Directorate of Prosecution constituted under **Section 20 BNSS 2023** (District Directorate mandated in every district); Public Prosecutors / Additional PPs / Assistant PPs appointed and empowered under **Sections 18–19 BNSS**.
**Matching VirtualAI pattern (seeded):** the Prajavani grievance copilot — Field Extractor → History/Duplicate Checker → Records Verifier → Router/Endorsement Drafter. We re-point a working machine at prosecution scrutiny.

> **ప్రాసిక్యూటరే నిర్ణయిస్తారు. ఎల్లప్పుడూ. / The Public Prosecutor decides. Always.**
> VirtualAI reads the charge-sheet, checks the history, verifies completeness, and drafts the opinion. It never gives the legal opinion, never files, never decides to prosecute or not, never examines a witness, never adjudicates. Every output carries a **confidence score**, a **source citation**, a **one-click override**, and an **immutable audit entry**.

---

## 1. Positioning — గోడలు దాటని AI ("AI that never leaves your walls")

The material a Prosecutor works from is the **most sensitive class of state data there is**: FIRs, full charge-sheets, victim and witness identities, child-victim records, forensic (FSL/DNA) reports, undertrial custody records, and pre-decisional legal opinions. None of it can sit behind a cloud AI API — and Telangana already knows the cost of getting this wrong. Between **29 May and 7 June 2024** the state's own police apps — **TSCOP** (facial recognition) and **Hawk Eye** — suffered three data breaches; offender records, gun licences and officer identities were offered for sale for as little as **USD 150**, the root cause being **API passwords hard-coded in plaintext over HTTP** ([The Cyber Express](https://thecyberexpress.com/tscop-app-cyberattack-telangana-police/); [Internet Freedom Foundation](https://internetfreedom.in/three-telangana-police-data-breaches/)).

VirtualAI is built for exactly this constraint:

- **On-premise, air-gapped** — runs inside the **State Data Centre / NIC facility** or the Directorate's own server room. Case material never leaves government infrastructure.
- **Private open-weights LLM via Ollama** — no OpenAI, no Gemini, no cloud inference. **Fully-offline operation is possible precisely because the model is local**; the reasoning happens on the department's own hardware.
- **Decision-support only** — the Public Prosecutor stays the decision-maker at every step (see §8).

*Honesty note:* "Fully offline" is a property of the **local open-weights model**. The only network calls VirtualAI makes are read-only pulls from the **same government rails the Prosecutor already uses** (e-Prosecution / ICJS / CCTNS over the secure State network) — never to an external or cloud AI API. Take away the local model and you have an ordinary networked app; that distinction is the whole product.

**The mapping the client already knows** (from the Revenue "Prajavani" copilot):
- **AI Agent = the subject clerk** — here, the Prosecutor's law clerk / scrutiny assistant, grounded in the Directorate's *own* records.
- **Workflow = the file's noting path** — the legal-opinion → charge-sheet-scrutiny → case-brief → trial-record → appeal-opinion journey.
- **Automation = the typing & compiling** — opinions, scrutiny notes, case briefs and appeal opinions drafted for signature.

---

## 2. The core recurring process — ప్రధాన ప్రక్రియ

Every working day, in every prosecution district, the same loop runs hundreds of times:

> **Police forward an FIR / draft charge-sheet → the Prosecutor gives a legal opinion on sufficiency of evidence → scrutinises the Sec 193 BNSS charge-sheet for defects and completeness → prepares the case brief, opening address and witness-examination sequence → maintains daily under-trial records through trial → and, on an adverse verdict, gives an appeal-worthiness opinion.**

This is what the Directorate is statutorily *for*. Under **Section 20 BNSS**, the Deputy Director of Prosecution **examines and scrutinises police reports** and monitors cases punishable with 7–10 years for expeditious disposal ([Legal Service India](https://legalserviceindia.com/legal/article-17414-directorate-of-prosecution-understanding-section-20-of-the-bharatiya-nagarik-suraksha-sanhita-2023.html); [Indian Kanoon — Sec 20 BNSS](https://indiankanoon.org/doc/89718546/)). The whole cadre — Director → Additional / Joint Director → Deputy Director (district) → Additional PP Gr-I & II (Sessions) → Senior APP / APP (Magistrate courts) — runs under the **Home Department** ([prosecution.telangana.gov.in](https://www.prosecution.telangana.gov.in/); [Know Your Prosecution](https://prosecution.telangana.gov.in/KnowYourProsecution.html)). AP runs the identical service from its Directorate at **Vijayawada** on the same national e-Prosecution/ICJS stack — so everything below is replicable in AP with no redesign.

---

## 3. The Problem — సమస్య: the leak is *after* charging, not at charging

**This is the key insight, and it inverts the usual pitch.** Telangana and AP are *not* weak chargesheeters. On crimes against women, **Telangana's charge-sheeting rate is 88.1% — well above the national 77.6%** (NCRB *Crime in India 2023*) ([Siasat / NCRB 2023](https://www.siasat.com/ncrb-2023-report-telangana-records-rise-in-crimes-against-women-3278206/)). The police are getting cases *to* court. The leak is **between the charge-sheet and the conviction** — precisely the stretch the Prosecutor owns: **sufficiency-of-evidence scrutiny before filing, and trial-completeness after.**

The gap is real and quantified:

- **Conviction lags charge-sheeting badly.** Nationally, the IPC conviction rate has sat around **~48.8%** — over half of decided trials end in acquittal. Telangana's IPC conviction rate has moved between roughly **57% and 70%** across recent NCRB years; AP's is among the highest in India at **~84%** ([The Wire — NCRB conviction data](https://m.thewire.in/article/government/ncrb-data-conviction-rates); [IndiaDataMap — state-wise conviction](https://indiadatamap.com/2025/10/05/state-wise-conviction-rates-in-india-2025/)). Every point of that charge-sheet-to-conviction gap is a case that *was* built but did not *hold*.
- **Recognition failure #1 — the witness sequence collapses.** A parliamentary standing committee found that, once witness hostility/perjury is accounted for, the effective conviction rate in criminal cases can fall to **as low as 10%**; hostile witnesses are widely identified as the **single largest cause of acquittals**, a problem the Law Commission's **198th Report** and the **Malimath Committee** both flagged ([Legal Service India — hostile witness & acquittal](https://www.legalserviceindia.com/legal/article-597-impact-of-hostile-witness-on-acquittal.html); [Juris Centre](https://juriscentre.com/2023/08/24/impact-of-hostile-witnesses-in-the-administration-of-indian-criminal-justice-system/)). Witnesses turn — but they turn *more* when examination is out of sequence and the chronology gives the defence a gap to exploit.
- **Recognition failure #2 — the electronic-evidence certificate is missing or defective.** Courts routinely acquit where the **Section 65B** certificate for electronic records is absent or defective — and from **1 July 2024 the bar rose**: **Section 63 of the Bharatiya Sakshya Adhiniyam 2023** now demands **dual certification** (device custodian *and* an independent expert) plus a stated **hash value and algorithm** ([iPleaders — electronic evidence under BSA](https://blog.ipleaders.in/electronic-evidence-under-the-bsa-2023/); [K&K — Sec 63 BSA](https://ksandk.com/litigation/section-63-bharatiya-sakshya-adhiniyam-2023/); Supreme Court line from *Anvar P.V.* to *Arjun Panditrao Khotkar* [Cyril Amarchand](https://corporate.cyrilamarchandblogs.com/2021/01/supreme-court-on-the-admissibility-of-electronic-evidence-under-section-65b-of-the-evidence-act/)). Every phone dump, CCTV clip and CDR now needs a stricter certificate — and any one omission can sink an otherwise strong case.
- **Recognition failure #3 — the sanction order is missing, late, or unchecked.** Prosecution of a public servant needs prior sanction under **Section 218 BNSS** (successor to Sec 197 CrPC), now with a **120-day deemed-sanction clock** ([LiveLaw — Sec 197 CrPC vs Sec 218 BNSS](https://www.livelaw.in/articles/sanction-to-prosecute-public-servants-section-197-crpc-vs-section-218-bnss-285065)). The Telangana reality: an RTI found **only ~25% of Anti-Corruption Bureau cases were approved for prosecution** — a sanction bottleneck that quietly kills cases before trial ([Siasat — 25% ACB sanction RTI](https://www.siasat.com/just-25-pc-of-acb-cases-in-telangana-approved-for-prosecution-rti-3313737/)).
- **Recognition failure #4 — the Sec 193/230 file is incomplete.** A charge-sheet must arrive **duly indexed** with the witness list, the Sec 180/183 statements, forensic (Sec 176(3)) reports, seizure memos and sanction — and under **Section 230 BNSS** the accused must get these within **14 days** ([ApniLaw — Sec 230 BNSS](https://www.apnilaw.com/bare-act/bnss/section-230-bharatiya-nagarik-suraksha-sanhitabnss-supply-to-accused-of-copy-of-police-report-and-other-documents/); [Law Trend — Sec 193(8)](https://lawtrend.in/filing-of-chargesheet-ends-right-to-default-bail-even-if-additional-copies-under-section-1938-bnss-are-omitted-supreme-court/)). A gap discovered at trial is a gap discovered too late.

**None of this is a "work harder" problem.** It is a **pattern-recognition and completeness-checking problem** — spotting the missing certificate, the absent sanction, the un-indexed exhibit, the witness order that hands the defence an opening — across dozens of simultaneous case files. That is exactly what a tireless, fully-cited assistant is for, and exactly what only the Prosecutor is positioned to catch.

---

## 4. Where the time goes — సమయం ఎక్కడ పోతుంది (current journey, bottlenecks marked)

| # | Step today | Who | Bottleneck |
|---|-----------|-----|-----------|
| 1 | Read the FIR / draft charge-sheet and form a **legal opinion on sufficiency of evidence** | APP / PP | ⛔ Manual read of a fat file; weak cases spotted late, strong cases under-argued |
| 2 | **Scrutinise the Sec 193 charge-sheet** for defects & completeness | Dy. Director / PP | ⛔ Checklist held in the head — missing **Sec 63 (65B) certificate**, forensic report, sanction, witness list slip through |
| 3 | Confirm **sanction (Sec 218)** obtained and within the 120-day clock | PP | ⛔ Sanction status tracked by hand across many cases; deemed-sanction window missed |
| 4 | Prepare the **case brief, opening address (Sec 249) and witness-examination sequence** | PP | ⛔ Days of manual chronology-building; sub-optimal witness order → hostile-witness damage |
| 5 | Maintain **daily under-trial records** and cause-list follow-up | APP | ⛔ Repetitive data entry into e-Prosecution; the 12-KPI MIS compiled by hand |
| 6 | On an adverse verdict, give an **appeal-worthiness opinion** within limitation | PP / Dy. Director | ⛔ Slow turnaround against the limitation clock; appealable acquittals lapse |
| 7 | Report performance on the **12 KPIs** to the Directorate | District office | ⛔ Manual aggregation; no live view of defect patterns |

Steps 1–2 (opinion & scrutiny), 3 (sanction), 4 (brief & sequencing) and 6 (appeal opinion) are precisely the clerical-analytical stages VirtualAI compresses — freeing the Prosecutor to do the judgement work only a Prosecutor can do.

---

## 5. The Solution — పరిష్కారం: four named agents (EXTRACT → CHECK HISTORY → VERIFY RECORDS → ROUTE & DRAFT)

Each agent produces a **confidence score** and a **source citation** on every output. Nothing is asserted without pointing to the exact charge-sheet page, statement, FSL line, or statute section it came from. **Typed/digital records only — no Telugu handwritten OCR.**

### Agent 1 — **Charge-Sheet Extractor** (EXTRACT) · *అభియోగ పత్రం సంగ్రహకర్త*
Reads the already-digital record in **e-Prosecution / CCTNS / ICJS** — FIR, Sec 193 police report, witness statements, forensic reports, seizure & arrest memos, sanction orders — and produces a **structured case skeleton**: accused, victims, witnesses, charged sections (BNS/BNSS), exhibits, electronic records, incident/committal dates and the trial clock.
*Cites:* every extracted field back to its source document/page. *Confidence:* per field; low-confidence fields flagged for the Prosecutor.

### Agent 2 — **History & Precedent Checker** (CHECK HISTORY) · *చరిత్ర & పూర్వ నిదర్శన తనిఖీ*
Checks the accused's antecedents across CCTNS and prior charge-sheets; surfaces the Directorate's **own prior legal opinions on similar FIRs**; and flags how comparable **charge-combinations have fared at trial** (recurring acquittal patterns, repeat defect types) so weaknesses are known before, not after, filing.
*Cites:* the matched FIR / charge-sheet numbers and prior opinion IDs. *Confidence:* ranked; **AI proposes the pattern, the Prosecutor draws the conclusion.**

### Agent 3 — **Completeness & Admissibility Verifier** (VERIFY RECORDS) · *సంపూర్ణత & ఆమోదయోగ్యత పరిశీలన*
The compliance brain, and the heart of this pitch. Runs the **Sec 193 / Sec 230 completeness checklist**: witness list indexed? Sec 180/183 statements attached? **Sec 63 BSA electronic-evidence certificate present, dual-signed, with hash value?** Sec 176(3) forensic report for 7yr+ offences? **Sanction (Sec 218) obtained and inside the 120-day clock?** seizure memos present? section-to-fact mapping (IPC → BNS) sound? Each gap is raised against the **exact statute text**.
*Cites:* the missing-item rule and the point in the file where it should be. *Confidence:* per item; ambiguous admissibility questions routed to the PP.

### Agent 4 — **Opinion & Brief Drafter / Router** (ROUTE & DRAFT) · *అభిప్రాయం & కేసు సారాంశం రూపకల్పన*
From verified data, drafts the documents that eat the Prosecutor's day:
- the **legal opinion on the FIR / charge-sheet** (sufficient to proceed, or *return-for-rectification* with the specific defects listed),
- the **case brief + opening-address outline (Sec 249)** and a proposed **witness-examination sequence with evidence chronology**,
- the **daily under-trial record entry** for e-Prosecution, and
- the **appeal-worthiness opinion** on an acquittal, against the limitation clock.
Routes each draft to the **APP → PP → Deputy Director** for scrutiny and sign-off.
*Cites:* each paragraph back to statement / FSL / statute. *Confidence:* whole-document readiness score; a flagged admissibility gap or missing sanction **forces a human-in-the-loop pause** before the draft can advance.

> The four together are the **Prosecution Scrutiny & Brief Workflow**: EXTRACT the charge-sheet → CHECK history & precedent → VERIFY completeness & admissibility → ROUTE & DRAFT the opinion/brief for the Prosecutor's signature. It mirrors the proven Prajavani pipeline one-for-one.

---

## 6. Department data sources (read-only) — శాఖ డేటా వనరులు

VirtualAI **reads**, it does not write to systems of record. Real systems, named precisely:

| System | What it holds | Used by |
|--------|---------------|---------|
| **e-Prosecution** (eprosecution.gov.in) — NIC, under ICJS | Legal opinions on FIRs, charge-sheet scrutiny notes, daily under-trial records, cause-list, **12-KPI MIS** | ① ② ④ |
| **CCTNS** (via ICJS) | FIR, Sec 193 police report / charge-sheet, statements, antecedents | ① ② ③ |
| **e-Courts** (via ICJS) | Cause list, framing-of-charge orders, judgments | ② ④ |
| **e-Forensics / FSL** (via ICJS) | DNA, chemical, digital-forensic reports | ③ |
| **e-Prisons** (via ICJS) | Undertrial custody status | ④ |
| **prosecution.telangana.gov.in / AP Directorate (Vijayawada)** | Cadre, GOs, jurisdiction master | ② |

The **e-Prosecution** app is the anchor system: built by NIC, it already gives PPs an interface to record **legal opinions on FIRs, scrutiny of draft charge-sheets and daily under-trial records**, does **real-time data fetch from Police and the concerned Court**, and produces a **performance report on 12 KPIs** — and it is live across **751 prosecution districts** ([e-Prosecution — About](https://eprosecution.gov.in/eprosecution/about-prosecution.jsp); [Google Play — e-Prosecution, 12 KPIs](https://play.google.com/store/apps/details?id=com.eprosecutionapp&hl=en_IN); [ForumIAS — e-Prosecution under ICJS](https://forumias.com/blog/e-prosecution-portal-home-ministry-develops-online-module-for-timely-disposal-of-criminal-cases/)).

**Integration counterpart:** brokered through **NIC** (e-Prosecution / ICJS national) and **NCRB / SCRB** (CCTNS/ICJS connectivity and read-API clearance).

**Pattern — nightly extract, then live APIs.** Begin with **nightly read-only extracts** from e-Prosecution / CCTNS into the air-gapped VirtualAI box (lowest integration risk, zero change to live systems); graduate to **read-only APIs** where NIC permits. VirtualAI never writes back; the Prosecutor enters the final opinion/record into e-Prosecution and signs it there.

---

## 7. Sovereign by design — సార్వభౌమ నిర్మాణం

- **Hosting:** inside the **Telangana State Data Centre / NIC Hyderabad** (BRKR Bhavan, **ISO 27001:2022 certified**) or the Directorate's own server room — on-prem, air-gapped ([NIC Telangana Data Centres](https://tg.nic.in/en/service/data-centres/)). AP hosts on its own State Data Centre equivalent.
- **Model:** on-prem **open-weights LLM via Ollama** — no cloud AI API; inference on department hardware.
- **Workflow engine:** VirtualAI Workflows orchestrate EXTRACT→CHECK→VERIFY→ROUTE&DRAFT with **Prosecutor sign-off gates**.
- **Audit log:** every extract, suggestion, confidence score, citation, Prosecutor edit, override and sign-off is written to an **immutable audit trail** — court-defensible provenance for every drafted line of an opinion or brief.

**Why air-gapped is non-negotiable here:** an opinion file names the victim, the child witness, the informant and the forensic result *before* the case is decided. The TSCOP / Hawk Eye breach is the case study for why the AI that touches this material must live **inside the wire**.

---

## 8. Accountability — జవాబుదారీతనం: "The Prosecutor decides. Always." (ప్రాసిక్యూటరే నిర్ణయిస్తారు. ఎల్లప్పుడూ.)

- **AI never decides, files, or signs.** It does **not** give the legal opinion, does **not** decide to prosecute or drop, does **not** scrutinise-and-clear a charge-sheet on its own, does **not** examine a witness, does **not** adjudicate anything. It **drafts and flags**.
- **Every output carries four things:** a **confidence score** (*విశ్వాస స్కోరు*), a **source citation** (*మూలాధార ఉల్లేఖనం*), a **one-click override**, and an **audit-log entry**.
- **Human-in-the-loop is mandatory.** Low confidence, a flagged admissibility gap (missing Sec 63 certificate, absent Sec 218 sanction), or an ambiguous section mapping **pauses the workflow** for the Prosecutor's input before it can advance.
- **The Prosecutor signs.** The final legal opinion, scrutiny note, brief and appeal opinion are reviewed, edited and **signed by the PP/APP** — the discretion and legal responsibility of the office are untouched. VirtualAI produces the first draft; the Prosecutor produces the decision.

---

## 9. Projected impact — అంచనా ప్రభావం (honest & illustrative)

> **Illustrative directions of travel, not guarantees.** Each metric is **baselined in Week 1 of the pilot on the Directorate's own cases**, and we **report against measured reality, not marketing claims.**

| Metric | Today (baseline set in pilot) | With VirtualAI (target to measure) |
|--------|------|------|
| Legal-opinion / charge-sheet **scrutiny turnaround** | days of manual reading | same-day reviewable **first draft** |
| **Completeness at filing** — % of charge-sheets with Sec 63 cert, forensic, sanction, witness list all present | baseline TBD | measurable lift; defects caught **before** trial |
| **Return-for-rectification precision** — defects found at scrutiny vs discovered in court | many surface at trial | more caught up-front, each cited to statute |
| **Sanction-clock** (Sec 218, 120 days) misses | tracked by hand | fewer lapses; live countdown |
| **Appeal-worthiness opinions** on acquittals within limitation | slow | faster turnaround, fewer lapses |
| **12-KPI MIS** compilation | manual aggregation | auto-populated from the workflow, with defect-pattern view |

The honest framing for both states: **protect what already works.** Telangana and AP already charge-sheet strongly (88.1% CAW in TS) and AP already converts at ~84%. The new **BSA Sec 63** dual-certification burden and the **Sec 230** 14-day clock make completeness *harder*, not easier — VirtualAI's job is to defend those numbers against the new-law completeness load, and to close the charge-sheet-to-conviction gap by catching the recoverable defects before they reach a courtroom.

---

## 10. The 12-week pilot — 12-వారాల పైలట్: Baseline → Shadow → Assisted-Live

**Scope:** one prosecution district (a Hyderabad unit or an AP district), a few APPs plus one Deputy Director reviewer.

| Phase | Weeks | What happens |
|---|---|---|
| **Baseline (బేస్‌లైన్)** | 1–3 | Stand up the air-gapped box; ingest a **nightly read-only e-Prosecution / CCTNS extract**; **instrument the current process** — scrutiny turnaround, completeness-at-filing, sanction-clock misses, appeal-opinion turnaround. No AI in the Prosecutors' loop yet. |
| **Shadow (షాడో)** | 4–8 | The four agents draft **in parallel, out of the way**. Compare AI scrutiny notes, defect flags and section mappings against Prosecutor output; **calibrate confidence scores**; tune to TS/AP SOPs, the BNS/BNSS/BSA section set, and the Directorate's scrutiny checklist. **No AI output reaches a court.** |
| **Assisted-Live (సహాయక ప్రత్యక్ష)** | 9–12 | Prosecutors use the AI draft as their **first draft** — review, edit, and **sign**. Measure completeness uplift, scrutiny time saved and defect-catch rate against the Week-1 baseline. **The Prosecutor always decides.** |

**What we need from the Directorate:** a nominated sponsor (Director / Deputy Director of Prosecution); **read-only extract clearance** brokered via **NIC / e-Prosecution / CCTNS**; space on the **State Data Centre** (or an on-prem box) for the air-gapped model; 3–5 pilot Prosecutors; and the current **scrutiny checklist and charge-sheet SOPs** for tuning. **What we do not need:** any data to leave the building.

---

## 11. Bilingual by default — ద్విభాషా లేబుళ్లు (Telugu / English glossary)

| English | తెలుగు (Telugu) |
|---------|------|
| The Prosecutor decides. Always. | ప్రాసిక్యూటరే నిర్ణయిస్తారు. ఎల్లప్పుడూ. |
| Data never leaves your walls | డేటా మీ గోడలు దాటదు |
| Legal opinion (on FIR) | న్యాయ అభిప్రాయం |
| Charge-sheet scrutiny | అభియోగ పత్రం పరిశీలన |
| Sufficiency of evidence | సాక్ష్యం సమగ్రత |
| Witness | సాక్షి |
| Case brief | కేసు సారాంశం |
| Acquittal | నిర్దోష విడుదల |
| Confidence score | విశ్వాస స్కోరు |
| Source citation | మూలాధార ఉల్లేఖనం |

- **Interface and drafts in both Telugu and English.** Opinions and briefs are drafted in the **language of the court record**; the Prosecutor's working interface can run in Telugu.
- **Standing tagline in the UI:** **ప్రాసిక్యూటరే నిర్ణయిస్తారు. ఎల్లప్పుడూ. — The Prosecutor decides. Always.**
- **Scope guardrail:** Telugu support is for **UI, drafting and display over already-typed digital records**, using the local open-weights model's language ability. There is **no Telugu handwritten OCR, no image generation, and no cloud fallback** — the system reads structured e-Prosecution / CCTNS text and drafts against it, on-prem.

---

## Sources (public)

1. NCRB *Crime in India 2023* — **Telangana charge-sheeting 88.1% vs national 77.6%** (crimes against women) — [Siasat](https://www.siasat.com/ncrb-2023-report-telangana-records-rise-in-crimes-against-women-3278206/)
2. **Section 20 BNSS** — Directorate of Prosecution; Deputy Director scrutinises police reports — [Legal Service India](https://legalserviceindia.com/legal/article-17414-directorate-of-prosecution-understanding-section-20-of-the-bharatiya-nagarik-suraksha-sanhita-2023.html); [Indian Kanoon](https://indiankanoon.org/doc/89718546/)
3. **e-Prosecution portal** — modules (legal opinion on FIRs, charge-sheet scrutiny, daily under-trial records), part of ICJS, 751 districts — [ForumIAS](https://forumias.com/blog/e-prosecution-portal-home-ministry-develops-online-module-for-timely-disposal-of-criminal-cases/); [e-Prosecution About](https://eprosecution.gov.in/eprosecution/about-prosecution.jsp)
4. **e-Prosecution 12-KPI performance dashboard / MIS**, real-time Police & Court fetch — [Google Play listing](https://play.google.com/store/apps/details?id=com.eprosecutionapp&hl=en_IN)
5. **Directorate of Prosecutions, Telangana** — under Home Department; cadre structure — [prosecution.telangana.gov.in](https://www.prosecution.telangana.gov.in/); [Know Your Prosecution](https://prosecution.telangana.gov.in/KnowYourProsecution.html)
6. **Section 63 BSA 2023** replaces IEA **Section 65B** (w.e.f. 1 Jul 2024); dual certification + hash value — [iPleaders](https://blog.ipleaders.in/electronic-evidence-under-the-bsa-2023/); [K&K](https://ksandk.com/litigation/section-63-bharatiya-sakshya-adhiniyam-2023/)
7. **65B admissibility line & acquittals** (*Anvar P.V.* → *Arjun Panditrao Khotkar*) — [Cyril Amarchand](https://corporate.cyrilamarchandblogs.com/2021/01/supreme-court-on-the-admissibility-of-electronic-evidence-under-section-65b-of-the-evidence-act/)
8. **Hostile witnesses = leading cause of acquittal; ~10% effective conviction (parliamentary committee); Law Commission 198th / Malimath** — [Legal Service India](https://www.legalserviceindia.com/legal/article-597-impact-of-hostile-witness-on-acquittal.html); [Juris Centre](https://juriscentre.com/2023/08/24/impact-of-hostile-witnesses-in-the-administration-of-indian-criminal-justice-system/)
9. **Conviction rates** — national ~48.8%; Telangana ~57–70%; AP ~84% — [The Wire](https://m.thewire.in/article/government/ncrb-data-conviction-rates); [IndiaDataMap](https://indiadatamap.com/2025/10/05/state-wise-conviction-rates-in-india-2025/)
10. **Section 218 BNSS** — sanction to prosecute public servants; **120-day deemed sanction** — [LiveLaw](https://www.livelaw.in/articles/sanction-to-prosecute-public-servants-section-197-crpc-vs-section-218-bnss-285065)
11. **Telangana ACB — only ~25% of cases approved for prosecution (RTI)** (sanction bottleneck) — [Siasat](https://www.siasat.com/just-25-pc-of-acb-cases-in-telangana-approved-for-prosecution-rti-3313737/)
12. **Section 230 BNSS** (14-day supply of documents) & **Section 193(8)** (indexed report; electronic filing) — [ApniLaw](https://www.apnilaw.com/bare-act/bnss/section-230-bharatiya-nagarik-suraksha-sanhitabnss-supply-to-accused-of-copy-of-police-report-and-other-documents/); [Law Trend](https://lawtrend.in/filing-of-chargesheet-ends-right-to-default-bail-even-if-additional-copies-under-section-1938-bnss-are-omitted-supreme-court/)
13. **BNSS trial timelines** — Sec 249 (prosecutor opens case), Sec 232 (commitment ≤90 days), Sec 346 (expeditious trial), Sec 392 (judgment ≤30, extendable 45 days) — [JuriGram](https://jurigram.com/advocates/resources/new-laws/bnss-timelines-investigation-trial-completion); [latestlaws — Sec 249](https://www.latestlaws.com/bare-acts/central-acts-rules/bnss-section-249-opening-case-for-prosecution/)
14. **TSCOP / Hawk Eye breaches** (29 May–7 Jun 2024; sold for USD 150; plaintext API passwords) — [The Cyber Express](https://thecyberexpress.com/tscop-app-cyberattack-telangana-police/); [Internet Freedom Foundation](https://internetfreedom.in/three-telangana-police-data-breaches/)
15. **Telangana State Data Centre / NIC** (ISO 27001:2022; on-prem hosting) — [NIC Telangana](https://tg.nic.in/en/service/data-centres/)

_Statutes named: **BNSS 2023** — Sec 18–19 (PP/APP appointment), Sec 20 (Directorate of Prosecution), Sec 176(3) (forensic visit 7yr+), Sec 180/183 (statements), Sec 193 & 193(8) (police report / supplementary), Sec 218 (sanction; 120-day deemed), Sec 230 (14-day supply), Sec 232/249 (commitment / opening), Sec 346 & 392 (expeditious trial / judgment). **BSA 2023** — Sec 63 (electronic-evidence certificate, ex-65B IEA). **BNS 2023** — charged offences. AP parallel: Directorate of Prosecutions, Vijayawada, on the identical e-Prosecution / ICJS / CCTNS stack — replicable without redesign._
