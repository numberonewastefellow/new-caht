#!/usr/bin/env bash
# Build compose services, retrying on transient network failures (npm / pip registry timeouts).
# Docker layer caching plus the npm/uv BuildKit cache mounts mean each retry resumes at the
# failed step instead of starting over.
#
# Usage: ./build_retry.sh [-p project] [-f compose.yml ...] <service> [service ...]
#   e.g. ./build_retry.sh -p virtualai -f docker-compose.yml -f docker-compose.dev-windows.yml web_server api_server
# Env:   BUILD_ATTEMPTS (default 3), BUILD_RETRY_DELAY seconds (default 15)
set -u
attempts="${BUILD_ATTEMPTS:-3}"
delay="${BUILD_RETRY_DELAY:-15}"
args=()
services=()
while [ $# -gt 0 ]; do
  case "$1" in
    -p|-f) args+=("$1" "$2"); shift 2 ;;
    *) services+=("$1"); shift ;;
  esac
done
[ ${#services[@]} -gt 0 ] || { echo "usage: $0 [-p project] [-f file ...] <service>..." >&2; exit 2; }

# Build one service at a time so a failure in one does not discard another's finished build.
for svc in "${services[@]}"; do
  n=1
  until docker compose "${args[@]}" build "$svc"; do
    if [ "$n" -ge "$attempts" ]; then
      echo "build of '$svc' failed after $attempts attempts" >&2
      exit 1
    fi
    echo "build of '$svc' failed (attempt $n/$attempts); retrying in ${delay}s..." >&2
    n=$((n + 1))
    sleep "$delay"
  done
done
