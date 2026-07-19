"""Persistence helpers for :class:`HierarchyNode` rows.

A hierarchy node captures the structural skeleton of a connected source --
drives, spaces, folders, channels and the like -- alongside the same permission
triple that documents carry (``is_public`` / ``external_user_emails`` /
``external_team_ids``), which is what makes user-scoped hierarchy browsing
possible.

Every function in this module works against a caller-supplied
:class:`~sqlalchemy.orm.Session`. Nothing here opens its own session or reaches
for ambient tenant state, so the whole module stays safe to call from any
multi-tenant context; transaction ownership is left to the caller via the
``commit`` flags.
"""

from sqlalchemy import any_
from sqlalchemy import cast
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from om.configs.constants import DocumentSource
from om.connectors.models import HierarchyNode as PydanticHierarchyNode
from om.db.enums import HierarchyNodeType
from om.db.models import Document
from om.db.models import HierarchyNode
from om.utils.logger import setup_logger

logger = setup_logger()


# A few connectors expose pages that are simultaneously a browsable hierarchy
# node *and* an indexed document: a Notion or Confluence page can own child
# pages while also carrying its own body text. For every other source a
# structural node -- e.g. a Google Drive folder -- is never a document in its
# own right, so there is nothing to cross-link back to a document row.
SOURCES_WITH_HIERARCHY_NODE_DOCUMENTS: set[DocumentSource] = {
    DocumentSource.NOTION,
    DocumentSource.CONFLUENCE,
}


def _flush_or_commit(db_session: Session, commit: bool) -> None:
    """Finalise pending writes.

    When the caller owns the transaction we commit; otherwise we merely flush so
    the changes become visible to later statements in the same unit of work.
    """
    if commit:
        db_session.commit()
    else:
        db_session.flush()


# ---------------------------------------------------------------------------
# Single-row lookups
# ---------------------------------------------------------------------------
def get_hierarchy_node_by_raw_id(
    db_session: Session,
    raw_node_id: str,
    source: DocumentSource,
) -> HierarchyNode | None:
    """Fetch the node uniquely identified by ``(raw_node_id, source)``."""
    query = select(HierarchyNode).where(
        HierarchyNode.raw_node_id == raw_node_id,
        HierarchyNode.source == source,
    )
    return db_session.execute(query).scalar_one_or_none()


def get_hierarchy_node_by_id(
    db_session: Session,
    node_id: int,
) -> HierarchyNode | None:
    """Fetch a node by its integer primary key, or ``None`` if absent."""
    return db_session.get(HierarchyNode, node_id)


def get_source_hierarchy_node(
    db_session: Session,
    source: DocumentSource,
) -> HierarchyNode | None:
    """Fetch the SOURCE-typed root node for ``source`` if it has been created."""
    query = select(HierarchyNode).where(
        HierarchyNode.source == source,
        HierarchyNode.node_type == HierarchyNodeType.SOURCE,
    )
    return db_session.execute(query).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Source root management
# ---------------------------------------------------------------------------
def ensure_source_node_exists(
    db_session: Session,
    source: DocumentSource,
    commit: bool = True,
) -> HierarchyNode:
    """Return the SOURCE root for ``source``, creating it on first use.

    The SOURCE node is the anchor of a connector type's tree -- every other node
    for that source ultimately descends from it. It stores the source name as
    its ``raw_node_id``, a humanised ``display_name`` (e.g. "Google Drive") and
    no parent.

    The call is idempotent and tolerant of concurrent creation: if two workers
    race, the one whose insert violates the uniqueness constraint rolls back and
    re-reads the row the winner committed. A failure that does *not* turn out to
    be such a race is re-raised untouched.
    """
    existing = get_source_hierarchy_node(db_session, source)
    if existing is not None:
        return existing

    display_name = source.value.replace("_", " ").title()
    root = HierarchyNode(
        raw_node_id=source.value,
        display_name=display_name,
        link=None,
        source=source,
        node_type=HierarchyNodeType.SOURCE,
        parent_id=None,
    )
    db_session.add(root)

    try:
        # Flush eagerly so a duplicate-key clash surfaces here (where we can
        # recover) rather than later at commit time, and so ``root.id`` is
        # populated for the log line below.
        db_session.flush()
    except Exception:
        db_session.rollback()
        winner = get_source_hierarchy_node(db_session, source)
        if winner is not None:
            return winner
        # No row appeared on re-read, so this was not a creation race -- the
        # original error is the real problem.
        raise

    if commit:
        db_session.commit()

    logger.info(
        f"Created SOURCE hierarchy node for {source.value}: "
        f"id={root.id}, display_name={display_name}"
    )
    return root


