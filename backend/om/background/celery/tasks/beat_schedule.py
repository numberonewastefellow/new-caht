import copy
from datetime import timedelta
from typing import Any

from celery.schedules import crontab

from om.configs.app_configs import AUTO_LLM_CONFIG_URL
from om.configs.app_configs import AUTO_LLM_UPDATE_INTERVAL_SECONDS
from om.configs.app_configs import CHECK_TTL_MANAGEMENT_TASK_FREQUENCY_IN_HOURS
from om.configs.app_configs import DISABLE_OPENSEARCH_MIGRATION_TASK
from om.configs.app_configs import DISABLE_VECTOR_DB
from om.configs.app_configs import ENABLE_OPENSEARCH_INDEXING_FOR_ONYX
from om.configs.app_configs import SCHEDULED_EVAL_DATASET_NAMES
from om.configs.constants import OM_CLOUD_CELERY_TASK_PREFIX
from om.configs.constants import OmCeleryPriority
from om.configs.constants import OmCeleryQueues
from om.configs.constants import OmCeleryTask
from shared_configs.configs import MULTI_TENANT

# choosing 15 minutes because it roughly gives us enough time to process many tasks
# we might be able to reduce this greatly if we can run a unified
# loop across all tenants rather than tasks per tenant

# we set expires because it isn't necessary to queue up these tasks
# it's only important that they run relatively regularly
BEAT_EXPIRES_DEFAULT = 15 * 60  # 15 minutes (in seconds)

# hack to slow down task dispatch in the cloud until
# we have a better implementation (backpressure, etc)
# Note that DynamicTenantScheduler can adjust the runtime value for this via Redis
CLOUD_BEAT_MULTIPLIER_DEFAULT = 8.0
CLOUD_DOC_PERMISSION_SYNC_MULTIPLIER_DEFAULT = 1.0

