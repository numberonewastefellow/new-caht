# VirtualAI — Truthful Capability Inventory (for the Government GTM)

_Purpose: keep every claim in the department briefs honest. This is what VirtualAI can and cannot do, and —
critically — what runs **fully offline** vs what **reaches an external service**. The pitch's central promise
("data never leaves your infrastructure") is architecturally true **only when paired with a local LLM**; say
so plainly. Evidence is in the repo (`backend/om/…`, `web/src/…`) and the office-mcp / code-interpreter
containers._

## The one thing that makes "offline" true
- **Local LLM (Ollama / any OpenAI-compatible local endpoint).** VirtualAI supports Ollama as a first-class
  provider — an on-prem, open-weights model with no cloud API. **This is the linchpin.** With a cloud LLM
  selected (OpenAI/Anthropic/Azure/Bedrock/Vertex/OpenRouter) prompts leave the network; with Ollama they do
  not. Every "fully offline / air-gapped" claim in the briefs is qualified by this.

## Capability → offline status

| Capability | What it does | Offline? |
|---|---|---|
| **AI Agents / personas** | Subject-expert copilots grounded in the department's own records; custom prompts, attachable tools, per-agent model, knowledge/document-set grounding | 🟢 Offline (config) |
| **Workflows** | Multi-step pipelines: **sequential** + **llm_decision** orchestration, **HITL** (human-in-the-loop pause/resume for officer sign-off), **conditional router**, per-step overrides, crash-recovery checkpoints, execution trace/graph | 🟢 Offline (LLM call follows provider choice) |
| **Two workflow editors** | Form/wizard editor + node-based visual builder (drag-and-drop) | 🟢 Offline |
| **RAG / search** | Hybrid retrieval (BM25 keyword + dense vector) over knowledge files/connectors on **self-hosted OpenSearch**; **local embedding + rerank model server**; permission-aware (ACL) index | 🟢 Offline (self-hosted) |
| **Document parsing / extraction** | Local text extraction for PDF/DOCX/PPTX/XLSX/CSV/TXT/HTML/EML/EPUB/JSON; encrypted-Office detection | 🟢 Offline (local) |
| **Office document generation** | DOCX/PPTX/**PDF** generation via the self-hosted **office-mcp-server** (python-docx/pptx + LibreOffice headless) — the "auto-draft the letter/register/report" automation | 🟡 Offline via a self-hosted container (local only) |
| **Code interpreter (PythonTool)** | Runs Python in a **self-hosted sandbox container** — data analysis/compute; streaming + self-heal | 🟡 Offline via a self-hosted container |
| **Connectors (~50)** | Ingest from Web/File/Folder/IMAP/SharePoint/Confluence/Jira/GDrive/Slack/S3/… | 🟡 Local sources fully offline; SaaS-source connectors reach that vendor's cloud (the *code* is local, the *source* isn't) |
| **Security / deployment** | Self-hosted Docker; **SSO (SAML/OIDC)**, **SCIM** provisioning, **RBAC/teams**, multi-tenant, API keys/PAT; telemetry-off | 🟢 Offline with an on-prem IdP |
| **Telugu / English** | Bilingual agents already shipped (the ~16 seeded gov agents run in Telugu + English) | 🟢 Offline — but quality depends on the chosen LLM, not a VirtualAI-native language model |
| **LLM for generation** | The reasoning engine | 🟢 via **Ollama / OpenAI-compatible local**; 🔴 via OpenAI/Anthropic/Azure/Bedrock/Vertex/OpenRouter |
| **Web search** | SearXNG/SmartSearch/built-in crawler, or Exa/Brave/Serper/Google | 🟡 needs the public internet — **not usable in a true air-gap**; keep it out of air-gapped pitches |
| **Image generation** | OpenAI/Azure/Vertex only | 🔴 **Cloud only — never market as offline** |
| **Telugu HANDWRITTEN OCR** | — | ❌ **Not a product capability. Out of scope. Do not feature.** |

## Real proof points to cite (already in the product)
- **~16 seeded government-department agents** exist in the codebase (`backend/tests/agents_creator/assistants/`):
  police FIR/BNS/BNSS/CCTNS, MRO/revenue, collector, health, disaster management, law & order, village
  administration, municipality, irrigation, registration, finance/treasury, education, etc. — bilingual
  Telugu/English. These are demonstrable, not vaporware.
- **The Revenue "Prajavani" copilot + RDO prototype** the client already built = the working exemplar every
  department brief re-points.

## Honesty rules (enforced across all briefs)
1. "Fully offline / air-gapped" → always qualify with "when paired with the local (Ollama) open-weights model."
2. Never present image generation, cloud LLMs, external web search, or SaaS-source connectors as offline.
3. Never feature Telugu handwritten OCR (absent). Telugu/English **generation & extraction on digital text** is fine.
4. AI is **decision-support**: it drafts and flags with confidence + citations; the officer decides and signs.
5. Projections are **illustrative, baselined in the pilot** — "we report against measured reality, not claims."
