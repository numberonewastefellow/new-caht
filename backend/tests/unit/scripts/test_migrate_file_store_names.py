import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "migrate_file_store_names.py"
_spec = importlib.util.spec_from_file_location("migrate_file_store_names", SCRIPT)
assert _spec and _spec.loader
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

ARGS = ("onyx-file-store-bucket", "om-file-store-bucket", "onyx-files", "om-files")


def test_legacy_location_maps_to_om_names() -> None:
    assert mod._map_location("onyx-file-store-bucket", "onyx-files/public/abc", *ARGS) == (
        "om-file-store-bucket",
        "om-files/public/abc",
    )


def test_tenant_segment_is_preserved() -> None:
    assert mod._map_location("onyx-file-store-bucket", "onyx-files/tenant_x/f.pdf", *ARGS) == (
        "om-file-store-bucket",
        "om-files/tenant_x/f.pdf",
    )


def test_already_migrated_or_foreign_locations_are_left_alone() -> None:
    assert mod._map_location("om-file-store-bucket", "om-files/public/abc", *ARGS) is None
    assert mod._map_location("some-other-bucket", "custom/key", *ARGS) is None


def test_prefix_match_is_exact_not_a_substring() -> None:
    # "onyx-files-archive/..." must not be treated as the legacy prefix "onyx-files/..."
    assert mod._map_location("some-other-bucket", "onyx-files-archive/x", *ARGS) is None
