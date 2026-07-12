from om.background.celery.apps import app_base
from om.background.celery.apps.background import celery_app


celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "om.background.celery.tasks.doc_permission_syncing",
            "om.background.celery.tasks.external_group_syncing",
            "om.background.celery.tasks.cleanup",
            "om.background.celery.tasks.tenant_provisioning",
            "om.background.celery.tasks.query_history",
        ]
    )
)
