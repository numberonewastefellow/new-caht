# Cortex: generic OpenAI-compatible model service on vLLM.
#   POST /v1/embeddings  (embedding models)
#   POST /v1/rerank      (cross-encoder rerankers)
# One container serves ONE model, chosen at runtime by CORTEX_MODEL.
ARG VLLM_IMAGE=vllm/vllm-openai:latest
FROM ${VLLM_IMAGE}

COPY entrypoint.sh /usr/local/bin/cortex-entrypoint.sh
# Guard against CRLF line endings from a Windows checkout (would break the shebang)
RUN sed -i 's/\r$//' /usr/local/bin/cortex-entrypoint.sh && chmod +x /usr/local/bin/cortex-entrypoint.sh

ENV HF_HOME=/root/.cache/huggingface

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=10 \
    CMD python3 -c "import urllib.request,os; urllib.request.urlopen('http://localhost:%s/health' % os.environ.get('CORTEX_PORT', os.environ.get('EMBEDDING_PORT','8000')))"

ENTRYPOINT ["/usr/local/bin/cortex-entrypoint.sh"]
