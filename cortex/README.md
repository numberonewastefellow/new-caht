# Cortex

Generic OpenAI-compatible model service on top of the latest vLLM image. It replaces the
former bespoke model-server containers. One container serves one model:

| Service (compose)    | Profile  | Model (default)                              | API                |
|----------------------|----------|----------------------------------------------|--------------------|
| `cortex_embed_vllm`  | `vllm`   | `nomic-ai/nomic-embed-text-v1` (768-d)       | `/v1/embeddings`   |
| `cortex_embed_tei`   | `tei`    | same model, Hugging Face TEI engine          | `/v1/embeddings`   |
| `cortex_rerank_vllm` | `rerank` | `BAAI/bge-reranker-v2-m3` (multilingual)      | `/v1/rerank`       |

Network aliases: `cortex_embed` (also the legacy `embedding_server`), `cortex_rerank`.
Enable with `COMPOSE_PROFILES=...,vllm[,rerank]` in `.env`.

## Embeddings
Backend wiring: Admin > Embedding provider `litellm`, API URL
`http://cortex_embed:8000/v1/embeddings`, model name = `EMBEDDING_MODEL`
(or set `EMBEDDING_SERVER_URL` and the backend does it on startup).

## Reranking (off by default)
Set `RERANK_ENABLED=true` for `api_server` and `background` and start the `rerank` profile.
Both search and chat then rerank the top `RERANK_TOP_N` chunks through `RERANK_SERVER_URL`.
It fails open: if Cortex is down the original order is returned.

`jinaai/jina-reranker-v1-tiny-en` was tried first but cannot be served by current vLLM
(its remote code imports the removed `transformers.onnx`, and its ALiBi BERT is not a native
vLLM architecture). Any `*ForSequenceClassification` cross-encoder works. Tested end to end:
`BAAI/bge-reranker-v2-m3` (default, multilingual, about 1.1 GB, GPU share 0.30) and the tiny
English-only `cross-encoder/ms-marco-MiniLM-L-6-v2` (GPU share 0.10) if VRAM is tight.

## Checks
    curl http://localhost:8000/v1/embeddings -H 'Content-Type: application/json' \
      -d '{"model":"nomic-ai/nomic-embed-text-v1","input":["search_query: hello"]}'
    curl http://localhost:8000/v1/rerank -H 'Content-Type: application/json' \
      -d '{"model":"<RERANK_MODEL>","query":"q","documents":["a","b"]}'
