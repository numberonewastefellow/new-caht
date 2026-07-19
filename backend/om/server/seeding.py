import json
import os
from copy import deepcopy
from typing import List
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from om.standard_answers.service import StandardAnswerService
from om.server.app_settings.logo import save_logo_from_path
from om.server.app_settings.models import AppSettingsSchema
from om.server.app_settings.models import NavigationItem
from om.server.app_settings.service import AppSettingsService
from om.context.search.enums import RecencyBiasSetting
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.llm import update_default_provider
from om.db.llm import upsert_llm_provider
from om.db.models import Tool
from om.db.agent import upsert_agent
from om.server.features.agent.models import AgentUpsertRequest
from om.server.manage.llm.models import LLMProviderUpsertRequest
from om.server.settings.models import Settings
from om.server.settings.store import store_settings as store_base_settings
from om.utils.logger import setup_logger


class CustomToolSeed(BaseModel):
    name: str
    description: str
    definition_path: str
    custom_headers: Optional[List[dict]] = None
    display_name: Optional[str] = None
    in_code_tool_id: Optional[str] = None
    user_id: Optional[str] = None


logger = setup_logger()

_SEED_CONFIG_ENV_VAR_NAME = "ENV_SEED_CONFIGURATION"


class NavigationItemSeed(BaseModel):
    link: str
    title: str
    # NOTE: SVG at this path must not have a width / height specified
    svg_path: str


class SeedConfiguration(BaseModel):
    llms: list[LLMProviderUpsertRequest] | None = None
    admin_user_emails: list[str] | None = None
    seeded_logo_path: str | None = None
    agents: list[AgentUpsertRequest] | None = None
    settings: Settings | None = None
    enterprise_settings: AppSettingsSchema | None = None

    # allows for specifying custom navigation items that have your own custom SVG logos
    nav_item_overrides: list[NavigationItemSeed] | None = None

    # Use existing `CUSTOM_ANALYTICS_SECRET_KEY` for reference
    analytics_script_path: str | None = None
    custom_tools: List[CustomToolSeed] | None = None


def _parse_env() -> SeedConfiguration | None:
    seed_config_str = os.getenv(_SEED_CONFIG_ENV_VAR_NAME)
    if not seed_config_str:
        return None
    seed_config = SeedConfiguration.model_validate_json(seed_config_str)
    return seed_config


def _seed_custom_tools(db_session: Session, tools: List[CustomToolSeed]) -> None:
    if tools:
        logger.notice("Seeding Custom Tools")
        for tool in tools:
            try:
                logger.debug(f"Attempting to seed tool: {tool.name}")
                logger.debug(f"Reading definition from: {tool.definition_path}")
                with open(tool.definition_path, "r") as file:
                    file_content = file.read()
                    if not file_content.strip():
                        raise ValueError("File is empty")
                    openapi_schema = json.loads(file_content)
                db_tool = Tool(
                    name=tool.name,
                    description=tool.description,
                    openapi_schema=openapi_schema,
                    custom_headers=tool.custom_headers,
                    display_name=tool.display_name,
                    in_code_tool_id=tool.in_code_tool_id,
                    user_id=tool.user_id,
                )
                db_session.add(db_tool)
                logger.debug(f"Successfully added tool: {tool.name}")
            except FileNotFoundError:
                logger.error(
                    f"Definition file not found for tool {tool.name}: {tool.definition_path}"
                )
            except json.JSONDecodeError as e:
                logger.error(
                    f"Invalid JSON in definition file for tool {tool.name}: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Failed to seed tool {tool.name}: {str(e)}")
        db_session.commit()
        logger.notice(f"Successfully seeded {len(tools)} Custom Tools")


def _seed_llms(
    db_session: Session, llm_upsert_requests: list[LLMProviderUpsertRequest]
) -> None:
    if llm_upsert_requests:
        logger.notice("Seeding LLMs")
        seeded_providers = [
            upsert_llm_provider(llm_upsert_request, db_session)
            for llm_upsert_request in llm_upsert_requests
        ]
        update_default_provider(
            provider_id=seeded_providers[0].id, db_session=db_session
        )


