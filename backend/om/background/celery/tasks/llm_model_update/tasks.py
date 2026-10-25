from celery import shared_task
from celery import Task

from om.background.celery.apps.app_base import task_logger
from om.configs.constants import OmCeleryTask
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.llm.well_known_providers.auto_update_service import (
    sync_llm_models_from_github,
)


@shared_task(
    name=OmCeleryTask.CHECK_FOR_AUTO_LLM_UPDATE,
    ignore_result=True,
    soft_time_limit=300,  # 5 minute timeout
    trail=False,
    bind=True,
)
def check_for_auto_llm_updates(
    self: Task, *, tenant_id: str  # noqa: ARG001
) -> bool | None:
    """Periodic task to sync the recommended-models config (bundled, or
    AUTO_LLM_CONFIG_URL if set) to providers that have is_auto_mode=True.
    """
    try:
        # Sync to database
        with get_session_with_current_tenant() as db_session:
            results = sync_llm_models_from_github(db_session)

            if results:
                task_logger.info(f"Auto mode sync results: {results}")
            else:
                task_logger.debug("No model updates applied")

    except Exception:
        task_logger.exception("Error in auto LLM update task")
        raise

    return True
