"""Formerly the EE/MIT dynamic-dispatch hub.

Everything that made this module interesting is gone, and that is the point of the EE
removal:

  * `fetch_versioned_implementation(module, attribute)` resolved a module path held in a
    STRING at runtime, preferring an `ee.`-prefixed mirror and falling back to the MIT
    module. All ~109 call sites are now direct imports of the merged implementation.
  * `fetch_versioned_implementation_with_fallback` / `fetch_ee_implementation_or_noop`
    were the same mechanism with a fallback / no-op branch for when EE was absent. EE is
    never absent now.
  * `global_version` / `set_is_ee_based_on_env_variable()` answered "are we the paid
    edition?". There is one edition.

Those string-keyed module paths were the single most dangerous thing in this codebase to
rename or move: no import, no type checker, and no test that merely starts the app can
see them -- they fail only when that specific code path first executes, which for a
Celery task can be days after deploy. They are deliberately not coming back; a test
(tests/unit/migration_safety/test_fetch_versioned_impl_resolves.py) fails if one does.

Only `build_api_server_url_for_http_requests` survives, which was never part of the EE
machinery and just happened to live here.
"""

from om.configs.app_configs import API_SERVER_HOST
from om.configs.app_configs import API_SERVER_PROTOCOL
from om.configs.app_configs import API_SERVER_URL_OVERRIDE_FOR_HTTP_REQUESTS
from om.configs.app_configs import APP_API_PREFIX
from om.configs.app_configs import APP_PORT
from om.configs.app_configs import DEV_MODE
from om.utils.logger import setup_logger

logger = setup_logger()


def build_api_server_url_for_http_requests(
    respect_env_override_if_set: bool = False,
) -> str:
    """
    Builds the API server URL for HTTP requests.
    """
    if DEV_MODE:
        url = f"http://127.0.0.1:{APP_PORT}"
    elif respect_env_override_if_set and API_SERVER_URL_OVERRIDE_FOR_HTTP_REQUESTS:
        url = API_SERVER_URL_OVERRIDE_FOR_HTTP_REQUESTS.rstrip("/")
    else:
        url = f"{API_SERVER_PROTOCOL}://{API_SERVER_HOST}:{APP_PORT}"

    if APP_API_PREFIX:
        url += f"/{APP_API_PREFIX.strip('/')}"

    return url
