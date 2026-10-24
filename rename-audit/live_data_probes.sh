#!/usr/bin/env bash
# READ-ONLY shell probes for non-DB state. Run on the Docker host.
echo "== docker volumes named onyx*"; docker volume ls --format '{{.Name}}' | grep -i onyx || echo none
echo "== compose projects";            docker compose ls 2>/dev/null | grep -i onyx || echo none
echo "== containers named onyx*";      docker ps -a --format '{{.Names}}' | grep -i onyx || echo none
echo "== redis keys by prefix (count)"
for p in 'onyx:*' 'onyx_kv_store:*' 'da_function_lock:*'; do
  printf '%s -> ' "$p"; docker compose exec -T cache redis-cli --scan --pattern "$p" 2>/dev/null | wc -l
done
echo "== minio objects under onyx-files/ (needs mc configured)"; mc ls --recursive local/onyx-file-store-bucket/onyx-files 2>/dev/null | wc -l
echo "== k8s namespace (if used)"; kubectl get ns onyx-sandboxes 2>/dev/null || echo none
