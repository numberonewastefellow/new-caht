"""Listen mode: for a few minutes the owner can send a test call and see exactly what
arrived. Nothing runs, nothing reaches the database, and no dedup key is used. Captures
expire with the listen window.
"""

import json
from typing import Any
from typing import cast

from redis import Redis
from redis.exceptions import RedisError

from om.configs.pulse_configs import PULSE_WEBHOOK_LISTEN_TTL_SECONDS
from om.pulse.webhooks.limits import LimiterUnavailable
from om.redis.redis_pool import get_redis_client

_MAX_CAPTURES = 5


def _keys(webhook_id: int) -> tuple[str, str]:
    return f"pulse:webhook:listen:{webhook_id}", f"pulse:webhook:captures:{webhook_id}"


def start_listening(tenant_id: str, webhook_id: int) -> int:
    """Open (or extend) the listen window. Returns its length in seconds."""
    redis = get_redis_client(tenant_id=tenant_id)
    listen_key, captures_key = _keys(webhook_id)
    redis.delete(captures_key)
    redis.set(listen_key, "1", ex=PULSE_WEBHOOK_LISTEN_TTL_SECONDS)
    return PULSE_WEBHOOK_LISTEN_TTL_SECONDS


def stop_listening(tenant_id: str, webhook_id: int) -> None:
    redis = get_redis_client(tenant_id=tenant_id)
    for key in _keys(webhook_id):
        redis.delete(key)


def seconds_left(tenant_id: str, webhook_id: int) -> int:
    """0 when not listening."""
    redis = get_redis_client(tenant_id=tenant_id)
    return max(0, cast(int, redis.ttl(_keys(webhook_id)[0])))


def _read_captures(redis: Redis, captures_key: str) -> list[dict[str, Any]]:
    raw = cast(bytes | None, redis.get(captures_key))
    return json.loads(raw) if raw else []


def capture(tenant_id: str, webhook_id: int, event: dict[str, Any]) -> bool:
    """Store a test call for the owner. False when Listen isn't open. Only commands the
    tenant Redis client prefixes are used (not lists or pipelines), so keys can't collide
    between tenants."""
    try:
        redis = get_redis_client(tenant_id=tenant_id)
        listen_key, captures_key = _keys(webhook_id)
        ttl = cast(int, redis.ttl(listen_key))
        if ttl <= 0:
            return False
        events = [event, *_read_captures(redis, captures_key)][:_MAX_CAPTURES]
        redis.set(captures_key, json.dumps(events), ex=ttl)
        return True
    except RedisError as e:
        raise LimiterUnavailable() from e


def captures(tenant_id: str, webhook_id: int) -> list[dict[str, Any]]:
    """Newest first."""
    redis = get_redis_client(tenant_id=tenant_id)
    return _read_captures(redis, _keys(webhook_id)[1])
