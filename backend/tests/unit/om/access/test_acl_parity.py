"""ACL parity / correctness test for the team-based document ACL (Contract 2).

Access is decided by set-intersection: a user may see a document iff the user's
principal set (read-side, ``get_acl_for_user``) shares at least one entry with
the document's principal set (write-side, ``DocumentAccess.to_acl``). Both sides
route through the SAME encoders in ``om.access.utils`` — this test pins that the
encoding is team-based (``team:`` / ``external_team:``, never the old ``group:``)
and that the allow/deny outcome is correct across a fixed corpus + user set.
"""

from __future__ import annotations

from types import SimpleNamespace

import om.access.access as access_mod
from om.access.access import get_acl_for_user
from om.access.models import DocumentAccess
from om.access.utils import prefix_external_team
from om.access.utils import prefix_team
from om.access.utils import prefix_user_email
from om.configs.constants import PUBLIC_DOC_PAT


# --- fixed corpus (write-side) -------------------------------------------------

DOC_PUBLIC = DocumentAccess.build([], [], [], [], is_public=True)
DOC_OWNER = DocumentAccess.build(["alice@x.io"], [], [], [], is_public=False)
DOC_TEAM_ENG = DocumentAccess.build([], ["eng"], [], [], is_public=False)
DOC_EXT_TEAM = DocumentAccess.build([], [], [], ["confluence_g1"], is_public=False)
DOC_MIXED = DocumentAccess.build(
    ["bob@x.io"], ["sales"], [], ["gdrive_g2"], is_public=False
)


def _visible(user_acl: set[str], doc: DocumentAccess) -> bool:
    return bool(user_acl & doc.to_acl())


def test_prefixes_are_team_based_not_group():
    all_acls = " ".join(
        e for doc in (DOC_TEAM_ENG, DOC_EXT_TEAM, DOC_MIXED, DOC_OWNER, DOC_PUBLIC)
        for e in doc.to_acl()
    )
    assert "team:eng" in DOC_TEAM_ENG.to_acl()
    assert "external_team:confluence_g1" in DOC_EXT_TEAM.to_acl()
    assert "user_email:alice@x.io" in DOC_OWNER.to_acl()
    assert PUBLIC_DOC_PAT in DOC_PUBLIC.to_acl()
    # The legacy encodings must be gone entirely.
    assert "group:" not in all_acls
    assert "external_group:" not in all_acls


def test_allow_deny_matrix():
    anon = {PUBLIC_DOC_PAT}
    alice = {prefix_user_email("alice@x.io"), PUBLIC_DOC_PAT, prefix_team("eng")}
    bob = {
        prefix_user_email("bob@x.io"),
        PUBLIC_DOC_PAT,
        prefix_external_team("confluence_g1"),
    }

    # (user_acl, doc) -> expected visibility
    expectations = [
        (anon, DOC_PUBLIC, True),
        (anon, DOC_OWNER, False),
        (anon, DOC_TEAM_ENG, False),
        (anon, DOC_EXT_TEAM, False),
        (alice, DOC_PUBLIC, True),
        (alice, DOC_OWNER, True),          # owner email match
        (alice, DOC_TEAM_ENG, True),       # team member
        (alice, DOC_EXT_TEAM, False),      # not in that external team
        (alice, DOC_MIXED, False),         # not bob, not sales, not gdrive_g2
        (bob, DOC_OWNER, False),           # different owner (alice)
        (bob, DOC_EXT_TEAM, True),         # external team match
        (bob, DOC_MIXED, True),            # bob@x.io is the owner of MIXED
        (bob, DOC_TEAM_ENG, False),        # bob not in team eng
    ]
    for user_acl, doc, expected in expectations:
        assert _visible(user_acl, doc) is expected, (user_acl, doc.to_acl(), expected)


def test_read_side_get_acl_for_user_emits_team_prefixes(monkeypatch):
    """The read-side must produce the same team-based encoding as the write-side."""
    fake_teams = [SimpleNamespace(name="eng"), SimpleNamespace(name="sales")]
    fake_ext = [SimpleNamespace(external_team_id="confluence_g1")]

    # get_acl_for_user lazily imports fetch_teams_for_user from om.db.team,
    # and uses fetch_external_teams_for_user bound into the access module.
    import om.db.team as team_mod

    monkeypatch.setattr(team_mod, "fetch_teams_for_user", lambda db, uid: fake_teams)
    monkeypatch.setattr(
        access_mod, "fetch_external_teams_for_user", lambda db, uid: fake_ext
    )

    user = SimpleNamespace(id="u1", email="alice@x.io", is_anonymous=False)
    acl = get_acl_for_user(user, db_session=object())

    assert acl == {
        prefix_user_email("alice@x.io"),
        PUBLIC_DOC_PAT,
        prefix_team("eng"),
        prefix_team("sales"),
        prefix_external_team("confluence_g1"),
    }
    # And a document granted to team "eng" is therefore visible to alice.
    assert _visible(acl, DOC_TEAM_ENG) is True


def test_anonymous_user_only_sees_public():
    user = SimpleNamespace(id="anon", email="", is_anonymous=True)
    acl = get_acl_for_user(user, db_session=object())
    assert acl == {PUBLIC_DOC_PAT}
    assert _visible(acl, DOC_PUBLIC) is True
    assert _visible(acl, DOC_TEAM_ENG) is False
