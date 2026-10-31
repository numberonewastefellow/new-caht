#!/bin/sh
# Pulse — scheduled workflow engine entrypoint.
#   pulse_entrypoint.sh scheduler    -> HA ticker loop (run 2+ replicas)
#   pulse_entrypoint.sh worker       -> Celery worker for $PULSE_WORKER_QUEUE (default `pulse`; scale horizontally)
#   pulse_entrypoint.sh healthcheck  -> liveness probe for either role (uses $PULSE_ROLE)
# Without an argument, $PULSE_ROLE (default: worker) selects the role.
set -e

ROLE="${1:-${PULSE_ROLE:-worker}}"

if [ -f /etc/ssl/certs/custom-ca.crt ]; then
  update-ca-certificates >/dev/null 2>&1 || true
fi

case "$ROLE" in
  scheduler)
    exec python -m om.pulse.scheduler
    ;;
  worker)
    exec celery -A om.background.celery.versioned_apps.pulse_worker worker \
      --pool=threads \
      --concurrency="${PULSE_WORKER_CONCURRENCY:-4}" \
      --prefetch-multiplier=1 \
      --loglevel="${PULSE_LOG_LEVEL:-INFO}" \
      --hostname="${PULSE_WORKER_QUEUE:-pulse}@%h" \
      -Q "${PULSE_WORKER_QUEUE:-pulse}"
    ;;
  healthcheck)
    if [ "${PULSE_ROLE:-worker}" = "scheduler" ]; then
      # The scheduler touches this file every tick; stale for > 2 minutes => unhealthy
      HB="${PULSE_SCHEDULER_HEARTBEAT_FILE:-/tmp/pulse_scheduler.heartbeat}"
      [ -f "$HB" ] && [ -n "$(find "$HB" -mmin -2 2>/dev/null)" ] && exit 0
      exit 1
    fi
    # Celery touches /tmp/<prefix>_k8s_<queue>_readiness.txt on worker_ready (app_base), with
    # the queue's underscores removed: pulse or pulsewebhook. Glob the prefix and the queue
    # so the probe works for both workers and survives package renames.
    for f in /tmp/*_k8s_pulse*_readiness.txt; do
      [ -f "$f" ] && exit 0
    done
    exit 1
    ;;
  *)
    echo "Unknown Pulse role: $ROLE (expected scheduler|worker|healthcheck)" >&2
    exit 2
    ;;
esac
