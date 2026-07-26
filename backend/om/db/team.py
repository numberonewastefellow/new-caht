"""Team persistence + lifecycle service (clean-room replacement for the old
``user_group`` DB module).

Layering: thin query/CRUD functions over the ORM, with the RBAC policy checks
delegated to :class:`om.access.rbac.service.PermissionService` and mutations
wrapped in :func:`om.access.rbac.audit.audit_event` (structured OpenSearch logs).
All functions take a caller-supplied tenant-bound ``Session`` (multi-tenant-safe).

Sync lifecycle contract (unchanged, relied on by the celery propagation tasks):
* ``Team.is_up_to_date`` — False whenever membership/grants changed and the
  document index has not yet been re-stamped. The sync task flips it back True.
* ``Team.is_up_for_deletion`` — the sync task tears down ACLs then deletes.
* ``team__connector_credential_pair.is_current`` — False marks a grant edge that
  was removed but is kept until the sync task has cleared it from the index.
"""

from __future__ import annotations

from collections.abc import Sequence
from operator import and_
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import Session

from typing import Any

from om.access.rbac.audit import audit_event
from om.access.rbac.repository import TeamRepository
from om.auth.schemas import UserRole
from om.db.enums import AccessType
from om.db.enums import ConnectorCredentialPairStatus
from om.db.enums import MembershipSource
from om.db.enums import TeamRole
from om.db.models import ConnectorCredentialPair
from om.db.models import Document
from om.db.models import DocumentByConnectorCredentialPair
from om.db.models import Team
from om.db.models import Team__ConnectorCredentialPair
from om.db.models import User
from om.db.models import User__Team

_repo = TeamRepository()

# Sentinel distinguishing "argument not supplied" from an explicit ``None`` in
# partial-update helpers (so a caller can, e.g., clear ``description`` to NULL).
_UNSET: Any = object()


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #


def fetch_team(db_session: Session, team_id: int) -> Team | None:
    return _repo.get(db_session, team_id)


def fetch_teams(db_session: Session, only_up_to_date: bool = True) -> Sequence[Team]:
    stmt = select(Team)
    if only_up_to_date:
        stmt = stmt.where(Team.is_up_to_date.is_(True))
    return db_session.scalars(stmt).all()


def fetch_teams_for_user(
    db_session: Session, user_id: UUID, only_curator_teams: bool = False
) -> Sequence[Team]:
    """Teams the user belongs to (optionally only those they curate)."""
    stmt = (
        select(Team)
        .join(User__Team, User__Team.team_id == Team.id)
        .where(User__Team.user_id == user_id)
    )
    if only_curator_teams:
        stmt = stmt.where(User__Team.is_curator.is_(True))
    return db_session.scalars(stmt).all()


def fetch_teams_for_documents(
    db_session: Session,
    document_ids: list[str],
) -> Sequence[tuple[str, list[str]]]:
    """Map each document id -> the names of teams that grant access to it.

    A team grants access to a document when the team owns a *non-SYNC*,
    *non-deleting*, currently-active connector-credential-pair that produced the
    document. SYNC cc-pairs are excluded here because their access is enforced by
    externally-synced ACLs, not team membership.
    """
    stmt = (
        select(Document.id, func.array_agg(Team.name))
        .join(
            Team__ConnectorCredentialPair,
            Team.id == Team__ConnectorCredentialPair.team_id,
        )
        .join(
            ConnectorCredentialPair,
            and_(
                ConnectorCredentialPair.id == Team__ConnectorCredentialPair.cc_pair_id,
                ConnectorCredentialPair.access_type != AccessType.SYNC,
            ),
        )
        .join(
            DocumentByConnectorCredentialPair,
            and_(
                DocumentByConnectorCredentialPair.connector_id
                == ConnectorCredentialPair.connector_id,
                DocumentByConnectorCredentialPair.credential_id
                == ConnectorCredentialPair.credential_id,
            ),
        )
        .join(Document, Document.id == DocumentByConnectorCredentialPair.id)
        .where(Document.id.in_(document_ids))
        .where(Team__ConnectorCredentialPair.is_current.is_(True))
        .where(ConnectorCredentialPair.status != ConnectorCredentialPairStatus.DELETING)
        .group_by(Document.id)
    )
    return db_session.execute(stmt).all()  # type: ignore[return-value]


