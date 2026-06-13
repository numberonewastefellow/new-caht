#!/usr/bin/env bash
#
# Waits for the Vespa -> OpenSearch backfill to finish, then switches the
# RETRIEVAL engine to OpenSearch via the admin API.
#
# Use this AFTER you have started both engines (mode [B] in .env:
# COMPOSE_PROFILES=s3-filestore,vespa,opensearch + ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true)
# and run `dev up`. It polls the migration status until the existing corpus has
# been copied into OpenSearch, then flips retrieval over.
#
# Requires an ADMIN API key (create one in the UI: Admin > API Keys).
#
# Usage:
#   ONYX_API_KEY=<key> ./switch-retrieval-to-opensearch.sh            # wait + switch to OpenSearch
#   ONYX_API_KEY=<key> ./switch-retrieval-to-opensearch.sh --revert   # switch back to Vespa (no wait)
#
# Optional env vars:
#   BASE_URL        (default http://localhost:3000)
#   POLL_INTERVAL   seconds between status polls (default 10)
#   TIMEOUT         max seconds to wait for backfill (default 3600)
#
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000}"
POLL_INTERVAL="${POLL_INTERVAL:-10}"
TIMEOUT="${TIMEOUT:-3600}"

ENABLE=true
if [ "${1:-}" = "--revert" ]; then
  ENABLE=false
fi

if [ -z "${ONYX_API_KEY:-}" ]; then
  echo "ERROR: ONYX_API_KEY is not set. Create an admin API key in the UI (Admin > API Keys)" >&2
  echo "       and run:  ONYX_API_KEY=<key> $0" >&2
  exit 1
fi

base="${BASE_URL%/}"
status_url="${base}/api/admin/opensearch-migration/status"
retrieval_url="${base}/api/admin/opensearch-migration/retrieval"
auth=(-H "Authorization: Bearer ${ONYX_API_KEY}")

if [ "$ENABLE" = "true" ]; then
  echo "Waiting for the Vespa -> OpenSearch backfill to complete..."
  echo "  status endpoint: ${status_url}"
  start=$(date +%s)
  while true; do
    resp="$(curl -fsS "${auth[@]}" "$status_url" 2>/dev/null || true)"
    if [ -z "$resp" ]; then
      echo "  ...no response yet (is the API up and the key valid?)"
    else
      echo "  ${resp}"
      # Starlette emits compact JSON (no spaces). 'migration_completed_at' is
      # null until the backfill finishes, then an ISO timestamp.
      if ! printf '%s' "$resp" | tr -d ' ' | grep -q '"migration_completed_at":null'; then
        echo "Backfill complete."
        break
      fi
    fi
    now=$(date +%s)
    if [ $((now - start)) -ge "$TIMEOUT" ]; then
      echo "ERROR: timed out after ${TIMEOUT}s waiting for the backfill to finish." >&2
      exit 1
    fi
    sleep "$POLL_INTERVAL"
  done
fi

echo "Setting enable_opensearch_retrieval=${ENABLE} ..."
curl -fsS -X PUT "${auth[@]}" -H 'Content-Type: application/json' \
  -d "{\"enable_opensearch_retrieval\": ${ENABLE}}" "$retrieval_url"
echo ""
echo "Current retrieval state:"
curl -fsS "${auth[@]}" "$retrieval_url"
echo ""
if [ "$ENABLE" = "true" ]; then
  echo "Done. Retrieval is now served by OpenSearch."
else
  echo "Done. Retrieval is now served by Vespa."
fi
