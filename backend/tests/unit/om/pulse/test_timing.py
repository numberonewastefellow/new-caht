"""Unit tests for om.pulse.timing (pure scheduling math)."""

import datetime as dt

import pytest

from om.pulse.timing import decide_fire
from om.pulse.timing import describe
from om.pulse.timing import describe_cron
from om.pulse.timing import jitter_seconds
from om.pulse.timing import latest_slot_at_or_before
from om.pulse.timing import max_start_delay_seconds
from om.pulse.timing import next_fire_after
from om.pulse.timing import next_fires
from om.pulse.timing import nominal_period_seconds
from om.pulse.timing import render_input_message
from om.pulse.timing import ScheduleSpec
from om.pulse.timing import ScheduleValidationError
from om.pulse.timing import validate_spec

UTC = dt.timezone.utc


def u(*args: int) -> dt.datetime:
    return dt.datetime(*args, tzinfo=UTC)


def cron(expr: str, tz: str = "UTC") -> ScheduleSpec:
    return ScheduleSpec(schedule_type="cron", cron_expression=expr, timezone=tz)


def interval(seconds: int) -> ScheduleSpec:
    return ScheduleSpec(schedule_type="interval", interval_seconds=seconds)


# ---------------------------------------------------------------- cron basics


def test_cron_daily_in_kolkata() -> None:
    spec = cron("0 9 * * *", "Asia/Kolkata")  # 09:00 IST == 03:30 UTC
    assert next_fire_after(spec, u(2026, 10, 25, 0, 0)) == u(2026, 10, 25, 3, 30)
    assert next_fire_after(spec, u(2026, 10, 25, 3, 30)) == u(2026, 10, 26, 3, 30)


def test_cron_is_strictly_after() -> None:
    spec = cron("*/15 * * * *")
    assert next_fire_after(spec, u(2026, 1, 1, 10, 15)) == u(2026, 1, 1, 10, 30)


def test_cron_weekdays_skips_weekend() -> None:
    spec = cron("0 9 * * 1-5")
    # Fri 2026-10-23 10:00 UTC -> next is Mon 2026-10-26 09:00
    assert next_fire_after(spec, u(2026, 10, 23, 10, 0)) == u(2026, 10, 26, 9, 0)


def test_cron_monthly_last_day() -> None:
    spec = cron("0 8 L * *")
    assert next_fire_after(spec, u(2026, 2, 1)) == u(2026, 2, 28, 8, 0)


# ---------------------------------------------------------------- DST


def test_dst_spring_forward_new_york_fires_at_transition() -> None:
    # 2026-03-08: 02:00 EST -> 03:00 EDT. 02:30 local does not exist.
    spec = cron("30 2 * * *", "America/New_York")
    fire = next_fire_after(spec, u(2026, 3, 8, 0, 0))
    # transition instant = 03:00 EDT = 07:00 UTC
    assert fire == u(2026, 3, 8, 7, 0)
    # the day after is normal again: 02:30 EDT = 06:30 UTC
    assert next_fire_after(spec, fire) == u(2026, 3, 9, 6, 30)


def test_dst_fall_back_new_york_fires_once() -> None:
    # 2026-11-01: 02:00 EDT -> 01:00 EST. 01:30 local happens twice.
    spec = cron("30 1 * * *", "America/New_York")
    first = next_fire_after(spec, u(2026, 11, 1, 0, 0))
    assert first == u(2026, 11, 1, 5, 30)  # 01:30 EDT (first occurrence)
    # The repeated 01:30 EST (06:30 UTC) must NOT fire again the same day
    second = next_fire_after(spec, first)
    assert second == u(2026, 11, 2, 6, 30)  # next day 01:30 EST


def test_dst_fall_back_after_inside_repeated_hour() -> None:
    # `after` falls inside the second (fold=1) 01:xx hour; result must be > after.
    spec = cron("*/15 * * * *", "America/New_York")
    after = u(2026, 11, 1, 6, 10)  # 01:10 EST (second occurrence)
    fire = next_fire_after(spec, after)
    assert fire is not None and fire > after


def test_dst_london_spring_and_fall() -> None:
    # 2026-03-29 01:00 GMT -> 02:00 BST ; 2026-10-25 02:00 BST -> 01:00 GMT
    spec = cron("30 1 * * *", "Europe/London")
    assert next_fire_after(spec, u(2026, 3, 29, 0, 0)) == u(2026, 3, 29, 1, 0)
    fall_first = next_fire_after(spec, u(2026, 10, 25, 0, 0))
    assert fall_first == u(2026, 10, 25, 0, 30)  # 01:30 BST
    assert next_fire_after(spec, fall_first) == u(2026, 10, 26, 1, 30)  # 01:30 GMT


