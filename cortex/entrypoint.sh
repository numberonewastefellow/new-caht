#!/bin/sh
# Cortex: starts vLLM in pooling mode (embeddings or reranking, chosen by the model).
# Configured purely via env vars. CORTEX_* wins; the legacy EMBEDDING_* names are
# still honoured so old .env files keep working.
#   CORTEX_MODEL                 HF model id (embedding model or cross-encoder reranker)
#   CORTEX_MAX_LEN               max sequence length
#   CORTEX_GPU_UTIL              fraction of GPU memory to reserve
#   CORTEX_DTYPE                 auto | half | float16 | bfloat16 | float32
#   CORTEX_PORT                  listen port
#   CORTEX_API_KEY               optional; clients must send "Authorization: Bearer <key>"
#   CORTEX_TRUST_REMOTE_CODE     true/false (needed by e.g. nomic-embed-text-v1)
#   CORTEX_EXTRA_ARGS            anything else passed verbatim to `vllm serve`
set -eu

MODEL="${CORTEX_MODEL:-${EMBEDDING_MODEL:-nomic-ai/nomic-embed-text-v1}}"
MAX_LEN="${CORTEX_MAX_LEN:-${EMBEDDING_MAX_LEN:-2048}}"
GPU_UTIL="${CORTEX_GPU_UTIL:-${EMBEDDING_GPU_UTIL:-0.25}}"
DTYPE="${CORTEX_DTYPE:-${EMBEDDING_DTYPE:-auto}}"
PORT="${CORTEX_PORT:-${EMBEDDING_PORT:-8000}}"
API_KEY="${CORTEX_API_KEY:-${EMBEDDING_API_KEY:-}}"
TRUST="${CORTEX_TRUST_REMOTE_CODE:-${EMBEDDING_TRUST_REMOTE_CODE:-false}}"
EXTRA="${CORTEX_EXTRA_ARGS:-${EMBEDDING_EXTRA_ARGS:-}}"

# The flag that selects pooling mode changed across vLLM releases
# (`--task embed` -> `--runner pooling`); pick whichever this build supports.
if vllm serve --help=all 2>/dev/null | grep -q -- '--runner'; then
    MODE_FLAGS="--runner pooling"
else
    MODE_FLAGS="--task embed"
fi

ARGS="--served-model-name ${MODEL} ${MODE_FLAGS}"
ARGS="${ARGS} --max-model-len ${MAX_LEN} --gpu-memory-utilization ${GPU_UTIL}"
ARGS="${ARGS} --dtype ${DTYPE} --host 0.0.0.0 --port ${PORT}"

case "${TRUST}" in
    true|True|1) ARGS="${ARGS} --trust-remote-code" ;;
esac
if [ -n "${API_KEY}" ]; then
    ARGS="${ARGS} --api-key ${API_KEY}"
fi

echo "cortex: model=${MODEL} mode='${MODE_FLAGS}' gpu_util=${GPU_UTIL}"
# shellcheck disable=SC2086
exec vllm serve "${MODEL}" ${ARGS} ${EXTRA}
