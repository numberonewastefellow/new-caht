"""Pure scheduling math for Pulse. No DB / Celery imports — unit-test friendly.

All datetimes passed in or returned are timezone-aware UTC unless stated otherwise.

Cron expressions are evaluated on the schedule's *local wall clock* (IANA timezone):
  * a local time skipped by a DST "spring forward" fires at the transition instant
    (e.g. 02:30 on the US spring-forward day fires at 03:00 local);
  * a local time repeated by a DST "fall back" fires once (first occurrence, fold=0).
Interval schedules are plain UTC arithmetic and ignore DST.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass
from typing import Literal
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

from croniter import croniter
from croniter import CroniterBadDateError

ScheduleType = Literal["cron", "interval", "once"]
SCHEDULE_TYPES: tuple[str, ...] = ("cron", "interval", "once")

UTC = dt.timezone.utc

# Safety bound for loops that walk cron fire times
_MAX_CRON_STEPS = 2000
# How far ahead to sample when estimating a cron schedule's minimum gap
_GAP_SAMPLE_SIZE = 12

_WEEKDAY_NAMES = {
    "0": "Sun",
    "1": "Mon",
    "2": "Tue",
    "3": "Wed",
    "4": "Thu",
    "5": "Fri",
    "6": "Sat",
    "7": "Sun",
}


class ScheduleValidationError(ValueError):
    """Raised for an invalid schedule definition; message is user-facing."""


@dataclass(frozen=True)
class ScheduleSpec:
    schedule_type: str
    timezone: str = "UTC"
    cron_expression: str | None = None
    interval_seconds: int | None = None
    run_at: dt.datetime | None = None


@dataclass(frozen=True)
class FireDecision:
    """What the scheduler should do with a due schedule.

    fire_slot:   nominal slot to run now (None => nothing to run)
    missed_slot: a slot to record as `missed` (None => nothing missed)
    next_run_at: next nominal slot strictly after `now` (None => schedule is finished)
    """

    fire_slot: dt.datetime | None
    missed_slot: dt.datetime | None
    next_run_at: dt.datetime | None


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def utc_now() -> dt.datetime:
    return dt.datetime.now(tz=UTC)


def ensure_utc(value: dt.datetime) -> dt.datetime:
    """Interpret naive datetimes as UTC; convert aware ones to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_zone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ScheduleValidationError(f"Unknown timezone '{tz_name}'")


def _local_wall_to_utc(wall: dt.datetime, zone: ZoneInfo) -> dt.datetime:
    """Convert a naive local wall-clock time to UTC with the DST rules above."""
    first = wall.replace(tzinfo=zone, fold=0)
    first_utc = first.astimezone(UTC)
    # Does this wall time exist? (round-trip check)
    if first_utc.astimezone(zone).replace(tzinfo=None) == wall:
        return first_utc  # normal or ambiguous (fold=0 => first occurrence)

    # Non-existent (DST gap): fire at the transition instant, i.e. the earliest
    # UTC instant whose local wall time is >= `wall`.
    lo = wall.replace(tzinfo=zone, fold=1).astimezone(UTC)
    hi = first_utc
    if lo > hi:
        lo, hi = hi, lo
    while (hi - lo) > dt.timedelta(seconds=1):
        mid = lo + (hi - lo) / 2
        if mid.astimezone(zone).replace(tzinfo=None) >= wall:
            hi = mid
        else:
            lo = mid
    return hi.replace(microsecond=0)


def _cron_parts(expr: str) -> list[str]:
    return expr.split()


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------


def validate_cron_expression(expr: str | None) -> str:
    if not expr or not expr.strip():
        raise ScheduleValidationError("Cron expression is required")
    expr = " ".join(expr.split())
    if len(_cron_parts(expr)) != 5:
        raise ScheduleValidationError(
            "Cron expression must have 5 fields: minute hour day-of-month month day-of-week"
        )
    if not croniter.is_valid(expr):
        raise ScheduleValidationError(f"Invalid cron expression '{expr}'")
    return expr


