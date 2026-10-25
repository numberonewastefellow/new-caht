from om.db.models import PulseSchedule
from om.pulse.timing import ScheduleSpec


def spec_from_schedule(schedule: PulseSchedule) -> ScheduleSpec:
    return ScheduleSpec(
        schedule_type=schedule.schedule_type,
        timezone=schedule.timezone or "UTC",
        cron_expression=schedule.cron_expression,
        interval_seconds=schedule.interval_seconds,
        run_at=schedule.run_at,
    )
