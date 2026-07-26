"""Unit tests for knowledge-file (individual-user KB) access resolution.

``get_access_for_knowledge_files`` is the write-side ACL source for user knowledge
files: a file is PRIVATE to its owner (``user_email:<owner>``) and PUBLIC only when
it has no owner. No teams are ever involved for knowledge files. These tests pin
that mapping without touching a real DB by faking the SQLAlchemy query chain.
"""

from __future__ import annotations

from types import SimpleNamespace

from om.access.access import get_access_for_knowledge_files
from om.access.utils import prefix_user_email
from om.configs.constants import PUBLIC_DOC_PAT


class _FakeQuery:
    """Minimal stand-in for a SQLAlchemy Query: every builder call returns self,
    and ``.all()`` yields the preloaded rows (filter args are ignored)."""

    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def options(self, *args: object, **kwargs: object) -> "_FakeQuery":
        return self

    def filter(self, *args: object, **kwargs: object) -> "_FakeQuery":
        return self

    def all(self) -> list[object]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def query(self, *args: object, **kwargs: object) -> _FakeQuery:
        return _FakeQuery(self._rows)


def _kf(file_id: str, owner_email: str | None) -> SimpleNamespace:
    """A fake KnowledgeFile with an optional owner user (joinedload target)."""
    user = SimpleNamespace(email=owner_email) if owner_email is not None else None
    return SimpleNamespace(id=file_id, user=user)


def test_owned_knowledge_file_is_private_to_owner():
    session = _FakeSession([_kf("kf-1", "alice@x.io")])

    access_map = get_access_for_knowledge_files(["kf-1"], session)  # type: ignore[arg-type]

    acl = access_map["kf-1"].to_acl()
    assert prefix_user_email("alice@x.io") in acl
    assert access_map["kf-1"].is_public is False
    # Nobody else, no team, not public.
    assert PUBLIC_DOC_PAT not in acl
    assert not any(entry.startswith("team:") for entry in acl)


def test_ownerless_knowledge_file_is_public():
    session = _FakeSession([_kf("kf-2", None)])

    access_map = get_access_for_knowledge_files(["kf-2"], session)  # type: ignore[arg-type]

    assert access_map["kf-2"].is_public is True
    assert PUBLIC_DOC_PAT in access_map["kf-2"].to_acl()


def test_mixed_batch_maps_each_file_independently():
    session = _FakeSession(
        [_kf("kf-1", "alice@x.io"), _kf("kf-2", None), _kf("kf-3", "bob@x.io")]
    )

    access_map = get_access_for_knowledge_files(["kf-1", "kf-2", "kf-3"], session)  # type: ignore[arg-type]

    assert set(access_map) == {"kf-1", "kf-2", "kf-3"}
    assert prefix_user_email("alice@x.io") in access_map["kf-1"].to_acl()
    assert access_map["kf-2"].is_public is True
    assert prefix_user_email("bob@x.io") in access_map["kf-3"].to_acl()
    # Owners never leak across files.
    assert prefix_user_email("bob@x.io") not in access_map["kf-1"].to_acl()
    assert prefix_user_email("alice@x.io") not in access_map["kf-3"].to_acl()


def test_visibility_intersection_owner_vs_other_user():
    """A knowledge file's owner sees it; a different user does not (public files
    are seen by everyone via PUBLIC)."""
    session = _FakeSession([_kf("kf-1", "alice@x.io"), _kf("kf-2", None)])
    access_map = get_access_for_knowledge_files(["kf-1", "kf-2"], session)  # type: ignore[arg-type]

    alice_acl = {prefix_user_email("alice@x.io"), PUBLIC_DOC_PAT}
    bob_acl = {prefix_user_email("bob@x.io"), PUBLIC_DOC_PAT}

    # Private file kf-1: only alice.
    assert bool(alice_acl & access_map["kf-1"].to_acl()) is True
    assert bool(bob_acl & access_map["kf-1"].to_acl()) is False
    # Public file kf-2: everyone.
    assert bool(alice_acl & access_map["kf-2"].to_acl()) is True
    assert bool(bob_acl & access_map["kf-2"].to_acl()) is True


def test_empty_input_returns_empty_map():
    session = _FakeSession([])
    assert get_access_for_knowledge_files([], session) == {}  # type: ignore[arg-type]
