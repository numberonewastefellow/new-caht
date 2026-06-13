<a name="readme-top"></a>

<h2 align="center">
    <a href="https://www.vertualai.app/?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme"> <img width="50%" src="https://github.com/vertualai/vertualai/blob/logo/VertualAILogoCropped.jpg?raw=true" /></a>
</h2>

<p align="center">Open Source AI Platform</p>

<p align="center">
    <a href="https://discord.gg/TDJ59cGV2X" target="_blank">
        <img src="https://img.shields.io/badge/discord-join-blue.svg?logo=discord&logoColor=white" alt="Discord" />
    </a>
    <a href="https://docs.vertualai.app/?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme" target="_blank">
        <img src="https://img.shields.io/badge/docs-view-blue" alt="Documentation" />
    </a>
    <a href="https://www.vertualai.app/?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme" target="_blank">
        <img src="https://img.shields.io/website?url=https://www.vertualai.app&up_message=visit&up_color=blue" alt="Documentation" />
    </a>
    <a href="https://github.com/vertualai/vertualai/blob/main/LICENSE" target="_blank">
        <img src="https://img.shields.io/static/v1?label=license&message=MIT&color=blue" alt="License" />
    </a>
</p>

<p align="center">
  <a href="https://trendshift.io/repositories/12516" target="_blank">
    <img src="https://trendshift.io/api/badge/repositories/12516" alt="vertualai/vertualai | Trendshift" style="width: 250px; height: 55px;" />
  </a>
</p>


