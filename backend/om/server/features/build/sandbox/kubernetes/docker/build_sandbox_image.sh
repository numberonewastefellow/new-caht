#!/usr/bin/env bash
# Build (and optionally push) the Craft sandbox image used when SANDBOX_BACKEND=kubernetes.
#
#   ./build_sandbox_image.sh                      # builds om/sandbox:<version> locally
#   OM_REGISTRY=ghcr.io/your-org ./build_sandbox_image.sh --push
#
# Then point the backend at it:  SANDBOX_CONTAINER_IMAGE=<registry>/om/sandbox:<version>
# (the default, om/sandbox:v0.1.5, only resolves on a machine that has built it locally).
set -euo pipefail
cd "$(dirname "$0")"
VERSION="${SANDBOX_IMAGE_VERSION:-v0.1.5}"
IMAGE="${OM_REGISTRY:+${OM_REGISTRY%/}/}om/sandbox:${VERSION}"
echo "Building ${IMAGE}"
docker build -t "${IMAGE}" -f Dockerfile .
if [ "${1:-}" = "--push" ]; then
  docker push "${IMAGE}"
fi
echo "Done: ${IMAGE}"
