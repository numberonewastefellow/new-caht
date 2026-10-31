"""Whether a webhook may act right now. Checked when a call arrives and again when its run
starts, because a run can wait in the queue after the owner has paused or revoked it."""

from om.configs.constants import KV_SETTINGS_KEY
from om.db.models import PulseWebhook
from om.key_value_store.factory import get_kv_store
from om.key_value_store.interface import KvKeyNotFoundError
from om.server.settings.models import Settings


def webhooks_allowed() -> bool:
    """The admin switch. Reads the store directly rather than through load_settings, which
    answers with defaults when the store fails: that would turn webhooks back on. A failure
    here raises, so the caller refuses instead."""
    try:
        stored = get_kv_store().load(KV_SETTINGS_KEY)
    except KvKeyNotFoundError:
        return Settings().webhooks_enabled
    return Settings.model_validate(stored).webhooks_enabled if stored else True


def closed_reason(webhook: PulseWebhook) -> str | None:
    """Why a queued run must not start, or None. The message is shown in run history."""
    if webhook.revoked_at is not None:
        return "The webhook was revoked before this run started"
    if not webhook.enabled:
        return "The webhook was paused before this run started"
    if not webhooks_allowed():
        return "An admin turned webhooks off before this run started"
    return None
