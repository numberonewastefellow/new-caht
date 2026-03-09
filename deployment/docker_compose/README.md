# Welcome to VertualAI

To set up VertualAI there are several options, VertualAI supports the following for deployment:
1. Quick guided install via the install.sh script
2. Pulling the repo and running `docker compose up -d` from the deployment/docker_compose directory
  - Note, it is recommended to copy over the env.template file to .env and edit the necessary values
3. For large scale deployments leveraging Kubernetes, there are two options, Helm or Terraform.

This README focuses on the easiest guided deployment which is via install.sh.

**For more detailed guides, please refer to the documentation: https://docs.vertualai.app/deployment/overview**

## install.sh script

```
curl -fsSL https://raw.githubusercontent.com/vertualai/vertualai/main/deployment/docker_compose/install.sh > install.sh && chmod +x install.sh && ./install.sh
```

This provides a guided installation of VertualAI via Docker Compose. It will deploy the latest version of VertualAI
and set up the volumes to ensure data is persisted across deployments or upgrades.

The script will create an onyx_data directory, all necessary files for the deployment will be stored in
there. Note that no application critical data is stored in that directory so even if you delete it, the
data needed to restore the app will not be destroyed.

The data about chats, users, etc. are instead stored as named Docker Volumes. This is managed by Docker
and where it is stored will depend on your Docker setup. You can always delete these as well by running
the install.sh script with --delete-data.

To shut down the deployment without deleting, use install.sh --shutdown.

### Upgrading the deployment
VertualAI maintains backwards compatibility across all minor versions following SemVer. If following the install.sh script (or through Docker Compose), you can
upgrade it by first bringing down the containers. To do this, use `install.sh --shutdown`
(or `docker compose down` from the directory with the docker-compose.yml file).

After the containers are stopped, you can safely upgrade by either re-running the `install.sh` script (if you left the values as default which is latest,
then it will automatically update to latest each time the script is run). If you are more comfortable running docker compose commands, you can also run
commands directly from the directory with the docker-compose.yml file. First verify the version you want in the environment file (see below),
(if using `latest` tag, be sure to run `docker compose pull`) and run `docker compose up` to restart the services on the latest version

### Environment variables
The Docker Compose files try to look for a .env file in the same directory. The `install.sh` script sets it up from a file called env.template which is
downloaded during the initial setup. Feel free to edit the .env file to customize your deployment. The most important / common changed values are
located near the top of the file.

IMAGE_TAG is the version of VertualAI to run. It is recommended to leave it as latest to get all updates with each redeployment.

## Arize Phoenix — LLM Observability & Tracing

Phoenix provides real-time LLM observability: trace every LLM call, tool invocation, and agent handoff with full input/output capture, token usage, cost tracking, and latency analysis.

### What Gets Traced

| Span Kind | Captured Data                                                                                                          |
| --------- | -------------------------------------------------------------------------------------------------------------------------- |
| **LLM**   | Model name, input/output, token usage (prompt/completion/cache), cost, reasoning, time-to-first-action, model parameters |
| **Tool**  | Tool name, input/output (e.g. `internal_search` with Vespa results)                                                      |
| **Agent** | Agent name, available tools, handoffs, output type                                                                        |
| **Chain** | Generic spans for pipeline steps                                                                                          |

All spans are nested in a trace hierarchy: `root → LLM → Tool → LLM → ...`

### Enable Phoenix

1. **Set the environment variable** in your `.env` file:
   ```
   PHOENIX_COLLECTOR_ENDPOINT=http://phoenix:6006/v1/traces
   ```

2. **Start the stack** (Phoenix container is included in `docker-compose.yml`):
   ```bash
   # Standard deployment
   docker compose up -d

   # Windows dev (exposes Phoenix UI on port 6006)
   docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml up -d
   ```

3. **Open the Phoenix dashboard**: <http://localhost:6006>

That's it. The backend auto-detects the endpoint and starts exporting traces via OTLP/HTTP.

### Disable Phoenix

Remove or comment out `PHOENIX_COLLECTOR_ENDPOINT` in `.env` and restart the backend containers:

```bash
docker compose up -d api_server background
```

The Phoenix container will still run but receive no traces. To stop it entirely, stop the `phoenix` service.

### Architecture

```
api_server / background
    └── PhoenixTracingProcessor (OTLP/HTTP)
            └── BatchSpanProcessor (queue: 4096, batch: 512, flush: 2s)
                    └── OTLPSpanExporter → http://phoenix:6006/v1/traces
                            └── Phoenix container (SQLite storage at /phoenix_data)
```

