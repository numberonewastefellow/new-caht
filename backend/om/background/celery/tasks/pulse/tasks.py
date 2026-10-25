"""Pulse worker task: execute one scheduled workflow run."""

import socket

from celery import shared_task
from celery import Task

from om.configs.constants import OmCeleryTask
from om.pulse.runner import execute_pulse_run
from om.utils.logger import setup_logger

logger = setup_logger()


@shared_task(
    name=OmCeleryTask.PULSE_RUN_SCHEDULED_WORKFLOW,
    bind=True,
    ignore_result=True,
    acks_late=False,
    # No Celery retries: a half-finished LLM run is never replayed automatically.
    max_retries=0,
)
def pulse_run_scheduled_workflow(self: Task, *, run_id: int, tenant_id: str) -> str | None:  # noqa: ARG001
    hostname = self.request.hostname or socket.gethostname()
    logger.info(f"Pulse: executing run {run_id} (tenant={tenant_id}, host={hostname})")
    status = execute_pulse_run(run_id, tenant_id, hostname)
    logger.info(f"Pulse: run {run_id} finished with status={status}")
    return status