def construct_document_id_select_by_team(team_id: int) -> Select:
    """Statement yielding every document id a team can access (use ``.yield_per``
    in the background sync generators)."""
    return (
        select(Document.id)
        .join(
            DocumentByConnectorCredentialPair,
            Document.id == DocumentByConnectorCredentialPair.id,
        )
        .join(
            ConnectorCredentialPair,
            and_(
                DocumentByConnectorCredentialPair.connector_id
                == ConnectorCredentialPair.connector_id,
                DocumentByConnectorCredentialPair.credential_id
                == ConnectorCredentialPair.credential_id,
            ),
        )
        .join(
            Team__ConnectorCredentialPair,
            Team__ConnectorCredentialPair.cc_pair_id == ConnectorCredentialPair.id,
        )
        .join(Team, Team__ConnectorCredentialPair.team_id == Team.id)
        .where(Team.id == team_id)
        .order_by(Document.id)
        .distinct()
    )


# --------------------------------------------------------------------------- #
# RBAC validation for creating/editing team-scoped objects
# --------------------------------------------------------------------------- #


def validate_object_creation_for_user(
    db_session: Session,
    user: User,
    target_team_ids: list[int] | None = None,
    object_is_public: bool | None = None,
    object_is_perm_sync: bool | None = None,
    object_is_owned_by_user: bool = False,
    object_is_new: bool = False,
) -> None:
    """Guard used when a non-admin assigns an object (document-set, connector,
    agent, ...) to teams. Raises HTTP 400 if the assignment exceeds the user's
    curator scope. Mirrors the least-privilege policy in
    :mod:`om.access.rbac.permissions`.
    """
    # Perm-synced objects with no explicit team are allowed for anyone.
    if object_is_perm_sync and not target_team_ids:
        return

    if user.role == UserRole.ADMIN:
        return

    # Curators / global-curators may create public objects they own / that are new.
    if (
        object_is_public
        and user.role in (UserRole.CURATOR, UserRole.GLOBAL_CURATOR)
        and (object_is_new or object_is_owned_by_user)
    ):
        return

    if object_is_public:
        raise HTTPException(
            status_code=400,
            detail="User does not have permission to create public objects",
        )

    if not target_team_ids:
        raise HTTPException(status_code=400, detail="Curators must specify 1+ teams")

    # A global-curator may act on any team they are a member of; a curator only on
    # teams they curate.
    if user.role == UserRole.GLOBAL_CURATOR:
        scope = _repo.member_team_ids(db_session, user.id)
    else:
        scope = _repo.curated_team_ids(db_session, user.id)

    if not set(target_team_ids).issubset(scope):
        raise HTTPException(
            status_code=400, detail="Curators cannot control teams they don't curate"
        )


# --------------------------------------------------------------------------- #
# Mutations (lifecycle) — each wrapped in a structured audit event
# --------------------------------------------------------------------------- #


def _check_modifiable(team: Team) -> None:
    if not team.is_up_to_date:
        raise ValueError(
            "Team is currently syncing; wait for the sync to finish before editing."
        )


