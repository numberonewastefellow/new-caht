import om.background.celery.configs.base as shared_config
from om.configs.pulse_configs import PULSE_WORKER_CONCURRENCY

broker_url = shared_config.broker_url
broker_connection_retry_on_startup = shared_config.broker_connection_retry_on_startup
broker_pool_limit = shared_config.broker_pool_limit
broker_transport_options = shared_config.broker_transport_options

redis_socket_keepalive = shared_config.redis_socket_keepalive
redis_retry_on_timeout = shared_config.redis_retry_on_timeout
redis_backend_health_check_interval = shared_config.redis_backend_health_check_interval

result_backend = shared_config.result_backend
result_expires = shared_config.result_expires  # 86400 seconds is the default

task_default_priority = shared_config.task_default_priority
# Pulse runs are LLM pipelines with side effects: ack on receipt and never let the
# broker replay a half-finished run. Crashed runs are reaped (`interrupted`) via the
# DB heartbeat instead, and the CAS in the worker de-duplicates any redelivery.
task_acks_late = False

worker_concurrency = PULSE_WORKER_CONCURRENCY
worker_pool = "threads"
# One run at a time per thread slot: long tasks must not be prefetched behind others
worker_prefetch_multiplier = 1