def resolve_parent_hierarchy_node_id(
    db_session: Session,
    raw_parent_id: str | None,
    source: DocumentSource,
) -> int | None:
    """Map a source-level parent identifier onto a database ``parent_id``.

    A concrete ``raw_parent_id`` resolves to that parent's primary key when the
    parent row exists. A missing parent id -- or one that cannot be found --
    means the node hangs directly off the source root, so the SOURCE node's id
    is returned instead (with a warning in the not-found case). ``None`` comes
    back only in the degenerate situation where no SOURCE node exists yet.
    """
    if raw_parent_id is not None:
        parent = get_hierarchy_node_by_raw_id(db_session, raw_parent_id, source)
        if parent is not None:
            return parent.id
        logger.warning(
            f"Parent hierarchy node not found: raw_id={raw_parent_id}, source={source}. "
            "Falling back to SOURCE node."
        )

    root = get_source_hierarchy_node(db_session, source)
    return root.id if root is not None else None


# ---------------------------------------------------------------------------
# Upserts
# ---------------------------------------------------------------------------
def _extract_node_permissions(
    node: PydanticHierarchyNode,
    is_connector_public: bool,
) -> tuple[bool, list[str] | None, list[str] | None]:
    """Compute the ``(is_public, external_user_emails, external_team_ids)`` triple
    to persist for ``node``.

    A public connector wins outright: everything it yields is world-readable and
    stores no principal lists. Otherwise the values come from the node's own
    ``external_access``, with empty collections normalised to ``None`` so the
    columns stay NULL rather than empty arrays. A node with no access
    information is stored fully private.
    """
    if is_connector_public:
        return True, None, None

    access = node.external_access
    if access is None:
        return False, None, None

    emails = list(access.external_user_emails) if access.external_user_emails else None
    teams = list(access.external_team_ids) if access.external_team_ids else None
    return access.is_public, emails, teams


def upsert_hierarchy_node(
    db_session: Session,
    node: PydanticHierarchyNode,
    source: DocumentSource,
    commit: bool = True,
    is_connector_public: bool = False,
) -> HierarchyNode:
    """Insert or update the DB row backing a connector-yielded hierarchy node.

    Identity is ``(raw_node_id, source)``: a matching row is mutated in place,
    otherwise a fresh row is inserted. Parent linkage and the permission triple
    are recomputed on every call so repeated syncs keep the row in step with the
    source. ``is_connector_public`` forces public visibility on the node
    regardless of its own ``external_access``.
    """
    parent_id = (
        None
        if node.node_type == HierarchyNodeType.SOURCE
        else resolve_parent_hierarchy_node_id(db_session, node.raw_parent_id, source)
    )
    is_public, external_user_emails, external_team_ids = _extract_node_permissions(
        node, is_connector_public
    )

    row = get_hierarchy_node_by_raw_id(db_session, node.raw_node_id, source)
    if row is not None:
        row.display_name = node.display_name
        row.link = node.link
        row.node_type = node.node_type
        row.parent_id = parent_id
        row.is_public = is_public
        row.external_user_emails = external_user_emails
        row.external_team_ids = external_team_ids
    else:
        row = HierarchyNode(
            raw_node_id=node.raw_node_id,
            display_name=node.display_name,
            link=node.link,
            source=source,
            node_type=node.node_type,
            parent_id=parent_id,
            is_public=is_public,
            external_user_emails=external_user_emails,
            external_team_ids=external_team_ids,
        )
        db_session.add(row)

    _flush_or_commit(db_session, commit)
    return row


def upsert_parents(
    db_session: Session,
    node: PydanticHierarchyNode,
    source: DocumentSource,
    node_by_id: dict[str, PydanticHierarchyNode],
    done_ids: set[str],
    is_connector_public: bool = False,
) -> None:
    """Ensure ``node``'s in-batch ancestors are persisted before ``node`` itself.

    Follows the ``raw_parent_id`` chain and upserts each ancestor root-first, so
    that by the time any child is written its parent already exists and
    ``parent_id`` resolves cleanly. ``done_ids`` tracks ancestors already handled
    during the current batch to keep the work linear. The walk stops when the
    node is itself a SOURCE node, when its parent is not part of this batch, or
    when the parent has already been processed.
    """
    parent_raw_id = node.raw_parent_id
    if node.node_type == HierarchyNodeType.SOURCE:
        return
    if parent_raw_id not in node_by_id or parent_raw_id in done_ids:
        return

    parent = node_by_id[parent_raw_id]
    # Recurse before writing this parent so grandparents land ahead of parents.
    upsert_parents(
        db_session,
        parent,
        source,
        node_by_id,
        done_ids,
        is_connector_public=is_connector_public,
    )
    upsert_hierarchy_node(
        db_session,
        parent,
        source,
        commit=False,
        is_connector_public=is_connector_public,
    )
    done_ids.add(parent.raw_node_id)


