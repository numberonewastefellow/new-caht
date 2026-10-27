from typing import Any

import pytest

from om.configs.constants import KV_SETTINGS_KEY
from om.configs.constants import LEGACY_KV_SETTINGS_KEY
from om.key_value_store.interface import KvKeyNotFoundError
from om.server.settings import store


class _FakeKv:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = dict(data)

    def load(self, key: str, refresh_cache: bool = False) -> Any:
        if key not in self.data:
            raise KvKeyNotFoundError()
        return self.data[key]

    def store(self, key: str, val: Any, encrypt: bool = False) -> None:
        self.data[key] = val


@pytest.fixture
def kv(monkeypatch: pytest.MonkeyPatch) -> _FakeKv:
    fake = _FakeKv({})
    monkeypatch.setattr(store, "get_kv_store", lambda: fake)
    return fake


def test_keys_are_om_named_and_legacy_alias_is_the_old_name() -> None:
    assert KV_SETTINGS_KEY == "om_settings"
    assert LEGACY_KV_SETTINGS_KEY == "onyx_settings"


def test_new_key_wins_and_legacy_row_is_ignored(kv: _FakeKv) -> None:
    kv.data = {KV_SETTINGS_KEY: {"a": 1}, LEGACY_KV_SETTINGS_KEY: {"a": 2}}
    assert store._load_stored_settings() == {"a": 1}


def test_legacy_row_is_copied_to_the_new_key_and_left_in_place(kv: _FakeKv) -> None:
    kv.data = {LEGACY_KV_SETTINGS_KEY: {"auto_scroll": True}}
    assert store._load_stored_settings() == {"auto_scroll": True}
    assert kv.data[KV_SETTINGS_KEY] == {"auto_scroll": True}  # migrated
    assert kv.data[LEGACY_KV_SETTINGS_KEY] == {"auto_scroll": True}  # rollback-safe
    kv.data[LEGACY_KV_SETTINGS_KEY] = {"auto_scroll": False}  # later legacy changes are not re-imported
    assert store._load_stored_settings() == {"auto_scroll": True}


def test_neither_key_raises_not_found(kv: _FakeKv) -> None:
    with pytest.raises(KvKeyNotFoundError):
        store._load_stored_settings()