def test_interval_ignores_dst() -> None:
    spec = ScheduleSpec(
        schedule_type="interval", interval_seconds=3600, timezone="America/New_York"
    )
    fires = next_fires(spec, after=u(2026, 11, 1, 4, 0), count=4, anchor=u(2026, 11, 1, 4, 0))
    gaps = {(b - a).total_seconds() for a, b in zip(fires, fires[1:])}
    assert gaps == {3600.0}


# ---------------------------------------------------------------- interval / once


def test_interval_anchor_keeps_cadence() -> None:
    spec = interval(300)
    anchor = u(2026, 1, 1, 10, 0)
    assert next_fire_after(spec, u(2026, 1, 1, 10, 7), anchor=anchor) == u(2026, 1, 1, 10, 10)
    assert next_fire_after(spec, u(2026, 1, 1, 10, 0), anchor=anchor) == u(2026, 1, 1, 10, 5)


def test_interval_without_anchor_starts_after_one_period() -> None:
    assert next_fire_after(interval(600), u(2026, 1, 1, 10, 0)) == u(2026, 1, 1, 10, 10)


def test_once() -> None:
    spec = ScheduleSpec(schedule_type="once", run_at=u(2026, 12, 1, 9, 0))
    assert next_fire_after(spec, u(2026, 11, 1)) == u(2026, 12, 1, 9, 0)
    assert next_fire_after(spec, u(2026, 12, 1, 9, 0)) is None


# ---------------------------------------------------------------- misfire


def test_on_time_fire() -> None:
    spec = interval(300)
    d = decide_fire(spec, due=u(2026, 1, 1, 10, 0), now=u(2026, 1, 1, 10, 0, 3), misfire_grace_seconds=300)
    assert d.fire_slot == u(2026, 1, 1, 10, 0)
    assert d.missed_slot is None
    assert d.next_run_at == u(2026, 1, 1, 10, 5)


def test_late_within_grace_still_fires() -> None:
    spec = cron("0 9 * * *")
    d = decide_fire(spec, due=u(2026, 1, 1, 9, 0), now=u(2026, 1, 1, 9, 4), misfire_grace_seconds=300)
    assert d.fire_slot == u(2026, 1, 1, 9, 0)
    assert d.next_run_at == u(2026, 1, 2, 9, 0)


def test_beyond_grace_is_missed_not_fired() -> None:
    spec = cron("0 9 * * *")
    d = decide_fire(spec, due=u(2026, 1, 1, 9, 0), now=u(2026, 1, 1, 12, 0), misfire_grace_seconds=300)
    assert d.fire_slot is None
    assert d.missed_slot == u(2026, 1, 1, 9, 0)
    assert d.next_run_at == u(2026, 1, 2, 9, 0)


def test_downtime_fires_latest_slot_once_and_records_one_missed() -> None:
    spec = interval(300)
    due = u(2026, 1, 1, 10, 0)
    now = u(2026, 1, 1, 10, 22)  # slots 10:00..10:20 passed; 10:20 within grace
    d = decide_fire(spec, due=due, now=now, misfire_grace_seconds=300)
    assert d.fire_slot == u(2026, 1, 1, 10, 20)
    assert d.missed_slot == due
    assert d.next_run_at == u(2026, 1, 1, 10, 25)


def test_week_of_downtime_does_not_loop_or_backfill() -> None:
    spec = cron("*/5 * * * *")
    due = u(2026, 1, 1, 0, 0)
    now = u(2026, 1, 8, 0, 2)
    d = decide_fire(spec, due=due, now=now, misfire_grace_seconds=300)
    assert d.fire_slot == u(2026, 1, 8, 0, 0)
    assert d.missed_slot == due
    assert d.next_run_at == u(2026, 1, 8, 0, 5)


def test_once_misfire_finishes_schedule() -> None:
    spec = ScheduleSpec(schedule_type="once", run_at=u(2026, 1, 1, 9, 0))
    d = decide_fire(spec, due=u(2026, 1, 1, 9, 0), now=u(2026, 1, 1, 9, 1), misfire_grace_seconds=300)
    assert d.fire_slot == u(2026, 1, 1, 9, 0)
    assert d.next_run_at is None


def test_latest_slot_cron() -> None:
    spec = cron("0 * * * *")
    assert latest_slot_at_or_before(spec, u(2026, 1, 1, 1, 0), u(2026, 1, 1, 4, 30)) == u(2026, 1, 1, 4, 0)


