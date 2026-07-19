"""Celery cleanup tasks.

The former ``export_query_history_cleanup_task`` was removed along with the
EE-origin query-history CSV export pipeline (replaced by the synchronous export
in ``om.server.query_history``). This module is intentionally left without task
definitions; it is retained so the ``om.background.celery.tasks.cleanup``
autodiscover entry continues to resolve.
"""

from om.utils.logger import setup_logger

logger = setup_logger()
