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



## 🔍 Search Engine (OpenSearch)

VertualAI uses **OpenSearch** as its document index — indexing and retrieval both run on it, on by
default with **zero configuration**. (Vespa, the previous backend, has been removed.) The local stack
is built/run via `deployment/docker_compose/dev.bat` (`dev build`, `dev up`, `dev down`); all config
lives in `deployment/docker_compose/.env` (see `deployment/docker_compose/env.template`).

The `opensearch` service starts by default — there is no engine profile to toggle and no runtime
retrieval switch. `COMPOSE_PROFILES` only needs `s3-filestore` (MinIO for file storage):

```bash
COMPOSE_PROFILES=s3-filestore
```

Index schemas are created automatically on backend startup by `verify_and_create_index_if_necessary`.
There is no manual Alembic step for the index — Alembic migrations only build the Postgres schema and
are engine-agnostic; they run automatically on backend startup.

### Disable search entirely
`DISABLE_VECTOR_DB=true` turns the document index off — connectors and RAG search are disabled, but
chat, tools, and file uploads still work.

### Key environment variables

| Variable | Default | Purpose |
|---|---|---|
| `COMPOSE_PROFILES` | `s3-filestore` | Compose profiles to start (keep `s3-filestore` for MinIO) |
| `OPENSEARCH_ADMIN_PASSWORD` | `StrongPassword123!` | OpenSearch admin password (must be strong; OpenSearch 2.12+ requires it) |
| `OPENSEARCH_HOST` | `opensearch` | Backend → OpenSearch host (compose service name) |
| `OPENSEARCH_USE_SSL` | `true` | Use HTTPS to talk to OpenSearch |
| `OPENSEARCH_IMAGE_TAG` | `3.6.0` | OpenSearch Docker image tag |
| `OPENSEARCH_JAVA_OPTS` | `-Xms2g -Xmx2g` | OpenSearch JVM heap (~50% of its memory limit) |
| `DISABLE_VECTOR_DB` | `false` | `true` = disable the document index (no RAG) |

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

### Default "Files & Chunks" dashboard

A ready-made dashboard (no query writing) shows **total files / chunks**, lets you **drill into
chunks by file**, and breaks down **files per workspace**. Import it once (idempotent):

```bash
cd deployment/docker_compose/opensearch_dashboards
./import_dashboards.sh          # or: bash import_dashboards.sh
```

Then open **[localhost:5601](http://localhost:5601)** → **☰ (menu) → Dashboard → "VirtualAI — Files & Chunks"**
(it's under the **Dashboard** app, _not_ "Dashboards Management"). The import targets the **Global**
tenant so it's visible to everyone; if you don't see it, switch tenant via the top-right user menu →
**Switch tenants → Global**. It contains:

- **Total Files** (unique `document_id`) and **Total Chunks** metrics.
- **Files** table — each file (filename + `document_id`) with its chunk count.
- **Files by Workspace** table — `user_workspaces` → number of files and chunks.
- **Chunk Text** panel — the chunk rows; expand a row to read the full `content`.

**Drill-down:**

- Click a file in the **Files** table → the **Chunk Text** panel filters to that file → expand a row to read its text.
- Click a workspace value in **Files by Workspace** (e.g. `6`) → everything scopes to that workspace. You can also type KQL in the dashboard search bar, e.g. `user_workspaces: 6`.

> The dashboard saved objects live in
> `deployment/docker_compose/opensearch_dashboards/files_and_chunks.ndjson` (regenerate with
> `python build_ndjson.py`). Re-running the import overwrites/updates them.


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
