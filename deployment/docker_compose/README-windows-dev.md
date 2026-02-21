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

The app will be available at http://localhost:3000

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
| `model` | inference_model_server + indexing_model_server |
| `nginx` | nginx |
| `db` | relational_db (PostgreSQL) |
| `cache` | cache (Redis) |
| `vespa` | index (Vespa) |

## Volumes

All data is stored under `E:\temp\vert\` with subdirectories per service (db, vespa, minio_data, etc.).

## Migrating from Named Volumes

If you previously used `docker-compose.dev.yml` with default Docker named volumes, stop services and copy them:

```bat
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

docker run --rm -v onyx-stack_db_volume:/source -v E:/temp/vert/db:/dest alpine sh -c "cp -a /source/. /dest/"
docker run --rm -v onyx-stack_vespa_volume:/source -v E:/temp/vert/vespa:/dest alpine sh -c "cp -a /source/. /dest/"
docker run --rm -v onyx-stack_minio_data:/source -v E:/temp/vert/minio_data:/dest alpine sh -c "cp -a /source/. /dest/"
docker run --rm -v onyx-stack_model_cache_huggingface:/source -v E:/temp/vert/model_cache_huggingface:/dest alpine sh -c "cp -a /source/. /dest/"
docker run --rm -v onyx-stack_indexing_huggingface_model_cache:/source -v E:/temp/vert/indexing_huggingface_model_cache:/dest alpine sh -c "cp -a /source/. /dest/"
```

Then start with `dev build`.
