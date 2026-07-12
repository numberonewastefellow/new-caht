"""OAuth configuration feature module."""

from om.server.features.oauth_config.api import admin_router
from om.server.features.oauth_config.api import router

__all__ = ["admin_router", "router"]
