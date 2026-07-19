from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import exists
from sqlalchemy import func
from sqlalchemy import not_
from sqlalchemy import or_
from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import aliased
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from om.access.hierarchy_access import get_user_external_group_ids
from om.auth.schemas import UserRole
from om.configs.app_configs import CURATORS_CANNOT_VIEW_OR_EDIT_NON_OWNED_ASSISTANTS
from om.configs.chat_configs import CONTEXT_CHUNKS_ABOVE
from om.configs.chat_configs import CONTEXT_CHUNKS_BELOW
from om.configs.constants import DEFAULT_AGENT_ID
from om.configs.constants import NotificationType
from om.context.search.enums import RecencyBiasSetting
from om.db.constants import SLACK_BOT_AGENT_PREFIX
from om.db.document_access import get_accessible_documents_by_ids
from om.db.models import ConnectorCredentialPair
from om.db.models import Document
from om.db.models import DocumentSet
from om.db.models import HierarchyNode
from om.db.models import Agent
from om.db.models import Agent__User
from om.db.models import Agent__Team
from om.db.models import AgentLabel
from om.db.models import StarterMessage
from om.db.models import Tool
from om.db.models import User
from om.db.models import User__Team
from om.db.models import KnowledgeFile
from om.db.models import Team
from om.db.notification import create_notification
from om.server.features.agent.models import FullAgentSnapshot
from om.server.features.agent.models import MinimalAgentSnapshot
from om.server.features.agent.models import AgentSharedNotificationData
from om.server.features.agent.models import AgentSnapshot
from om.server.features.agent.models import AgentUpsertRequest
from om.server.features.tool.tool_visibility import should_expose_tool_to_fe
from om.utils.logger import setup_logger

logger = setup_logger()


def get_default_behavior_agent(db_session: Session) -> Agent | None:
    stmt = select(Agent).where(Agent.id == DEFAULT_AGENT_ID)
    return db_session.scalars(stmt).first()


class AgentLoadType(Enum):
    NONE = "none"
    MINIMAL = "minimal"
    FULL = "full"


def _add_user_filters(
    stmt: Select[tuple[Agent]], user: User, get_editable: bool = True
) -> Select[tuple[Agent]]:
    if user.role == UserRole.ADMIN:
        return stmt

    stmt = stmt.distinct()
    Agent__UG = aliased(Agent__Team)
    User__UG = aliased(User__Team)
    """
    Here we select cc_pairs by relation:
    User -> User__Team -> Agent__Team -> Agent
    """
    stmt = (
        stmt.outerjoin(Agent__UG)
        .outerjoin(
            User__Team,
            User__Team.team_id == Agent__UG.team_id,
        )
        .outerjoin(
            Agent__User,
            Agent__User.agent_id == Agent.id,
        )
    )
    """
    Filter Agents by:
    - if the user is in the team that owns the Agent
    - if the user is not a global_curator, they must also have a curator relationship
    to the team
    - if editing is being done, we also filter out Agents that are owned by groups
    that the user isn't a curator for
    - if we are not editing, we show all Agents in the groups the user is a curator
    for (as well as public Agents)
    - if we are not editing, we return all Agents directly connected to the user
    """

    # Anonymous users only see public Agents
    if user.is_anonymous:
        where_clause = Agent.is_public == True  # noqa: E712
        return stmt.where(where_clause)

    # If curator ownership restriction is enabled, curators can only access their own assistants
    if CURATORS_CANNOT_VIEW_OR_EDIT_NON_OWNED_ASSISTANTS and user.role in [
        UserRole.CURATOR,
        UserRole.GLOBAL_CURATOR,
    ]:
        where_clause = (Agent.user_id == user.id) | (Agent.user_id.is_(None))
        return stmt.where(where_clause)

    where_clause = User__Team.user_id == user.id
    if user.role == UserRole.CURATOR and get_editable:
        where_clause &= User__Team.is_curator == True  # noqa: E712
    if get_editable:
        teams = select(User__UG.team_id).where(User__UG.user_id == user.id)
        if user.role == UserRole.CURATOR:
            teams = teams.where(User__UG.is_curator == True)  # noqa: E712
        where_clause &= (
            ~exists()
            .where(Agent__UG.agent_id == Agent.id)
            .where(~Agent__UG.team_id.in_(teams))
            .correlate(Agent)
        )
    else:
        # Group the public agent conditions
        public_condition = (Agent.is_public == True) & (  # noqa: E712
            Agent.is_visible == True  # noqa: E712
        )

        where_clause |= public_condition
        where_clause |= Agent__User.user_id == user.id

    where_clause |= Agent.user_id == user.id

    return stmt.where(where_clause)


def fetch_agent_by_id_for_user(
    db_session: Session, agent_id: int, user: User, get_editable: bool = True
) -> Agent:
    stmt = select(Agent).where(Agent.id == agent_id).distinct()
    stmt = _add_user_filters(stmt=stmt, user=user, get_editable=get_editable)
    agent = db_session.scalars(stmt).one_or_none()
    if not agent:
        raise HTTPException(
            status_code=403,
            detail=f"Agent with ID {agent_id} does not exist or user is not authorized to access it",
        )
    return agent