- No Phoenix SDK required — uses standard OpenTelemetry packages already in the dependency tree
- Runs alongside other tracing providers (Langfuse, Braintrust) without conflict
- Data persists in the `phoenix_data` Docker volume (or `E:/temp/vert/phoenix_data` in dev-windows)
- Sensitive data is masked before export (same masking as Langfuse)

### Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PHOENIX_COLLECTOR_ENDPOINT` | *(empty — disabled)* | OTLP/HTTP endpoint for Phoenix. Set to `http://phoenix:6006/v1/traces` to enable. |

### Verify Traces Are Flowing

After sending a chat message, check the Phoenix GraphQL API:

```bash
curl -s http://localhost:6006/graphql -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "{ projects { edges { node { name traceCount } } } }"}'
```

Expected: `traceCount > 0`

### Production Notes

- Pin `arizephoenix/phoenix` to a specific version tag (e.g. `arizephoenix/phoenix:8.0.0`) instead of `latest`
- For high-throughput deployments, consider running Phoenix with PostgreSQL storage instead of the default SQLite — see [Phoenix docs](https://docs.arize.com/phoenix/deployment)
- The BatchSpanProcessor queue (4096 spans) will drop spans under extreme load rather than blocking the backend
- Phoenix port 6006 is **not exposed** by default in production compose — only in dev overrides

---

## SmartSearch AI (Perplexica) Setup

SmartSearch AI is an AI-powered web search provider that uses [Perplexica](https://github.com/ItzCrazyKns/Perplexica) as its backend.
The Perplexica source code lives at `Perplexica/` in the repo root and is built as the `smartsearch` service in `docker-compose.yml`.

### How It Works

Perplexica runs a 4-stage pipeline for each search request:
1. **Classifier** — Rewrites the query into a standalone form and classifies search type
2. **Researcher** — Agentic loop that generates SEO keyword queries and searches via SearxNG (iteration limits: speed=2, balanced=6, quality=25)
3. **Writer** — Synthesizes an AI answer with `[N]` citations from search results
4. **Response** — Returns `{message, sources[]}` to VirtualAI

### First-Time Configuration

After starting the stack, Perplexica needs its LLM providers configured:

1. **Build and start the stack** (first time builds Perplexica from `../../Perplexica`):
   ```
   docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml up -d --build
   ```

2. **Configure Perplexica's LLM providers** — Open `http://localhost:3001` in your browser and set up:
   - **Chat Model**: Select an OpenAI-compatible provider (e.g., your existing OpenAI API key)
   - **Embedding Model**: Select a Transformers-based local model or an API provider

3. **Get Perplexica's provider IDs** (needed for VirtualAI config):
   ```
   curl http://localhost:3001/api/providers
   ```
   Note the `chatModelProviders` and `embeddingModelProviders` IDs from the response.

4. **Configure VirtualAI to use SmartSearch**:
   - Go to **Admin > Web Search** in VirtualAI
   - Select **SmartSearch AI** as the provider
   - Set **Base URL**: `http://smartsearch:3000` (Docker internal network)
   - Save and activate

### Networking Notes

- Perplexica listens on port 3000 inside the container, mapped to 3001 on the host (since nginx uses 3000)
- VirtualAI services should use `http://smartsearch:3000` (Docker DNS) — not `localhost`
- The dev-windows override maps the data volume to `E:/temp/vert/smartsearch_data`

### Building from Source

Perplexica is a Next.js app that compiles to `.next/standalone`. Unlike Python services, you cannot
bind-mount the source code for live reloading. After editing files in `Perplexica/src/`, rebuild:

```
docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml build smartsearch
docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml up -d smartsearch
```

### SearxNG Configuration

Perplexica bundles its own SearxNG instance internally. The dev-windows override mounts
`Perplexica/searxng/settings.yml` directly into the container, so you can edit it locally
and restart the container to apply changes (no rebuild needed):

```
docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml restart smartsearch
```

Common fixes:
- Disable DuckDuckGo if you get CAPTCHA blocks (enable Google + Bing instead)
- For production, consider using a paid search API (Serper, Brave Search) instead of SearxNG scrapers

### Architecture Notes

See `SMARTSEARCH_AI_INTEGRATION.md` in the project root for a detailed analysis of:
- The full Perplexica pipeline internals
- Known limitations (double LLM cost, multiplicative search explosion, double query rewriting)
- Four improvement options (A-D) for production deployments
