"""Tests for the warm pool of single-use run_function containers.

A fake runtime stands in for Docker and a manual clock drives TTL/scale-down, so the
tests are deterministic. ``maintain()`` is called directly; the background thread is
only started in the lifecycle tests.
"""

from __future__ import annotations

import itertools
import threading
import time
from collections.abc import Callable, Generator

import pytest

from app.services.warm_pool import PoolConfig, WarmContainerPool


class FakeRuntime:
    def __init__(self) -> None:
        self.running: set[str] = set()
        self.started: list[str] = []
        self.removed: list[str] = []
        self.fail_starts = False
        self.fail_list = False
        self._lock = threading.Lock()

    def start(self, name: str) -> None:
        if self.fail_starts:
            raise RuntimeError("docker is down")
        with self._lock:
            self.started.append(name)
            self.running.add(name)

    def remove(self, name: str) -> None:
        with self._lock:
            self.removed.append(name)
            self.running.discard(name)

    def list_owned(self, *, include_stopped: bool = False) -> list[str]:  # noqa: ARG002
        if self.fail_list:
            raise RuntimeError("docker is down")
        with self._lock:
            return sorted(self.running)


class ManualClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _wait_until(predicate: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not reached in time")
        time.sleep(0.01)


@pytest.fixture()
def runtime() -> FakeRuntime:
    return FakeRuntime()


@pytest.fixture()
def clock() -> ManualClock:
    return ManualClock()


@pytest.fixture()
def make_pool(
    runtime: FakeRuntime, clock: ManualClock
) -> Generator[Callable[..., WarmContainerPool], None, None]:
    pools: list[WarmContainerPool] = []
    counter = itertools.count()

    def factory(**overrides: float) -> WarmContainerPool:
        params: dict[str, float] = {"min_size": 2, "max_size": 4, "ttl_sec": 600}
        params.update(overrides)
        pool = WarmContainerPool(
            runtime,
            PoolConfig(**params),  # type: ignore[arg-type]
            name_factory=lambda: f"ci-fn-{next(counter)}",
            clock=clock,
        )
        pools.append(pool)
        return pool

    yield factory
    for pool in pools:
        pool.shutdown()


def _settle(pool: WarmContainerPool) -> None:
    """Run one maintenance pass and wait for the starts it triggered."""
    pool.maintain()
    _wait_until(lambda: pool.stats().starting == 0)


def test_config_rejects_bad_sizes() -> None:
    with pytest.raises(ValueError):
        PoolConfig(min_size=3, max_size=2, ttl_sec=60)
    with pytest.raises(ValueError):
        PoolConfig(min_size=1, max_size=2, ttl_sec=0)


def test_fills_to_min(make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime) -> None:
    pool = make_pool(min_size=2, max_size=4)
    _settle(pool)
    assert pool.stats().idle == 2
    assert len(runtime.started) == 2
    _settle(pool)  # already full: no extra starts
    assert len(runtime.started) == 2


def test_take_hands_each_container_out_once(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime
) -> None:
    pool = make_pool(min_size=2, max_size=2)
    _settle(pool)
    first, second = pool.take(), pool.take()
    assert first is not None and second is not None
    assert first.name != second.name
    assert pool.stats().idle == 0
    # The pool never gives a taken container back out, even after refills.
    _settle(pool)
    later = {pool.take(), pool.take()}
    assert all(c is not None for c in later)
    assert {c.name for c in later if c is not None}.isdisjoint({first.name, second.name})


def test_take_does_not_remove_container(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime
) -> None:
    # The caller owns (and destroys) the taken container; the pool must not.
    pool = make_pool(min_size=1, max_size=1)
    _settle(pool)
    taken = pool.take()
    assert taken is not None
    _settle(pool)
    assert taken.name not in runtime.removed


def test_refills_after_take(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime
) -> None:
    pool = make_pool(min_size=2, max_size=2)
    _settle(pool)
    assert pool.take() is not None
    assert pool.stats().idle == 1
    _settle(pool)
    assert pool.stats().idle == 2
    assert len(runtime.started) == 3


def test_empty_pool_returns_none_and_grows_toward_max(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime
) -> None:
    pool = make_pool(min_size=0, max_size=2)
    _settle(pool)
    assert pool.stats().idle == 0

    assert pool.take() is None  # caller falls back to a cold start
    assert pool.stats().misses == 1
    assert pool.stats().target == 1
    assert pool.take() is None
    assert pool.take() is None
    assert pool.stats().target == 2  # capped at max
    _settle(pool)
    assert pool.stats().idle == 2


def test_scales_back_down_after_quiet_period(
    make_pool: Callable[..., WarmContainerPool], clock: ManualClock
) -> None:
    pool = make_pool(min_size=1, max_size=3, scale_down_after_sec=60)
    pool.take()
    pool.take()
    assert pool.stats().target == 3
    clock.advance(61)
    pool.maintain()
    assert pool.stats().target == 2
    pool.maintain()  # one step per quiet window
    assert pool.stats().target == 2
    clock.advance(61)
    pool.maintain()
    clock.advance(61)
    pool.maintain()
    assert pool.stats().target == 1  # never below min


def test_ttl_recycles_old_idle_containers(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime, clock: ManualClock
) -> None:
    pool = make_pool(min_size=2, max_size=2, ttl_sec=600)
    _settle(pool)
    old = set(runtime.running)
    clock.advance(601)
    _settle(pool)
    assert old.issubset(set(runtime.removed))
    assert pool.stats().idle == 2
    assert set(runtime.running).isdisjoint(old)


def test_take_skips_expired_containers(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime, clock: ManualClock
) -> None:
    pool = make_pool(min_size=1, max_size=1, ttl_sec=600)
    _settle(pool)
    (stale,) = runtime.running
    clock.advance(601)
    assert pool.take() is None  # expired one is not handed out
    _settle(pool)
    assert stale in runtime.removed  # removed off the request path


def test_cap_at_max_discards_surplus_start(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime
) -> None:
    pool = make_pool(min_size=1, max_size=1)
    _settle(pool)
    # Simulate a start finishing while the pool is already full.
    pool._start_one()
    assert pool.stats().idle == 1
    assert runtime.removed == [runtime.started[-1]]


def test_failed_starts_back_off(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime, clock: ManualClock
) -> None:
    runtime.fail_starts = True
    pool = make_pool(min_size=2, max_size=2)
    _settle(pool)
    assert pool.stats().idle == 0
    runtime.fail_starts = False
    _settle(pool)  # still inside the backoff window
    assert pool.stats().idle == 0
    clock.advance(31)
    _settle(pool)
    assert pool.stats().idle == 2


def test_reconcile_drops_vanished_containers(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime, clock: ManualClock
) -> None:
    pool = make_pool(min_size=2, max_size=2, reconcile_interval_sec=30)
    _settle(pool)
    vanished = sorted(runtime.running)[0]
    runtime.running.discard(vanished)  # e.g. killed by a daemon restart
    clock.advance(31)
    _settle(pool)
    assert pool.stats().idle == 2
    names = set()
    while (c := pool.take()) is not None:
        names.add(c.name)
    assert vanished not in names


def test_reconcile_failure_keeps_pool(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime, clock: ManualClock
) -> None:
    pool = make_pool(min_size=2, max_size=2, reconcile_interval_sec=30)
    _settle(pool)
    runtime.fail_list = True
    clock.advance(31)
    _settle(pool)
    assert pool.stats().idle == 2


def test_shutdown_removes_idle_containers(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime
) -> None:
    pool = make_pool(min_size=3, max_size=3)
    _settle(pool)
    pool.shutdown()
    assert runtime.running == set()
    assert pool.take() is None


def test_background_thread_fills_and_refills(
    make_pool: Callable[..., WarmContainerPool], runtime: FakeRuntime
) -> None:
    pool = make_pool(min_size=2, max_size=2, maintenance_interval_sec=0.05)
    pool.start()
    _wait_until(lambda: pool.stats().idle == 2)
    assert pool.take() is not None
    _wait_until(lambda: pool.stats().idle == 2)  # take() wakes the refill
    pool.shutdown()
    assert runtime.running == {n for n in runtime.started if n not in runtime.removed}
    assert len(runtime.running) == 1  # only the taken one, which the caller owns


def test_concurrent_takes_never_share_a_container(
    make_pool: Callable[..., WarmContainerPool],
) -> None:
    pool = make_pool(min_size=4, max_size=4)
    _settle(pool)
    got: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        c = pool.take()
        if c is not None:
            with lock:
                got.append(c.name)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(got) == 4
    assert len(set(got)) == 4