def get_best_agent_id_for_user(
    db_session: Session, user: User, agent_id: int | None = None
) -> int | None:
    if agent_id is not None:
        stmt = select(Agent).where(Agent.id == agent_id).distinct()
        stmt = _add_user_filters(
            stmt=stmt,
            user=user,
            # We don't want to filter by editable here, we just want to see if the
            # agent is usable by the user
            get_editable=False,
        )
        agent = db_session.scalars(stmt).one_or_none()
        if agent:
            return agent.id

    # If the agent is not found, or the slack bot is using doc sets instead of agents,
    # we need to find the best agent for the user
    # This is the agent with the highest display priority that the user has access to
    stmt = select(Agent).order_by(Agent.display_priority.desc()).distinct()
    stmt = _add_user_filters(stmt=stmt, user=user, get_editable=True)
    agent = db_session.scalars(stmt).one_or_none()
    return agent.id if agent else None


def _get_agent_by_name(
    agent_name: str, user: User | None, db_session: Session
) -> Agent | None:
    """Fetch a agent by name with access control.

    Access rules:
    - user=None (system operations): can see all agents
    - Admin users: can see all agents
    - Non-admin users: can only see their own agents
    """
    stmt = select(Agent).where(Agent.name == agent_name)
    if user and user.role != UserRole.ADMIN:
        stmt = stmt.where(Agent.user_id == user.id)
    result = db_session.execute(stmt).scalar_one_or_none()
    return result


def update_agent_access(
    agent_id: int,
    creator_user_id: UUID | None,
    db_session: Session,
    is_public: bool | None = None,
    user_ids: list[UUID] | None = None,
    group_ids: list[int] | None = None,
) -> None:
    """Updates the access settings for a agent including public status, user shares,
    and group shares.

    NOTE: This function batches all updates. If we don't dedupe the inputs,
    the commit will exception.

    NOTE: Callers are responsible for committing."""

    if is_public is not None:
        agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
        if agent:
            agent.is_public = is_public

    # NOTE: For user-ids and group-ids, `None` means "leave unchanged", `[]` means "clear all shares",
    # and a non-empty list means "replace with these shares".

    if user_ids is not None:
        db_session.query(Agent__User).filter(
            Agent__User.agent_id == agent_id
        ).delete(synchronize_session="fetch")

        user_ids_set = set(user_ids)
        for user_id in user_ids_set:
            db_session.add(Agent__User(agent_id=agent_id, user_id=user_id))
            if user_id != creator_user_id:
                create_notification(
                    user_id=user_id,
                    notif_type=NotificationType.AGENT_SHARED,
                    title="A new agent was shared with you!",
                    db_session=db_session,
                    additional_data=AgentSharedNotificationData(
                        agent_id=agent_id,
                    ).model_dump(),
                )

    if group_ids is not None:
        db_session.query(Agent__Team).filter(
            Agent__Team.agent_id == agent_id
        ).delete(synchronize_session="fetch")

        group_ids_set = set(group_ids)
        for group_id in group_ids_set:
            db_session.add(
                Agent__Team(agent_id=agent_id, team_id=group_id)
            )


def create_update_agent(
    agent_id: int | None,
    create_agent_request: AgentUpsertRequest,
    user: User,
    db_session: Session,
) -> FullAgentSnapshot:
    """Higher level function than upsert_agent, although either is valid to use."""
    # Permission to actually use these is checked later

    try:
        # Default agent validation
        if create_agent_request.is_default_agent:
            if not create_agent_request.is_public:
                raise ValueError("Cannot make a default agent non public")

            # Curators can edit default agents, but not make them
            if user.role == UserRole.CURATOR or user.role == UserRole.GLOBAL_CURATOR:
                pass
            elif user.role != UserRole.ADMIN:
                raise ValueError("Only admins can make a default agent")

        # Convert incoming string UUIDs to UUID objects for DB operations
        converted_knowledge_file_ids = None
        if create_agent_request.knowledge_file_ids is not None:
            try:
                converted_knowledge_file_ids = [
                    UUID(str_id) for str_id in create_agent_request.knowledge_file_ids
                ]
            except Exception:
                raise ValueError("Invalid knowledge_file_ids; must be UUID strings")

        agent = upsert_agent(
            agent_id=agent_id,
            user=user,
            db_session=db_session,
            description=create_agent_request.description,
            name=create_agent_request.name,
            document_set_ids=create_agent_request.document_set_ids,
            tool_ids=create_agent_request.tool_ids,
            is_public=create_agent_request.is_public,
            recency_bias=create_agent_request.recency_bias,
            llm_model_provider_override=create_agent_request.llm_model_provider_override,
            llm_model_version_override=create_agent_request.llm_model_version_override,
            max_output_tokens=create_agent_request.max_output_tokens,
            starter_messages=create_agent_request.starter_messages,
            system_prompt=create_agent_request.system_prompt,
            task_prompt=create_agent_request.task_prompt,
            datetime_aware=create_agent_request.datetime_aware,
            replace_base_system_prompt=create_agent_request.replace_base_system_prompt,
            uploaded_image_id=create_agent_request.uploaded_image_id,
            icon_name=create_agent_request.icon_name,
            display_priority=create_agent_request.display_priority,
            remove_image=create_agent_request.remove_image,
            search_start_date=create_agent_request.search_start_date,
            label_ids=create_agent_request.label_ids,
            num_chunks=create_agent_request.num_chunks,
            llm_relevance_filter=create_agent_request.llm_relevance_filter,
            llm_filter_extraction=create_agent_request.llm_filter_extraction,
            is_default_agent=create_agent_request.is_default_agent,
            knowledge_file_ids=converted_knowledge_file_ids,
            commit=False,
            hierarchy_node_ids=create_agent_request.hierarchy_node_ids,
            document_ids=create_agent_request.document_ids,
        )

        versioned_update_agent_access = update_agent_access

        versioned_update_agent_access(
            agent_id=agent.id,
            creator_user_id=user.id,
            db_session=db_session,
            user_ids=create_agent_request.users,
            group_ids=create_agent_request.groups,
        )
        db_session.commit()

    except ValueError as e:
        logger.exception("Failed to create agent")
        raise HTTPException(status_code=400, detail=str(e))

    return FullAgentSnapshot.from_model(agent)