# tasks that run in either self-hosted on cloud
beat_task_templates: list[dict] = [
    {
        "name": "check-for-user-file-processing",
        "task": OmCeleryTask.CHECK_FOR_USER_FILE_PROCESSING,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": OmCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-user-file-project-sync",
        "task": OmCeleryTask.CHECK_FOR_USER_FILE_PROJECT_SYNC,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": OmCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-user-file-delete",
        "task": OmCeleryTask.CHECK_FOR_USER_FILE_DELETE,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": OmCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-indexing",
        "task": OmCeleryTask.CHECK_FOR_INDEXING,
        "schedule": timedelta(seconds=15),
        "options": {
            "priority": OmCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-checkpoint-cleanup",
        "task": OmCeleryTask.CHECK_FOR_CHECKPOINT_CLEANUP,
        "schedule": timedelta(hours=1),
        "options": {
            "priority": OmCeleryPriority.LOW,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-index-attempt-cleanup",
        "task": OmCeleryTask.CHECK_FOR_INDEX_ATTEMPT_CLEANUP,
        "schedule": timedelta(minutes=30),
        "options": {
            "priority": OmCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-connector-deletion",
        "task": OmCeleryTask.CHECK_FOR_CONNECTOR_DELETION,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": OmCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-document-index-sync",
        "task": OmCeleryTask.CHECK_FOR_DOC_INDEX_SYNC_TASK,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": OmCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-pruning",
        "task": OmCeleryTask.CHECK_FOR_PRUNING,
        "schedule": timedelta(seconds=20),
        "options": {
            "priority": OmCeleryPriority.MEDIUM,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "check-for-hierarchy-fetching",
        "task": OmCeleryTask.CHECK_FOR_HIERARCHY_FETCHING,
        "schedule": timedelta(hours=1),  # Check hourly, but only fetch once per day
        "options": {
            "priority": OmCeleryPriority.LOW,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": "monitor-background-processes",
        "task": OmCeleryTask.MONITOR_BACKGROUND_PROCESSES,
        "schedule": timedelta(minutes=5),
        "options": {
            "priority": OmCeleryPriority.LOW,
            "expires": BEAT_EXPIRES_DEFAULT,
            "queue": OmCeleryQueues.MONITORING,
        },
    },
    # Sandbox cleanup tasks
    {
        "name": "cleanup-idle-sandboxes",
        "task": OmCeleryTask.CLEANUP_IDLE_SANDBOXES,
        "schedule": timedelta(minutes=1),
        "options": {
            "priority": OmCeleryPriority.LOW,
            "expires": BEAT_EXPIRES_DEFAULT,
            "queue": OmCeleryQueues.SANDBOX,
        },
    },
    {
        "name": "cleanup-old-snapshots",
        "task": OmCeleryTask.CLEANUP_OLD_SNAPSHOTS,
        "schedule": timedelta(hours=24),
        "options": {
            "priority": OmCeleryPriority.LOW,
            "expires": BEAT_EXPIRES_DEFAULT,
            "queue": OmCeleryQueues.SANDBOX,
        },
    },
]

beat_task_templates.extend(
    [
        {
            "name": "check-for-doc-permissions-sync",
            "task": OmCeleryTask.CHECK_FOR_DOC_PERMISSIONS_SYNC,
            "schedule": timedelta(seconds=30),
            "options": {
                "priority": OmCeleryPriority.MEDIUM,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        },
        {
            "name": "check-for-external-group-sync",
            "task": OmCeleryTask.CHECK_FOR_EXTERNAL_GROUP_SYNC,
            "schedule": timedelta(seconds=20),
            "options": {
                "priority": OmCeleryPriority.MEDIUM,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        },
        # Merged from the former ee/om/.../beat_schedule.py override. Appending to
        # beat_task_templates covers BOTH consumers at once: get_cloud_tasks_to_schedule
        # reads the templates directly, and tasks_to_schedule (self-hosted) extends them
        # below -- which is exactly the split the EE override maintained by hand via
        # ee_beat_task_templates + ee_tasks_to_schedule (identical entries in both).
        {
            "name": "autogenerate-usage-report",
            "task": OmCeleryTask.GENERATE_USAGE_REPORT_TASK,
            "schedule": timedelta(days=30),
            "options": {
                "priority": OmCeleryPriority.MEDIUM,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        },
        {
            "name": "check-ttl-management",
            "task": OmCeleryTask.CHECK_TTL_MANAGEMENT_TASK,
            "schedule": timedelta(hours=CHECK_TTL_MANAGEMENT_TASK_FREQUENCY_IN_HOURS),
            "options": {
                "priority": OmCeleryPriority.MEDIUM,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        },
        {
            "name": "export-query-history-cleanup-task",
            "task": OmCeleryTask.EXPORT_QUERY_HISTORY_CLEANUP_TASK,
            "schedule": timedelta(hours=1),
            "options": {
                "priority": OmCeleryPriority.MEDIUM,
                "expires": BEAT_EXPIRES_DEFAULT,
                "queue": OmCeleryQueues.CSV_GENERATION,
            },
        },
    ]
)

# Add the Auto LLM update task if the config URL is set (has a default)
if AUTO_LLM_CONFIG_URL:
    beat_task_templates.append(
        {
            "name": "check-for-auto-llm-update",
            "task": OmCeleryTask.CHECK_FOR_AUTO_LLM_UPDATE,
            "schedule": timedelta(seconds=AUTO_LLM_UPDATE_INTERVAL_SECONDS),
            "options": {
                "priority": OmCeleryPriority.LOW,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        }
    )

# Add scheduled eval task if datasets are configured
if SCHEDULED_EVAL_DATASET_NAMES:
    beat_task_templates.append(
        {
            "name": "scheduled-eval-pipeline",
            "task": OmCeleryTask.SCHEDULED_EVAL_TASK,
            # run every Sunday at midnight UTC
            "schedule": crontab(
                hour=0,
                minute=0,
                day_of_week=0,
            ),
            "options": {
                "priority": OmCeleryPriority.LOW,
                "expires": BEAT_EXPIRES_DEFAULT,
            },
        }
    )

# Add OpenSearch migration (Vespa->OpenSearch backfill) task if enabled. Skipped
# when DISABLE_OPENSEARCH_MIGRATION_TASK is set (e.g. a fresh OpenSearch-only
# deployment with no Vespa to migrate from).
if ENABLE_OPENSEARCH_INDEXING_FOR_ONYX and not DISABLE_OPENSEARCH_MIGRATION_TASK:
    beat_task_templates.append(
        {
            "name": "migrate-chunks-from-vespa-to-opensearch",
            "task": OmCeleryTask.MIGRATE_CHUNKS_FROM_VESPA_TO_OPENSEARCH_TASK,
            # Try to enqueue an invocation of this task with this frequency.
            "schedule": timedelta(seconds=120),  # 2 minutes
            "options": {
                "priority": OmCeleryPriority.LOW,
                # If the task was not dequeued in this time, revoke it.
                "expires": BEAT_EXPIRES_DEFAULT,
                "queue": OmCeleryQueues.OPENSEARCH_MIGRATION,
            },
        }
    )


# Beat task names that require a vector DB. Filtered out when DISABLE_VECTOR_DB.
_VECTOR_DB_BEAT_TASK_NAMES: set[str] = {
    "check-for-indexing",
    "check-for-connector-deletion",
    "check-for-document-index-sync",
    "check-for-pruning",
    "check-for-hierarchy-fetching",
    "check-for-checkpoint-cleanup",
    "check-for-index-attempt-cleanup",
    "check-for-doc-permissions-sync",
    "check-for-external-group-sync",
    "check-for-documents-for-opensearch-migration",
    "migrate-documents-from-vespa-to-opensearch",
}

if DISABLE_VECTOR_DB:
    beat_task_templates = [
        t for t in beat_task_templates if t["name"] not in _VECTOR_DB_BEAT_TASK_NAMES
    ]


def make_cloud_generator_task(task: dict[str, Any]) -> dict[str, Any]:
    cloud_task: dict[str, Any] = {}

    # constant options for cloud beat task generators
    task_schedule: timedelta = task["schedule"]
    cloud_task["schedule"] = task_schedule
    cloud_task["options"] = {}
    cloud_task["options"]["priority"] = OmCeleryPriority.HIGHEST
    cloud_task["options"]["expires"] = BEAT_EXPIRES_DEFAULT

    # settings dependent on the original task
    cloud_task["name"] = f"{OM_CLOUD_CELERY_TASK_PREFIX}_{task['name']}"
    cloud_task["task"] = OmCeleryTask.CLOUD_BEAT_TASK_GENERATOR
    cloud_task["kwargs"] = {}
    cloud_task["kwargs"]["task_name"] = task["task"]

    optional_fields = ["queue", "priority", "expires"]
    for field in optional_fields:
        if field in task["options"]:
            cloud_task["kwargs"][field] = task["options"][field]

    return cloud_task


# tasks that only run in the cloud and are system wide
# the name attribute must start with ONYX_CLOUD_CELERY_TASK_PREFIX = "cloud" to be seen
# by the DynamicTenantScheduler as system wide task and not a per tenant task
beat_cloud_tasks: list[dict] = [
    # cloud specific tasks
    {
        "name": f"{OM_CLOUD_CELERY_TASK_PREFIX}_monitor-alembic",
        "task": OmCeleryTask.CLOUD_MONITOR_ALEMBIC,
        "schedule": timedelta(hours=1),
        "options": {
            "queue": OmCeleryQueues.MONITORING,
            "priority": OmCeleryPriority.HIGH,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": f"{OM_CLOUD_CELERY_TASK_PREFIX}_monitor-celery-queues",
        "task": OmCeleryTask.CLOUD_MONITOR_CELERY_QUEUES,
        "schedule": timedelta(seconds=30),
        "options": {
            "queue": OmCeleryQueues.MONITORING,
            "priority": OmCeleryPriority.HIGH,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": f"{OM_CLOUD_CELERY_TASK_PREFIX}_check-available-tenants",
        "task": OmCeleryTask.CLOUD_CHECK_AVAILABLE_TENANTS,
        "schedule": timedelta(minutes=10),
        "options": {
            "queue": OmCeleryQueues.MONITORING,
            "priority": OmCeleryPriority.HIGH,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
    {
        "name": f"{OM_CLOUD_CELERY_TASK_PREFIX}_monitor-celery-pidbox",
        "task": OmCeleryTask.CLOUD_MONITOR_CELERY_PIDBOX,
        "schedule": timedelta(hours=4),
        "options": {
            "queue": OmCeleryQueues.MONITORING,
            "priority": OmCeleryPriority.HIGH,
            "expires": BEAT_EXPIRES_DEFAULT,
        },
    },
]

# tasks that only run self hosted
tasks_to_schedule: list[dict] = []
if not MULTI_TENANT:
    tasks_to_schedule.extend(
        [
            {
                "name": "monitor-celery-queues",
                "task": OmCeleryTask.MONITOR_CELERY_QUEUES,
                "schedule": timedelta(seconds=10),
                "options": {
                    "priority": OmCeleryPriority.MEDIUM,
                    "expires": BEAT_EXPIRES_DEFAULT,
                    "queue": OmCeleryQueues.MONITORING,
                },
            },
            {
                "name": "monitor-process-memory",
                "task": OmCeleryTask.MONITOR_PROCESS_MEMORY,
                "schedule": timedelta(minutes=5),
                "options": {
                    "priority": OmCeleryPriority.LOW,
                    "expires": BEAT_EXPIRES_DEFAULT,
                    "queue": OmCeleryQueues.MONITORING,
                },
            },
            {
                "name": "celery-beat-heartbeat",
                "task": OmCeleryTask.CELERY_BEAT_HEARTBEAT,
                "schedule": timedelta(minutes=1),
                "options": {
                    "priority": OmCeleryPriority.HIGHEST,
                    "expires": BEAT_EXPIRES_DEFAULT,
                    "queue": OmCeleryQueues.PRIMARY,
                },
            },
        ]
    )

    tasks_to_schedule.extend(beat_task_templates)


def generate_cloud_tasks(
    beat_tasks: list[dict], beat_templates: list[dict], beat_multiplier: float
) -> list[dict[str, Any]]:
    """
    beat_tasks: system wide tasks that can be sent as is
    beat_templates: task templates that will be transformed into per tenant tasks via
    the cloud_beat_task_generator
    beat_multiplier: a multiplier that can be applied on top of the task schedule
    to speed up or slow down the task generation rate. useful in production.

    Returns a list of cloud tasks, which consists of incoming tasks + tasks generated
    from incoming templates.
    """

    if beat_multiplier <= 0:
        raise ValueError("beat_multiplier must be positive!")

    cloud_tasks: list[dict] = []

    # generate our tenant aware cloud tasks from the templates
    for beat_template in beat_templates:
        cloud_task = make_cloud_generator_task(beat_template)
        cloud_tasks.append(cloud_task)

    # factor in the cloud multiplier for the above
    for cloud_task in cloud_tasks:
        cloud_task["schedule"] = cloud_task["schedule"] * beat_multiplier

    # add the fixed cloud/system beat tasks. No multiplier for these.
    cloud_tasks.extend(copy.deepcopy(beat_tasks))
    return cloud_tasks


def get_cloud_tasks_to_schedule(beat_multiplier: float) -> list[dict[str, Any]]:
    return generate_cloud_tasks(beat_cloud_tasks, beat_task_templates, beat_multiplier)


def get_tasks_to_schedule() -> list[dict[str, Any]]:
    return tasks_to_schedule