def _add_memberships(
    db_session: Session,
    team_id: int,
    user_ids: list[UUID],
    role: str = TeamRole.MEMBER.value,
    source: MembershipSource | None = None,
) -> None:
    """Add memberships for ``user_ids`` (skipping ones that already exist).

    Each new row records ``joined_at`` (now), the given ``role`` (with
    ``is_curator`` derived from it so RBAC stays consistent), and a ``source``.
    When ``source`` is omitted it is derived per-user: SSO if the user has an
    external identity (OAuth/OIDC) linked, otherwise MANUAL.
    """
    if not user_ids:
        return

    # Load the User rows once: validates existence AND lets us derive `source`
    # from linked OAuth/OIDC accounts without an N+1. A missing user would
    # otherwise raise an opaque FK IntegrityError (HTTP 500); a ValueError here
    # is turned into a clean 400 by the /teams endpoints.
    # .unique() is required because User.oauth_accounts is a joined eager-load
    # collection, so selecting the User entity yields duplicate parent rows.
    users_by_id = {
        u.id: u
        for u in db_session.scalars(
            select(User).where(User.id.in_(user_ids))
        ).unique()
    }
    missing = [str(uid) for uid in user_ids if uid not in users_by_id]
    if missing:
        raise ValueError(f"Unknown user id(s): {', '.join(missing)}")

    existing = {
        uid
        for uid in db_session.scalars(
            select(User__Team.user_id).where(User__Team.team_id == team_id)
        )
    }

    is_curator = TeamRole(role).is_curator()
    new_rows: list[User__Team] = []
    for uid in user_ids:
        if uid in existing:
            continue
        row_source = source or (
            MembershipSource.SSO
            if users_by_id[uid].oauth_accounts
            else MembershipSource.MANUAL
        )
        new_rows.append(
            User__Team(
                team_id=team_id,
                user_id=uid,
                role=role,
                is_curator=is_curator,
                source=row_source.value,
                joined_at=func.now(),
            )
        )
    db_session.add_all(new_rows)


def _add_cc_pair_grants(
    db_session: Session, team_id: int, cc_pair_ids: list[int]
) -> None:
    db_session.add_all(
        Team__ConnectorCredentialPair(team_id=team_id, cc_pair_id=cc_pair_id)
        for cc_pair_id in cc_pair_ids
    )


def _mark_cc_pair_grants_outdated(db_session: Session, team_id: int) -> None:
    for grant in db_session.scalars(
        select(Team__ConnectorCredentialPair).where(
            Team__ConnectorCredentialPair.team_id == team_id
        )
    ):
        grant.is_current = False


def insert_team(
    db_session: Session,
    name: str,
    user_ids: list[UUID],
    cc_pair_ids: list[int],
    actor_user_id: str | None = None,
    description: str | None = None,
    is_public: bool = False,
    tags: list[str] | None = None,
) -> Team:
    with audit_event(
        event="team.created", entity="team", action="create", actor_user_id=actor_user_id
    ) as ev:
        creator_id = UUID(actor_user_id) if actor_user_id else None
        team = Team(
            name=name,
            description=description,
            is_public=is_public,
            tags=tags,
            owner_id=creator_id,
            is_up_to_date=False,
            is_up_for_deletion=False,
            time_last_modified_by_user=func.now(),
        )
        db_session.add(team)
        db_session.flush()  # assign id
        # The creator is always an OWNER of the team they create.
        if creator_id is not None:
            _add_memberships(
                db_session, team.id, [creator_id], role=TeamRole.OWNER.value
            )
        # Everyone else joins at the team's default role.
        other_ids = [uid for uid in user_ids if uid != creator_id]
        _add_memberships(
            db_session, team.id, other_ids, role=team.default_member_role
        )
        _add_cc_pair_grants(db_session, team.id, cc_pair_ids)
        db_session.commit()
        ev["entity_id"] = team.id
        return team