def update_agent_shared(
    agent_id: int,
    user_ids: list[UUID] | None,
    user: User,
    db_session: Session,
    group_ids: list[int] | None = None,
    is_public: bool | None = None,
) -> None:
    """Simplified version of `create_update_agent` which only touches the
    accessibility rather than any of the logic (e.g. prompt, connected data sources,
    etc.)."""
    agent = fetch_agent_by_id_for_user(
        db_session=db_session, agent_id=agent_id, user=user, get_editable=True
    )

    if user and user.role != UserRole.ADMIN and agent.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="You don't have permission to modify this agent"
        )

    versioned_update_agent_access = update_agent_access
    versioned_update_agent_access(
        agent_id=agent_id,
        creator_user_id=user.id,
        db_session=db_session,
        is_public=is_public,
        user_ids=user_ids,
        group_ids=group_ids,
    )

    db_session.commit()


def update_agent_public_status(
    agent_id: int,
    is_public: bool,
    db_session: Session,
    user: User,
) -> None:
    agent = fetch_agent_by_id_for_user(
        db_session=db_session, agent_id=agent_id, user=user, get_editable=True
    )
    if user.role != UserRole.ADMIN and agent.user_id != user.id:
        raise ValueError("You don't have permission to modify this agent")

    agent.is_public = is_public
    db_session.commit()


def _build_agent_filters(
    stmt: Select[tuple[Agent]],
    include_default: bool,
    include_slack_bot_agents: bool,
    include_deleted: bool,
) -> Select[tuple[Agent]]:
    """Filters which Agents are included in the query.

    Args:
        stmt: The base query to filter.
        include_default: If True, includes builtin/default agents.
        include_slack_bot_agents: If True, includes Slack bot agents.
        include_deleted: If True, includes deleted agents.

    Returns:
        The modified query with the filters applied.
    """
    if not include_default:
        stmt = stmt.where(Agent.builtin_agent.is_(False))
    if not include_slack_bot_agents:
        stmt = stmt.where(not_(Agent.name.startswith(SLACK_BOT_AGENT_PREFIX)))
    if not include_deleted:
        stmt = stmt.where(Agent.deleted.is_(False))
    return stmt


def get_minimal_agent_snapshots_for_user(
    user: User,
    db_session: Session,
    get_editable: bool = True,
    include_default: bool = True,
    include_slack_bot_agents: bool = False,
    include_deleted: bool = False,
) -> list[MinimalAgentSnapshot]:
    stmt = select(Agent)
    stmt = _add_user_filters(stmt, user, get_editable)
    stmt = _build_agent_filters(
        stmt, include_default, include_slack_bot_agents, include_deleted
    )
    stmt = stmt.options(
        selectinload(Agent.tools),
        selectinload(Agent.labels),
        selectinload(Agent.document_sets)
        .selectinload(DocumentSet.connector_credential_pairs)
        .selectinload(ConnectorCredentialPair.connector),
        selectinload(Agent.hierarchy_nodes),
        selectinload(Agent.attached_documents).selectinload(
            Document.parent_hierarchy_node
        ),
        selectinload(Agent.user),
    )
    results = db_session.scalars(stmt).all()
    return [MinimalAgentSnapshot.from_model(agent) for agent in results]


def get_agent_snapshots_for_user(
    user: User,
    db_session: Session,
    get_editable: bool = True,
    include_default: bool = True,
    include_slack_bot_agents: bool = False,
    include_deleted: bool = False,
) -> list[AgentSnapshot]:
    stmt = select(Agent)
    stmt = _add_user_filters(stmt, user, get_editable)
    stmt = _build_agent_filters(
        stmt, include_default, include_slack_bot_agents, include_deleted
    )
    stmt = stmt.options(
        selectinload(Agent.tools),
        selectinload(Agent.hierarchy_nodes),
        selectinload(Agent.attached_documents).selectinload(
            Document.parent_hierarchy_node
        ),
        selectinload(Agent.labels),
        selectinload(Agent.document_sets),
        selectinload(Agent.user),
        selectinload(Agent.knowledge_files),
        selectinload(Agent.users),
        selectinload(Agent.groups),
    )

    results = db_session.scalars(stmt).all()
    return [AgentSnapshot.from_model(agent) for agent in results]


def get_agent_count_for_user(
    user: User,
    db_session: Session,
    get_editable: bool = True,
    include_default: bool = True,
    include_slack_bot_agents: bool = False,
    include_deleted: bool = False,
    search_query: str | None = None,
) -> int:
    """Counts the total number of agents accessible to the user.

    Args:
        user: The user to filter agents for. If None and auth is disabled,
            assumes the user is an admin. Otherwise, if None shows only public
            agents.
        db_session: Database session for executing queries.
        get_editable: If True, only returns agents the user can edit.
        include_default: If True, includes builtin/default agents.
        include_slack_bot_agents: If True, includes Slack bot agents.
        include_deleted: If True, includes deleted agents.

    Returns:
        Total count of agents matching the filters and user permissions.
    """
    stmt = _build_agent_base_query(
        user=user,
        get_editable=get_editable,
        include_default=include_default,
        include_slack_bot_agents=include_slack_bot_agents,
        include_deleted=include_deleted,
        search_query=search_query,
    )
    # Convert to count query.
    count_stmt = stmt.with_only_columns(func.count(func.distinct(Agent.id))).order_by(
        None
    )
    return db_session.scalar(count_stmt) or 0


