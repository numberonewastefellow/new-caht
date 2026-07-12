from om.background.celery.apps import app_base
from om.background.celery.apps.background import celery_app


celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "ee.om.background.celery.tasks.doc_permission_syncing",
            "ee.om.background.celery.tasks.external_group_syncing",
            "ee.om.background.celery.tasks.cleanup",
            "ee.om.background.celery.tasks.tenant_provisioning",
            "ee.om.background.celery.tasks.query_history",
        ]
    )
)
