"""Per-tenant "does any enabled policy exist?" cache.

Kept in its own module (no dependency on service/dependencies) so both the enforcement dependency
and the record hook can gate on it cheaply. The old ``@lru_cache`` existence check was process-global
and would have leaked one tenant's answer to another — this is keyed by tenant id.
"""

import threading
import time

from sqlalchemy.orm import Session

from om.server.rate_limits.repository import RateLimitRepository


class _PolicyExistenceCache:
    """Short-TTL, explicitly-invalidatable, per-tenant existence cache."""

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self._ttl = ttl_seconds
        self._data: dict[str, tuple[bool, float]] = {}
        self._lock = threading.Lock()

    def exists(self, tenant_id: str, db_session: Session) -> bool:
        now = time.time()
        with self._lock:
            cached = self._data.get(tenant_id)
            if cached is not None and now - cached[1] < self._ttl:
                return cached[0]
        value = RateLimitRepository(db_session).any_enabled_policy_exists()
        with self._lock:
            self._data[tenant_id] = (value, now)
        return value

    def invalidate(self, tenant_id: str) -> None:
        with self._lock:
            self._data.pop(tenant_id, None)


_policy_existence_cache = _PolicyExistenceCache()


def policy_exists(tenant_id: str, db_session: Session) -> bool:
    """True if the tenant has at least one enabled policy (TTL-cached)."""
    return _policy_existence_cache.exists(tenant_id, db_session)


def invalidate_policy_existence(tenant_id: str) -> None:
    """Drop the cached answer so a create/delete takes effect immediately."""
    _policy_existence_cache.invalidate(tenant_id)
