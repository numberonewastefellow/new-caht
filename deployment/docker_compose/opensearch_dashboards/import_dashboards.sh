#!/usr/bin/env bash
# Import the default "Files & Chunks" dashboard (and its visualizations / index
# pattern / saved search) into the running OpenSearch Dashboards.
#
# Idempotent: uses overwrite=true, so re-running just updates the saved objects.
#
# Usage:
#   ./import_dashboards.sh
# Optional env overrides:
#   DASH_URL   (default http://localhost:5601)
#   DASH_USER  (default admin)
#   DASH_PASS  (default StrongPassword123!)
set -euo pipefail

DASH_URL="${DASH_URL:-http://localhost:5601}"
DASH_USER="${DASH_USER:-admin}"
DASH_PASS="${DASH_PASS:-StrongPassword123!}"
NDJSON="$(dirname "$0")/files_and_chunks.ndjson"

if [ ! -f "$NDJSON" ]; then
  echo "Saved-objects file not found: $NDJSON" >&2
  echo "Generate it first:  python build_ndjson.py" >&2
  exit 1
fi

# Target tenant. Multi-tenancy is enabled, so import into the GLOBAL tenant
# (securitytenant: global) -> visible to all users regardless of their selected
# tenant. Override with DASH_TENANT (e.g. "" for the user's default/private).
DASH_TENANT="${DASH_TENANT:-global}"

echo "Importing $(basename "$NDJSON") into $DASH_URL (tenant: ${DASH_TENANT:-default}) ..."
curl -sf -u "$DASH_USER:$DASH_PASS" \
  -H "osd-xsrf: true" \
  ${DASH_TENANT:+-H "securitytenant: $DASH_TENANT"} \
  -X POST "$DASH_URL/api/saved_objects/_import?overwrite=true" \
  --form "file=@$NDJSON;type=application/ndjson"
echo
echo "Done. Open $DASH_URL -> menu (☰) -> Dashboard -> 'VirtualAI — Files & Chunks'."
echo "If you don't see it, switch tenant to 'Global' (top-right user menu -> Switch tenants)."
