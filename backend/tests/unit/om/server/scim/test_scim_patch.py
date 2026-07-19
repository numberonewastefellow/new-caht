"""Clean-room tests for the RFC 7644 §3.5.2 PATCH applier, incl. Okta/Entra shapes."""

import pytest

from om.server.scim.errors import ScimError
from om.server.scim.patch_ops import apply_patch
from om.server.scim.resources import ScimPatchOperation as Op


def test_pathless_replace_active_bool() -> None:
    src = {"active": True}
    out = apply_patch(src, [Op(op="replace", value={"active": False})])
    assert out["active"] is False
    assert src["active"] is True  # original untouched (atomic)


def test_op_is_case_insensitive() -> None:
    out = apply_patch({"active": True}, [Op(op="Replace", value={"active": False})])
    assert out["active"] is False


def test_pathless_dotted_key_sets_nested() -> None:
    out = apply_patch({}, [Op(op="replace", value={"name.givenName": "Barbara"})])
    assert out["name"]["givenName"] == "Barbara"


def test_path_active_string_value_preserved_for_downstream_coercion() -> None:
    out = apply_patch({"active": True}, [Op(op="replace", path="active", value="False")])
    assert out["active"] == "False"  # ScimUserResource coerces on re-parse


def test_add_member_appends() -> None:
    grp = {"members": [{"value": "u1"}]}
    out = apply_patch(grp, [Op(op="add", path="members", value=[{"value": "u2"}])])
    assert {m["value"] for m in out["members"]} == {"u1", "u2"}


def test_remove_member_value_path_shape() -> None:
    grp = {"members": [{"value": "u1"}, {"value": "u2"}]}
    out = apply_patch(grp, [Op(op="remove", path='members[value eq "u1"]')])
    assert {m["value"] for m in out["members"]} == {"u2"}


def test_remove_member_entra_legacy_value_array_shape() -> None:
    grp = {"members": [{"value": "u1"}, {"value": "u2"}]}
    out = apply_patch(grp, [Op(op="remove", path="members", value=[{"value": "u2"}])])
    assert {m["value"] for m in out["members"]} == {"u1"}


def test_replace_members_full_sync() -> None:
    grp = {"members": [{"value": "u1"}, {"value": "u2"}]}
    out = apply_patch(grp, [Op(op="replace", path="members", value=[{"value": "u9"}])])
    assert {m["value"] for m in out["members"]} == {"u9"}


def test_remove_whole_attribute() -> None:
    out = apply_patch({"members": [{"value": "u1"}]}, [Op(op="remove", path="members")])
    assert out.get("members", []) == []


def test_remove_without_path_raises() -> None:
    with pytest.raises(ScimError):
        apply_patch({"active": True}, [Op(op="remove", value={"active": False})])


def test_replace_scalar_display_name() -> None:
    out = apply_patch({"displayName": "Eng"}, [Op(op="replace", path="displayName", value="Engineering")])
    assert out["displayName"] == "Engineering"
