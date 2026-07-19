"""Clean-room tests for SCIM service mapping logic (no DB required).

Full DB persistence (User/Team rows, user__team membership) is integrator-verified
(needs WS-B's Team model + Postgres). These tests exercise the pure mapping logic.
"""

from types import SimpleNamespace

import pytest

from om.server.scim import constants
from om.server.scim import scim_logging
from om.server.scim.errors import ScimError
from om.server.scim.resources import ScimUserResource
from om.server.scim.service import _paginate, ScimGroupService, ScimUserService


class _FakeUserMappingRepo:
    def __init__(self) -> None:
        self.by_user: dict = {}
        self.by_ext: dict = {}

    def get_user_mapping_by_user_id(self, uid):
        return self.by_user.get(uid)

    def get_user_mapping_by_external_id(self, ext):
        return self.by_ext.get(ext)

    def create_user_mapping(self, *, external_id, user_id):
        m = SimpleNamespace(external_id=external_id, user_id=user_id)
        self.by_user[user_id] = m
        self.by_ext[external_id] = m
        return m

    def update_user_mapping_external_id(self, mapping, external_id):
        self.by_ext.pop(mapping.external_id, None)
        mapping.external_id = external_id
        self.by_ext[external_id] = mapping
        return mapping


class _FakeDb:
    """Minimal stand-in that records commits (no real transaction)."""

    def __init__(self) -> None:
        self.committed = 0

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:  # pragma: no cover - not hit on the happy path
        pass


def _user_service() -> ScimUserService:
    svc = ScimUserService.__new__(ScimUserService)
    svc.repo = _FakeUserMappingRepo()
    return svc


def test_sync_external_id_creates_then_updates() -> None:
    svc = _user_service()
    svc._sync_external_id("userA", "ext1")
    assert svc.repo.by_ext["ext1"].user_id == "userA"
    svc._sync_external_id("userA", "ext2")
    assert "ext1" not in svc.repo.by_ext
    assert svc.repo.by_ext["ext2"].user_id == "userA"


def test_sync_external_id_none_is_noop() -> None:
    svc = _user_service()
    svc._sync_external_id("userA", None)
    assert svc.repo.by_ext == {}


def test_sync_external_id_cross_user_conflict_raises_409() -> None:
    svc = _user_service()
    svc._sync_external_id("userA", "shared")
    with pytest.raises(ScimError) as exc_info:
        svc._sync_external_id("userB", "shared")
    assert exc_info.value.status_code == 409
    assert exc_info.value.scim_type == "uniqueness"


def test_include_members_honors_excluded_attributes() -> None:
    assert ScimGroupService._include_members(None) is True
    assert ScimGroupService._include_members("") is True
    assert ScimGroupService._include_members("members") is False
    assert ScimGroupService._include_members("Members") is False  # case-insensitive
    assert ScimGroupService._include_members("displayName,members") is False
    assert ScimGroupService._include_members("displayName") is True


def test_group_serialization_shape() -> None:
    svc = ScimGroupService.__new__(ScimGroupService)
    svc.base_url = "https://h/scim/v2"
    team = SimpleNamespace(id=7, name="Engineering")
    d = svc._to_scim(team, "grp-ext", include_members=False)
    assert d["schemas"] == [constants.SCHEMA_GROUP]
    assert d["id"] == "7"
    assert d["displayName"] == "Engineering"
    assert d["externalId"] == "grp-ext"
    assert d["meta"]["location"].endswith("/Groups/7")


# --- C2: re-provisioning a deprovisioned user reactivates it in place ------
def _reactivating_service() -> ScimUserService:
    svc = ScimUserService.__new__(ScimUserService)
    svc.repo = _FakeUserMappingRepo()
    svc.db = _FakeDb()
    svc.base_url = "https://h/scim/v2"
    svc.actor_user_id = "actor-1"
    return svc


def test_reactivate_activates_relinks_and_commits() -> None:
    svc = _reactivating_service()
    user = SimpleNamespace(
        id="u1", email="alice@x.com", is_active=False, personal_name=None
    )
    resource = ScimUserResource(
        userName="alice@x.com",
        externalId="ext-1",
        displayName="Alice",
        active=True,
    )
    out = svc._reactivate(user, resource, "Alice", scim_logging._OperationHandle())

    assert user.is_active is True  # deprovisioned → reactivated in place
    assert user.personal_name == "Alice"
    assert svc.db.committed == 1
    assert svc.repo.by_ext["ext-1"].user_id == "u1"  # mapping relinked
    assert out["externalId"] == "ext-1"
    assert out["active"] is True
    assert out["id"] == "u1"


# --- pagination math (RFC 7644 §3.4.2) -------------------------------------
def test_paginate_slices_and_reports_full_total() -> None:
    items = [{"id": str(i)} for i in range(10)]
    out = _paginate(items, start_index=1, count=3)
    assert out["totalResults"] == 10
    assert out["startIndex"] == 1
    assert out["itemsPerPage"] == 3
    assert [r["id"] for r in out["Resources"]] == ["0", "1", "2"]


def test_paginate_offset_is_one_based() -> None:
    items = [{"id": str(i)} for i in range(10)]
    out = _paginate(items, start_index=4, count=3)
    assert [r["id"] for r in out["Resources"]] == ["3", "4", "5"]
    assert out["startIndex"] == 4


def test_paginate_count_zero_returns_total_only() -> None:
    items = [{"id": str(i)} for i in range(5)]
    out = _paginate(items, start_index=1, count=0)
    assert out["totalResults"] == 5
    assert out["itemsPerPage"] == 0
    assert out["Resources"] == []


def test_paginate_start_beyond_end_is_empty() -> None:
    out = _paginate([{"id": "0"}], start_index=99, count=10)
    assert out["totalResults"] == 1
    assert out["Resources"] == []