**[VertualAI](https://www.vertualai.app/?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme)** is a feature-rich, self-hostable Chat UI that works with any LLM. It is easy to deploy and can run in a completely airgapped environment.

VertualAI comes loaded with advanced features like Agents, Web Search, RAG, MCP, Deep Research, Connectors to 40+ knowledge sources, and more.

> [!TIP]
> Run VertualAI with one command (or see deployment section below):
> ```
> curl -fsSL https://raw.githubusercontent.com/vertualai/vertualai/main/deployment/docker_compose/install.sh > install.sh && chmod +x install.sh && ./install.sh
> ```

****

![VertualAI Chat Silent Demo](https://github.com/vertualai/vertualai/releases/download/v0.21.1/VertualAIChatSilentDemo.gif)



## ⭐ Features
- **🤖 Custom Agents:** Build AI Agents with unique instructions, knowledge and actions.
- **🌍 Web Search:** Browse the web with Google PSE, Exa, and Serper as well as an in-house scraper or Firecrawl.
- **🔍 RAG:** Best in class hybrid-search + knowledge graph for uploaded files and ingested documents from connectors. 
- **🔄 Connectors:** Pull knowledge, metadata, and access information from over 40 applications.
- **🔬 Deep Research:** Get in depth answers with an agentic multi-step search.
- **▶️ Actions & MCP:** Give AI Agents the ability to interact with external systems.
- **💻 Code Interpreter:** Execute code to analyze data, render graphs and create files.
- **🎨 Image Generation:** Generate images based on user prompts.
- **👥 Collaboration:** Chat sharing, feedback gathering, user management, usage analytics, and more.

VertualAI works with all LLMs (like OpenAI, Anthropic, Gemini, etc.) and self-hosted LLMs (like Ollama, vLLM, etc.)

To learn more about the features, check out our [documentation](https://docs.vertualai.app/welcome?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme)!



## 🚀 Deployment
VertualAI supports deployments in Docker, Kubernetes, Terraform, along with guides for major cloud providers.

See guides below:
- [Docker](https://docs.vertualai.app/deployment/local/docker?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme) or [Quickstart](https://docs.vertualai.app/deployment/getting_started/quickstart?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme) (best for most users)
- [Kubernetes](https://docs.vertualai.app/deployment/local/kubernetes?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme) (best for large teams)
- [Terraform](https://docs.vertualai.app/deployment/local/terraform?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme) (best for teams already using Terraform)
- Cloud specific guides (best if specifically using [AWS EKS](https://docs.vertualai.app/deployment/cloud/aws/eks?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme), [Azure VMs](https://docs.vertualai.app/deployment/cloud/azure?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme), etc.)

> [!TIP]  
> **To try VertualAI for free without deploying, check out [VertualAI Cloud](https://cloud.vertualai.app/signup?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme)**.



## 🔍 Search Engine Configuration (Vespa / OpenSearch)

VertualAI supports two interchangeable search/index backends — **Vespa** (default) and
**OpenSearch** — behind a single unified interface. You can run either one, run both at once
(dual-index) and switch which one serves retrieval at runtime, or disable search entirely.

All configuration is done through `deployment/docker_compose/.env` (see
`deployment/docker_compose/env.template` for the documented block). The local stack is built/run via
`deployment/docker_compose/dev.bat` (`dev build`, `dev up`, `dev down`).

### Default: Vespa only
The shipped `.env` sets `COMPOSE_PROFILES=s3-filestore,vespa`, so the Vespa `index` container runs and
serves both indexing and retrieval, and `ONYX_DISABLE_VESPA` defaults to `false`. Keep `vespa` in
`COMPOSE_PROFILES` for this default setup (it's a profile-gated container — see "How the engine
containers are gated" below).

### Enable OpenSearch (run both, switchable)
The OpenSearch container is **opt-in** via a compose profile, so it does not run unless you ask for it.
In `deployment/docker_compose/.env`:

```bash
# 1) Start the OpenSearch container ALONGSIDE Vespa (keep "vespa" so both run)
COMPOSE_PROFILES=s3-filestore,vespa,opensearch

# 2) Set a strong admin password (OpenSearch 2.12+ requires it)
OPENSEARCH_ADMIN_PASSWORD=StrongPassword123!

# 3) Also index documents into OpenSearch (so it has data to serve)
ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true
```

Then rebuild and start: `dev build` (or `dev up`). Vespa stays the retrieval engine until you switch.

### `.env` engine controls (which containers run + indexing)
Each engine container is gated by a compose profile, so `COMPOSE_PROFILES` turns an engine **on/off
permanently** (no leftover container): `vespa` starts the Vespa `index` container, `opensearch` starts
the OpenSearch container. Always keep `s3-filestore` (MinIO). Set, then `dev up`.

| Goal | `COMPOSE_PROFILES` | `ENABLE_OPENSEARCH_INDEXING_FOR_ONYX` | `ONYX_DISABLE_VESPA` |
|---|---|---|---|
| **[A] Vespa only** (default) | `s3-filestore,vespa` | `false` | `false` |
| **[B] Both engines** (dual-index) | `s3-filestore,vespa,opensearch` | `true` | `false` |
| **[C] OpenSearch only** (no Vespa container) | `s3-filestore,opensearch` | `true` | `true` |

```bash
# [B] Run both engines:
COMPOSE_PROFILES=s3-filestore,vespa,opensearch
OPENSEARCH_ADMIN_PASSWORD=StrongPassword123!
ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true
```

> For mode **[C]**, switch retrieval to OpenSearch **before** selecting it (see next section),
> otherwise the backend raises `ONYX_DISABLE_VESPA is set but opensearch_retrieval_enabled is not set`.

#### How the engine containers are gated (for reference)
Both search engines are optional compose services controlled purely by `COMPOSE_PROFILES`:
- The Vespa `index` service has `profiles: ["vespa"]`; the OpenSearch service has `profiles: ["opensearch"]`.
- `api_server` / `background` do **not** `depends_on` the search engine, so an engine that's off is never
  force-started (the backend retries the index connection on startup).
- `dev.bat`'s `INFRA` group no longer lists the engine; a full `dev up` (or `docker compose up`) starts
  whichever engines are active in `COMPOSE_PROFILES`. Use `dev up vespa` to start Vespa explicitly.

Consequence: `dev up` / `docker compose up` only starts an engine whose profile is active — so an engine
you remove from `COMPOSE_PROFILES` stays **off permanently across restarts** (no leftover container, no
`dev stop` needed). The trade-off: **you must keep `vespa` in `COMPOSE_PROFILES` for the default Vespa
setup**, or Vespa won't start.

### Which engine answers searches (retrieval) — runtime toggle, no rebuild
When both engines run, **which one serves retrieval is a DB-backed toggle**, not an env var. It is
resolved by `get_opensearch_retrieval_state` (`backend/onyx/db/opensearch_migration.py`):
the DB record's `enable_opensearch_retrieval` flag (default **`false`** = Vespa) wins; the
`ENABLE_OPENSEARCH_RETRIEVAL_FOR_ONYX` env var is **only a bootstrap fallback used until that record
exists** — and the backfill task creates the record as soon as indexing is enabled, so in practice you
switch retrieval through the **admin API** (admin auth required):

```bash
# Check migration progress
GET  /api/admin/opensearch-migration/status
# Check current retrieval engine
GET  /api/admin/opensearch-migration/retrieval
# Switch retrieval to OpenSearch (false = back to Vespa)
PUT  /api/admin/opensearch-migration/retrieval   {"enable_opensearch_retrieval": true}
```

Easiest locally: log into the web UI as an admin, then run in the browser DevTools console
(the session cookie is sent automatically):

```js
await fetch('/api/admin/opensearch-migration/retrieval', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ enable_opensearch_retrieval: true }),
}).then(r => r.json());
```

A background task ports existing Vespa documents into OpenSearch once indexing is enabled, so there is
data to serve before you flip the toggle (watch `/status` until `migration_completed_at` is set).

### OpenSearch-only mode (Vespa container never starts)
Because the Vespa `index` service is profile-gated, simply **omitting `vespa` from
`COMPOSE_PROFILES`** means the container is never created — no `dev stop vespa` needed, and it stays off
across restarts. First run both engines (above), let the backfill finish, and switch retrieval to
OpenSearch; **then** set in `.env`:

```bash
COMPOSE_PROFILES=s3-filestore,opensearch
ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true
ENABLE_OPENSEARCH_RETRIEVAL_FOR_ONYX=true
ONYX_DISABLE_VESPA=true
```

`dev up` now starts everything except Vespa. To go back, restore `vespa` in `COMPOSE_PROFILES` and set
`ONYX_DISABLE_VESPA=false`.

#### Brand-new deployment that never needs Vespa
On a **fresh** system there is no existing corpus to migrate, so you can go straight to OpenSearch-only —
no backfill, no admin-API switch, no special Alembic step. Alembic migrations run automatically on
backend startup and are **engine-agnostic** (they build the Postgres schema regardless of search engine);
there is no "Alembic by engine". The OpenSearch index schema is created on startup by
`verify_and_create_index_if_necessary`. Set in `.env` and `dev up`:

```bash
COMPOSE_PROFILES=s3-filestore,opensearch
OPENSEARCH_ADMIN_PASSWORD=StrongPassword123!
ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true
ENABLE_OPENSEARCH_RETRIEVAL_FOR_ONYX=true   # fresh DB has no toggle record, so this is used directly
ONYX_DISABLE_VESPA=true
DISABLE_OPENSEARCH_MIGRATION_TASK=true      # no Vespa corpus to migrate; skips the backfill task
```

### Helper scripts (migrating an existing Vespa deployment)
`deployment/docker_compose/switch-retrieval-to-opensearch.{sh,bat}` automate the migration switch: they
poll the backfill status until it completes, then flip retrieval to OpenSearch. They need an admin API
key (UI → Admin → API Keys).

```bash
# after `dev up` in mode [B]:
ONYX_API_KEY=<key> ./switch-retrieval-to-opensearch.sh            # wait for backfill, then switch
ONYX_API_KEY=<key> ./switch-retrieval-to-opensearch.sh --revert   # switch back to Vespa
```
On Windows: `set ONYX_API_KEY=<key>` then `switch-retrieval-to-opensearch.bat`. (Not needed for a
brand-new OpenSearch-only system — that's handled entirely by `.env` above.)

### Disable search entirely
`DISABLE_VECTOR_DB=true` turns off both engines — connectors and RAG are disabled, but chat, tools, and
file uploads still work.

### Key environment variables

| Variable | Default | Purpose |
|---|---|---|
| `COMPOSE_PROFILES` | `s3-filestore,vespa` | Engine containers to start: `vespa` and/or `opensearch` (keep `s3-filestore` for MinIO) |
| `ONYX_DISABLE_VESPA` | `false` | `true` = run OpenSearch only (no Vespa) |
| `ENABLE_OPENSEARCH_INDEXING_FOR_ONYX` | `false` | `true` = also index into OpenSearch |
| `ENABLE_OPENSEARCH_RETRIEVAL_FOR_ONYX` | `false` | Fallback retrieval engine (runtime DB toggle wins) |
| `OPENSEARCH_ADMIN_PASSWORD` | `StrongPassword123!` | OpenSearch admin password (must be strong) |
| `OPENSEARCH_HOST` | `opensearch` | Backend → OpenSearch host (compose service name) |
| `OPENSEARCH_USE_SSL` | `true` | Use HTTPS to talk to OpenSearch |
| `OPENSEARCH_IMAGE_TAG` | `3.6.0` | OpenSearch Docker image tag |
| `OPENSEARCH_JAVA_OPTS` | `-Xms2g -Xmx2g` | OpenSearch JVM heap (~50% of its memory limit) |
| `DISABLE_VECTOR_DB` | `false` | `true` = disable both engines (no RAG) |

> Index schemas are created automatically on backend startup (no manual Alembic). The first run with a
> new engine provisions its schema before indexing begins.



## 🔍 Other Notable Benefits
VertualAI is built for teams of all sizes, from individual users to the largest global enterprises.

- **Enterprise Search**: far more than simple RAG, VertualAI has custom indexing and retrieval that remains performant and accurate for scales of up to tens of millions of documents.
- **Security**: SSO (OIDC/SAML/OAuth2), RBAC, encryption of credentials, etc.
- **Management UI**: different user roles such as basic, curator, and admin.
- **Document Permissioning**: mirrors user access from external apps for RAG use cases.



## 🌱 Database Seeding (Restore Agents & Workflows)

After a fresh deployment or database reset, use `seed_all.py` to restore all LLM providers, agents, and workflows in one command.

```bash
cd backend/tests

# Seed everything (default: http://localhost:3000, key from agents_creator/apikey.txt)
python seed_all.py

# Custom target and API key
python seed_all.py --url http://localhost:3000 --key <your-api-key>

# With LLM provider API key (e.g. OpenRouter)
python seed_all.py --llm-key sk-or-...
```

**Options:**

| Flag | Description |
| ---- | ----------- |
| `--only providers` | Seed only LLM providers |
| `--only agents` | Seed only standalone agents (153 agents from 31 JSON files) |
| `--only workflows` | Seed only workflows (36 workflows from 36 JSON files) |
| `--force` | Re-create even if name already exists |
| `--dry-run` | Preview what would be created without making changes |
| `--no-icons` | Skip icon generation for workflow wrapper personas |
| `--llm-key KEY` | API key for LLM provider (or set `LLM_API_KEY` env var) |
| `--url URL` | Target VirtualAI instance (default: `http://localhost:3000`) |
| `--key KEY` | VirtualAI API key (default: from `agents_creator/apikey.txt`) |

**Dependency order** (handled automatically):

1. LLM Providers → from `backend/tests/llm_providers.json`
2. Standalone Agents → from `backend/tests/agents_creator/assistants/*.json`
3. Workflows → from `backend/tests/workflow_creator/workflows/*.json`

The script is **idempotent** — safe to run multiple times. Existing items are skipped by name.


## 🔍 OpenSearch Dashboards (Dev Tools GUI)

A Kibana-equivalent UI for inspecting/querying the OpenSearch index in dev (Dev Tools console,
Query Workbench, Discover). It runs as a **standalone, opt-in** compose service that joins the
existing dev network and connects to the `opensearch` container over TLS.

**Manage lifecycle** (from `deployment/docker_compose/`):

```bash
# start
docker compose -p virtualai-dashboards -f docker-compose.opensearch-dashboards.yml up -d
# stop
docker compose -p virtualai-dashboards -f docker-compose.opensearch-dashboards.yml down
```

**How to use it:**

1. Open **[localhost:5601](http://localhost:5601)** → log in `admin` / `StrongPassword123!`.
2. Go to **☰ → Management → Dev Tools** and run, e.g.:

```jsonc
GET _cat/indices?v
GET danswer_chunk_nomic_ai_nomic_embed_text_v1/_count
GET danswer_chunk_nomic_ai_nomic_embed_text_v1/_search
{ "query": { "term": { "source_type": "user_file" } }, "size": 5 }
```

> Tip: the index name follows your embedding model (here `nomic-embed-text-v1`). Use
> `GET _cat/indices?v` to list the actual `danswer_chunk_*` index.


## 🚧 Roadmap
To see ongoing and upcoming projects, check out our [roadmap](https://github.com/orgs/vertualai/projects/2)!



## 📚 Licensing
There are two editions of VertualAI:

- VertualAI Community Edition (CE) is available freely under the MIT license.
- VertualAI Enterprise Edition (EE) includes extra features that are primarily useful for larger organizations.
For feature details, check out [our website](https://www.vertualai.app/pricing?utm_source=vertualai_repo&utm_medium=github&utm_campaign=readme).



## 👪 Community
Join our open source community on **[Discord](https://discord.gg/TDJ59cGV2X)**!



## 💡 Contributing
Looking to contribute? Please check out the [Contribution Guide](CONTRIBUTING.md) for more details.