def _seed_agents(db_session: Session, agents: list[AgentUpsertRequest]) -> None:
    if agents:
        logger.notice("Seeding Agents")
        try:
            for agent in agents:
                upsert_agent(
                    user=None,  # Seeding is done as admin
                    name=agent.name,
                    description=agent.description,
                    num_chunks=(
                        agent.num_chunks if agent.num_chunks is not None else 0.0
                    ),
                    llm_relevance_filter=agent.llm_relevance_filter,
                    llm_filter_extraction=agent.llm_filter_extraction,
                    recency_bias=RecencyBiasSetting.AUTO,
                    document_set_ids=agent.document_set_ids,
                    llm_model_provider_override=agent.llm_model_provider_override,
                    llm_model_version_override=agent.llm_model_version_override,
                    starter_messages=agent.starter_messages,
                    is_public=agent.is_public,
                    db_session=db_session,
                    tool_ids=agent.tool_ids,
                    display_priority=agent.display_priority,
                    system_prompt=agent.system_prompt,
                    task_prompt=agent.task_prompt,
                    datetime_aware=agent.datetime_aware,
                    commit=False,
                )
            db_session.commit()
        except Exception:
            logger.exception("Failed to seed agents.")
            raise


def _seed_settings(settings: Settings) -> None:
    logger.notice("Seeding Settings")
    try:
        store_base_settings(settings)
        logger.notice("Successfully seeded Settings")
    except ValueError as e:
        logger.error(f"Failed to seed Settings: {str(e)}")


def _seed_enterprise_settings(
    db_session: Session, seed_config: SeedConfiguration
) -> None:
    if (
        seed_config.enterprise_settings is not None
        or seed_config.nav_item_overrides is not None
    ):
        final_settings = (
            deepcopy(seed_config.enterprise_settings)
            if seed_config.enterprise_settings
            else AppSettingsSchema()
        )

        if seed_config.nav_item_overrides is not None:
            final_nav_items = []
            for item in seed_config.nav_item_overrides:
                with open(item.svg_path, "r") as file:
                    svg_content = file.read().strip()

                final_nav_items.append(
                    NavigationItem(
                        link=item.link,
                        title=item.title,
                        svg_logo=svg_content,
                    )
                )

            # model_copy(update=...) marks custom_nav_items as explicitly set so
            # AppSettingsService.save (which uses exclude_unset) persists it.
            final_settings = final_settings.model_copy(
                update={"custom_nav_items": final_nav_items}
            )

        logger.notice("Seeding application settings")
        AppSettingsService(db_session).save(final_settings)


def _seed_logo(logo_path: str | None) -> None:
    if logo_path:
        logger.notice("Uploading logo")
        save_logo_from_path(logo_path)


def _seed_analytics_script(
    db_session: Session, seed_config: SeedConfiguration
) -> None:
    if seed_config.analytics_script_path:
        logger.notice("Seeding analytics script")
        try:
            with open(seed_config.analytics_script_path, "r") as file:
                script_content = file.read()
            AppSettingsService(db_session).set_custom_analytics_script(script_content)
        except FileNotFoundError:
            logger.error(
                f"Analytics script file not found: {seed_config.analytics_script_path}"
            )


def get_seed_config() -> SeedConfiguration | None:
    return _parse_env()


def seed_db() -> None:
    seed_config = _parse_env()
    if seed_config is None:
        logger.debug("No seeding configuration file passed")
        return

    with get_session_with_current_tenant() as db_session:
        if seed_config.llms is not None:
            _seed_llms(db_session, seed_config.llms)
        if seed_config.agents is not None:
            _seed_agents(db_session, seed_config.agents)
        if seed_config.settings is not None:
            _seed_settings(seed_config.settings)
        if seed_config.custom_tools is not None:
            _seed_custom_tools(db_session, seed_config.custom_tools)

        _seed_logo(seed_config.seeded_logo_path)
        _seed_enterprise_settings(db_session, seed_config)
        _seed_analytics_script(db_session, seed_config)

        logger.notice("Verifying default standard answer category exists.")
        StandardAnswerService(db_session).ensure_default_category()
