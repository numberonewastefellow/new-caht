"""Service for fetching and syncing LLM model configurations.

This service manages Auto mode LLM providers, where models and configuration
are managed centrally via a recommended-models JSON config. In Auto mode:
- Model list is controlled by the config
- Model visibility is controlled by the config
- Default model is controlled by the config
- Admin only needs to provide API credentials

The config is bundled with the code (`recommended-models.json`). If
AUTO_LLM_CONFIG_URL is set, a remote copy is fetched instead (cached in-process).
"""

import json
import pathlib
import threading
import time
from datetime import datetime
from functools import lru_cache

import httpx
from sqlalchemy.orm import Session

from om.configs.app_configs import AUTO_LLM_CONFIG_URL
from om.db.llm import fetch_auto_mode_providers
from om.db.llm import sync_auto_mode_models
from om.llm.well_known_providers.auto_update_models import LLMRecommendations
from om.redis.redis_pool import get_redis_client
from om.utils.logger import setup_logger

logger = setup_logger()

# Redis key for caching the last updated timestamp (per-tenant)
_REDIS_KEY_LAST_UPDATED_AT = "auto_llm_update:last_updated_at"

_BUNDLED_RECOMMENDATIONS_PATH = pathlib.Path(__file__).parent / "recommended-models.json"

# In-process cache for the remote config (only used when AUTO_LLM_CONFIG_URL is set).
# Failures are cached for a shorter time so an unreachable URL doesn't make every
# request wait for the HTTP timeout.
_REMOTE_CONFIG_TTL_SECONDS = 60 * 60
_REMOTE_CONFIG_FAILURE_TTL_SECONDS = 5 * 60
_remote_config_lock = threading.Lock()
_remote_config_cache: tuple[float, LLMRecommendations | None] | None = None


def _get_cached_last_updated_at() -> datetime | None:
    """Get the cached last_updated_at timestamp from Redis."""
    try:
        redis_client = get_redis_client()
        value = redis_client.get(_REDIS_KEY_LAST_UPDATED_AT)
        if value and isinstance(value, bytes):
            # Value is bytes, decode to string then parse as ISO format
            return datetime.fromisoformat(value.decode("utf-8"))
    except Exception as e:
        logger.warning(f"Failed to get cached last_updated_at from Redis: {e}")
    return None


def _set_cached_last_updated_at(updated_at: datetime) -> None:
    """Set the cached last_updated_at timestamp in Redis."""
    try:
        redis_client = get_redis_client()
        # Store as ISO format string, with 24 hour expiration
        redis_client.set(
            _REDIS_KEY_LAST_UPDATED_AT,
            updated_at.isoformat(),
            ex=60 * 60 * 24,  # 24 hours
        )
    except Exception as e:
        logger.warning(f"Failed to set cached last_updated_at in Redis: {e}")


@lru_cache(maxsize=1)
def load_bundled_recommendations() -> LLMRecommendations:
    """Load the recommended-models config bundled with the code (read once per process)."""
    with open(_BUNDLED_RECOMMENDATIONS_PATH, "r") as f:
        return LLMRecommendations.model_validate(json.load(f))


def _fetch_remote_recommendations(timeout: float) -> LLMRecommendations | None:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(AUTO_LLM_CONFIG_URL)
            response.raise_for_status()

            data = response.json()
            return LLMRecommendations.model_validate(data)
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch LLM config from {AUTO_LLM_CONFIG_URL}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing LLM config: {e}")
        return None


def fetch_llm_recommendations_from_github(
    timeout: float = 30.0,
    use_cache: bool = True,
) -> LLMRecommendations | None:
    """Get the recommended-models config.

    Without AUTO_LLM_CONFIG_URL this returns the bundled config. With it, the
    remote copy is fetched and cached in-process for an hour; pass
    `use_cache=False` to force a fresh fetch (the periodic sync does this).

    Returns:
        LLMRecommendations if available, None if the remote fetch failed.
    """
    global _remote_config_cache

    if not AUTO_LLM_CONFIG_URL:
        return load_bundled_recommendations()

    with _remote_config_lock:
        if use_cache and _remote_config_cache is not None:
            fetched_at, cached_config = _remote_config_cache
            ttl = (
                _REMOTE_CONFIG_TTL_SECONDS
                if cached_config is not None
                else _REMOTE_CONFIG_FAILURE_TTL_SECONDS
            )
            if time.monotonic() - fetched_at < ttl:
                return cached_config

        # Fetch while holding the lock so concurrent callers share one request
        config = _fetch_remote_recommendations(timeout)
        _remote_config_cache = (time.monotonic(), config)
        return config


def sync_llm_models_from_github(
    db_session: Session,
    force: bool = False,
) -> dict[str, int]:
    """Sync models from the recommended-models config to all Auto mode providers.

    In Auto mode, EVERYTHING is controlled by the config:
    - Model list
    - Model visibility (is_visible)
    - Default model
    - Fast default model

    Args:
        db_session: Database session
        config: GitHub LLM configuration
        force: If True, skip the updated_at check and force sync

    Returns:
        Dict of provider_name -> number of changes made.
    """
    results: dict[str, int] = {}

    # Get all providers in Auto mode
    auto_providers = fetch_auto_mode_providers(db_session)
    if not auto_providers:
        logger.debug("No providers in Auto mode found")
        return {}

    config = fetch_llm_recommendations_from_github(use_cache=False)
    if not config:
        logger.warning("Failed to fetch LLM recommendations config")
        return {}

    # Skip if we've already processed this version (unless forced)
    last_updated_at = _get_cached_last_updated_at()
    if not force and last_updated_at and config.updated_at <= last_updated_at:
        logger.debug("LLM recommendations config unchanged, skipping sync")
        _set_cached_last_updated_at(config.updated_at)
        return {}

    for provider in auto_providers:
        provider_type = provider.provider  # e.g., "openai", "anthropic"

        if provider_type not in config.providers:
            logger.debug(
                f"No config for provider type '{provider_type}' in recommendations"
            )
            continue

        # Sync models - this replaces the model list entirely for Auto mode
        changes = sync_auto_mode_models(
            db_session=db_session,
            provider=provider,
            llm_recommendations=config,
        )

        if changes > 0:
            results[provider.name] = changes
            logger.info(
                f"Applied {changes} model changes to provider '{provider.name}'"
            )

    _set_cached_last_updated_at(config.updated_at)
    return results


def reset_cache() -> None:
    """Reset the cache timestamp in Redis. Useful for testing."""
    try:
        redis_client = get_redis_client()
        redis_client.delete(_REDIS_KEY_LAST_UPDATED_AT)
    except Exception as e:
        logger.warning(f"Failed to reset cache in Redis: {e}")
