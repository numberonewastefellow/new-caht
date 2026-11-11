# Windows Development Setup

## Prerequisites

- Docker Desktop with WSL 2 backend enabled
- Allocate at least 6-8 GB RAM to Docker Desktop (Settings > Resources)

## Quick Start

```bat
cd deployment\docker_compose
copy env.template .env
dev build
```

The app will be available at http://localhost:3000, or https://localhost with [local HTTPS](#local-https).

## Local HTTPS

```bat
setup-local-https.bat
```

This installs `mkcert` if needed, asks Windows to trust its local certificate authority (choose Yes), and creates `deployment\data\sslcerts\ssl.crt` and `ssl.key`. Those files stay on your machine and are gitignored. Let's Encrypt can't issue for `localhost`; `init-letsencrypt.sh` is the production path.

`dev.bat` turns HTTPS on when `ssl.crt` exists. Add `WEB_DOMAIN=https://localhost` to `.env`, then run `dev up`.

| Address | What it is |
|---|---|
| https://localhost | The app |
| http://localhost, http://localhost:3000 | Redirect to https://localhost |
| https://localhost:9443 | MinIO console |
| https://localhost:6443 | Phoenix |
| https://localhost:3443 | SmartSearch |

- Postgres, Redis, OpenSearch, the API, MinIO, Phoenix, SmartSearch and Office MCP keep their host ports, but only this machine can reach them.
- Containers still talk to each other in plain HTTP on the Docker network. Scripts running on that network use `http://nginx:8088`.
- Any registered OAuth or OIDC redirect URLs need to change to `https://localhost/...`.

To go back to HTTP: delete `ssl.crt`, remove `WEB_DOMAIN` from `.env`, and run `dev up`.

## dev.bat Commands

| Command | Description |
|---|---|
| `dev up` | Start all services (no build) |
| `dev down` | Stop all services |
| `dev down-v` | Stop all services and remove volumes |
| `dev build` | Build and start all services |
| `dev build api` | Build and start API server only |
| `dev build web` | Build and start web server only |
| `dev build web api` | Build and start both web + API |
| `dev build background` | Build and start background worker |
| `dev build model` | Build and start model servers |
| `dev restart` | Restart all services |
| `dev restart api` | Restart API server |
| `dev restart web` | Restart web server |
| `dev restart api web` | Restart both API + web |
| `dev logs` | Tail logs for all services |
| `dev logs api` | Tail logs for API server |
| `dev ps` | Show running containers |

## Service Shortcuts

| Shortcut | Actual Service |
|---|---|
| `api` | api_server |
| `web` | web_server |
| `background` | background |
| `cortex` / `model` / `embedding` | cortex_embed_vllm (OpenAI-compatible vLLM embeddings) |
| `rerank` | cortex_rerank_vllm (optional reranker) |
| `nginx` | nginx |
| `db` | relational_db (PostgreSQL) |
| `cache` | cache (Redis) |
| `opensearch` | opensearch |

## Volumes

All data is stored under `E:\temp\vert\` with subdirectories per service (db, opensearch, minio_data, etc.).