def validate_spec(
    spec: ScheduleSpec,
    *,
    min_interval_seconds: int,
    now: dt.datetime | None = None,
) -> ScheduleSpec:
    """Validate and normalise a spec. Returns the normalised spec."""
    now = ensure_utc(now or utc_now())
    if spec.schedule_type not in SCHEDULE_TYPES:
        raise ScheduleValidationError(
            f"schedule_type must be one of {', '.join(SCHEDULE_TYPES)}"
        )
    get_zone(spec.timezone)

    if spec.schedule_type == "cron":
        expr = validate_cron_expression(spec.cron_expression)
        normalised = ScheduleSpec(
            schedule_type="cron", timezone=spec.timezone, cron_expression=expr
        )
        fires = next_fires(normalised, after=now, count=_GAP_SAMPLE_SIZE)
        if not fires:
            raise ScheduleValidationError(
                f"Cron expression '{expr}' never fires (e.g. a date that does not exist)"
            )
        gap = min_gap_seconds(fires)
        if gap is not None and gap < min_interval_seconds:
            raise ScheduleValidationError(
                f"Schedule fires too often (every {format_duration(gap)}); "
                f"the minimum is every {format_duration(min_interval_seconds)}"
            )
        return normalised

    if spec.schedule_type == "interval":
        if spec.interval_seconds is None or spec.interval_seconds <= 0:
            raise ScheduleValidationError("interval_seconds must be a positive number")
        if spec.interval_seconds < min_interval_seconds:
            raise ScheduleValidationError(
                f"Interval must be at least {format_duration(min_interval_seconds)}"
            )
        return ScheduleSpec(
            schedule_type="interval",
            timezone=spec.timezone,
            interval_seconds=int(spec.interval_seconds),
        )

    # once
    if spec.run_at is None:
        raise ScheduleValidationError("run_at is required for a one-time schedule")
    run_at = ensure_utc(spec.run_at)
    if run_at <= now - dt.timedelta(seconds=60):
        raise ScheduleValidationError("run_at must be in the future")
    return ScheduleSpec(schedule_type="once", timezone=spec.timezone, run_at=run_at)


# ---------------------------------------------------------------------------
# fire-time computation
# ---------------------------------------------------------------------------


