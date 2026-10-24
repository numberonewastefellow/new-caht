"""Helpers used by the pulse_worker Celery app's lifecycle signals."""

from om.db.engine.sql_engine import get_session_with_tenant
from om.db.engine.tenant_utils import get_all_tenant_ids
from om.db.pulse import interrupt_runs_for_host
from om.utils.logger import setup_logger

logger = setup_logger()


def interrupt_local_runs(hostname: str) -> None:
    """Mark runs owned by this worker node as interrupted (after the pool stopped)."""
    if not hostname:
        return
    for tenant_id in get_all_tenant_ids():
        with get_session_with_tenant(tenant_id=tenant_id) as db_session:
            ids = interrupt_runs_for_host(db_session, hostname)
        if ids:
            logger.warning(
                f"Pulse: marked {len(ids)} in-flight run(s) interrupted on shutdown: {ids}"
            )
