"""Enqueue a Pulse run on the `pulse` Celery queue (consumed by `pulse_worker`)."""

from om.background.celery.versioned_apps.client import app as client_app
from om.configs.constants import OmCeleryPriority
from om.configs.constants import OmCeleryQueues
from om.configs.constants import OmCeleryTask


def pulse_task_id(run_id: int) -> str:
    return f"pulse-run-{run_id}"


def enqueue_pulse_run(run_id: int, tenant_id: str, countdown: int = 0) -> None:
    """At-least-once enqueue. Safe to call repeatedly for the same run: the worker's
    compare-and-swap (pending -> running) makes duplicate deliveries no-ops."""
    client_app.send_task(
        OmCeleryTask.PULSE_RUN_SCHEDULED_WORKFLOW,
        kwargs={"run_id": run_id, "tenant_id": tenant_id},
        queue=OmCeleryQueues.PULSE,
        task_id=pulse_task_id(run_id),
        priority=OmCeleryPriority.MEDIUM,
        countdown=countdown or None,
        ignore_result=True,
    )