# ---------------------------------------------------------------- validation


def test_validate_rejects_too_frequent_cron() -> None:
    with pytest.raises(ScheduleValidationError, match="too often"):
        validate_spec(cron("* * * * *"), min_interval_seconds=300)


def test_validate_rejects_short_interval() -> None:
    with pytest.raises(ScheduleValidationError, match="at least 5 minutes"):
        validate_spec(interval(60), min_interval_seconds=300)


@pytest.mark.parametrize("expr", ["", "0 9 * *", "61 9 * * *", "0 9 * * * *", "banana"])
def test_validate_rejects_bad_cron(expr: str) -> None:
    with pytest.raises(ScheduleValidationError):
        validate_spec(cron(expr), min_interval_seconds=60)


def test_validate_rejects_never_firing_cron() -> None:
    with pytest.raises(ScheduleValidationError):
        validate_spec(cron("0 9 30 2 *"), min_interval_seconds=60)


def test_validate_rejects_unknown_timezone() -> None:
    with pytest.raises(ScheduleValidationError, match="timezone"):
        validate_spec(cron("0 9 * * *", "Mars/Olympus"), min_interval_seconds=60)


def test_validate_normalises_whitespace() -> None:
    spec = validate_spec(cron("  0   9 * *  1-5 "), min_interval_seconds=60)
    assert spec.cron_expression == "0 9 * * 1-5"


def test_validate_once_in_past() -> None:
    spec = ScheduleSpec(schedule_type="once", run_at=u(2020, 1, 1))
    with pytest.raises(ScheduleValidationError, match="future"):
        validate_spec(spec, min_interval_seconds=60, now=u(2026, 1, 1))


# ---------------------------------------------------------------- jitter / period


def test_jitter_is_deterministic_and_bounded() -> None:
    for sid in range(1, 200):
        j = jitter_seconds(sid, 3600)
        assert 0 <= j < 60
        assert j == jitter_seconds(sid, 3600)
    assert jitter_seconds(1, 300) < 30
    assert jitter_seconds(1, None) == 0


def test_period_and_stale_delay() -> None:
    assert nominal_period_seconds(interval(600)) == 600
    assert nominal_period_seconds(cron("0 * * * *"), now=u(2026, 1, 1)) == 3600
    assert max_start_delay_seconds(cron("0 0 * * *"), misfire_grace_seconds=300, now=u(2026, 1, 1)) == 43200
    assert max_start_delay_seconds(interval(300), misfire_grace_seconds=300) == 300


# ---------------------------------------------------------------- describe


@pytest.mark.parametrize(
    "expr,text",
    [
        ("0 9 * * *", "Every day at 09:00"),
        ("0 9 * * 1-5", "Every weekday at 09:00"),
        ("30 8 * * 1,3", "Every Mon, Wed at 08:30"),
        ("0 6 1 * *", "Monthly on day 1 at 06:00"),
        ("0 6 L * *", "Monthly on the last day at 06:00"),
        ("15 * * * *", "Every hour at :15"),
        ("*/30 * * * *", "Every 30 minutes"),
        ("0 9 1 1 *", "Cron: 0 9 1 1 *"),
    ],
)
def test_describe_cron(expr: str, text: str) -> None:
    assert describe_cron(expr) == text


def test_describe_includes_timezone() -> None:
    assert describe(cron("0 9 * * 1-5", "Asia/Kolkata")) == "Every weekday at 09:00 (Asia/Kolkata)"
    assert describe(interval(7200)) == "Every 2 hours"


# ---------------------------------------------------------------- templating


def test_render_template_variables() -> None:
    out = render_input_message(
        "Brief for {{date}} ({{ window_start }} -> {{window_end}}) at {{now}} {{unknown}}",
        timezone="Asia/Kolkata",
        scheduled_for=u(2026, 10, 26, 3, 30),
        now=u(2026, 10, 26, 3, 30, 5),
        last_success_scheduled_for=u(2026, 10, 23, 3, 30),
        period_seconds=86400,
    )
    assert out.startswith("Brief for 2026-10-26 (2026-10-23 09:00 IST -> 2026-10-26 09:00 IST)")
    assert "{{unknown}}" in out


def test_render_template_first_run_window_falls_back_to_one_period() -> None:
    out = render_input_message(
        "{{window_start}}",
        timezone="UTC",
        scheduled_for=u(2026, 1, 2, 9, 0),
        now=u(2026, 1, 2, 9, 0),
        last_success_scheduled_for=None,
        period_seconds=86400,
    )
    assert out == "2026-01-01 09:00 UTC"
