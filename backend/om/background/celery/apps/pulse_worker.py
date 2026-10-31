"""Celery app for `pulse_worker`: executes scheduled workflow runs (queue `pulse`).

Runs as its own service (docker compose `pulse_worker`, Helm `pulse-worker`) so long
LLM runs never share threads with indexing. Scale horizontally by adding replicas.
"""

from typing import Any

from celery import Celery
from celery import signals
from celery import Task
from celery.apps.worker import Worker
from celery.signals import celeryd_init
from celery.signals import worker_init
from celery.signals import worker_ready
from celery.signals import worker_shutdown
from celery.signals import worker_shutting_down

import om.background.celery.apps.app_base as app_base
from om.configs.constants import POSTGRES_CELERY_WORKER_PULSE_APP_NAME
from om.configs.pulse_configs import PULSE_WORKER_QUEUE
from om.db.engine.sql_engine import SqlEngine
from om.pulse.worker_presence import WorkerPresence
from om.utils.logger import setup_logger

logger = setup_logger()

celery_app = Celery(__name__)
celery_app.config_from_object("om.background.celery.configs.pulse_worker")
celery_app.Task = app_base.TenantAwareTask  # type: ignore [misc]

_presence: WorkerPresence | None = None


@signals.task_prerun.connect
def on_task_prerun(
    sender: Any | None = None,
    task_id: str | None = None,
    task: Task | None = None,
    args: tuple | None = None,
    kwargs: dict | None = None,
    **kwds: Any,
) -> None:
    app_base.on_task_prerun(sender, task_id, task, args, kwargs, **kwds)


@signals.task_postrun.connect
def on_task_postrun(
    sender: Any | None = None,
    task_id: str | None = None,
    task: Task | None = None,
    args: tuple | None = None,
    kwargs: dict | None = None,
    retval: Any | None = None,
    state: str | None = None,
    **kwds: Any,
) -> None:
    app_base.on_task_postrun(sender, task_id, task, args, kwargs, retval, state, **kwds)


@celeryd_init.connect
def on_celeryd_init(sender: str, conf: Any = None, **kwargs: Any) -> None:
    app_base.on_celeryd_init(sender, conf, **kwargs)


@worker_init.connect
def on_worker_init(sender: Worker, **kwargs: Any) -> None:
    # Each run thread holds one session; the heartbeat thread opens short-lived ones.
    EXTRA_CONCURRENCY = 8

    logger.info("worker_init signal received.")
    logger.info(f"Concurrency: {sender.concurrency}")  # type: ignore

    SqlEngine.set_app_name(POSTGRES_CELERY_WORKER_PULSE_APP_NAME)
    SqlEngine.init_engine(pool_size=sender.concurrency, max_overflow=EXTRA_CONCURRENCY)  # type: ignore

    app_base.wait_for_redis(sender, **kwargs)
    app_base.wait_for_db(sender, **kwargs)
    # NOTE: no wait for the primary worker — pulse_worker is an independent service.


@worker_ready.connect
def on_worker_ready(sender: Any, **kwargs: Any) -> None:
    global _presence
    app_base.on_worker_ready(sender, **kwargs)
    _presence = WorkerPresence(PULSE_WORKER_QUEUE, str(sender.hostname))
    _presence.start()


@worker_shutting_down.connect
def on_worker_shutting_down(**kwargs: Any) -> None:
    # A stopping worker takes no new runs, but can spend a long time finishing the ones it
    # has. It shouldn't count as alive meanwhile: nothing is serving its queue.
    if _presence is not None:
        _presence.withdraw()


@worker_shutdown.connect
def on_worker_shutdown(sender: Any, **kwargs: Any) -> None:
    if _presence is not None:
        _presence.stop()
    # Fires after the pool stopped. A warm shutdown has already let in-flight runs
    # finish (compose stop_grace_period >= workflow timeout); anything of this node
    # still `running` now was cut off (cold shutdown) — mark it `interrupted` right away
    # instead of waiting for the scheduler's heartbeat reaper. Runs are never replayed.
    try:
        from om.pulse.tasks_support import interrupt_local_runs

        interrupt_local_runs(str(getattr(sender, "hostname", "") or ""))
    except Exception:
        logger.exception("Pulse: failed to interrupt local runs on shutdown")
    app_base.on_worker_shutdown(sender, **kwargs)


@signals.setup_logging.connect
def on_setup_logging(
    loglevel: Any, logfile: Any, format: Any, colorize: Any, **kwargs: Any
) -> None:
    app_base.on_setup_logging(loglevel, logfile, format, colorize, **kwargs)


base_bootsteps = app_base.get_bootsteps()
for bootstep in base_bootsteps:
    celery_app.steps["worker"].add(bootstep)

celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "om.background.celery.tasks.pulse",
        ]
    )
)
