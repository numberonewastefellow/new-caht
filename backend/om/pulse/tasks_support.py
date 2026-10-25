"""Helpers used by the pulse_worker Celery app's lifecycle signals."""

from om.db.engine.sql_engine import get_session_with_tenant
from om.db.engine.tenant_utils import get_all_tenant_ids
from om.db.pulse import get_running_runs_for_host
from om.pulse.scheduler import interrupt_run
from om.utils.logger import setup_logger

logger = setup_logger()


def interrupt_local_runs(hostname: str) -> None:
    """Interrupt runs owned by this worker node (called after its pool stopped).

    Same handling as the scheduler's heartbeat reaper, just immediate."""
    if not hostname:
        return
    for tenant_id in get_all_tenant_ids():
        with get_session_with_tenant(tenant_id=tenant_id) as db_session:
            runs = [
                (r.id, r.schedule_id, r.chat_session_id)
                for r in get_running_runs_for_host(db_session, hostname)
            ]
            done = [
                run_id
                for run_id, schedule_id, chat_session_id in runs
                if interrupt_run(
                    db_session,
                    tenant_id,
                    run_id=run_id,
                    schedule_id=schedule_id,
                    chat_session_id=chat_session_id,
                    error="Worker shut down while the run was in progress",
                )
            ]
        if done:
            logger.warning(
                f"Pulse: marked {len(done)} in-flight run(s) interrupted on shutdown: {done}"
            )
