# Department Briefing — Police Verification / Special Branch: Antecedent Verification (Passport PV · Tenant · Employee PVC · Arms-License · PCC)

**Cluster:** Police / Home / Law-Enforcement (Telangana Police & Andhra Pradesh Police)
**Wave-1 rank:** #3 of 8 (18/20) — **highest feasibility in the police cluster**: a bounded task, structured input/output, and a clean clear/adverse binary. The **best low-risk first pilot** — the technical proof-of-concept the rest of the police roadmap stands on.
**Matching VirtualAI agent (seeded):** Police / Law & Order antecedent-verification agent
**Exemplar to point at:** Prajavani grievance copilot (on-prem, officer signs with DSC) — same EXTRACT → CHECK → VERIFY → ROUTE & DRAFT pipeline, different file.

> **అధికారే నిర్ణయిస్తారు. ఎల్లప్పుడూ. / The officer decides. Always.**
> VirtualAI reads the application, searches the antecedent indices, disambiguates the namesakes, and drafts a **clear or adverse report with every hit cited**. It never clears anyone, never marks anyone adverse, never confirms an identity, never signs. Every output carries a confidence score, a source citation, a one-click override, and an immutable audit entry.

---

## 1. Positioning — Offline, Air-Gapped, Sovereign

Antecedent verification is the business of writing down, against a **named citizen**, whether the state holds a **criminal record or an adverse security finding** on them. A passport "adverse" report, an arms-license refusal, a tenant flagged as a history-sheeter — these are the **most reputation-sensitive judgements a police force issues about ordinary people**. They cannot sit behind a cloud AI API.

Telangana learned exactly this, and the lesson landed on **these very systems**. Between **29 May and 7 June 2024 the Telangana Police suffered three data breaches**; the apps compromised were **Hawk Eye** — the department's own **tenant and citizen verification app** — and **TSCOP**, together with the SMS service. Leaked data included **SOS calls from women, names, emails, phone numbers and locations of over 2 lakh users**, plus ~1.3 lakh SOS records and ~70,000 incident reports; the hacker offered it for sale for as little as **USD 150**, and the vendor had **hard-coded plain-text passwords inside TSCOP** ([MediaNama](https://www.medianama.com/2024/06/223-telangana-police-arrest-hacker-for-breaching-hawk-eye-app-deny-sharing-hyderabad-hotel-data-with-third-party/); [Internet Freedom Foundation](https://internetfreedom.in/three-telangana-police-data-breaches/); [Siasat](https://www.siasat.com/hacker-who-leaked-sold-telangana-police-data-for-150-arrested-3041609/)). The tool that verifies citizens was itself breached and sold. Any AI that reads antecedent data must live **inside the wire**.

VirtualAI is built for exactly this constraint:

- **On-premise, air-gapped** — runs inside the **Special Branch server room** or the **State Data Centre / NIC facility**. Antecedent data never leaves government infrastructure.
- **Private open-weights LLM via Ollama** — no OpenAI, no Gemini, no cloud inference. **Fully-offline operation is possible precisely because the model is local**; the reasoning happens on the department's own hardware.
- **Decision-support only** — the verifying officer stays the decision-maker at every step (see §8).

*Honesty note:* "Fully offline" is a property of the **local model**. If a department ever chose a hosted model, that offline guarantee would not hold. VirtualAI's design assumption is the local open-weights model, and everything below is scoped to that.

---

## 2. The Core Recurring Process — the file's noting path

Special Branch and District Special Branch (DSB) run a small set of **highly repetitive, form-driven, already-digital** antecedent checks, each ending in a **clear/adverse binary**:

