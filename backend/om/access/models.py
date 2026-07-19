"""Typed representations of "who may access a document".

* :class:`ExternalAccess` — access granted by an *external* source system
  (emails + external group ids + a public flag), produced by permission-sync.
* :class:`DocumentAccess` — the full picture for one Om document: internal user
  emails + internal **teams**, plus the external access, plus public. Its
  :meth:`DocumentAccess.to_acl` renders the flat, prefixed principal set that is
  written to the index ``access_control_list`` field.

Team rename (Contract 2): ``user_groups`` -> ``teams`` and
``external_user_group_ids`` -> ``external_team_ids`` throughout.
"""

from __future__ import annotations

from dataclasses import dataclass

from om.access.utils import prefix_external_team
from om.access.utils import prefix_team
from om.access.utils import prefix_user_email
from om.configs.constants import PUBLIC_DOC_PAT


def _truncate_set(values: set[str], max_len: int = 100) -> str:
    rendered = str(values)
    if len(rendered) > max_len:
        return f"{rendered[:max_len]}... ({len(values)} items)"
    return rendered


@dataclass(frozen=True)
class ExternalAccess:
    """Access a document has in its source system (pre-sync into Om ACLs)."""

    # Advisory cap; callers may check ``num_entries`` before persisting.
    MAX_NUM_ENTRIES = 5000

    external_user_emails: set[str]
    external_team_ids: set[str]
    is_public: bool

    def __str__(self) -> str:
        return (
            "ExternalAccess("
            f"external_user_emails={_truncate_set(self.external_user_emails)}, "
            f"external_team_ids={_truncate_set(self.external_team_ids)}, "
            f"is_public={self.is_public})"
        )

    @property
    def num_entries(self) -> int:
        return len(self.external_user_emails) + len(self.external_team_ids)

    @classmethod
    def public(cls) -> "ExternalAccess":
        return cls(external_user_emails=set(), external_team_ids=set(), is_public=True)

    @classmethod
    def empty(cls) -> "ExternalAccess":
        """No principals, not public — i.e. private/inaccessible. A safe
        fail-closed fallback when a document's permissions can't be resolved."""
        return cls(external_user_emails=set(), external_team_ids=set(), is_public=False)


@dataclass(frozen=True)
class DocExternalAccess:
    """External access paired with the document id it applies to (index sync)."""

    external_access: ExternalAccess
    doc_id: str

    def to_dict(self) -> dict:
        return {
            "external_access": {
                "external_user_emails": list(self.external_access.external_user_emails),
                "external_team_ids": list(self.external_access.external_team_ids),
                "is_public": self.external_access.is_public,
            },
            "doc_id": self.doc_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DocExternalAccess":
        payload = data["external_access"]
        return cls(
            external_access=ExternalAccess(
                external_user_emails=set(payload.get("external_user_emails", [])),
                external_team_ids=set(payload.get("external_team_ids", [])),
                is_public=payload["is_public"],
            ),
            doc_id=data["doc_id"],
        )


@dataclass(frozen=True)
class NodeExternalAccess:
    """External access for a hierarchy node (e.g. a folder / space / drive)."""

    external_access: ExternalAccess
    raw_node_id: str
    source: str

    def to_dict(self) -> dict:
        return {
            "external_access": {
                "external_user_emails": list(self.external_access.external_user_emails),
                "external_team_ids": list(self.external_access.external_team_ids),
                "is_public": self.external_access.is_public,
            },
            "raw_node_id": self.raw_node_id,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NodeExternalAccess":
        payload = data["external_access"]
        return cls(
            external_access=ExternalAccess(
                external_user_emails=set(payload.get("external_user_emails", [])),
                external_team_ids=set(payload.get("external_team_ids", [])),
                is_public=payload["is_public"],
            ),
            raw_node_id=data["raw_node_id"],
            source=data["source"],
        )


# Elements whose permissions can be synced to the index.
ElementExternalAccess = DocExternalAccess | NodeExternalAccess


@dataclass(frozen=True, init=False)
class DocumentAccess(ExternalAccess):
    """Full access description for an Om document.

    Constructed only via :meth:`build`; incoming principals are stored *unprefixed*
    and prefixed lazily in :meth:`to_acl` so the encoding lives in exactly one place.
    """

    # ``None`` in ``user_emails`` historically denoted "admin"; it is filtered out.
    user_emails: set[str | None]
    # Internal team names granting access to this document.
    teams: set[str]

    external_user_emails: set[str]
    external_team_ids: set[str]
    is_public: bool

    def __init__(self) -> None:
        raise TypeError("Use DocumentAccess.build(...) instead of constructing directly.")

    @classmethod
    def build(
        cls,
        user_emails: list[str | None],
        teams: list[str],
        external_user_emails: list[str],
        external_team_ids: list[str],
        is_public: bool,
    ) -> "DocumentAccess":
        obj = object.__new__(cls)
        object.__setattr__(obj, "user_emails", {e for e in user_emails if e})
        object.__setattr__(obj, "teams", set(teams))
        object.__setattr__(obj, "external_user_emails", set(external_user_emails))
        object.__setattr__(obj, "external_team_ids", set(external_team_ids))
        object.__setattr__(obj, "is_public", is_public)
        return obj

    def to_acl(self) -> set[str]:
        """Render the prefixed principal set stored in the index ACL field.

        The query-time filter (``get_acl_for_user``) MUST format its principals
        the same way, or matching silently fails.
        """
        acl: set[str] = set()
        for email in self.user_emails:
            if email:
                acl.add(prefix_user_email(email))
        for external_email in self.external_user_emails:
            acl.add(prefix_user_email(external_email))
        for team_name in self.teams:
            acl.add(prefix_team(team_name))
        for external_team_id in self.external_team_ids:
            acl.add(prefix_external_team(external_team_id))
        if self.is_public:
            acl.add(PUBLIC_DOC_PAT)
        return acl


default_public_access = DocumentAccess.build(
    user_emails=[],
    teams=[],
    external_user_emails=[],
    external_team_ids=[],
    is_public=True,
)
