"""Factory stub for running the Pulse celery worker.
There is no EE version of this worker."""

from celery import Celery

from om.background.celery.apps.pulse_worker import celery_app as _impl_celery_app

app: Celery = _impl_celery_app
