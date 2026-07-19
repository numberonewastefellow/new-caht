"""Core rate-limiting engine: a token-weighted sliding-window counter over Redis.

Algorithm choice (see README for the cited research):
- **Sliding-window counter** (not fixed-window, token-bucket, or GCRA). Fixed windows allow a
  2x burst across the window boundary; GCRA cannot answer "how much budget is left" (which we
  need for the remaining-budget API + admin gauge); token-bucket is request-shaped whereas our
  budget is a smooth token-per-hour cap. The sliding-window counter approximates a true rolling
  window with O(1) memory (two integers) and, per Cloudflare's published numbers, ~0.003% error.
- **Atomic via Redis Lua** (`EVAL`/`register_script`). A single server-side script does the
  read-modify-write so concurrent chat requests can neither lose an increment nor read a torn
  value. We never use WATCH/MULTI/EXEC (which retry-storms under contention).

Tenant isolation: ``TenantRedis`` only auto-prefixes a fixed allow-list of commands and does
**not** wrap ``eval``/``evalsha``, so this engine prepends ``"{tenant_id}:"`` to every KEY it
passes to Lua itself — the same scheme ``TenantRedis._prefixed`` uses, keeping counters isolated
per tenant.
"""

import time
from dataclasses import dataclass

from redis import Redis
from redis.commands.core import Script

from om.server.rate_limits.constants import REDIS_RATELIMIT_NAMESPACE
from om.server.rate_limits.constants import SECONDS_PER_HOUR


# Peek: estimate tokens used across the sliding window without mutating anything.
#   KEYS[1] current-window counter, KEYS[2] previous-window counter
#   ARGV[1] elapsed_ms within current window, ARGV[2] window_ms
_PEEK_LUA = """
local cur = tonumber(redis.call('GET', KEYS[1]) or '0')
local prev = tonumber(redis.call('GET', KEYS[2]) or '0')
local elapsed = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local weight = (window - elapsed) / window
if weight < 0 then weight = 0 end
return cur + math.floor(prev * weight)
"""

# Record: add `cost` tokens to the current window (creating/refreshing its TTL) and return the
# new sliding estimate. INCRBY + PEXPIRE + weighted read run atomically in one script.
#   KEYS[1] current-window counter, KEYS[2] previous-window counter
#   ARGV[1] cost, ARGV[2] ttl_ms, ARGV[3] elapsed_ms, ARGV[4] window_ms
_RECORD_LUA = """
local cost = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
local newcur = redis.call('INCRBY', KEYS[1], cost)
redis.call('PEXPIRE', KEYS[1], ttl)
local prev = tonumber(redis.call('GET', KEYS[2]) or '0')
local elapsed = tonumber(ARGV[3])
local window = tonumber(ARGV[4])
local weight = (window - elapsed) / window
if weight < 0 then weight = 0 end
return newcur + math.floor(prev * weight)
"""


@dataclass(frozen=True)
class WindowMath:
    """Pure sliding-window arithmetic for a given period, evaluated at ``now_ms``.

    Split out from Redis I/O so it is trivially unit-testable.
    """

    window_ms: int
    current_index: int
    previous_index: int
    elapsed_ms: int

    @classmethod
    def compute(cls, period_hours: int, now_ms: int) -> "WindowMath":
        if period_hours <= 0:
            raise ValueError("period_hours must be positive")
        window_ms = period_hours * SECONDS_PER_HOUR * 1000
        current_index = now_ms // window_ms
        window_start_ms = current_index * window_ms
        return cls(
            window_ms=window_ms,
            current_index=current_index,
            previous_index=current_index - 1,
            elapsed_ms=now_ms - window_start_ms,
        )

    @property
    def ttl_ms(self) -> int:
        # Keep counters alive for two full windows so the "previous" bucket survives the roll.
        return self.window_ms * 2

    @property
    def reset_seconds(self) -> int:
        """Seconds until the current window closes and the previous bucket fully rolls off.

        A conservative, client-friendly reset hint (analogous to ``RateLimit-Reset``): once the
        window closes, the previous window's weighted contribution drops to zero.
        """
        remaining_ms = self.window_ms - self.elapsed_ms
        return max(1, (remaining_ms + 999) // 1000)


class RateLimiterEngine:
    """Sliding-window token counter for a single tenant.

    One instance wraps one tenant-scoped Redis client. Methods take a ``subject_key`` (see
    ``constants.subject_key``) and the policy's ``period_hours``.
    """

    def __init__(self, redis_client: Redis, tenant_id: str) -> None:
        self._redis = redis_client
        self._tenant_id = tenant_id
        self._peek: Script = redis_client.register_script(_PEEK_LUA)
        self._record: Script = redis_client.register_script(_RECORD_LUA)

    def _key(self, subject_key: str, period_hours: int, window_index: int) -> str:
        # Mirror TenantRedis._prefixed so Lua-addressed keys land in the same tenant keyspace as
        # every other command. (eval/evalsha are not auto-prefixed by TenantRedis.)
        #
        # period_hours is part of the key: a subject may have several policies with different
        # windows, and two windows can share a window_index value, so the period must
        # disambiguate their counters.
        return (
            f"{self._tenant_id}:{REDIS_RATELIMIT_NAMESPACE}"
            f":{subject_key}:{period_hours}h:{window_index}"
        )

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    def estimate_used(self, subject_key: str, period_hours: int) -> int:
        """Return the current sliding-window token estimate for a subject (no mutation)."""
        w = WindowMath.compute(period_hours, self._now_ms())
        result = self._peek(
            keys=[
                self._key(subject_key, period_hours, w.current_index),
                self._key(subject_key, period_hours, w.previous_index),
            ],
            args=[w.elapsed_ms, w.window_ms],
            client=self._redis,
        )
        return int(result)

    def record_usage(self, subject_key: str, period_hours: int, tokens: int) -> int:
        """Add ``tokens`` to the current window and return the new sliding estimate."""
        if tokens <= 0:
            return self.estimate_used(subject_key, period_hours)
        w = WindowMath.compute(period_hours, self._now_ms())
        result = self._record(
            keys=[
                self._key(subject_key, period_hours, w.current_index),
                self._key(subject_key, period_hours, w.previous_index),
            ],
            args=[tokens, w.ttl_ms, w.elapsed_ms, w.window_ms],
            client=self._redis,
        )
        return int(result)

    def seed_current_window(
        self, subject_key: str, period_hours: int, tokens: int
    ) -> None:
        """Cold-start reconciliation: seed the current window from a durable roll-up.

        Called by the service only when the live estimate is zero but the persisted roll-up shows
        recent usage (e.g. right after a Redis flush), so a restart does not silently reset every
        budget to zero. ``tokens`` is the roll-up's token sum over the last ``period_hours`` — a
        deliberately conservative value (all recent usage placed in the current window at full
        weight) so reconciliation can only over-count, never let a subject slip past its budget.

        Uses SET NX so a concurrent live INCRBY that already re-created the key always wins; the key
        is written pre-prefixed, and ``TenantRedis._prefixed`` is idempotent, so the wrapped ``set``
        does not double-prefix.
        """
        if tokens <= 0:
            return
        w = WindowMath.compute(period_hours, self._now_ms())
        self._redis.set(
            name=self._key(subject_key, period_hours, w.current_index),
            value=tokens,
            px=w.ttl_ms,
            nx=True,
        )
