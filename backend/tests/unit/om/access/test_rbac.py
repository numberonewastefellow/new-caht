"""Unit tests for the clean-room RBAC layer.

Two review gates from WS-B Phase 1:
  * the least-privilege matrix holds (no lateral/vertical privilege leaks), and
  * the PermissionService (PDP) enforces team scoping + separation of duties.

Pure/fast: no DB. The service is exercised against an in-memory fake repository.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from om.access.rbac import Permission
from om.access.rbac import PermissionService
from om.access.rbac import ResourceType
from om.access.rbac import TeamRole
from om.access.rbac.permissions import ALL_PERMISSIONS
from om.access.rbac.permissions import global_permissions_for
from om.access.rbac.permissions import team_permissions_for
from om.auth.schemas import UserRole


# Permissions that must NEVER be held by a non-admin role (instance administration).
INSTANCE_ONLY = {
    Permission.INSTANCE_ADMIN,
    Permission.USER_MANAGE,
    Permission.LLM_PROVIDER_MANAGE,
    Permission.TEAM_CREATE,
    Permission.TEAM_DELETE,
}


def _user(role: UserRole):
    return SimpleNamespace(id=uuid4(), role=role, is_anonymous=False, email="u@x.io")


# --------------------------------------------------------------------------- #
# Matrix (pure data) — least privilege
# --------------------------------------------------------------------------- #


def test_admin_holds_every_permission():
    assert global_permissions_for(UserRole.ADMIN) == ALL_PERMISSIONS


@pytest.mark.parametrize(
    "role",
    [UserRole.GLOBAL_CURATOR, UserRole.CURATOR, UserRole.BASIC, UserRole.LIMITED,
     UserRole.SLACK_USER, UserRole.EXT_PERM_USER],
)
def test_no_non_admin_role_holds_instance_only_permissions(role):
    assert not (global_permissions_for(role) & INSTANCE_ONLY), (
        f"{role} must not hold instance-administration permissions"
    )


def test_role_hierarchy_global_curator_superset_of_curator():
    # Hierarchical RBAC: a global curator can do everything a curator can, +more.
    assert global_permissions_for(UserRole.CURATOR) <= global_permissions_for(
        UserRole.GLOBAL_CURATOR
    )


def test_separation_of_duties_only_global_curator_mints_curators():
    # A plain curator must NOT be able to create curators (lateral escalation).
    assert Permission.TEAM_MANAGE_CURATORS not in global_permissions_for(UserRole.CURATOR)
    assert Permission.TEAM_MANAGE_CURATORS in global_permissions_for(UserRole.GLOBAL_CURATOR)


def test_curators_can_curate_resources_but_not_manage_llm_providers():
    for role in (UserRole.CURATOR, UserRole.GLOBAL_CURATOR):
        perms = global_permissions_for(role)
        assert Permission.DOCUMENT_SET_CURATE in perms
        assert Permission.AGENT_CURATE in perms
        assert Permission.LLM_PROVIDER_MANAGE not in perms


def test_basic_can_only_view_and_lower_roles_have_nothing():
    assert global_permissions_for(UserRole.BASIC) == {Permission.TEAM_VIEW}
    for role in (UserRole.LIMITED, UserRole.SLACK_USER, UserRole.EXT_PERM_USER):
        assert global_permissions_for(role) == frozenset()


def test_team_role_matrix():
    assert Permission.DOCUMENT_SET_CURATE in team_permissions_for(TeamRole.CURATOR)
    assert team_permissions_for(TeamRole.MEMBER) == {Permission.TEAM_VIEW}


# --------------------------------------------------------------------------- #
# PermissionService (PDP) — scoping + enforcement
# --------------------------------------------------------------------------- #


class FakeRepo:
    """In-memory stand-in for TeamRepository (only the methods the PDP uses)."""

    def __init__(self, *, members: dict, curators: dict) -> None:
        # user_id -> set[team_id]
        self._members = members
        self._curators = curators

    def is_member(self, db, user_id, team_id) -> bool:
        return team_id in self._members.get(user_id, set())

    def is_curator(self, db, user_id, team_id) -> bool:
        return team_id in self._curators.get(user_id, set())

    def member_team_ids(self, db, user_id) -> set:
        return set(self._members.get(user_id, set()))

    def curated_team_ids(self, db, user_id) -> set:
        return set(self._curators.get(user_id, set()))


def test_auth_disabled_user_is_none_allows_everything():
    svc = PermissionService(FakeRepo(members={}, curators={}))
    assert svc.decide_create_team(None).allowed
    assert svc.decide_delete_team(None).allowed
    assert svc.decide_edit_team(None, 1, db=None).allowed
    assert svc.decide_manage_curators(None, 1, db=None).allowed


def test_admin_allowed_on_any_team_and_instance_ops():
    admin = _user(UserRole.ADMIN)
    svc = PermissionService(FakeRepo(members={}, curators={}))
    assert svc.decide_create_team(admin).allowed
    assert svc.decide_delete_team(admin).allowed
    assert svc.decide_edit_team(admin, 999, db=None).allowed
    assert svc.decide_manage_curators(admin, 999, db=None).allowed


def test_global_curator_scoped_to_member_teams():
    gc = _user(UserRole.GLOBAL_CURATOR)
    svc = PermissionService(FakeRepo(members={gc.id: {1}}, curators={}))
    # in scope (member of team 1)
    assert svc.decide_edit_team(gc, 1, db=None).allowed
    assert svc.decide_manage_members(gc, 1, db=None).allowed
    assert svc.decide_manage_curators(gc, 1, db=None).allowed  # global_curator holds it
    # out of scope (not a member of team 2)
    assert not svc.decide_edit_team(gc, 2, db=None).allowed
    # never instance ops
    assert not svc.decide_create_team(gc).allowed
    assert not svc.decide_delete_team(gc).allowed


def test_curator_scoped_to_curated_teams_and_cannot_manage_curators():
    cur = _user(UserRole.CURATOR)
    # curator of team 5, only a member (not curator) of team 7
    svc = PermissionService(FakeRepo(members={cur.id: {5, 7}}, curators={cur.id: {5}}))
    assert svc.decide_edit_team(cur, 5, db=None).allowed
    assert svc.decide_manage_members(cur, 5, db=None).allowed
    # curator lacks TEAM_MANAGE_CURATORS entirely (SoD) — denied even in scope
    assert not svc.decide_manage_curators(cur, 5, db=None).allowed
    # member-but-not-curator of team 7 -> not in curator scope
    assert not svc.decide_edit_team(cur, 7, db=None).allowed
    # team they have no relationship with
    assert not svc.decide_edit_team(cur, 99, db=None).allowed


def test_basic_can_view_but_not_administer():
    basic = _user(UserRole.BASIC)
    svc = PermissionService(FakeRepo(members={basic.id: {1}}, curators={}))
    assert svc.can_view_teams(basic)
    assert not svc.decide_edit_team(basic, 1, db=None).allowed
    assert not svc.decide_create_team(basic).allowed


def test_limited_cannot_even_view():
    limited = _user(UserRole.LIMITED)
    svc = PermissionService(FakeRepo(members={}, curators={}))
    assert not svc.can_view_teams(limited)


def test_resource_curation_requires_administering_an_owning_team():
    cur = _user(UserRole.CURATOR)
    svc = PermissionService(FakeRepo(members={cur.id: {5}}, curators={cur.id: {5}}))
    # resource owned by team 5 (which the curator curates) -> allow
    assert svc.decide_curate_resource(cur, ResourceType.DOCUMENT_SET, {5}, db=None).allowed
    # resource owned only by team 6 -> deny
    assert not svc.decide_curate_resource(cur, ResourceType.DOCUMENT_SET, {6}, db=None).allowed
    # resource with no team (instance-scoped) -> deny for curator
    assert not svc.decide_curate_resource(cur, ResourceType.DOCUMENT_SET, set(), db=None).allowed
    # admin may curate regardless of ownership
    admin = _user(UserRole.ADMIN)
    assert svc.decide_curate_resource(admin, ResourceType.DOCUMENT_SET, set(), db=None).allowed


def test_administerable_team_ids_scoping():
    svc = PermissionService(
        FakeRepo(members={}, curators={})
    )
    assert svc.administerable_team_ids(None, db=None) is None  # auth disabled -> all
    admin = _user(UserRole.ADMIN)
    assert svc.administerable_team_ids(admin, db=None) is None  # admin -> all

    gc = _user(UserRole.GLOBAL_CURATOR)
    svc2 = PermissionService(FakeRepo(members={gc.id: {1, 2}}, curators={}))
    assert svc2.administerable_team_ids(gc, db=None) == {1, 2}

    cur = _user(UserRole.CURATOR)
    svc3 = PermissionService(FakeRepo(members={cur.id: {1, 2}}, curators={cur.id: {2}}))
    assert svc3.administerable_team_ids(cur, db=None) == {2}

    basic = _user(UserRole.BASIC)
    assert svc.administerable_team_ids(basic, db=None) == set()


def test_require_raises_on_deny():
    from om.access.rbac import PermissionDenied

    basic = _user(UserRole.BASIC)
    svc = PermissionService(FakeRepo(members={}, curators={}))
    decision = svc.decide_create_team(basic)
    with pytest.raises(PermissionDenied):
        svc.require(decision)
