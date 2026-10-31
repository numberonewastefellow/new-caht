"""Which Pulse workers are alive, per queue.

Each worker keeps refreshing a short-lived Redis key, so a worker that dies disappears by
itself. This is the same pattern as scheduler presence. Celery's `inspect` isn't used: it
blocks for its timeout on every call, and can return nothing under load, which would look
the same as having no workers.
"""

import threading

from om.redis.redis_pool import get_redis_client
from om.utils.logger import setup_logger
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA

logger = setup_logger()

WORKER_PRESENCE_KEY_PREFIX = "pulse:worker:alive:"
PRESENCE_REFRESH_SECONDS = 30
# Long enough to survive a missed refresh, short enough that a dead worker shows soon.
PRESENCE_EXPIRY_SECONDS = 90


def _presence_key(queue: str, hostname: str) -> str:
    return f"{WORKER_PRESENCE_KEY_PREFIX}{queue}:{hostname}"


def count_alive_workers(queue: str) -> int:
    """Raises if Redis can't be read, because that doesn't mean there are no workers."""
    r = get_redis_client(tenant_id=POSTGRES_DEFAULT_SCHEMA)
    match = f"{WORKER_PRESENCE_KEY_PREFIX}{queue}:*"
    return sum(1 for _ in r.scan_iter(match=match, count=100))


class WorkerPresence:
    """Publishes one worker's presence until stopped."""

    def __init__(self, queue: str, hostname: str) -> None:
        self._key = _presence_key(queue, hostname)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="pulse-worker-presence", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def withdraw(self) -> None:
        """Stop counting as alive. Doesn't block, so it's safe from a signal handler."""
        self._stop.set()

    def stop(self) -> None:
        self.withdraw()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            # A Redis outage must not end the thread: the worker should reappear afterwards.
            try:
                get_redis_client(tenant_id=POSTGRES_DEFAULT_SCHEMA).set(
                    self._key, "1", ex=PRESENCE_EXPIRY_SECONDS
                )
            except Exception:
                logger.exception("Pulse: failed to publish worker presence")
            self._stop.wait(PRESENCE_REFRESH_SECONDS)
        try:
            get_redis_client(tenant_id=POSTGRES_DEFAULT_SCHEMA).delete(self._key)
        except Exception:
            logger.exception("Pulse: failed to withdraw worker presence")
