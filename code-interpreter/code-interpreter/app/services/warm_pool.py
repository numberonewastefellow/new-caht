"""A warm pool of pre-started, single-use sandbox containers.

The pool only removes the ``docker run`` from the request path. It never reuses a
container: :meth:`WarmContainerPool.take` hands each container out at most once and
forgets it, and the caller destroys it after its one execution. Nothing, therefore,
can be shared across executions or tenants.

Sizing:

* the pool keeps ``target`` idle-or-starting containers, ``min_size <= target <=
  max_size``;
* ``target`` starts at ``min_size``, grows by one for every request that finds the pool
  empty (it then falls back to a cold start), and shrinks by one per
  ``scale_down_after_sec`` without such a miss;
* idle containers older than ``ttl_sec`` are destroyed and replaced;
* every ``reconcile_interval_sec`` idle entries whose container is no longer running
  (killed externally, daemon restart) are dropped.

A background thread does all of this; requests only pop from a deque.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

# Longest pause between two start attempts while starts keep failing.
_MAX_START_BACKOFF_SEC = 30.0
_SHUTDOWN_JOIN_SEC = 10.0


class PoolRuntime(Protocol):
    """What the pool needs from a container runtime."""

    def start(self, name: str) -> None:
        """Start an idle container; raise on failure."""

    def remove(self, name: str) -> None:
        """Kill and remove a container; never raise."""

    def list_owned(self, *, include_stopped: bool = False) -> list[str]:
        """Names of this instance's running containers; raise on failure."""


@dataclass(frozen=True, slots=True)
class PoolConfig:
    min_size: int
    max_size: int
    ttl_sec: float
    maintenance_interval_sec: float = 1.0
    reconcile_interval_sec: float = 30.0
    scale_down_after_sec: float = 60.0
    max_parallel_starts: int = 4

    def __post_init__(self) -> None:
        if not 0 <= self.min_size <= self.max_size:
            raise ValueError("pool sizes must satisfy 0 <= min_size <= max_size")
        if self.ttl_sec <= 0:
            raise ValueError("ttl_sec must be positive")


@dataclass(frozen=True, slots=True)
class PooledContainer:
    name: str
    # Monotonic time at which the container became idle.
    created_at: float


@dataclass(frozen=True, slots=True)
class PoolStats:
    idle: int
    starting: int
    target: int
    hits: int
    misses: int


