"""Rate limits for the public endpoint, checked before any database work.

Counts per fixed one-minute window in Redis. All keys use the default schema's client:
the tenant in a token is unverified at this point, so it must not choose Redis keys.
"""

from typing import cast

from redis import Redis
from redis.exceptions import RedisError

from om.configs.pulse_configs import PULSE_WEBHOOK_PROXY_HOPS
from om.configs.pulse_configs import PULSE_WEBHOOK_RATE_PER_IP
from om.configs.pulse_configs import PULSE_WEBHOOK_RATE_PER_TOKEN
from om.redis.redis_pool import get_redis_client
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA

_WINDOW_SECONDS = 60
_NEGATIVE_CACHE_SECONDS = 60
_KEY_PREFIX = "pulse:webhook"

# Atomic, so concurrent calls can't lose a count or leave a key without an expiry.
_COUNT_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""


class RateLimited(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"retry after {retry_after}s")
        self.retry_after = retry_after


class LimiterUnavailable(Exception):
    """Redis is down. The caller answers 503, so the limit is never silently dropped."""


def _client() -> Redis:
    return get_redis_client(tenant_id=POSTGRES_DEFAULT_SCHEMA)


def client_address(peer: str | None, forwarded_for: str | None) -> str:
    """The caller's address. Each trusted proxy appends the address it saw, so only the
    last PULSE_WEBHOOK_PROXY_HOPS entries can be believed: anything before them was
    written by the caller."""
    if PULSE_WEBHOOK_PROXY_HOPS > 0 and forwarded_for:
        entries = [e.strip() for e in forwarded_for.split(",") if e.strip()]
        if len(entries) >= PULSE_WEBHOOK_PROXY_HOPS:
            return entries[-PULSE_WEBHOOK_PROXY_HOPS]
    return peer or "unknown"


def _check(redis: Redis, key: str, limit: int) -> None:
    count, ttl = cast(list[int], redis.eval(_COUNT_LUA, 1, key, str(_WINDOW_SECONDS)))
    if int(count) > limit:
        raise RateLimited(retry_after=max(1, int(ttl)))


def check_rate_limits(address: str, token_hash: str) -> None:
    """Raises RateLimited or LimiterUnavailable."""
    try:
        redis = _client()
        _check(redis, f"{_KEY_PREFIX}:ip:{address}", PULSE_WEBHOOK_RATE_PER_IP)
        _check(redis, f"{_KEY_PREFIX}:token:{token_hash[:32]}", PULSE_WEBHOOK_RATE_PER_TOKEN)
    except RedisError as e:
        raise LimiterUnavailable() from e


def is_known_miss(token_hash: str) -> bool:
    """A token recently found not to exist, e.g. a sender retrying a revoked one."""
    try:
        return bool(_client().exists(f"{_KEY_PREFIX}:miss:{token_hash}"))
    except RedisError as e:
        raise LimiterUnavailable() from e


def remember_miss(token_hash: str) -> None:
    """Only misses are cached: a new or rotated token is random and can't have been
    cached as a miss, and hits always read the database, so a pause or revoke applies
    at once and no secret ever reaches Redis."""
    try:
        _client().set(f"{_KEY_PREFIX}:miss:{token_hash}", "1", ex=_NEGATIVE_CACHE_SECONDS)
    except RedisError as e:
        raise LimiterUnavailable() from e
