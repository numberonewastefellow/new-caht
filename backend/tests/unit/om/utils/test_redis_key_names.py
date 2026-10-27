from pathlib import Path

from om.configs.constants import OM_CELERY_BEAT_HEARTBEAT_KEY
from om.configs.constants import OM_REDIS_FUNCTION_LOCK_PREFIX
from om.key_value_store.store import REDIS_KEY_PREFIX

SUPERVISORD_CONF = Path(__file__).resolve().parents[4] / "supervisord.conf"


def test_supervisord_watchdog_checks_the_key_the_beat_task_writes() -> None:
    # supervisord.conf cannot import constants, so this pins the two together.
    assert f'--key "{OM_CELERY_BEAT_HEARTBEAT_KEY}"' in SUPERVISORD_CONF.read_text(encoding="utf-8")


def test_redis_namespaces_are_om_named() -> None:
    assert OM_CELERY_BEAT_HEARTBEAT_KEY == "om:celery:beat:heartbeat"
    assert OM_REDIS_FUNCTION_LOCK_PREFIX == "om_function_lock:"
    assert REDIS_KEY_PREFIX == "om_kv_store:"
