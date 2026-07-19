"""Observability for the rate-limits subsystem: Prometheus metrics + structured event logs.

- **Prometheus** (`prometheus_client`, already scraped at `/metrics`): request/allow/throttle
  counters, a remaining-budget gauge, and a fail-open error counter.
- **Structured logs** (Standard 9, OpenSearch-friendly): one JSON line per significant event, always
  wrapped in try/except so logging can never break enforcement or config changes.
"""

import json
import time
from typing import Any

from prometheus_client import Counter
from prometheus_client import Gauge

from om.server.rate_limits.constants import RateLimitDecision
from om.utils.logger import setup_logger

logger = setup_logger()

# ---- Prometheus metrics ----------------------------------------------------------------

RATELIMIT_CHECKS_TOTAL = Counter(
    "om_ratelimit_checks_total",
    "Rate-limit enforcement checks, labelled by scope and decision.",
    ["scope", "decision"],
)
RATELIMIT_THROTTLED_TOTAL = Counter(
    "om_ratelimit_throttled_total",
    "Requests rejected (429) by a rate-limit policy, labelled by the scope that tripped.",
    ["scope"],
)
RATELIMIT_TOKENS_RECORDED_TOTAL = Counter(
    "om_ratelimit_tokens_recorded_total",
    "Tokens recorded against rate-limit counters, labelled by scope.",
    ["scope"],
)
RATELIMIT_REMAINING_BUDGET = Gauge(
    "om_ratelimit_remaining_budget",
    "Tightest (minimum) remaining token budget observed for a scope. Labelled by scope only — "
    "per-subject values would explode Prometheus cardinality; use the /admin/rate-limits/budget "
    "API for per-subject detail.",
    ["scope"],
)
RATELIMIT_ENGINE_ERRORS_TOTAL = Counter(
    "om_ratelimit_engine_errors_total",
    "Rate-limit engine errors (e.g. Redis unreachable) that triggered fail-open.",
    ["operation"],
)


def observe_check(scope: str, decision: RateLimitDecision) -> None:
    RATELIMIT_CHECKS_TOTAL.labels(scope=scope, decision=decision.value).inc()
    if decision == RateLimitDecision.THROTTLED:
        RATELIMIT_THROTTLED_TOTAL.labels(scope=scope).inc()


def observe_recorded_tokens(scope: str, tokens: int) -> None:
    if tokens > 0:
        RATELIMIT_TOKENS_RECORDED_TOTAL.labels(scope=scope).inc(tokens)


def observe_remaining_budget(scope: str, remaining: int) -> None:
    """Set the per-scope remaining-budget gauge (caller passes the tightest value for the scope)."""
    RATELIMIT_REMAINING_BUDGET.labels(scope=scope).set(remaining)


def observe_engine_error(operation: str) -> None:
    RATELIMIT_ENGINE_ERRORS_TOTAL.labels(operation=operation).inc()


# ---- Structured logging (Standard 9) ---------------------------------------------------


def log_ratelimit_event(
    *,
    event: str,
    action: str,
    status: str,
    tenant_id: str | None = None,
    actor_user_id: str | None = None,
    entity: str = "rate_limit_policy",
    entity_id: str | int | None = None,
    duration_ms: float | None = None,
    remaining_budget: int | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    """Emit one OpenSearch-friendly JSON event line. Never raises."""
    try:
        payload: dict[str, Any] = {
            "event": event,
            "entity": entity,
            "entity_id": entity_id,
            "tenant_id": tenant_id,
            "actor_user_id": actor_user_id,
            "action": action,
            "status": status,
            "duration_ms": (
                round(duration_ms, 2) if duration_ms is not None else None
            ),
            "remaining_budget": remaining_budget,
            "error": error,
        }
        if extra:
            payload.update(extra)
        logger.info("ratelimit_event %s", json.dumps(payload, default=str))
    except Exception:
        # Logging must never break the caller. Best-effort fallback.
        try:
            logger.warning("Failed to emit ratelimit_event for event=%s", event)
        except Exception:
            pass


class Stopwatch:
    """Tiny monotonic timer for ``duration_ms`` on structured events."""

    def __init__(self) -> None:
        self._start = time.monotonic()

    def elapsed_ms(self) -> float:
        return (time.monotonic() - self._start) * 1000.0