def get_minimal_agent_snapshots_paginated(
    user: User,
    db_session: Session,
    page_num: int,
    page_size: int,
    get_editable: bool = True,
    include_default: bool = True,
    include_slack_bot_agents: bool = False,
    include_deleted: bool = False,
    search_query: str | None = None,
) -> list[MinimalAgentSnapshot]:
    """Gets a single page of minimal agent snapshots with ordering.

    Agents are ordered by display_priority (ASC, nulls last) then by ID (ASC
    distance from 0).

    Args:
        user: The user to filter agents for. If None and auth is disabled,
            assumes the user is an admin. Otherwise, if None shows only public
            agents.
        db_session: Database session for executing queries.
        page_num: Zero-indexed page number (e.g., 0 for the first page).
        page_size: Number of items per page.
        get_editable: If True, only returns agents the user can edit.
        include_default: If True, includes builtin/default agents.
        include_slack_bot_agents: If True, includes Slack bot agents.
        include_deleted: If True, includes deleted agents.

    Returns:
        List of MinimalAgentSnapshot objects for the requested page, ordered
        by display_priority (nulls last) then ID.
    """
    stmt = _get_paginated_agent_query(
        user,
        page_num,
        page_size,
        get_editable,
        include_default,
        include_slack_bot_agents,
        include_deleted,
        search_query=search_query,
    )
    # Do eager loading of columns we know MinimalAgentSnapshot.from_model will
    # need.
    stmt = stmt.options(
        selectinload(Agent.tools),
        selectinload(Agent.hierarchy_nodes),
        selectinload(Agent.attached_documents).selectinload(
            Document.parent_hierarchy_node
        ),
        selectinload(Agent.labels),
        selectinload(Agent.document_sets)
        .selectinload(DocumentSet.connector_credential_pairs)
        .selectinload(ConnectorCredentialPair.connector),
        selectinload(Agent.user),
    )

    results = db_session.scalars(stmt).all()
    return [MinimalAgentSnapshot.from_model(agent) for agent in results]


def get_agent_snapshots_paginated(
    user: User,
    db_session: Session,
    page_num: int,
    page_size: int,
    get_editable: bool = True,
    include_default: bool = True,
    include_slack_bot_agents: bool = False,
    include_deleted: bool = False,
    search_query: str | None = None,
) -> list[AgentSnapshot]:
    """Gets a single page of agent snapshots (admin view) with ordering.

    Agents are ordered by display_priority (ASC, nulls last) then by ID (ASC
    distance from 0).

    This function returns AgentSnapshot objects which contain more detailed
    information than MinimalAgentSnapshot, used for admin views.

    Args:
        user: The user to filter agents for. If None and auth is disabled,
            assumes the user is an admin. Otherwise, if None shows only public
            agents.
        db_session: Database session for executing queries.
        page_num: Zero-indexed page number (e.g., 0 for the first page).
        page_size: Number of items per page.
        get_editable: If True, only returns agents the user can edit.
        include_default: If True, includes builtin/default agents.
        include_slack_bot_agents: If True, includes Slack bot agents.
        include_deleted: If True, includes deleted agents.

    Returns:
        List of AgentSnapshot objects for the requested page, ordered by
        display_priority (nulls last) then ID.
    """
    stmt = _get_paginated_agent_query(
        user,
        page_num,
        page_size,
        get_editable,
        include_default,
        include_slack_bot_agents,
        include_deleted,
        search_query=search_query,
    )
    # Do eager loading of columns we know AgentSnapshot.from_model will need.
    stmt = stmt.options(
        selectinload(Agent.tools),
        selectinload(Agent.hierarchy_nodes),
        selectinload(Agent.attached_documents).selectinload(
            Document.parent_hierarchy_node
        ),
        selectinload(Agent.labels),
        selectinload(Agent.document_sets),
        selectinload(Agent.user),
        selectinload(Agent.knowledge_files),
        selectinload(Agent.users),
        selectinload(Agent.groups),
    )

    results = db_session.scalars(stmt).all()
    return [AgentSnapshot.from_model(agent) for agent in results]


def _get_paginated_agent_query(
    user: User,
    page_num: int,
    page_size: int,
    get_editable: bool = True,
    include_default: bool = True,
    include_slack_bot_agents: bool = False,
    include_deleted: bool = False,
    search_query: str | None = None,
) -> Select[tuple[Agent]]:
    """Builds a paginated query on agents ordered on display_priority and id.

    Agents are ordered by display_priority (ASC, nulls last) then by ID (ASC
    distance from 0) to match the frontend agentComparator() logic.

    Args:
        user: The user to filter agents for. If None and auth is disabled,
            assumes the user is an admin. Otherwise, if None shows only public
            agents.
        page_num: Zero-indexed page number (e.g., 0 for the first page).
        page_size: Number of items per page.
        get_editable: If True, only returns agents the user can edit.
        include_default: If True, includes builtin/default agents.
        include_slack_bot_agents: If True, includes Slack bot agents.
        include_deleted: If True, includes deleted agents.

    Returns:
        SQLAlchemy Select statement with all filters, ordering, and pagination
        applied.
    """
    stmt = _build_agent_base_query(
        user=user,
        get_editable=get_editable,
        include_default=include_default,
        include_slack_bot_agents=include_slack_bot_agents,
        include_deleted=include_deleted,
        search_query=search_query,
    )
    # Add the abs(id) expression to the SELECT list (required for DISTINCT +
    # ORDER BY).
    stmt = stmt.add_columns(func.abs(Agent.id).label("abs_id"))
    # Apply ordering.
    stmt = stmt.order_by(
        Agent.display_priority.asc().nullslast(),
        func.abs(Agent.id).asc(),
    )
    # Apply pagination.
    stmt = stmt.offset(page_num * page_size).limit(page_size)
    return stmt