def upsert_hierarchy_nodes_batch(
    db_session: Session,
    nodes: list[PydanticHierarchyNode],
    source: DocumentSource,
    commit: bool = True,
    is_connector_public: bool = False,
) -> list[HierarchyNode]:
    """Upsert many hierarchy nodes, sorting out parent ordering automatically.

    The only requirement on the input is that every ancestor of every supplied
    node lives either already in the database or somewhere within ``nodes`` --
    the list may otherwise be in any order. Ancestors found inside the batch are
    written on demand (via :func:`upsert_parents`) the first time one of their
    descendants is reached, so each node is persisted exactly once.

    The returned list holds the rows for nodes handled directly by the main loop
    (i.e. those not already written as some earlier node's ancestor), preserving
    input order.
    """
    # Index the batch by raw id for parent lookups. SOURCE nodes are excluded on
    # purpose: they never act as an in-batch resolvable parent.
    node_by_raw_id: dict[str, PydanticHierarchyNode] = {
        node.raw_node_id: node
        for node in nodes
        if node.node_type != HierarchyNodeType.SOURCE
    }
    processed: set[str] = set()
    persisted: list[HierarchyNode] = []

    for node in nodes:
        if node.raw_node_id in processed:
            # Already written while resolving a descendant's parent chain.
            continue
        upsert_parents(
            db_session,
            node,
            source,
            node_by_raw_id,
            processed,
            is_connector_public=is_connector_public,
        )
        row = upsert_hierarchy_node(
            db_session,
            node,
            source,
            commit=False,
            is_connector_public=is_connector_public,
        )
        processed.add(node.raw_node_id)
        persisted.append(row)

    if commit:
        db_session.commit()

    return persisted


# ---------------------------------------------------------------------------
# Linking nodes to their documents
# ---------------------------------------------------------------------------
def link_hierarchy_nodes_to_documents(
    db_session: Session,
    document_ids: list[str],
    source: DocumentSource,
    commit: bool = True,
) -> int:
    """Back-fill ``document_id`` on nodes that are also documents.

    For sources where a page is both a node and a document (Notion, Confluence)
    the node rows are created during hierarchy fetch -- before the document rows
    exist -- so their ``document_id`` FK starts out empty. Once the matching
    documents have been indexed, this links every still-unlinked node to the
    document that shares its ``raw_node_id``.

    Sources whose nodes are never documents, and an empty id list, are no-ops.
    Returns the number of nodes that were linked.
    """
    if source not in SOURCES_WITH_HIERARCHY_NODE_DOCUMENTS or not document_ids:
        return 0

    query = select(HierarchyNode).where(
        HierarchyNode.source == source,
        HierarchyNode.raw_node_id.in_(document_ids),
        HierarchyNode.document_id.is_(None),  # leave already-linked nodes alone
    )
    unlinked = list(db_session.execute(query).scalars().all())
    for node in unlinked:
        node.document_id = node.raw_node_id

    if commit:
        db_session.commit()

    if unlinked:
        logger.debug(
            f"Linked {len(unlinked)} hierarchy nodes to documents "
            f"for source {source.value}"
        )

    return len(unlinked)