def add_users_to_team(
    db_session: Session,
    team_id: int,
    user_ids: list[UUID],
    actor_user_id: str | None = None,
    role: str | None = None,
) -> Team:
    team = fetch_team(db_session, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    with audit_event(
        event="team.member_added",
        entity="team_membership",
        action="update",
        entity_id=team_id,
        actor_user_id=actor_user_id,
    ):
        _check_modifiable(team)
        _add_memberships(
            db_session,
            team_id,
            user_ids,
            role=role or team.default_member_role,
        )
        team.is_up_to_date = False
        team.time_last_modified_by_user = func.now()
        db_session.commit()
    return team


def update_team(
    db_session: Session,
    team_id: int,
    user_ids: list[UUID] | Any = _UNSET,
    cc_pair_ids: list[int] | Any = _UNSET,
    actor_user_id: str | None = None,
    *,
    description: str | None | Any = _UNSET,
    is_public: bool | Any = _UNSET,
    tags: list[str] | None | Any = _UNSET,
    default_member_role: str | Any = _UNSET,
    allow_guest_access: bool | Any = _UNSET,
) -> Team:
    """Partial-update a team.

    Only the arguments actually supplied are applied (``_UNSET`` = leave as-is,
    so an explicit ``None`` can still clear ``description``/``tags``). When
    ``user_ids``/``cc_pair_ids`` are given they REPLACE the current membership /
    connector grants: removed grant edges are marked non-current (not deleted) so
    the sync task can clear them from the index first, and the team is flagged
    not-up-to-date to trigger that sync. Settings-only changes that affect the
    document ACL (``is_public``) also trigger a resync; purely cosmetic settings
    (description/tags/default role/guest access) do not.
    """
    team = fetch_team(db_session, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    with audit_event(
        event="team.updated",
        entity="team",
        action="update",
        entity_id=team_id,
        actor_user_id=actor_user_id,
    ):
        _check_modifiable(team)

        index_affecting = False

        # scalar settings first so a membership change below picks up any new
        # default_member_role in the same request
        if description is not _UNSET:
            team.description = description
        if tags is not _UNSET:
            team.tags = tags
        if default_member_role is not _UNSET:
            team.default_member_role = TeamRole(default_member_role).value
        if allow_guest_access is not _UNSET:
            team.allow_guest_access = allow_guest_access
        if is_public is not _UNSET:
            if team.is_public != is_public:
                index_affecting = True
            team.is_public = is_public

        # membership: drop those no longer present, add the new ones (never drop
        # the owner's membership)
        if user_ids is not _UNSET:
            target_users = set(user_ids)
            if team.owner_id is not None:
                target_users.add(team.owner_id)
            drop_conditions = [User__Team.team_id == team_id]
            if target_users:
                # keep the target members; an empty target removes everyone
                drop_conditions.append(User__Team.user_id.notin_(target_users))
            db_session.execute(delete(User__Team).where(*drop_conditions))
            _add_memberships(
                db_session,
                team_id,
                list(target_users),
                role=team.default_member_role,
            )
            index_affecting = True

        # grants: mark all current outdated, then (re)add the target set
        if cc_pair_ids is not _UNSET:
            _mark_cc_pair_grants_outdated(db_session, team_id)
            _add_cc_pair_grants(db_session, team_id, cc_pair_ids)
            index_affecting = True

        if index_affecting:
            team.is_up_to_date = False
        team.time_last_modified_by_user = func.now()
        db_session.commit()
    return team


def set_member_role(
    db_session: Session,
    team_id: int,
    user_id: UUID,
    role: str | TeamRole,
    actor_user_id: str | None = None,
) -> None:
    """Set a member's team role, keeping ``is_curator`` in sync (OWNER/ADMIN =>
    curator, MEMBER => not) so RBAC decisions stay consistent. Raises
    ``ValueError`` if the user is not a member of the team.

    This is the general form of :func:`update_user_curator_relationship`.
    """
    role_enum = TeamRole(role)
    with audit_event(
        event="team.role_changed",
        entity="team_membership",
        action="update",
        entity_id=team_id,
        actor_user_id=actor_user_id,
    ):
        result = db_session.execute(
            update(User__Team)
            .where(User__Team.team_id == team_id, User__Team.user_id == user_id)
            .values(role=role_enum.value, is_curator=role_enum.is_curator())
        )
        if result.rowcount == 0:
            raise ValueError("User is not a member of this team")
        _recompute_curator_role(db_session, user_id)
        db_session.commit()


def update_user_curator_relationship(
    db_session: Session,
    team_id: int,
    user_id: UUID,
    is_curator: bool,
    actor_user_id: str | None = None,
) -> None:
    """Grant/revoke team-scoped curator status, keeping ``role`` in sync: granting
    curator promotes a MEMBER to ADMIN; revoking demotes an ADMIN to MEMBER. An
    OWNER is never altered (owners are always curators)."""
    with audit_event(
        event="team.grant_changed",
        entity="team_membership",
        action="update",
        entity_id=team_id,
        actor_user_id=actor_user_id,
    ):
        membership = db_session.scalar(
            select(User__Team).where(
                User__Team.team_id == team_id, User__Team.user_id == user_id
            )
        )
        if membership is None:
            raise ValueError("User is not a member of this team")
        membership.is_curator = is_curator
        if is_curator and membership.role == TeamRole.MEMBER.value:
            membership.role = TeamRole.ADMIN.value
        elif not is_curator and membership.role == TeamRole.ADMIN.value:
            membership.role = TeamRole.MEMBER.value
        _recompute_curator_role(db_session, user_id)
        db_session.commit()


def _recompute_curator_role(db_session: Session, user_id: UUID) -> None:
    """Keep the coarse ``UserRole`` consistent with team-scoped curator flags: a
    user who curates any team is (at least) a CURATOR; one who curates none is
    demoted from CURATOR back to BASIC (never touches ADMIN/GLOBAL_CURATOR)."""
    # .unique() required: User.oauth_accounts is a joined eager-load collection.
    user = (
        db_session.scalars(select(User).where(User.id == user_id))
        .unique()
        .one_or_none()
    )
    if user is None:
        return
    curates_any = (
        db_session.scalar(
            select(User__Team.team_id).where(
                User__Team.user_id == user_id, User__Team.is_curator.is_(True)
            )
        )
        is not None
    )
    if curates_any:
        if user.role == UserRole.BASIC:
            user.role = UserRole.CURATOR
    elif user.role == UserRole.CURATOR:
        user.role = UserRole.BASIC
    db_session.add(user)


def mark_team_as_synced(db_session: Session, team: Team) -> None:
    """Called by the sync task once the index reflects the team's current state.
    Clears the outdated grant edges and flips the team up-to-date."""
    with audit_event(
        event="team.perm_sync", entity="team", action="update", entity_id=team.id
    ):
        db_session.execute(
            delete(Team__ConnectorCredentialPair).where(
                Team__ConnectorCredentialPair.team_id == team.id,
                Team__ConnectorCredentialPair.is_current.is_(False),
            )
        )
        db_session.execute(
            update(Team).where(Team.id == team.id).values(is_up_to_date=True)
        )
        db_session.commit()


def remove_curator_status__no_commit(db_session: Session, user: User) -> None:
    """Strip the team-scoped curator flag from all of a user's memberships and
    reconcile their coarse role. Used when a user is demoted/deactivated. The
    per-team ``role`` is dropped to MEMBER to preserve the role<->is_curator
    invariant (a non-curator is never OWNER/ADMIN)."""
    db_session.execute(
        update(User__Team)
        .where(User__Team.user_id == user.id)
        .values(is_curator=False, role=TeamRole.MEMBER.value)
    )
    _recompute_curator_role(db_session, user.id)


def delete_team_cc_pair_relationship__no_commit(
    db_session: Session, cc_pair_id: int
) -> None:
    """Remove every team's grant edge to a connector-credential-pair (used when a
    connector is being deleted). Caller commits."""
    db_session.execute(
        delete(Team__ConnectorCredentialPair).where(
            Team__ConnectorCredentialPair.cc_pair_id == cc_pair_id
        )
    )


def prepare_team_for_deletion(
    db_session: Session, team_id: int, actor_user_id: str | None = None
) -> None:
    """Flag a team for teardown; the sync task strips its ACLs then deletes it."""
    team = fetch_team(db_session, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    with audit_event(
        event="team.deleted",
        entity="team",
        action="delete",
        entity_id=team_id,
        actor_user_id=actor_user_id,
    ):
        _mark_cc_pair_grants_outdated(db_session, team_id)
        team.is_up_to_date = False
        team.is_up_for_deletion = True
        db_session.commit()


def delete_team(db_session: Session, team: Team) -> None:
    """Hard-delete a team and its membership/grant edges (post-teardown)."""
    with audit_event(
        event="team.deleted", entity="team", action="delete", entity_id=team.id
    ):
        db_session.execute(delete(User__Team).where(User__Team.team_id == team.id))
        db_session.execute(
            delete(Team__ConnectorCredentialPair).where(
                Team__ConnectorCredentialPair.team_id == team.id
            )
        )
        db_session.execute(delete(Team).where(Team.id == team.id))
        db_session.commit()