def _build_agent_base_query(
    user: User,
    get_editable: bool = True,
    include_default: bool = True,
    include_slack_bot_agents: bool = False,
    include_deleted: bool = False,
    search_query: str | None = None,
) -> Select[tuple[Agent]]:
    """Builds a base agent query with all user and agent filters applied.

    This helper constructs a filtered query that can then be customized for
    counting, pagination, or full retrieval.

    Args:
        user: The user to filter agents for. If None and auth is disabled,
            assumes the user is an admin. Otherwise, if None shows only public
            agents.
        get_editable: If True, only returns agents the user can edit.
        include_default: If True, includes builtin/default agents.
        include_slack_bot_agents: If True, includes Slack bot agents.
        include_deleted: If True, includes deleted agents.
        search_query: If provided, case-insensitively matches the term against
            agent name OR description (substring match).

    Returns:
        SQLAlchemy Select statement with all filters applied.
    """
    stmt = select(Agent)
    stmt = _add_user_filters(stmt, user, get_editable)
    stmt = _build_agent_filters(
        stmt, include_default, include_slack_bot_agents, include_deleted
    )
    if search_query and search_query.strip():
        # Escape LIKE wildcards so user input is treated as a literal substring.
        safe = (
            search_query.strip()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        like = f"%{safe}%"
        stmt = stmt.where(
            or_(
                Agent.name.ilike(like, escape="\\"),
                Agent.description.ilike(like, escape="\\"),
            )
        )
    return stmt


def get_raw_agents_for_user(
    user: User,
    db_session: Session,
    get_editable: bool = True,
    include_default: bool = True,
    include_slack_bot_agents: bool = False,
    include_deleted: bool = False,
) -> Sequence[Agent]:
    stmt = _build_agent_base_query(
        user, get_editable, include_default, include_slack_bot_agents, include_deleted
    )
    return db_session.scalars(stmt).all()


def get_agents(db_session: Session) -> Sequence[Agent]:
    """WARNING: Unsafe, can fetch agents from all users."""
    stmt = select(Agent).distinct()
    stmt = stmt.where(not_(Agent.name.startswith(SLACK_BOT_AGENT_PREFIX)))
    stmt = stmt.where(Agent.deleted.is_(False))
    return db_session.execute(stmt).unique().scalars().all()


def mark_agent_as_deleted(
    agent_id: int,
    user: User,
    db_session: Session,
) -> None:
    agent = get_agent_by_id(agent_id=agent_id, user=user, db_session=db_session)
    agent.deleted = True
    db_session.commit()


def mark_agent_as_not_deleted(
    agent_id: int,
    user: User,
    db_session: Session,
) -> None:
    agent = get_agent_by_id(
        agent_id=agent_id, user=user, db_session=db_session, include_deleted=True
    )
    if agent.deleted:
        agent.deleted = False
        db_session.commit()
    else:
        raise ValueError(f"Agent with ID {agent_id} is not deleted.")


def mark_delete_agent_by_name(
    agent_name: str, db_session: Session, is_default: bool = True
) -> None:
    stmt = (
        update(Agent)
        .where(Agent.name == agent_name, Agent.builtin_agent == is_default)
        .values(deleted=True)
    )

    db_session.execute(stmt)
    db_session.commit()


def update_agents_display_priority(
    display_priority_map: dict[int, int],
    db_session: Session,
    user: User,
    commit_db_txn: bool = False,
) -> None:
    """Updates the display priorities of the specified Agents.

    Args:
        display_priority_map: A map of agent IDs to intended display
            priorities.
        db_session: Database session for executing queries.
        user: The user to filter agents for. If None and auth is disabled,
            assumes the user is an admin. Otherwise, if None shows only public
            agents.
        commit_db_txn: If True, commits the database transaction after
            updating the display priorities. Defaults to False.

    Raises:
        ValueError: The caller tried to update a agent for which the user does
            not have access.
    """
    # No-op to save a query if it is not necessary.
    if len(display_priority_map) == 0:
        return

    agents = get_raw_agents_for_user(
        user,
        db_session,
        get_editable=False,
        include_default=True,
        include_slack_bot_agents=True,
        include_deleted=True,
    )
    available_agents_map: dict[int, Agent] = {
        agent.id: agent for agent in agents
    }

    for agent_id, priority in display_priority_map.items():
        if agent_id not in available_agents_map:
            raise ValueError(
                f"Invalid agent ID provided: Agent with ID {agent_id} was not found for this user."
            )

        available_agents_map[agent_id].display_priority = priority

    if commit_db_txn:
        db_session.commit()


def upsert_agent(
    user: User | None,
    name: str,
    description: str,
    num_chunks: float,
    llm_relevance_filter: bool,
    llm_filter_extraction: bool,
    recency_bias: RecencyBiasSetting,
    llm_model_provider_override: str | None,
    llm_model_version_override: str | None,
    starter_messages: list[StarterMessage] | None,
    # Embedded prompt fields
    system_prompt: str | None,
    task_prompt: str | None,
    datetime_aware: bool | None,
    is_public: bool,
    db_session: Session,
    document_set_ids: list[int] | None = None,
    tool_ids: list[int] | None = None,
    agent_id: int | None = None,
    commit: bool = True,
    uploaded_image_id: str | None = None,
    icon_name: str | None = None,
    display_priority: int | None = None,
    is_visible: bool = True,
    remove_image: bool | None = None,
    search_start_date: datetime | None = None,
    builtin_agent: bool = False,
    is_default_agent: bool | None = None,
    label_ids: list[int] | None = None,
    knowledge_file_ids: list[UUID] | None = None,
    hierarchy_node_ids: list[int] | None = None,
    document_ids: list[str] | None = None,
    chunks_above: int = CONTEXT_CHUNKS_ABOVE,
    chunks_below: int = CONTEXT_CHUNKS_BELOW,
    replace_base_system_prompt: bool = False,
    max_output_tokens: int | None = None,
) -> Agent:
    """
    NOTE: This operation cannot update agent configuration options that
    are core to the agent, such as its display priority and
    whether or not the assistant is a built-in / default assistant
    """

    if agent_id is not None:
        existing_agent = db_session.query(Agent).filter_by(id=agent_id).first()
    else:
        existing_agent = _get_agent_by_name(
            agent_name=name, user=user, db_session=db_session
        )

        # Check for duplicate names when creating new agents
        # Deleted agents are allowed to be overwritten
        if existing_agent and not existing_agent.deleted:
            raise ValueError(
                f"Assistant with name '{name}' already exists. Please rename your assistant."
            )

    if existing_agent and user:
        # this checks if the user has permission to edit the agent
        # will raise an Exception if the user does not have permission
        # Skip check if user is None (system/admin operation)
        existing_agent = fetch_agent_by_id_for_user(
            db_session=db_session,
            agent_id=existing_agent.id,
            user=user,
            get_editable=True,
        )

    # Fetch and attach tools by IDs
    tools = None
    if tool_ids is not None:
        tools = db_session.query(Tool).filter(Tool.id.in_(tool_ids)).all()
        if not tools and tool_ids:
            raise ValueError("Tools not found")

    # Fetch and attach document_sets by IDs
    document_sets = None
    if document_set_ids is not None:
        document_sets = (
            db_session.query(DocumentSet)
            .filter(DocumentSet.id.in_(document_set_ids))
            .all()
        )
        if not document_sets and document_set_ids:
            raise ValueError("document_sets not found")

    # Fetch and attach knowledge_files by IDs
    knowledge_files = None
    if knowledge_file_ids is not None:
        knowledge_files = (
            db_session.query(KnowledgeFile).filter(KnowledgeFile.id.in_(knowledge_file_ids)).all()
        )
        if not knowledge_files and knowledge_file_ids:
            raise ValueError("knowledge_files not found")

    labels = None
    if label_ids is not None:
        labels = (
            db_session.query(AgentLabel).filter(AgentLabel.id.in_(label_ids)).all()
        )

    # Fetch and attach hierarchy_nodes by IDs
    hierarchy_nodes = None
    if hierarchy_node_ids:
        hierarchy_nodes = (
            db_session.query(HierarchyNode)
            .filter(HierarchyNode.id.in_(hierarchy_node_ids))
            .all()
        )
        if not hierarchy_nodes and hierarchy_node_ids:
            raise ValueError("hierarchy_nodes not found")

    # Fetch and attach documents by IDs, filtering for access permissions
    attached_documents = None
    if document_ids is not None:
        user_email = user.email if user else None
        external_group_ids = (
            get_user_external_group_ids(db_session, user) if user else []
        )
        attached_documents = get_accessible_documents_by_ids(
            db_session=db_session,
            document_ids=document_ids,
            user_email=user_email,
            external_group_ids=external_group_ids,
        )
        if not attached_documents and document_ids:
            raise ValueError("documents not found or not accessible")

    # ensure all specified tools are valid
    if tools:
        validate_agent_tools(tools, db_session)

    if existing_agent:
        # Built-in agents can only be updated through YAML configuration.
        # This ensures that core system agents are not modified unintentionally.
        if existing_agent.builtin_agent and not builtin_agent:
            raise ValueError("Cannot update builtin agent with non-builtin.")

        # The following update excludes `default`, `built-in`, and display priority.
        # Display priority is handled separately in the `display-priority` endpoint.
        # `default` and `built-in` properties can only be set when creating a agent.
        existing_agent.name = name
        existing_agent.description = description
        existing_agent.num_chunks = num_chunks
        existing_agent.chunks_above = chunks_above
        existing_agent.chunks_below = chunks_below
        existing_agent.llm_relevance_filter = llm_relevance_filter
        existing_agent.llm_filter_extraction = llm_filter_extraction
        existing_agent.recency_bias = recency_bias
        existing_agent.llm_model_provider_override = llm_model_provider_override
        existing_agent.llm_model_version_override = llm_model_version_override
        existing_agent.max_output_tokens = max_output_tokens
        existing_agent.starter_messages = starter_messages
        existing_agent.deleted = False  # Un-delete if previously deleted
        existing_agent.is_public = is_public
        if remove_image or uploaded_image_id:
            existing_agent.uploaded_image_id = uploaded_image_id
        existing_agent.icon_name = icon_name
        existing_agent.is_visible = is_visible
        existing_agent.search_start_date = search_start_date
        if label_ids is not None:
            existing_agent.labels.clear()
            existing_agent.labels = labels or []
        existing_agent.is_default_agent = (
            is_default_agent
            if is_default_agent is not None
            else existing_agent.is_default_agent
        )
        # Update embedded prompt fields if provided
        if system_prompt is not None:
            existing_agent.system_prompt = system_prompt
        if task_prompt is not None:
            existing_agent.task_prompt = task_prompt
        if datetime_aware is not None:
            existing_agent.datetime_aware = datetime_aware
        existing_agent.replace_base_system_prompt = replace_base_system_prompt

        # Do not delete any associations manually added unless
        # a new updated list is provided
        if document_sets is not None:
            existing_agent.document_sets.clear()
            existing_agent.document_sets = document_sets or []

        # Note: prompts are now embedded in agents - no separate prompts relationship

        if tools is not None:
            existing_agent.tools = tools or []

        if knowledge_file_ids is not None:
            existing_agent.knowledge_files.clear()
            existing_agent.knowledge_files = knowledge_files or []

        if hierarchy_node_ids is not None:
            existing_agent.hierarchy_nodes.clear()
            existing_agent.hierarchy_nodes = hierarchy_nodes or []

        if document_ids is not None:
            existing_agent.attached_documents.clear()
            existing_agent.attached_documents = attached_documents or []

        # We should only update display priority if it is not already set
        if existing_agent.display_priority is None:
            existing_agent.display_priority = display_priority

        agent = existing_agent

    else:
        # Create new agent - prompt configuration will be set separately if needed
        new_agent = Agent(
            id=agent_id,
            user_id=user.id if user else None,
            is_public=is_public,
            name=name,
            description=description,
            num_chunks=num_chunks,
            chunks_above=chunks_above,
            chunks_below=chunks_below,
            llm_relevance_filter=llm_relevance_filter,
            llm_filter_extraction=llm_filter_extraction,
            recency_bias=recency_bias,
            builtin_agent=builtin_agent,
            system_prompt=system_prompt or "",
            task_prompt=task_prompt or "",
            datetime_aware=(datetime_aware if datetime_aware is not None else True),
            replace_base_system_prompt=replace_base_system_prompt,
            document_sets=document_sets or [],
            llm_model_provider_override=llm_model_provider_override,
            llm_model_version_override=llm_model_version_override,
            max_output_tokens=max_output_tokens,
            starter_messages=starter_messages,
            tools=tools or [],
            uploaded_image_id=uploaded_image_id,
            icon_name=icon_name,
            display_priority=display_priority,
            is_visible=is_visible,
            search_start_date=search_start_date,
            is_default_agent=(
                is_default_agent if is_default_agent is not None else False
            ),
            knowledge_files=knowledge_files or [],
            labels=labels or [],
            hierarchy_nodes=hierarchy_nodes or [],
            attached_documents=attached_documents or [],
        )
        db_session.add(new_agent)
        agent = new_agent
    if commit:
        db_session.commit()
    else:
        # flush the session so that the agent has an ID
        db_session.flush()

    return agent


def delete_old_default_agents(
    db_session: Session,
) -> None:
    """Note, this locks out the Summarize and Paraphrase agents for now
    Need a more graceful fix later or those need to never have IDs.

    This function is idempotent, so it can be run multiple times without issue.
    """
    OLD_SUFFIX = "_old"
    stmt = (
        update(Agent)
        .where(
            Agent.builtin_agent,
            Agent.id > 0,
            or_(
                Agent.deleted.is_(False),
                not_(Agent.name.endswith(OLD_SUFFIX)),
            ),
        )
        .values(deleted=True, name=func.concat(Agent.name, OLD_SUFFIX))
    )

    db_session.execute(stmt)
    db_session.commit()


def update_agent_is_default(
    agent_id: int,
    is_default: bool,
    db_session: Session,
    user: User,
) -> None:
    agent = fetch_agent_by_id_for_user(
        db_session=db_session, agent_id=agent_id, user=user, get_editable=True
    )

    if not agent.is_public:
        agent.is_public = True

    agent.is_default_agent = is_default
    db_session.commit()


def update_agent_visibility(
    agent_id: int,
    is_visible: bool,
    db_session: Session,
    user: User,
) -> None:
    agent = fetch_agent_by_id_for_user(
        db_session=db_session, agent_id=agent_id, user=user, get_editable=True
    )

    agent.is_visible = is_visible
    db_session.commit()


def validate_agent_tools(tools: list[Tool], db_session: Session) -> None:
    # local import to avoid circular import. DB layer should not depend on tools layer.
    from om.tools.built_in_tools import get_built_in_tool_by_id

    for tool in tools:
        if tool.in_code_tool_id is not None:
            tool_cls = get_built_in_tool_by_id(tool.in_code_tool_id)
            if not tool_cls.is_available(db_session):
                raise ValueError(f"Tool {tool.in_code_tool_id} is not available")


# TODO: since this gets called with every chat message, could it be more efficient to pregenerate
# a direct mapping indicating whether a user has access to a specific agent?
def get_agent_by_id(
    agent_id: int,
    user: User | None,
    db_session: Session,
    include_deleted: bool = False,
    is_for_edit: bool = True,  # NOTE: assume true for safety
) -> Agent:
    agent_stmt = (
        select(Agent)
        .distinct()
        .outerjoin(Agent.groups)
        .outerjoin(Agent.users)
        .outerjoin(Team.team_relationships)
        .where(Agent.id == agent_id)
    )

    if not include_deleted:
        agent_stmt = agent_stmt.where(Agent.deleted.is_(False))

    if not user or user.role == UserRole.ADMIN:
        result = db_session.execute(agent_stmt)
        agent = result.scalar_one_or_none()
        if agent is None:
            raise ValueError(f"Agent with ID {agent_id} does not exist")
        return agent

    # or check if user owns agent
    or_conditions = Agent.user_id == user.id
    # allow access if agent user id is None
    or_conditions |= Agent.user_id == None  # noqa: E711
    if not is_for_edit:
        # if the user is in a group related to the agent
        or_conditions |= User__Team.user_id == user.id
        # if the user is in the .users of the agent
        or_conditions |= User.id == user.id
        or_conditions |= Agent.is_public == True  # noqa: E712
    elif user.role == UserRole.GLOBAL_CURATOR:
        # global curators can edit agents for the groups they are in
        or_conditions |= User__Team.user_id == user.id
    elif user.role == UserRole.CURATOR:
        # curators can edit agents for the groups they are curators of
        or_conditions |= (User__Team.user_id == user.id) & (
            User__Team.is_curator == True  # noqa: E712
        )

    agent_stmt = agent_stmt.where(or_conditions)
    result = db_session.execute(agent_stmt)
    agent = result.scalar_one_or_none()
    if agent is None:
        raise ValueError(
            f"Agent with ID {agent_id} does not exist or does not belong to user"
        )
    return agent


def get_agents_by_ids(
    agent_ids: list[int], db_session: Session
) -> Sequence[Agent]:
    """WARNING: Unsafe, can fetch agents from all users."""
    if not agent_ids:
        return []
    agents = db_session.scalars(
        select(Agent).where(Agent.id.in_(agent_ids))
    ).all()

    return agents


def delete_agent_by_name(
    agent_name: str, db_session: Session, is_default: bool = True
) -> None:
    stmt = (
        update(Agent)
        .where(Agent.name == agent_name, Agent.builtin_agent == is_default)
        .values(deleted=True)
    )

    db_session.execute(stmt)
    db_session.commit()


def get_assistant_labels(db_session: Session) -> list[AgentLabel]:
    return db_session.query(AgentLabel).all()


def create_assistant_label(db_session: Session, name: str) -> AgentLabel:
    label = AgentLabel(name=name)
    db_session.add(label)
    db_session.commit()
    return label


def update_agent_label(
    label_id: int,
    label_name: str,
    db_session: Session,
) -> None:
    agent_label = (
        db_session.query(AgentLabel).filter(AgentLabel.id == label_id).one_or_none()
    )
    if agent_label is None:
        raise ValueError(f"Agent label with ID {label_id} does not exist")
    agent_label.name = label_name
    db_session.commit()


def delete_agent_label(label_id: int, db_session: Session) -> None:
    db_session.query(AgentLabel).filter(AgentLabel.id == label_id).delete()
    db_session.commit()


def agent_has_search_tool(agent_id: int, db_session: Session) -> bool:
    agent = (
        db_session.query(Agent)
        .options(selectinload(Agent.tools))
        .filter(Agent.id == agent_id)
        .one_or_none()
    )
    if agent is None:
        raise ValueError(f"Agent with ID {agent_id} does not exist")
    return any(tool.in_code_tool_id == "run_search" for tool in agent.tools)


def get_default_assistant(db_session: Session) -> Agent | None:
    """Fetch the default assistant (agent with builtin_agent=True)."""
    return (
        db_session.query(Agent)
        .options(selectinload(Agent.tools))
        .filter(Agent.builtin_agent.is_(True))
        # NOTE: need to add this since we had prior builtin agents
        # that have since been deleted
        .filter(Agent.deleted.is_(False))
        .one_or_none()
    )


def update_default_assistant_configuration(
    db_session: Session,
    tool_ids: list[int] | None = None,
    system_prompt: str | None = None,
    update_system_prompt: bool = False,
) -> Agent:
    """Update only tools and system_prompt for the default assistant.

    Args:
        db_session: Database session
        tool_ids: List of tool IDs to enable (if None, tools are not updated)
        system_prompt: New system prompt value (None means use default)
        update_system_prompt: If True, update the system_prompt field (allows setting to None)

    Returns:
        Updated Agent object

    Raises:
        ValueError: If default assistant not found or invalid tool IDs provided
    """
    # Get the default assistant
    agent = get_default_assistant(db_session)
    if not agent:
        raise ValueError("Default assistant not found")

    # Update system prompt if explicitly requested
    if update_system_prompt:
        agent.system_prompt = system_prompt

    # Update tools if provided
    if tool_ids is not None:
        # Clear existing tool associations
        agent.tools = []

        # Add new tool associations
        for tool_id in tool_ids:
            tool = db_session.query(Tool).filter(Tool.id == tool_id).one_or_none()
            if not tool:
                raise ValueError(f"Tool with ID {tool_id} not found")

            if not should_expose_tool_to_fe(tool):
                raise ValueError(f"Tool with ID {tool_id} cannot be assigned")

            if not tool.enabled:
                raise ValueError(
                    f"Enable tool {tool.display_name or tool.name} before assigning it"
                )

            agent.tools.append(tool)

    db_session.commit()
    return agent


def user_can_access_agent(
    db_session: Session, agent_id: int, user: User, get_editable: bool = False
) -> bool:
    """Check if a user has access to a specific agent.

    Args:
        db_session: Database session
        agent_id: ID of the agent to check
        user: User to check access for
        get_editable: If True, check for edit access; if False, check for view access

    Returns:
        True if user can access the agent, False otherwise
    """
    stmt = select(Agent).where(Agent.id == agent_id, Agent.deleted.is_(False))
    stmt = _add_user_filters(stmt, user, get_editable=get_editable)
    return db_session.scalar(stmt) is not None
