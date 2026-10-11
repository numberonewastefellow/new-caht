# One Pattern, Every Department
## VirtualAI for Government — Telangana & Andhra Pradesh · Executive Summary
### ఒకే నమూనా, ప్రతి శాఖకు — ప్రభుత్వ మౌలిక వసతుల్లోనే

**Enterprise AI that never leaves your walls.** VirtualAI runs entirely inside the State Data Centre on a
private, open-weights LLM (Ollama) — air-gapped, sovereign, on-premise. Every prompt, every document, every
decision stays on government infrastructure. It reads the department's own systems, drafts the clerical work
an officer does by hand today, and hands each file back for the officer to check and sign.

The Revenue Department **Prajavani grievance copilot** proved the model. This programme extends the *same*
proven machine — **EXTRACT → CHECK HISTORY → VERIFY RECORDS → ROUTE & DRAFT**, every output carrying a
**confidence score + source citation**, the **officer deciding and signing** every time — to **nine
high-value departments** across both states. One pattern; each department gets its own briefing (linked
below) and, when approved, its own deck + prototype + 12-week pilot.

---

## The pattern (identical everywhere)
| Product concept | In government terms |
|---|---|
| **AI Agent** | a subject clerk who has read every Act, GO and record for one subject — answers from the department's own files, cites where it found it |
| **Workflow** | the file's noting path — extract → check history → verify records → route & draft — that **stops for signature exactly where the rules require it** |
| **Automation** | the typing & compiling — the endorsement/notice/report drafted in the department's format, ready for the officer to check and sign |
| **Sovereign by design** | on-prem open-weights model, agent workflow engine, full audit log — **no data leaves government infrastructure** |
| **Accountability** | "**The officer decides. Always.**" AI never decides/closes/signs; it drafts and flags with confidence + citation; the officer overrides in one click; every action is logged |

---

## The nine departments (each has its own brief in `departments/`)

_Set tuned for genuine-LLM value: two departments whose work is mostly deterministic lookup (Registration-22A,
Police Verification) were set aside (kept in `departments/_retired/`) in favour of higher-AI-density ones —
**CID** and **District Collectorate Coordination**._

| # | Department (cluster) | The one-line case | Brief |
|--:|---|---|---|
| 1 | **Cybercrime — TGCSB / AP** (Police) | Golden-hour freeze + fraud-ring linking + charge-sheet drafting. TGCSB 2024: 1.14L complaints, ₹1,866cr lost; TS has India's highest cybercrime rate. **Prajavani-identical, hard ROI.** | `cybercrime-tgcsb.md` |
| 2 | **State Police — charge-sheet/BNSS** (Police) | FIR→charge-sheet under the BNSS 60/90-day custody clock; IPC→BNS section-mapping; default-bail leakage. TSCOP breach = the offline argument. | `state-police-chargesheet.md` |
| 3 | **Land Mutation & ROR Correction** (Revenue) | Mutation + record-of-rights correction on Bhu Bharati/Webland. Dharani's 6.46L pending grievances; 66% of civil suits are land. Direct Revenue sibling of the exemplar. | `land-mutation-ror.md` |
| 4 | **CID — Economic Offences & Anti-Human-Trafficking** (Police) | Read seized ledgers/bank statements → link victims & mule-accounts across documents → **draft the fund-trail + investigation report.** Falcon ₹4,215cr / AgriGold ₹7,000cr scams; trafficking 3.7% conviction. **Genuine document-synthesis AI.** | `cid-economic-offences.md` |
| 5 | **Aarogyasri claim pre-authorization** (Health) | Pre-auth + claim audit + upcoding detection. NAFU blocked ₹678cr; CAG found ₹6.97cr paid on dead-patient claims. **PHI of ~1 crore families = maximal offline case.** | `aarogyasri-preauth.md` |
| 6 | **District Collectorate Coordination** (Revenue) | Summarize 20+ department feeds into the Collector's review brief + **draft VIP replies & tasking letters.** TG-DMS = 87 params × 20 depts; 15-day MP-reference rule. **Natural expansion of the deployed Prajavani copilot, same sponsor.** | `collectorate-coordination.md` |
| 7 | **Directorate of Prosecutions** (Judiciary) | Charge-sheet sufficiency-scrutiny + legal-opinion drafting — the leak is *after* charging. Executive (Home-Dept) sale; strongest air-gap case in the judiciary cluster. | `directorate-prosecutions.md` |
| 8 | **High Courts — Registry** (Judiciary) | e-filing defect-scrutiny + cause-list + judgment-indexing. ~60L cases pending across HCs; the defect "battle." **Registry/clerical wedge only — never adjudication.** | `high-court-registry.md` |
| 9 | **ePASS Scholarship verification** (Education) | Eligibility + institution-genuineness (U-DISE) + duplicate/fraud detection. Ghost-institution fraud; caste/income/Aadhaar of minors = sensitive PII. **Textbook verify + defect-check.** | `epass-scholarship.md` |

---

## Recommended pilot sequencing
- **Lead here (hungriest customers, hard ROI, airtight offline, Prajavani-identical):** **Cybercrime** and
  **Aarogyasri**. Both are near-clones of the proven Revenue copilot with a measurable money metric
  (funds frozen/refunded; pre-payment fraud blocked).
- **Fastest institutional path (natural expansion of the deployed Prajavani exemplar, same Collector sponsor):**
  **District Collectorate Coordination** and **Land Mutation** — one desk higher / the direct Revenue sibling.
- **Easiest executive-department entry:** **Directorate of Prosecutions** (Home Dept, nascent digitisation).
- **Highest genuine-AI leverage, deploy with strong HITL:** **CID** (economic-fraud document synthesis) and
  **ePASS** (fraud / ghost-institution detection) — high per-case value, heterogeneous cases.
- **Highest prestige, registry-only wedge:** **High Courts** — on the e-Committee/NIC-controlled CIS stack.
- **Flagship prize (bigger integration lift):** **State Police** charge-sheet under the new criminal codes.

---

## Cross-cutting themes
- **Sovereignty by architecture, not policy.** Air-gapped on-prem open-weights model (Ollama) in the State
  Data Centre; no cloud AI APIs. Fully offline is delivered by the **local model** — that is the whole product.
- **Bilingual by default.** Every agent works in **Telugu and English**; VirtualAI already ships ~16 seeded
  government-department agents (police FIR/BNS/CCTNS, MRO/revenue, collector, health, disaster, municipality,
  registration, education, …) — real proof points, not vaporware. _(Telugu handwritten OCR is explicitly out
  of scope; all inputs are already-digital, typed records.)_
- **The officer decides. Always.** Decision-support, not decision-making — the file moves faster, but on the
  officer's authority, with a full audit trail.
- **Measured, not promised.** Every impact number in every brief is illustrative and **baselined in the pilot**;
  we report against the department's own measured reality.

## The standard offer — one office, twelve weeks
**Baseline** (wks 1–2: measure today's real numbers) → **Shadow mode** (wks 3–8: AI runs alongside, nothing
changes for citizens) → **Assisted live** (wks 9–12: officers work with the copilot, results reported against
baseline). **What we need:** read-only data access (nightly extract via CGG/NIC first, live APIs later), one
nodal officer, one office willing to go first.

---

_Supporting files: `shortlist.md` (all 28 candidates scored across 4 clusters) · `01_capability_inventory.md`
(truthful offline-safe capability list) · `wave1/` (cluster research) · `departments/` (the nine briefs)._
