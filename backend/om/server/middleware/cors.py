from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send

from om.configs.app_configs import APP_API_PREFIX

_HOOKS_PATH = f"/{APP_API_PREFIX.strip('/')}/hooks/" if APP_API_PREFIX else "/hooks/"


class CORSExceptWebhooks(CORSMiddleware):
    """CORS for the app, but none for public webhook URLs: they are called by servers,
    and no web page should be able to call one or read its response."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith(_HOOKS_PATH):
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)
