# VirtualAI — Government GTM Package (Telangana & Andhra Pradesh)

**Offline enterprise AI — data never leaves your infrastructure.** One proven pattern, applied to nine
departments: every copilot runs **EXTRACT → CHECK HISTORY → VERIFY RECORDS → ROUTE & DRAFT**, cites its
sources, and hands the file back for the officer to check and sign. Air-gapped on-prem model (Ollama),
bilingual Telugu/English, "the officer decides — always."

## Start here
- **[00_executive_summary.md](00_executive_summary.md)** — "one pattern, every department" + pilot sequencing + the 12-week offer
- **[01_capability_inventory.md](01_capability_inventory.md)** — truthful offline-safe capability list (what's real AI vs a lookup vs cloud)
- **[shortlist.md](shortlist.md)** — all 28 candidates scored across 4 clusters + why the final 9 were chosen

## The 9 selected departments — one-line use case each

### 🚔 Police / Home
| Department | Use case (extract → check → verify → **draft**) | Brief |
|---|---|---|
| **Cybercrime — TGCSB / AP** | Extract UPI/account/phone from 1930/NCRP complaints → link mule-accounts & fraud-rings → verify vs suspect registry → **draft golden-hour freeze requests, refund petitions & charge-sheets** | [cybercrime-tgcsb.md](departments/cybercrime-tgcsb.md) |
| **State Police — charge-sheet (BNSS)** | Extract case skeleton from FIR/case-diary → check repeat-accused/MO links (text-based, *no facial recognition*) → verify BNSS compliance + IPC→BNS mapping + custody-clock → **draft the charge-sheet** | [state-police-chargesheet.md](departments/state-police-chargesheet.md) |
| **CID — Economic Offences & Anti-Human-Trafficking** | Read seized ledgers/bank statements → link victims & shell entities across documents → verify registries → **draft the fund-trail + investigation report** | [cid-economic-offences.md](departments/cid-economic-offences.md) |

### ⚖️ Judiciary
| Department | Use case | Brief |
|---|---|---|
| **Directorate of Prosecutions** | Extract from FIR/charge-sheet/case file → check completeness (witnesses, BSA §63 e-evidence, sanction) → verify sufficiency-of-evidence & sections → **draft the legal opinion / scrutiny note** | [directorate-prosecutions.md](departments/directorate-prosecutions.md) |
| **High Courts — Registry** (clerical only, *never adjudication*) | Extract e-filing metadata → check connected-matter/precedent → verify defects (fee/index/vakalatnama) → **draft defect memo + cause-list + judgment headnote** | [high-court-registry.md](departments/high-court-registry.md) |

### 🏛️ Revenue / Collectorate
| Department | Use case | Brief |
|---|---|---|
| **Land Mutation & ROR Correction** | Extract from deed/succession application → check chain-of-title → verify deed-extent vs RoR (Bhu Bharati/Webland) → **draft the mutation / correction order** | [land-mutation-ror.md](departments/land-mutation-ror.md) |
| **District Collectorate Coordination** | Summarize 20+ department feeds (TG-DMS) → check pendency/SLA outliers → extract & route MP/MLA references → **draft VIP replies, tasking letters & review minutes** | [collectorate-coordination.md](departments/collectorate-coordination.md) |

### 🏥 Citizen-service
| Department | Use case | Brief |
|---|---|---|
| **Aarogyasri Claim Pre-Authorization** | Extract from the pre-auth packet (diagnosis/ICD/investigations) → check prior claims/benefit balance → verify package vs the 1,835-procedure master + upcoding → **draft the approve/query/reject note** | [aarogyasri-preauth.md](departments/aarogyasri-preauth.md) |
| **ePASS Post-Matric Scholarship Verification** | Extract application + caste/income certs → check duplicate/ghost applications → verify income caps + institution genuineness (U-DISE) → **draft sanction/rejection with cited discrepancies** | [epass-scholarship.md](departments/epass-scholarship.md) |

**Cluster balance:** Police 3 · Judiciary 2 · Revenue 2 · Citizen-service 2.

## Also in this folder
- **`departments/_retired/`** — two candidates set aside after an honesty review (Registration-22A, Police
  Verification): their work is mostly deterministic lookup, so they were swapped for higher genuine-AI-density
  departments (CID, Collectorate Coordination). Research preserved, not deleted.
- **`wave1/`** — the four cluster research shortlists behind `shortlist.md`.

_All figures in the briefs are illustrative and baselined in the pilot — "we report against measured reality,
not claims." Not committed to git; for review._