class WarmContainerPool:
    """Keeps pre-started sandbox containers ready for single use."""

    def __init__(
        self,
        runtime: PoolRuntime,
        config: PoolConfig,
        *,
        name_factory: Callable[[], str],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._runtime = runtime
        self._config = config
        self._name_factory = name_factory
        self._clock = clock

        self._lock = threading.Lock()
        self._idle: deque[PooledContainer] = deque()
        # Taken-but-expired containers, removed by the maintenance thread so the
        # request path never waits on `docker rm`.
        self._retired: list[str] = []
        self._starting = 0
        self._target = config.min_size
        self._hits = 0
        self._misses = 0
        self._last_miss_at = clock()
        self._last_reconcile_at = clock()
        self._start_failures = 0
        self._next_start_at = 0.0
        self._closed = False

        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._starter = ThreadPoolExecutor(
            max_workers=max(1, config.max_parallel_starts), thread_name_prefix="fn-pool-start"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background maintenance thread (fills the pool right away)."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._maintenance_loop, daemon=True, name="fn-pool-maintenance"
        )
        self._thread.start()

    def take(self) -> PooledContainer | None:
        """Hand out one fresh idle container, or None if there is none.

        The container leaves the pool for good: the caller owns it and must destroy
        it after use. Never blocks on docker.
        """
        now = self._clock()
        taken: PooledContainer | None = None
        with self._lock:
            if self._closed:
                return None
            while self._idle:
                candidate = self._idle.popleft()
                if now - candidate.created_at < self._config.ttl_sec:
                    taken = candidate
                    break
                self._retired.append(candidate.name)
            if taken is None:
                self._misses += 1
                self._last_miss_at = now
                self._target = min(self._target + 1, self._config.max_size)
            else:
                self._hits += 1
        self._wake.set()
        return taken

    def stats(self) -> PoolStats:
        with self._lock:
            return PoolStats(
                idle=len(self._idle),
                starting=self._starting,
                target=self._target,
                hits=self._hits,
                misses=self._misses,
            )

    def shutdown(self) -> None:
        """Stop maintenance and destroy every container the pool still holds."""
        with self._lock:
            self._closed = True
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=_SHUTDOWN_JOIN_SEC)
        # Starts already running finish and see ``_closed`` (they remove their own
        # container); queued ones are cancelled before they create anything.
        self._starter.shutdown(wait=True, cancel_futures=True)
        with self._lock:
            leftovers = [c.name for c in self._idle] + self._retired
            self._idle.clear()
            self._retired = []
        for name in leftovers:
            self._runtime.remove(name)

    def maintain(self) -> None:
        """One maintenance pass: retire, reconcile, resize, refill."""
        self._retire_expired()
        self._reconcile_if_due()
        self._scale_down_if_idle()
        self._refill()

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def _maintenance_loop(self) -> None:
        while True:
            with self._lock:
                if self._closed:
                    return
            try:
                self.maintain()
            except Exception:
                logger.exception("run_function pool maintenance failed")
            self._wake.wait(timeout=self._config.maintenance_interval_sec)
            self._wake.clear()

    def _retire_expired(self) -> None:
        now = self._clock()
        with self._lock:
            fresh: deque[PooledContainer] = deque()
            for container in self._idle:
                if now - container.created_at >= self._config.ttl_sec:
                    self._retired.append(container.name)
                else:
                    fresh.append(container)
            self._idle = fresh
            retired, self._retired = self._retired, []
        for name in retired:
            self._runtime.remove(name)

    def _reconcile_if_due(self) -> None:
        listed_at = self._clock()
        if listed_at - self._last_reconcile_at < self._config.reconcile_interval_sec:
            return
        self._last_reconcile_at = listed_at
        try:
            running = set(self._runtime.list_owned())
        except Exception as exc:
            logger.warning(f"run_function pool: could not reconcile with docker: {exc}")
            return
        with self._lock:
            # Containers that became idle after the listing are unknown to it; keep them.
            gone = [c for c in self._idle if c.created_at < listed_at and c.name not in running]
            if gone:
                gone_names = {c.name for c in gone}
                self._idle = deque(c for c in self._idle if c.name not in gone_names)
        if gone:
            logger.warning(f"run_function pool: dropped {len(gone)} vanished container(s)")

    def _scale_down_if_idle(self) -> None:
        now = self._clock()
        with self._lock:
            if (
                self._target > self._config.min_size
                and now - self._last_miss_at >= self._config.scale_down_after_sec
            ):
                self._target -= 1
                # One step per quiet window; surplus idle containers age out via TTL.
                self._last_miss_at = now

    def _refill(self) -> None:
        now = self._clock()
        with self._lock:
            if self._closed or now < self._next_start_at:
                return
            needed = self._target - len(self._idle) - self._starting
            if needed <= 0:
                return
            self._starting += needed
        for _ in range(needed):
            try:
                self._starter.submit(self._start_one)
            except RuntimeError:  # executor already shut down
                with self._lock:
                    self._starting -= 1

    def _start_one(self) -> None:
        name = self._name_factory()
        try:
            self._runtime.start(name)
        except Exception as exc:
            with self._lock:
                self._starting -= 1
                self._start_failures += 1
                backoff = min(_MAX_START_BACKOFF_SEC, 2.0 ** (self._start_failures - 1))
                self._next_start_at = self._clock() + backoff
            logger.warning(
                f"run_function pool: failed to start a sandbox (retry in {backoff:.0f}s): {exc}"
            )
            return

        with self._lock:
            self._starting -= 1
            self._start_failures = 0
            keep = not self._closed and len(self._idle) < self._config.max_size
            if keep:
                self._idle.append(PooledContainer(name=name, created_at=self._clock()))
        if not keep:
            self._runtime.remove(name)
