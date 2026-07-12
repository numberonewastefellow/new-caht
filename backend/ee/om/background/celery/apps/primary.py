from om.background.celery.apps import app_base
from om.background.celery.apps.primary import celery_app


celery_app.autodiscover_tasks(
    app_base.filter_task_modules(
        [
            "ee.om.background.celery.tasks.doc_permission_syncing",
            "ee.om.background.celery.tasks.external_group_syncing",
            "ee.om.background.celery.tasks.cloud",
            "ee.om.background.celery.tasks.ttl_management",
            "ee.om.background.celery.tasks.usage_reporting",
        ]
    )
)