# ---------------------------------------------------------------------------
# Tree browsing
# ---------------------------------------------------------------------------
def get_hierarchy_node_children(
    db_session: Session,
    parent_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[HierarchyNode]:
    """Return one page of a node's direct children, ordered by display name."""
    query = (
        select(HierarchyNode)
        .where(HierarchyNode.parent_id == parent_id)
        .order_by(HierarchyNode.display_name)
        .limit(limit)
        .offset(offset)
    )
    return list(db_session.execute(query).scalars().all())


def get_root_hierarchy_nodes_for_source(
    db_session: Session,
    source: DocumentSource,
) -> list[HierarchyNode]:
    """Return a source's top-level nodes: the direct children of its SOURCE root."""
    root = get_source_hierarchy_node(db_session, source)
    if root is None:
        return []
    return get_hierarchy_node_children(db_session, root.id)


def get_all_hierarchy_nodes_for_source(
    db_session: Session,
    source: DocumentSource,
) -> list[HierarchyNode]:
    """Return every node belonging to ``source``, the SOURCE root included.

    Intended for warming the Redis cache, so no permission filtering or
    pagination is applied.
    """
    query = select(HierarchyNode).where(HierarchyNode.source == source)
    return list(db_session.execute(query).scalars().all())


# ---------------------------------------------------------------------------
# Permission-scoped browsing
# ---------------------------------------------------------------------------
def _visibility_predicate(
    user_email: str | None,
    external_group_ids: list[str],
) -> ColumnElement[bool]:
    """Build the WHERE clause governing whether a caller may see a node.

    A node is visible when *any* of the following is true:
      * it is public (``is_public IS TRUE``);
      * the caller's email is present in ``external_user_emails``;
      * one of the caller's group ids overlaps ``external_team_ids``.

    The group test casts the Python list to ``text[]`` before applying the
    array-overlap operator, otherwise PostgreSQL rejects comparing it against the
    ``varchar[]`` column.
    """
    clauses: list[ColumnElement[bool]] = [HierarchyNode.is_public.is_(True)]
    if user_email:
        clauses.append(any_(HierarchyNode.external_user_emails) == user_email)
    if external_group_ids:
        clauses.append(
            HierarchyNode.external_team_ids.overlap(
                cast(postgresql.array(external_group_ids), postgresql.ARRAY(String))
            )
        )
    return or_(*clauses)


def _get_accessible_hierarchy_nodes_for_source(
    db_session: Session,
    source: DocumentSource,
    user_email: str | None,
    external_group_ids: list[str],
) -> list[HierarchyNode]:
    """Query the nodes of ``source`` visible to the caller, ordered by name.

    Kept as a standalone callable (distinct from the public wrapper below)
    because the access-filter regression tests exercise it directly.
    """
    query = (
        select(HierarchyNode)
        .where(HierarchyNode.source == source)
        .where(_visibility_predicate(user_email, external_group_ids))
        .order_by(HierarchyNode.display_name)
    )
    return list(db_session.execute(query).scalars().all())


def get_accessible_hierarchy_nodes_for_source(
    db_session: Session,
    source: DocumentSource,
    user_email: str | None,
    external_group_ids: list[str],
) -> list[HierarchyNode]:
    """Return the nodes of ``source`` the caller is allowed to browse.

    Visibility follows the public / email / group rules of
    :func:`_visibility_predicate`.
    """
    return _get_accessible_hierarchy_nodes_for_source(
        db_session, source, user_email, external_group_ids
    )


# ---------------------------------------------------------------------------
# Permission maintenance & document lookups
# ---------------------------------------------------------------------------
def update_hierarchy_node_permissions(
    db_session: Session,
    raw_node_id: str,
    source: DocumentSource,
    is_public: bool,
    external_user_emails: list[str] | None,
    external_team_ids: list[str] | None,
    commit: bool = True,
) -> bool:
    """Overwrite the permission triple on an existing node.

    Used by permission-sync to refresh a folder's sharing without rebuilding the
    full connector model. Returns ``True`` when a matching node was updated, or
    ``False`` (after logging a warning) when no node exists for
    ``(raw_node_id, source)``.
    """
    row = get_hierarchy_node_by_raw_id(db_session, raw_node_id, source)
    if row is None:
        logger.warning(
            f"Hierarchy node not found for permission update: "
            f"raw_node_id={raw_node_id}, source={source}"
        )
        return False

    row.is_public = is_public
    row.external_user_emails = external_user_emails
    row.external_team_ids = external_team_ids

    _flush_or_commit(db_session, commit)
    return True


def get_document_parent_hierarchy_node_ids(
    db_session: Session,
    document_ids: list[str],
) -> dict[str, int | None]:
    """Look up each document's ``parent_hierarchy_node_id`` in a single query.

    Returns a mapping from document id to its parent hierarchy node id (``None``
    when the document has no hierarchy parent). Document ids with no matching row
    simply do not appear in the result; an empty input yields an empty mapping.
    """
    if not document_ids:
        return {}

    query = select(Document.id, Document.parent_hierarchy_node_id).where(
        Document.id.in_(document_ids)
    )
    return {
        doc_id: parent_node_id
        for doc_id, parent_node_id in db_session.execute(query).all()
    }
