"""Factory stub for running celery worker / celery beat."""

from celery import Celery

from om.background.celery.apps.monitoring import celery_app as _impl_celery_app

app: Celery = _impl_celery_app