1. **Passport Police Verification** — a residence check **plus** a criminal-antecedent check, returned as a **clear or adverse report to the Passport Seva Kendra (PSK)** under the **Passports Act, 1967**. The residence leg now runs on the **mPassport Police app** (geo-tagged field visit); the antecedent leg runs through the **Special Branch criminal-record index** ([Special Branch, Delhi Police — passport verification SOP](https://delhipolice.gov.in/doc/passport_verification.pdf)).
2. **Tenant verification (mandatory)** — the landlord submits the tenant's identity, photo and prior-address details (in Telangana via **Hawk Eye**), and police run an antecedent check. The obligation is imposed by a **commissioner's order under BNSS Sec 163** (successor to CrPC 144), backed by **BNSS Sec 172** (duty to conform to lawful police directions); non-compliance is punishable under **BNS Sec 223** (successor to **IPC 188**) ([BNSS Sec 172, ApniLaw](https://www.apnilaw.com/bare-act/bnss/section-172-bharatiya-nagarik-suraksha-sanhitabnss-persons-bound-to-conform-to-lawful-directions-of-police/); [IPC 188 → BNS 223, ILMS Academy](https://www.ilms.academy/blog/section-188-ipc-section-223-bns-explained-punishment-for-disobedience-scope-key-case-laws)).
3. **Private-employee PVC** — a **Police Verification Certificate** for private employees engaged by government offices, PSUs and defence establishments, issued on referral (in Telangana via **i-Verify / pvc.tspolice.gov.in**).
4. **Arms-license antecedent check** — under the **Arms Act, 1959**, the **SHO** conducts a thorough enquiry and reports through the **Circle Inspector** and **SP** on the applicant's **antecedents, threat assessment and character** — typically a two-month background investigation ([MHA — Grant of Arms Licences](https://www.mha.gov.in/sites/default/files/2022-10/GrantofArmsLicences10012011%5B1%5D.pdf)).
5. **Police Clearance Certificate (PCC)** — a clean-record certificate for citizens going abroad for study, employment, business or immigration.

Every one of these is the same loop: **EXTRACT** the applicant → **CHECK HISTORY** (FIRs / charge-sheets / convictions in the antecedent indices) → **VERIFY RECORDS** (disambiguate the true person from namesakes; confirm residence) → **ROUTE & DRAFT** the clear/adverse report for the officer's signature.

Map to VirtualAI: **AI Agent = the verification clerk / Special Branch dealing assistant; Workflow = the SB ↔ Intelligence noting path to the officer's sign-off; Automation = the typing and compiling of the clear/adverse report itself.**

---

## 3. The Problem — pattern-recognition failures, not effort failures

Verifying officers are not short on diligence; they are short on **bandwidth to search every index and disambiguate every namesake**, on a firehose of near-identical files. The scale and the failure modes are both on the public record:

- **Volume.** India issued **118.5 lakh (11.85 million) passports in the first 11 months of 2024 alone**, and has crossed **1 crore passports in 7 of the 11 years to 2024** ([MEA / Statista](https://www.statista.com/statistics/1477471/india-number-of-passports-issued/); [FACTLY](https://factly.in/data-kerala-goa-top-the-list-in-number-of-passports-issued-per-1000-persons/)). The **Hyderabad Regional Passport Office alone handled ~9.02 lakh applications in 2024 (~4,200 a day)** across 5 PSKs and 14 Post-Office PSKs ([Siasat](https://www.siasat.com/regional-passport-office-in-hyderabad-cut-appointment-wait-times-in-2024-3158882/)). **Every fresh passport is a residence check plus an antecedent search** — and that is before tenant, employee-PVC, arms-license and PCC files.
- **The residual bottleneck is the antecedent stage.** The rest of the passport pipeline has been compressed hard — Hyderabad now offers appointments in **6–8 days** and prints a normal passport in **5–7 working days, *excluding police verification*** ([Siasat](https://www.siasat.com/regional-passport-office-in-hyderabad-cut-appointment-wait-times-in-2024-3158882/)). Police verification is what is left outside the fast lane: officers are expected to finish residence verification in **~21 days but do so in less than one-third of cases — the other two-thirds take months, sometimes years** ([The India Post — Police Verification for Passport, 2026](https://indiapost.org/police-verification-for-passport)). The **mPassport Police app** cut the *residence* leg from ~15 to ~5 days in app-enabled districts (national average ~14 days) ([Tribune](https://www.tribuneindia.com/news/nation/now-passport-verification-in-just-5-days-centre-launches-mpassport-police-app-to-fast-track-process-480723)) — but the **antecedent search across indices and districts is still manual**, and that is the slow, error-prone tail.
- **The core error is a pattern-recognition error, in both directions.** A **false adverse** — a wrongful "police has submitted adverse report" — commonly stems from **namesake / mistaken identity, a door-number or name mismatch, or a current-vs-permanent address mix-up** ([RTI Wiki — adverse address mismatch](https://righttoinformation.wiki/practical-guides/passport-police-verification-adverse-address-mismatch)). A **false clear** — a real repeat offender or a different-district FIR **missed** because the index was searched only locally — is the mirror failure. Telangana's own **i-Verify** was built explicitly to run "**crime and criminal records search across all the districts in the State through photo and data match for a fool-proof character antecedent verification eliminating human errors**" ([Telangana Today](https://telanganatoday.com/police-verification-certificate-facility-i-verify-launched-in-telangana)). **The state has already named the failure mode.** VirtualAI is the tireless second reader that attacks it directly.
- **Tenant verification is mandatory but structurally under-served.** Rented premises are repeatedly found used as **cyber-fraud dens, drug-trafficking points, or shelters for undocumented persons** — with the **landlord liable and the property sealable** ([Siasat — verify tenants or face action](https://www.siasat.com/verify-tenants-or-face-action-hyderabad-police-warn-landlords-3507308/)). Running a genuine antecedent check on **every** tenant in a city, by hand, is simply not feasible at that volume — so many are rubber-stamped or skipped.

Each of these is a **pattern-recognition failure** that a tireless assistant is well suited to catch: a **namesake wrongly matched**, a **cross-district FIR missed**, a **mandatory tenant check skipped**, an **arms-license antecedent overlooked**.

---

## 4. Where the Time Goes — current journey & bottlenecks

| Step | What the officer does today | Bottleneck |
|---|---|---|
| Intake | Reads the PSK/PSP file, PVC/PCC application, Hawk Eye tenant form or arms-license application; re-keys applicant particulars | Same fields re-typed across systems; typos seed later namesake errors |
| Residence check | mPassport geo-tagged field visit confirms the address | Fast where the app is used; still a field visit per file |
| Antecedent search | **Manually searches the Special Branch / DSB criminal index and CCTNS** for FIRs, charge-sheets, convictions, history-sheeters | **Usually searched locally, not across all districts/states** — cross-jurisdiction hits slip through |
| Identity disambiguation | Decides whether a hit is *this* applicant or a **namesake**, by comparing name, parentage, DOB, address and photo | The single biggest error source — false adverse (namesake matched) or false clear (true match missed) |
| Two-tier verification | Application moves **Special Branch ↔ Intelligence** as both verifying agencies | Manual file/person movement; queueing between wings |
| Report drafting | **Hand-types** the clear or adverse report and pushes it to the PSK / PVC portal | Slow, inconsistent; adverse reports poorly evidenced are later challenged |

The delay and the risk both concentrate in the **antecedent search + identity-disambiguation + drafting** span — reading the indices, deciding "is this the same person?", and writing a defensible clear/adverse line. That is exactly the clerical layer VirtualAI absorbs.

---

## 5. The Solution — four named agents on EXTRACT → CHECK → VERIFY → ROUTE & DRAFT

Each agent produces a **confidence score** and a **source citation** on every output. Nothing is asserted without pointing to the exact FIR number, record ID, index row, or ID-document field it came from.

### Agent 1 — **Applicant & Request Extractor** (EXTRACT) · *దరఖాస్తు విశ్లేషణ*
Reads the already-digital request — the Passport Seva verification file, the **PVC/PCC application (i-Verify)**, the **Hawk Eye tenant form**, or the arms-license application — and produces a **clean, field-tagged subject sheet**: name and **aliases**, DOB, **parentage**, present and permanent address, ID numbers, purpose and referring authority.
*Cites:* every field back to its source document line. *Confidence:* per field; low-confidence fields flagged for officer entry. **Typed/portal records only — no handwritten Telugu OCR.**

### Agent 2 — **Antecedents & Criminal-Index Checker** (CHECK HISTORY) · *పూర్వ చరిత్ర తనిఖీ*
Searches the **Special Branch / DSB criminal-record index and the CCTNS national database — across all districts, not just the local station** — for FIRs, charge-sheets, convictions, and history-sheeter / watchlist entries against the subject. Returns a **ranked candidate-hit list**, each entry disambiguated on **name + parentage + DOB + address**.
*Cites:* the matching FIR / record IDs. *Confidence:* ranked candidates — **AI proposes possible matches; the officer confirms identity.** Where nothing is found, it returns an explicit **"no record found"** naming the exact indices searched — so a clear report is evidenced, not assumed.

### Agent 3 — **Identity & Residence Verifier** (VERIFY RECORDS) · *గుర్తింపు & నివాస ధృవీకరణ*
The disambiguation brain — the answer to *"is this hit actually this applicant?"*. Reconciles the **structured particulars** (name, parentage, DOB, address, ID numbers) between the application, the candidate antecedent records, and the **mPassport geo-tagged residence report**; separates **true match from namesake**; flags **current-vs-permanent address mismatch**. It **surfaces each candidate record's photo side-by-side for the officer's visual confirmation** — VirtualAI does the data reconciliation; **the face-match decision stays with the human** (mirroring i-Verify's data-match function, not automating it away).
*Cites:* the field-by-field match/mismatch. *Confidence:* per check; any unresolved mismatch is routed to the officer, never auto-resolved.

### Agent 4 — **Clear/Adverse Report Drafter & Router** (ROUTE & DRAFT) · *క్లియర్/ప్రతికూల నివేదిక*
Assembles the **clear or adverse report** — the cited hits (or the evidenced "no record found"), the residence-verification result, and the disambiguation reasoning — in the PSK/PVC/PCC format, and routes it through the **Special Branch → Intelligence two-tier** path to the SP for sign-off. **Any antecedent hit, or a low confidence score, forces a human-in-the-loop pause** before the report can advance.
*Cites:* each line back to its record or field. *Confidence:* whole-report readiness score; adverse drafts always require explicit officer confirmation.

> The four together are the **Antecedent Verification Workflow**: EXTRACT the request → CHECK the antecedent indices → VERIFY the identity & residence → ROUTE & DRAFT the clear/adverse report for the officer's signature. It mirrors the seeded **police / law & order agent** and the proven Prajavani pattern — and it slots directly into i-Verify's own stated goal of a **fool-proof antecedent check that eliminates human error**.

---

## 6. Data Sources — read-only, real systems

**Read-only from live police systems (no write-back — the officer commits the final report):**

- **i-Verify / [pvc.tspolice.gov.in](https://pvc.tspolice.gov.in/)** — Telangana's online **PVC and PCC** portal, which already automates the **Special Branch ↔ Intelligence** transmission and a **two-tier criminal-record verification** ([Telangana Today](https://telanganatoday.com/police-verification-certificate-facility-i-verify-launched-in-telangana); [OpenGov Asia](https://archive.opengovasia.com/2021/05/02/telangana-india-automates-police-verification-and-clearance-certificate/)).
- **Hawk Eye** (tenant / servant / worker verification) — **read-only lookup only** into the tenant-registration module.
- **Passport Seva / mPassport Police app** — the residence-verification field report and the incoming PSK verification request (MEA CPV division).
- **Special Branch / District Special Branch (DSB) criminal-record index** — the antecedent / character register.
- **CCTNS national database + ICJS** — antecedent search across **17,000+ connected police stations**, with a built-in facility for **antecedent verification of self / tenants / employees** (44 reports and 11 searches on the national database) ([Digital Police / MHA](https://digitalpolice.gov.in/DigitalPolice/AboutUs); [NewsOnAir — 17,000+ stations on CCTNS](https://www.newsonair.gov.in/government-reports-over-17-thousands-of-police-stations-connected-via-cctns-for-crime-tracking)).
- **Andhra Pradesh:** [citizen.appolice.gov.in](https://citizen.appolice.gov.in/) and **MeeSeva** for PCC/PVC issuance, plus Passport Seva integration ([National Government Services Portal — AP Police certificates](https://services.india.gov.in/service/detail/andhra-pradesh-issuance-of-certificates-police-1)).

**Integration counterpart:** the **State Crime Records Bureau (SCRB)** as CCTNS state nodal, with **NIC / NCRB** for ICJS connectivity, and the **MEA CPV division / Passport Seva** for the passport channel.

**Nightly-extract-then-APIs approach:** begin with **nightly read-only extracts** from the SB index / CCTNS into the air-gapped VirtualAI box (lowest integration risk, zero change to live systems); graduate to **read-only APIs** where SCRB / NIC permit. VirtualAI never writes to CCTNS, i-Verify, Hawk Eye or Passport Seva.

---

## 7. Sovereign by Design

- **Hosting:** inside the **Special Branch server room** or the **Telangana / AP State Data Centre (NIC Hyderabad, ISO 27001:2022 certified)** — on-prem, air-gapped behind the department firewall.
- **Model:** on-prem **open-weights LLM via Ollama** — no cloud AI API; inference on department hardware; model updates arrive as vetted files, not API calls.
- **Workflow engine:** VirtualAI Workflows encode the **Special Branch → Intelligence two-tier** antecedent path with **officer sign-off gates**.
- **Audit log:** every extract, index search, candidate match, confidence score, citation, officer edit, override and sign-off is written to an **immutable audit trail** — court-defensible provenance, which matters because an **adverse report can be legally challenged** by the citizen it names.

This is the on-prem answer to the **Hawk Eye / TSCOP breach** lesson: the AI that reads a citizen's criminal antecedents lives **inside the wire**, not behind a cloud API and never in a vendor's hard-coded password.

---

## 8. Accountability — "The officer decides. Always."

**అధికారే నిర్ణయిస్తారు. ఎల్లప్పుడూ.**

- **AI never clears, never marks adverse, never confirms an identity, never signs.** It searches, disambiguates and drafts; it does **not** issue a PVC/PCC, does **not** send a report to the PSK, does **not** decide an arms-license, does **not** confirm a face match.
- **Every output carries four things:** a **confidence score**, a **source citation**, a **one-click officer override**, and an **audit-log entry**.
- **Human-in-the-loop is mandatory.** **Any** antecedent hit, an unresolved namesake, or a low confidence score **pauses the workflow** for officer input before it can advance — the safeguard against a wrongful adverse report ruining a citizen's passport, job or travel.
- **The officer signs.** As in the Prajavani exemplar, the final clear/adverse report is reviewed, edited and **signed by the Special Branch / Intelligence officer** (with a Digital Signature Certificate where the workflow requires it). VirtualAI produces the first draft; the officer produces the decision.

---

## 9. Projected Impact — illustrative, to be baselined in the pilot

> These are **illustrative directions of travel, not guarantees.** Each is **baselined in Week 1 of the pilot**, and we **report against measured reality, not marketing claims.**

- **Antecedent-search cycle time** — from the "two-thirds take months" tail toward a same-day, pre-searched, cited candidate list waiting for the officer.
- **False-adverse (namesake) errors** — fewer wrongful adverse reports because disambiguation runs on **name + parentage + DOB + address + photo-for-officer**, not name alone.
- **Cross-district antecedent recall** — more true hits surfaced because the search spans **all districts / CCTNS**, not just the local station.
- **Tenant-verification coverage** — antecedent screening on far more tenants per week, closing the gap between the mandatory rule and what is actually checked.
- **Report defensibility** — every clear/adverse line evidenced and audit-logged, so challenges are answered from the record.

Every one of these is a **measurable metric with a Week-1 baseline and a Week-12 assisted-live comparison** in the pilot commissionerate / district.

---

## 10. The 12-Week Pilot — Baseline → Shadow → Assisted-Live

**Scope:** one commissionerate's **Special Branch / DSB** unit, starting with the **PVC/PCC + passport-verification** stream (the cleanest structured I/O), one Intelligence-wing reviewer.

| Phase | Weeks | What happens |
|---|---|---|
| **Baseline** | 1–3 | Stand up the air-gapped box; ingest a **nightly read-only extract** of the SB index / CCTNS antecedent data; **instrument the current process** — measure antecedent-search time, adverse-report rate, namesake-error incidence, cross-district recall. No AI in the officers' loop yet. |
| **Shadow** | 4–8 | The four agents search and draft **in parallel, out of the officers' way**, on **historical already-decided files**. Compare AI candidate matches and clear/adverse drafts against the officers' own outcomes; **calibrate confidence scores**; tune to TS/AP SOPs and the i-Verify two-tier flow. |
| **Assisted-Live** | 9–12 | Officers use the AI's cited candidate list and draft report as their **first draft** — review, confirm identity, edit, and **sign**. Measure time saved, namesake-error reduction and recall uplift against the Week-1 baseline. **Officer always decides.** |

**What's needed from the department:**
- A **nodal sponsor** (SP/DCP, Special Branch) + **SCRB** engagement.
- **Read-only data-extract clearance** for the SB index / CCTNS (nightly extract to start).
- **On-prem server** (or a State Data Centre VM) for the air-gapped box + Ollama model.
- A batch of **historical decided PVC/PCC/passport cases** for shadow-mode tuning.
- The department's current **antecedent-verification SOPs and i-Verify two-tier flow** for configuration.

---

## 11. Bilingual by Default — Telugu / English

- **Interface and reports in both Telugu and English.** Clear/adverse reports are drafted in the **language of the issuing record**; the verifying officer's working interface can run in Telugu.
- **Bilingual labels** — e.g. *పోలీసు ధ్రువీకరణ పత్రం (Police Verification Certificate / PVC)*, *పోలీసు క్లియరెన్స్ సర్టిఫికెట్ (Police Clearance Certificate / PCC)*, *పూర్వ చరిత్ర తనిఖీ (Antecedent Check)*, *అద్దెదారు ధ్రువీకరణ (Tenant Verification)*, *ఆయుధ లైసెన్సు (Arms Licence)*, *క్లియర్ / ప్రతికూల నివేదిక (Clear / Adverse Report)*, *విశ్వసనీయత స్కోరు (Confidence Score)*.
- **Standing tagline in the UI:** **అధికారే నిర్ణయిస్తారు. ఎల్లప్పుడూ. — The officer decides. Always.**
- **Scope guardrail:** Telugu support is for **UI, drafting and display over already-typed digital records**, using the local open-weights model's language ability. There is **no Telugu handwritten OCR, no image generation, no automated face-matching, and no cloud fallback** — the system reads structured i-Verify / Hawk Eye / CCTNS / SB-index text and drafts against it, on-prem, and surfaces record photos only for the **officer's own** visual confirmation.

---

## Sources

- Telangana i-Verify PVC/PCC — Special Branch ↔ Intelligence automation, cross-district crime-record search, "photo and data match … eliminating human errors" (launched Apr 2021, DGP M Mahendar Reddy) — [Telangana Today](https://telanganatoday.com/police-verification-certificate-facility-i-verify-launched-in-telangana); [OpenGov Asia](https://archive.opengovasia.com/2021/05/02/telangana-india-automates-police-verification-and-clearance-certificate/); portal: [pvc.tspolice.gov.in](https://pvc.tspolice.gov.in/)
- Special Branch role in passport / character & antecedent / PVC verification; local-PS → SP → Special Branch HQ (criminal records) → clear/adverse to PSK — [Special Branch, Delhi Police SOP](https://delhipolice.gov.in/doc/passport_verification.pdf)
- mPassport Police app — cuts residence verification ~15 → ~5 days, geo-tagged paperless field report, 25+ states/UTs — [Tribune](https://www.tribuneindia.com/news/nation/now-passport-verification-in-just-5-days-centre-launches-mpassport-police-app-to-fast-track-process-480723); [Zee Business](https://www.zeebiz.com/personal-finance/news-police-verification-for-passport-in-just-5-days-mea-launches-mpassport-police-app-to-expedite-process-222526)
- Police-verification bottleneck — ~21-day norm met in <1/3 of cases, remainder months/years; residual slow stage after appointment/print sped up — [The India Post — Police Verification for Passport 2026](https://indiapost.org/police-verification-for-passport)
- Passport volume — 118.5 lakh issued Jan–Nov 2024; 1 crore+ in 7 of 11 years (MEA) — [Statista/MEA](https://www.statista.com/statistics/1477471/india-number-of-passports-issued/); [FACTLY](https://factly.in/data-kerala-goa-top-the-list-in-number-of-passports-issued-per-1000-persons/)
- Hyderabad RPO — ~9.02 lakh applications in 2024 (~4,200/day); passport printed in 5–7 days *excluding* police verification — [Siasat](https://www.siasat.com/regional-passport-office-in-hyderabad-cut-appointment-wait-times-in-2024-3158882/)
- Adverse passport report causes — namesake / mistaken identity, name & door-number mismatch, current-vs-permanent address mix-up — [RTI Wiki](https://righttoinformation.wiki/practical-guides/passport-police-verification-adverse-address-mismatch)
- Hawk Eye tenant verification (landlord obligation, 3–7 day check; premises sealable if misused) — [Siasat — verify tenants or face action](https://www.siasat.com/verify-tenants-or-face-action-hyderabad-police-warn-landlords-3507308/); [The Hans India — Hawk Eye](https://www.thehansindia.com/technology/tech-news/hawk-eye--learn-to-download-and-use-the-hawk-eye-mobile-app-587347)
- Tenant-verification legal basis — commissioner order under BNSS Sec 163 (ex-CrPC 144), BNSS Sec 172 (duty to conform to police directions), non-compliance under BNS Sec 223 (ex-IPC 188) — [BNSS Sec 172, ApniLaw](https://www.apnilaw.com/bare-act/bnss/section-172-bharatiya-nagarik-suraksha-sanhitabnss-persons-bound-to-conform-to-lawful-directions-of-police/); [IPC 188 → BNS 223, ILMS Academy](https://www.ilms.academy/blog/section-188-ipc-section-223-bns-explained-punishment-for-disobedience-scope-key-case-laws)
- Arms-license antecedent verification — SHO enquiry → Circle Inspector → SP; antecedents, threat & character; ~2-month background check (Arms Act 1959) — [MHA — Grant of Arms Licences](https://www.mha.gov.in/sites/default/files/2022-10/GrantofArmsLicences10012011%5B1%5D.pdf)
- CCTNS — 17,000+ police stations, national antecedent database, self/tenant/employee antecedent-verification facility; ICJS integration — [Digital Police / MHA](https://digitalpolice.gov.in/DigitalPolice/AboutUs); [NewsOnAir](https://www.newsonair.gov.in/government-reports-over-17-thousands-of-police-stations-connected-via-cctns-for-crime-tracking)
- AP PCC/PVC — MeeSeva + citizen.appolice.gov.in + Passport Seva — [National Government Services Portal](https://services.india.gov.in/service/detail/andhra-pradesh-issuance-of-certificates-police-1)
- Telangana Police data breaches (May–Jun 2024) — Hawk Eye + TSCOP + SMS; 2 lakh+ users incl. women's SOS calls; sold for USD 150; hard-coded plain-text passwords in TSCOP — [MediaNama](https://www.medianama.com/2024/06/223-telangana-police-arrest-hacker-for-breaching-hawk-eye-app-deny-sharing-hyderabad-hotel-data-with-third-party/); [Internet Freedom Foundation](https://internetfreedom.in/three-telangana-police-data-breaches/); [Siasat](https://www.siasat.com/hacker-who-leaked-sold-telangana-police-data-for-150-arrested-3041609/)

**Statutes referenced:** Passports Act, 1967 · Arms Act, 1959 · Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023 — Sec 163 (tenant-info orders, ex-CrPC 144), Sec 172 (duty to conform to lawful police directions) · Bharatiya Nyaya Sanhita (BNS) 2023 — Sec 223 (disobedience of public-servant order, ex-IPC 188).