def next_fire_after(
    spec: ScheduleSpec,
    after: dt.datetime,
    *,
    anchor: dt.datetime | None = None,
) -> dt.datetime | None:
    """First nominal fire time strictly after `after` (UTC). None if none.

    For interval schedules, `anchor` (a previous nominal slot) keeps the cadence
    drift-free: result = anchor + k * interval. Without an anchor the first fire is
    `after + interval`.
    """
    after = ensure_utc(after)

    if spec.schedule_type == "once":
        if spec.run_at is None:
            return None
        run_at = ensure_utc(spec.run_at)
        return run_at if run_at > after else None

    if spec.schedule_type == "interval":
        interval = int(spec.interval_seconds or 0)
        if interval <= 0:
            return None
        if anchor is None:
            return after + dt.timedelta(seconds=interval)
        anchor = ensure_utc(anchor)
        if anchor > after:
            return anchor
        steps = int((after - anchor).total_seconds() // interval) + 1
        return anchor + dt.timedelta(seconds=steps * interval)

    if spec.schedule_type == "cron":
        if not spec.cron_expression:
            return None
        zone = get_zone(spec.timezone)
        # Walk local wall-clock times; guard against DST ambiguity by requiring
        # the UTC result to be strictly after `after`.
        start_wall = after.astimezone(zone).replace(tzinfo=None)
        # Step back one hour so a wall time inside a repeated (fold=1) hour is
        # still considered; the `> after` guard below filters stale candidates.
        itr = croniter(spec.cron_expression, start_wall - dt.timedelta(hours=1))
        try:
            for _ in range(_MAX_CRON_STEPS):
                wall = itr.get_next(dt.datetime)
                candidate = _local_wall_to_utc(wall, zone)
                if candidate > after:
                    return candidate
        except CroniterBadDateError:
            return None
        return None

    return None


def next_fires(
    spec: ScheduleSpec,
    *,
    after: dt.datetime,
    count: int,
    anchor: dt.datetime | None = None,
) -> list[dt.datetime]:
    out: list[dt.datetime] = []
    cursor = ensure_utc(after)
    for _ in range(count):
        nxt = next_fire_after(spec, cursor, anchor=anchor)
        if nxt is None:
            break
        out.append(nxt)
        cursor = nxt
        if spec.schedule_type == "interval":
            anchor = nxt
    return out


def latest_slot_at_or_before(
    spec: ScheduleSpec, due: dt.datetime, now: dt.datetime
) -> dt.datetime:
    """Latest nominal slot in [due, now]. `due` is assumed to be a valid slot <= now."""
    due = ensure_utc(due)
    now = ensure_utc(now)
    if now <= due or spec.schedule_type == "once":
        return due
    if spec.schedule_type == "interval":
        interval = int(spec.interval_seconds or 0)
        if interval <= 0:
            return due
        steps = int((now - due).total_seconds() // interval)
        return due + dt.timedelta(seconds=steps * interval)
    # cron: walk forward (bounded); after long downtime fall back to `get_prev`
    latest = due
    cursor = due
    for _ in range(_MAX_CRON_STEPS):
        nxt = next_fire_after(spec, cursor)
        if nxt is None or nxt > now:
            return latest
        latest = nxt
        cursor = nxt
    zone = get_zone(spec.timezone)
    assert spec.cron_expression
    prev_wall = croniter(
        spec.cron_expression, now.astimezone(zone).replace(tzinfo=None)
    ).get_prev(dt.datetime)
    prev = _local_wall_to_utc(prev_wall, zone)
    return prev if prev <= now else latest


def decide_fire(
    spec: ScheduleSpec,
    *,
    due: dt.datetime,
    now: dt.datetime,
    misfire_grace_seconds: int,
) -> FireDecision:
    """Misfire handling for a schedule whose nominal `next_run_at` (`due`) is <= now.

    * The latest slot in [due, now] runs if it is no later than the grace period;
      otherwise it is recorded as `missed`.
    * If earlier slots were skipped over (downtime), the first of them is recorded
      as `missed` (one row, never a backlog of runs).
    * The next slot is computed strictly after `now` — never loops through history.
    """
    due = ensure_utc(due)
    now = ensure_utc(now)
    latest = latest_slot_at_or_before(spec, due, now)
    lateness = (now - latest).total_seconds()

    fire_slot: dt.datetime | None
    missed_slot: dt.datetime | None
    if lateness <= misfire_grace_seconds:
        fire_slot = latest
        missed_slot = due if latest != due else None
    else:
        fire_slot = None
        missed_slot = latest

    if spec.schedule_type == "once":
        next_run_at = None
    else:
        anchor = latest if spec.schedule_type == "interval" else None
        next_run_at = next_fire_after(spec, now, anchor=anchor)
    return FireDecision(
        fire_slot=fire_slot, missed_slot=missed_slot, next_run_at=next_run_at
    )


def min_gap_seconds(fires: list[dt.datetime]) -> int | None:
    if len(fires) < 2:
        return None
    return int(min((b - a).total_seconds() for a, b in zip(fires, fires[1:])))


def nominal_period_seconds(
    spec: ScheduleSpec, *, now: dt.datetime | None = None
) -> int | None:
    """Typical gap between fires (interval, or the next cron gap). None for once."""
    if spec.schedule_type == "interval":
        return int(spec.interval_seconds or 0) or None
    if spec.schedule_type == "cron":
        fires = next_fires(spec, after=ensure_utc(now or utc_now()), count=2)
        return min_gap_seconds(fires)
    return None


def jitter_seconds(schedule_id: int, period_seconds: int | None) -> int:
    """Deterministic per-schedule delay in [0, min(60, period/10)) to spread load
    when many schedules share the same slot (e.g. top of the hour)."""
    if not period_seconds or period_seconds <= 0:
        return 0
    window = min(60, period_seconds // 10)
    if window <= 0:
        return 0
    digest = hashlib.sha256(f"pulse:{schedule_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % window


def max_start_delay_seconds(
    spec: ScheduleSpec, *, misfire_grace_seconds: int, now: dt.datetime | None = None
) -> int:
    """How late a run may start before it is considered stale (`missed`)."""
    period = nominal_period_seconds(spec, now=now)
    if period:
        return max(misfire_grace_seconds, period // 2)
    return misfire_grace_seconds


# ---------------------------------------------------------------------------
# human-readable description
# ---------------------------------------------------------------------------


def format_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds % 86400 == 0 and seconds >= 86400:
        n = seconds // 86400
        return f"{n} day{'s' if n != 1 else ''}"
    if seconds % 3600 == 0 and seconds >= 3600:
        n = seconds // 3600
        return f"{n} hour{'s' if n != 1 else ''}"
    if seconds % 60 == 0 and seconds >= 60:
        n = seconds // 60
        return f"{n} minute{'s' if n != 1 else ''}"
    return f"{seconds} second{'s' if seconds != 1 else ''}"


def _is_int(value: str) -> bool:
    return value.isdigit()


def _hhmm(hour: str, minute: str) -> str:
    return f"{int(hour):02d}:{int(minute):02d}"


def _describe_weekdays(field: str) -> str | None:
    if field in ("1-5", "MON-FRI", "mon-fri"):
        return "every weekday"
    if field in ("0,6", "6,0", "SAT,SUN", "sat,sun"):
        return "every weekend day"
    parts = field.split(",")
    if all(p in _WEEKDAY_NAMES for p in parts):
        names = [_WEEKDAY_NAMES[p] for p in parts]
        return "every " + ", ".join(names)
    return None


def describe_cron(expr: str) -> str:
    parts = _cron_parts(expr)
    if len(parts) != 5:
        return f"Cron: {expr}"
    minute, hour, dom, month, dow = parts
    if month != "*":
        return f"Cron: {expr}"

    # every N minutes / hours
    if minute.startswith("*/") and hour == "*" and dom == "*" and dow == "*":
        return f"Every {minute[2:]} minutes"
    if minute == "*" and hour == "*" and dom == "*" and dow == "*":
        return "Every minute"
    if _is_int(minute) and hour == "*" and dom == "*" and dow == "*":
        return f"Every hour at :{int(minute):02d}"
    if _is_int(minute) and hour.startswith("*/") and dom == "*" and dow == "*":
        return f"Every {hour[2:]} hours at :{int(minute):02d}"

    if not (_is_int(minute) and _is_int(hour)):
        return f"Cron: {expr}"
    at = _hhmm(hour, minute)

    if dom == "*" and dow == "*":
        return f"Every day at {at}"
    if dom == "*":
        days = _describe_weekdays(dow)
        if days:
            return f"{days[0].upper()}{days[1:]} at {at}"
        return f"Cron: {expr}"
    if dow == "*":
        if dom == "L":
            return f"Monthly on the last day at {at}"
        if _is_int(dom):
            return f"Monthly on day {int(dom)} at {at}"
    return f"Cron: {expr}"


def describe(spec: ScheduleSpec) -> str:
    tz_suffix = f" ({spec.timezone})"
    if spec.schedule_type == "interval" and spec.interval_seconds:
        return f"Every {format_duration(spec.interval_seconds)}"
    if spec.schedule_type == "once" and spec.run_at:
        local = ensure_utc(spec.run_at).astimezone(get_zone(spec.timezone))
        return f"Once on {local.strftime('%a %d %b %Y at %H:%M')}{tz_suffix}"
    if spec.schedule_type == "cron" and spec.cron_expression:
        return describe_cron(spec.cron_expression) + tz_suffix
    return "Invalid schedule"


# ---------------------------------------------------------------------------
# input templating
# ---------------------------------------------------------------------------

_TEMPLATE_RE = re.compile(r"\{\{\s*([a-zA-Z_]+)\s*\}\}")
TEMPLATE_VARIABLES: tuple[str, ...] = ("date", "now", "window_start", "window_end")
# Only available in list mode
LIST_TEMPLATE_VARIABLES: tuple[str, ...] = ("item",)


def _fmt_local(value: dt.datetime, zone: ZoneInfo) -> str:
    local = ensure_utc(value).astimezone(zone)
    return local.strftime("%Y-%m-%d %H:%M %Z").strip()


def render_input_message(
    template: str,
    *,
    timezone: str,
    scheduled_for: dt.datetime,
    now: dt.datetime,
    last_success_scheduled_for: dt.datetime | None,
    period_seconds: int | None,
    item: str | None = None,
) -> str:
    """Substitute {{date}} {{now}} {{window_start}} {{window_end}} (+ {{item}}).

    window_start = the previous *successful* run's slot (so a failed run never
    leaves a gap); on the first run it falls back to one period before this slot.
    Unknown placeholders are left untouched.
    """
    try:
        zone = get_zone(timezone)
    except ScheduleValidationError:
        zone = ZoneInfo("UTC")
    scheduled_for = ensure_utc(scheduled_for)

    if last_success_scheduled_for is not None:
        window_start: str = _fmt_local(last_success_scheduled_for, zone)
    elif period_seconds:
        window_start = _fmt_local(
            scheduled_for - dt.timedelta(seconds=period_seconds), zone
        )
    else:
        window_start = "the beginning"

    values = {
        "date": ensure_utc(scheduled_for).astimezone(zone).strftime("%Y-%m-%d"),
        "now": _fmt_local(now, zone),
        "window_start": window_start,
        "window_end": _fmt_local(scheduled_for, zone),
    }
    if item is not None:  # list mode: the current item (inserted verbatim)
        values["item"] = item

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        return values.get(key, match.group(0))

    return _TEMPLATE_RE.sub(_sub, template)
