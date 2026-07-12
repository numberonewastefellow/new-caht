from celery import Celery

from om.background.celery.apps.background import celery_app as _impl_celery_app

app: Celery = _impl_celery_app
