# Third-Party Notices and Attributions

OM-AI is proprietary software (see [LICENSE](LICENSE)). It is built upon, incorporates,
and is distributed together with the open-source components listed below. Each component
remains governed by its own upstream license; this file is provided both for license
compliance and, as a courtesy, to gratefully acknowledge the projects and authors whose
work OM-AI builds on.

This is a summary of the **notable** components. Full, authoritative, per-package license
texts are distributed with each dependency — in its own package manifest, in the vendored
project's `LICENSE`/`NOTICE` files, and under `web/node_modules/` for JavaScript packages.

---

## 1. Origins and foundations

OM-AI was initially bootstrapped from a fork of the Onyx project (formerly Danswer). It has
since been extensively re-engineered and customized — it has **diverged substantially** from
that project, is **no longer compatible** with the upstream fork, and its current architecture
and feature set are built upon and depend heavily on the third-party components listed below,
most notably **Perplexica**, **OpenSearch**, **Arize Phoenix**, and others.

For attribution and license compliance, we acknowledge the original starting point:

- Onyx / Danswer — © DanswerAI, Inc. — MIT License — <https://github.com/onyx-dot-app/onyx>

Where portions of the original Onyx / Danswer code remain, the MIT license of that project
continues to apply to those portions.

---

## 2. Vendored and derived subprojects

| Component | Author / Origin | License | Location |
|-----------|-----------------|---------|----------|
| Perplexica | ItzCrazyKns — <https://github.com/ItzCrazyKns/Perplexica> | MIT | `Perplexica/` |
| Phoenix | Arize AI — <https://github.com/Arize-ai/phoenix> | Elastic License 2.0 (client sub-packages: Apache-2.0) | `phoenix/` |
| Office-PowerPoint-MCP-Server | GongRzhe — <https://github.com/GongRzhe/Office-PowerPoint-MCP-Server> | MIT | `office-mcp-server/` (derived) |
| Office-Word-MCP-Server | GongRzhe — <https://github.com/GongRzhe/Office-Word-MCP-Server> | MIT | `office-mcp-server/` (derived) |
| python-pptx | Steve Canny | MIT | dependency of `office-mcp-server/` |
| python-docx | python-openxml | MIT | dependency of `office-mcp-server/` |
| LibreOffice | The Document Foundation — <https://www.libreoffice.org/> | MPL-2.0 | PDF conversion (external) |
| Chat Widget dependencies | — | lit (BSD-3-Clause), marked (MIT), DOMPurify (Apache-2.0 / MPL-2.0) | `widget/` |

---

## 3. Major Python dependencies

These are governed by their respective upstream licenses (MIT / BSD / Apache-2.0 / MPL /
LGPL as noted). This list highlights notable named components and is not exhaustive.

- **Web / API:** FastAPI, Starlette, Uvicorn, Pydantic, fastapi-users, fastapi-limiter,
  prometheus-fastapi-instrumentator
- **LLM / AI:** LiteLLM, langchain-core, tiktoken, OpenAI SDK, Anthropic claude-agent-sdk,
  Cohere, VoyageAI, google-genai / google-cloud-aiplatform, langfuse, braintrust,
  openinference-instrumentation
- **ML / model serving:** PyTorch (torch), transformers, sentence-transformers,
  huggingface-hub, tokenizers, accelerate, safetensors, scikit-learn, scipy, numpy,
  onnxruntime, einops
- **Task queue / infrastructure:** Celery, kombu, redis, dask / distributed, kubernetes
  client, supervisor, pydocket
- **Data / database:** SQLAlchemy, Alembic, asyncpg, psycopg2-binary (LGPL), opensearch-py
- **MCP:** mcp (MIT), fastmcp (Apache-2.0)
- **Document processing:** unstructured, markitdown, chonkie, python-docx, python-pptx,
  openpyxl, pypdf, pdfminer-six, trafilatura, beautifulsoup4, magika, nltk, playwright
- **Cloud SDKs:** boto3 / botocore, aioboto3, google-api-python-client, dropbox,
  office365-rest-python-client
- **Connectors:** slack-sdk, discord.py, atlassian-python-api / jira, PyGithub,
  python-gitlab, simple-salesforce, hubspot-api-client, asana, pyairtable, zulip, exa-py,
  sendgrid, pywikibot
- **Observability:** sentry-sdk, ddtrace, opentelemetry-*, posthog, prometheus-client

---

## 4. Major JavaScript / TypeScript dependencies

Governed by their respective upstream licenses (MIT / BSD / ISC / Apache-2.0). Notable
named components; not exhaustive.

- **Framework / UI:** Next.js, React / React DOM, Tailwind CSS (+ tailwind-merge,
  tailwindcss-animate), Radix UI, Headless UI, lucide-react, @phosphor-icons/react,
  react-icons
- **State / data:** zustand, SWR, @tanstack/react-table, Formik, yup
- **Interaction / graph:** @dnd-kit/*, @xyflow/react, motion, recharts, cmdk, vaul
- **Content / markdown:** react-markdown, remark-gfm, remark-math, rehype-katex,
  rehype-highlight, rehype-sanitize, rehype-stringify, KaTeX, highlight.js, lowlight
- **Integrations:** @sentry/nextjs, @stripe/stripe-js + stripe, posthog-js, pptxgenjs
- **Utilities:** date-fns, lodash, clsx, class-variance-authority, uuid, semver, sharp,
  js-cookie, cookies-next, react-select, react-datepicker, react-day-picker,
  react-dropzone, next-themes

---

Trademarks, product names, and logos are the property of their respective owners. Their
inclusion here is for attribution only and does not imply any endorsement.
