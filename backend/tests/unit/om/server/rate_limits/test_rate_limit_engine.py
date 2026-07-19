"""Unit tests for the rate-limits core logic (no live Redis/DB required).

Covers the pure, deterministic pieces: sliding-window arithmetic, subject keying, the roll-up hour
bucket, and API-model validation. The token-weighted sliding-window formula that runs inside the
engine's Lua is mirrored here by a small reference implementation so the algorithm's properties
(monotonic decay, boundary behaviour, budget math) are asserted directly.
"""

import math
from datetime import datetime
from datetime import timezone
from uuid import UUID

import pytest

from om.server.rate_limits.constants import RateLimitScope
from om.server.rate_limits.constants import subject_key
from om.server.rate_limits.engine import WindowMath
from om.server.rate_limits.repository import _hour_bucket


# ---- WindowMath (real code) ------------------------------------------------------------


def test_window_math_indices_and_elapsed() -> None:
    period_hours = 2
    window_ms = period_hours * 3600 * 1000
    # 1.5 windows in → current index 1, elapsed = half a window.
    now_ms = window_ms + window_ms // 2
    w = WindowMath.compute(period_hours, now_ms)
    assert w.window_ms == window_ms
    assert w.current_index == 1
    assert w.previous_index == 0
    assert w.elapsed_ms == window_ms // 2
    assert w.ttl_ms == 2 * window_ms


def test_window_math_reset_seconds_decreases_through_window() -> None:
    window_ms = 3600 * 1000  # 1h
    start = WindowMath.compute(1, window_ms * 5)  # exactly on a boundary
    mid = WindowMath.compute(1, window_ms * 5 + window_ms // 2)
    assert start.reset_seconds > mid.reset_seconds
    # At the boundary the reset is ~the full window; near the end it is small.
    assert start.reset_seconds == pytest.approx(3600, abs=2)
    assert mid.reset_seconds == pytest.approx(1800, abs=2)


def test_window_math_rejects_nonpositive_period() -> None:
    with pytest.raises(ValueError):
        WindowMath.compute(0, 1000)


# ---- sliding-window weighting (reference model of the Lua) ------------------------------


def _sliding_estimate(cur: int, prev: int, elapsed_ms: int, window_ms: int) -> int:
    """Mirror of the engine's Lua weighting so the algorithm is asserted independently."""
    weight = max(0.0, (window_ms - elapsed_ms) / window_ms)
    return cur + math.floor(prev * weight)


def test_sliding_weight_full_at_window_start() -> None:
    window = 3600 * 1000
    # Just after roll: previous window counts at ~full weight.
    assert _sliding_estimate(cur=0, prev=1000, elapsed_ms=0, window_ms=window) == 1000


def test_sliding_weight_zero_at_window_end() -> None:
    window = 3600 * 1000
    # At the very end of the window the previous window has rolled off.
    assert _sliding_estimate(cur=0, prev=1000, elapsed_ms=window, window_ms=window) == 0


def test_sliding_weight_linear_midpoint() -> None:
    window = 3600 * 1000
    est = _sliding_estimate(cur=200, prev=1000, elapsed_ms=window // 2, window_ms=window)
    # current (200) + half of previous (500) = 700
    assert est == 700


def test_budget_decision_boundary() -> None:
    # Throttle iff used >= budget (matches service.check).
    budget = 1000
    assert _sliding_estimate(1000, 0, 0, 3600_000) >= budget  # exactly at budget -> throttle
    assert not (_sliding_estimate(999, 0, 0, 3600_000) >= budget)  # just under -> allow


# ---- subject keying (real code) --------------------------------------------------------


def test_subject_key_tenant_wide_uses_scope_name() -> None:
    assert subject_key(RateLimitScope.GLOBAL, None, None) == "global"
    assert subject_key(RateLimitScope.TENANT, None, None) == "tenant"


def test_subject_key_user_and_team() -> None:
    uid = UUID(int=7)
    assert subject_key(RateLimitScope.USER, uid, None) == f"user:{uid}"
    assert subject_key(RateLimitScope.TEAM, None, 42) == "team:42"


def test_subject_key_requires_matching_subject() -> None:
    with pytest.raises(ValueError):
        subject_key(RateLimitScope.USER, None, None)
    with pytest.raises(ValueError):
        subject_key(RateLimitScope.TEAM, None, None)


# ---- roll-up hour bucket (real code) ---------------------------------------------------


def test_hour_bucket_truncates_to_utc_hour() -> None:
    moment = datetime(2026, 7, 19, 14, 37, 12, 500, tzinfo=timezone.utc)
    assert _hour_bucket(moment) == datetime(2026, 7, 19, 14, 0, 0, tzinfo=timezone.utc)


# ---- API-model validation (real code) --------------------------------------------------


def test_policy_args_validation() -> None:
    from om.server.rate_limits.api_models import RateLimitPolicyArgs

    # per-user default (user_id omitted) is valid
    RateLimitPolicyArgs(scope="user", token_budget=1000, period_hours=1)
    # tenant-wide with a subject is rejected
    with pytest.raises(ValueError):
        RateLimitPolicyArgs(
            scope="tenant", token_budget=1, period_hours=1, team_id=5
        )
    # team scope requires a team
    with pytest.raises(ValueError):
        RateLimitPolicyArgs(scope="team", token_budget=1, period_hours=1)
    # non-positive window rejected
    with pytest.raises(ValueError):
        RateLimitPolicyArgs(scope="global", token_budget=1, period_hours=0)
