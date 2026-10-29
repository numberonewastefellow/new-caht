from om.configs.constants import KV_SETTINGS_KEY


def test_settings_are_stored_under_the_om_key() -> None:
    assert KV_SETTINGS_KEY == "om_settings"
