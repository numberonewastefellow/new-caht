from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from om.configs.chat_configs import MAX_CHUNKS_FED_TO_CHAT
from om.context.search.enums import RecencyBiasSetting
from om.db.constants import DEFAULT_AGENT_SLACK_CHANNEL_NAME
from om.db.constants import SLACK_BOT_AGENT_PREFIX
from om.db.models import ChannelConfig
from om.db.models import Agent
from om.db.models import Agent__DocumentSet
from om.db.models import SlackChannelConfig
from om.db.models import User
from om.db.agent import mark_agent_as_deleted
from om.db.agent import upsert_agent
from om.db.tools import get_builtin_tool
from om.tools.tool_implementations.search.search_tool import SearchTool
from om.utils.errors import EERequiredError


def _build_agent_name(channel_name: str | None) -> str:
    return f"{SLACK_BOT_AGENT_PREFIX}{channel_name if channel_name else DEFAULT_AGENT_SLACK_CHANNEL_NAME}"


def _cleanup_relationships(db_session: Session, agent_id: int) -> None:
    """NOTE: does not commit changes"""
    # delete existing agent-document_set relationships
    existing_relationships = db_session.scalars(
        select(Agent__DocumentSet).where(
            Agent__DocumentSet.agent_id == agent_id
        )
    )
    for rel in existing_relationships:
        db_session.delete(rel)


def create_slack_channel_agent(
    db_session: Session,
    channel_name: str | None,
    document_set_ids: list[int],
    existing_agent_id: int | None = None,
    num_chunks: float = MAX_CHUNKS_FED_TO_CHAT,
    enable_auto_filters: bool = False,
) -> Agent:
    """NOTE: does not commit changes"""

    search_tool = get_builtin_tool(db_session=db_session, tool_type=SearchTool)

    # create/update agent associated with the Slack channel
    agent_name = _build_agent_name(channel_name)
    agent_id_to_update = existing_agent_id
    if agent_id_to_update is None:
        # Reuse any previous Slack agent for this channel (even if the config was
        # temporarily switched to a different agent) so we don't trip duplicate name
        # validation inside `upsert_agent`.
        existing_agent = db_session.scalar(
            select(Agent).where(Agent.name == agent_name)
        )
        if existing_agent:
            agent_id_to_update = existing_agent.id

    agent = upsert_agent(
        user=None,  # Slack channel Agents are not attached to users
        agent_id=agent_id_to_update,
        name=agent_name,
        description="",
        system_prompt="",
        task_prompt="",
        datetime_aware=True,
        num_chunks=num_chunks,
        llm_relevance_filter=True,
        llm_filter_extraction=enable_auto_filters,
        recency_bias=RecencyBiasSetting.AUTO,
        tool_ids=[search_tool.id],
        document_set_ids=document_set_ids,
        llm_model_provider_override=None,
        llm_model_version_override=None,
        starter_messages=None,
        is_public=True,
        is_default_agent=False,
        db_session=db_session,
        commit=False,
    )

    return agent


def _no_ee_standard_answer_categories(
    *args: Any, **kwargs: Any  # noqa: ARG001
) -> list:
    return []


def insert_slack_channel_config(
    db_session: Session,
    slack_bot_id: int,
    agent_id: int | None,
    channel_config: ChannelConfig,
    standard_answer_category_ids: list[int],
    enable_auto_filters: bool,
    is_default: bool = False,
) -> SlackChannelConfig:
    from om.db.standard_answer import fetch_standard_answer_categories_by_ids as _impl_fetch_standard_answer_categories_by_ids
    versioned_fetch_standard_answer_categories_by_ids = (
        _impl_fetch_standard_answer_categories_by_ids
    )
    existing_standard_answer_categories = (
        versioned_fetch_standard_answer_categories_by_ids(
            standard_answer_category_ids=standard_answer_category_ids,
            db_session=db_session,
        )
    )

    if len(existing_standard_answer_categories) != len(standard_answer_category_ids):
        if len(existing_standard_answer_categories) == 0:
            raise EERequiredError(
                "Standard answers are a paid Enterprise Edition feature - enable EE or remove standard answer categories"
            )
        else:
            raise ValueError(
                f"Some or all categories with ids {standard_answer_category_ids} do not exist"
            )

    if is_default:
        existing_default = db_session.scalar(
            select(SlackChannelConfig).where(
                SlackChannelConfig.slack_bot_id == slack_bot_id,
                SlackChannelConfig.is_default is True,  # type: ignore
            )
        )
        if existing_default:
            raise ValueError("A default config already exists for this Slack bot.")
    else:
        if "channel_name" not in channel_config:
            raise ValueError("Channel name is required for non-default configs.")

    slack_channel_config = SlackChannelConfig(
        slack_bot_id=slack_bot_id,
        agent_id=agent_id,
        channel_config=channel_config,
        standard_answer_categories=existing_standard_answer_categories,
        enable_auto_filters=enable_auto_filters,
        is_default=is_default,
    )
    db_session.add(slack_channel_config)
    db_session.commit()

    return slack_channel_config


def update_slack_channel_config(
    db_session: Session,
    slack_channel_config_id: int,
    agent_id: int | None,
    channel_config: ChannelConfig,
    standard_answer_category_ids: list[int],
    enable_auto_filters: bool,
    disabled: bool,  # noqa: ARG001
) -> SlackChannelConfig:
    from om.db.standard_answer import fetch_standard_answer_categories_by_ids as _impl_fetch_standard_answer_categories_by_ids
    slack_channel_config = db_session.scalar(
        select(SlackChannelConfig).where(
            SlackChannelConfig.id == slack_channel_config_id
        )
    )
    if slack_channel_config is None:
        raise ValueError(
            f"Unable to find Slack channel config with ID {slack_channel_config_id}"
        )

    versioned_fetch_standard_answer_categories_by_ids = (
        _impl_fetch_standard_answer_categories_by_ids
    )
    existing_standard_answer_categories = (
        versioned_fetch_standard_answer_categories_by_ids(
            standard_answer_category_ids=standard_answer_category_ids,
            db_session=db_session,
        )
    )
    if len(existing_standard_answer_categories) != len(standard_answer_category_ids):
        raise ValueError(
            f"Some or all categories with ids {standard_answer_category_ids} do not exist"
        )

    # update the config
    slack_channel_config.agent_id = agent_id
    slack_channel_config.channel_config = channel_config
    slack_channel_config.standard_answer_categories = list(
        existing_standard_answer_categories
    )
    slack_channel_config.enable_auto_filters = enable_auto_filters

    db_session.commit()

    return slack_channel_config


def remove_slack_channel_config(
    db_session: Session,
    slack_channel_config_id: int,
    user: User,
) -> None:
    slack_channel_config = db_session.scalar(
        select(SlackChannelConfig).where(
            SlackChannelConfig.id == slack_channel_config_id
        )
    )
    if slack_channel_config is None:
        raise ValueError(
            f"Unable to find Slack channel config with ID {slack_channel_config_id}"
        )

    existing_agent_id = slack_channel_config.agent_id
    if existing_agent_id:
        existing_agent = db_session.scalar(
            select(Agent).where(Agent.id == existing_agent_id)
        )
        # if the existing agent was one created just for use with this Slack channel,
        # then clean it up
        if existing_agent and existing_agent.name.startswith(
            SLACK_BOT_AGENT_PREFIX
        ):
            _cleanup_relationships(
                db_session=db_session, agent_id=existing_agent_id
            )
            mark_agent_as_deleted(
                agent_id=existing_agent_id, user=user, db_session=db_session
            )

    db_session.delete(slack_channel_config)
    db_session.commit()


def fetch_slack_channel_configs(
    db_session: Session, slack_bot_id: int | None = None
) -> Sequence[SlackChannelConfig]:
    if not slack_bot_id:
        return db_session.scalars(select(SlackChannelConfig)).all()

    return db_session.scalars(
        select(SlackChannelConfig).where(
            SlackChannelConfig.slack_bot_id == slack_bot_id
        )
    ).all()


def fetch_slack_channel_config(
    db_session: Session, slack_channel_config_id: int
) -> SlackChannelConfig | None:
    return db_session.scalar(
        select(SlackChannelConfig).where(
            SlackChannelConfig.id == slack_channel_config_id
        )
    )


def fetch_slack_channel_config_for_channel_or_default(
    db_session: Session, slack_bot_id: int, channel_name: str | None
) -> SlackChannelConfig | None:
    # attempt to find channel-specific config first
    if channel_name is not None:
        sc_config = db_session.scalar(
            select(SlackChannelConfig)
            .options(joinedload(SlackChannelConfig.agent))
            .where(
                SlackChannelConfig.slack_bot_id == slack_bot_id,
                SlackChannelConfig.channel_config["channel_name"].astext
                == channel_name,
            )
        )
    else:
        sc_config = None

    if sc_config:
        return sc_config

    # if none found, see if there is a default
    default_sc = db_session.scalar(
        select(SlackChannelConfig)
        .options(joinedload(SlackChannelConfig.agent))
        .where(
            SlackChannelConfig.slack_bot_id == slack_bot_id,
            SlackChannelConfig.is_default == True,  # noqa: E712
        )
    )

    return default_sc
