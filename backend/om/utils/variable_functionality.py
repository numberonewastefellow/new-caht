import functools
import importlib
from typing import Any
from typing import TypeVar

from om.configs.app_configs import API_SERVER_HOST
from om.configs.app_configs import API_SERVER_PROTOCOL
from om.configs.app_configs import API_SERVER_URL_OVERRIDE_FOR_HTTP_REQUESTS
from om.configs.app_configs import APP_API_PREFIX
from om.configs.app_configs import APP_PORT
from om.configs.app_configs import DEV_MODE
from om.utils.logger import setup_logger

logger = setup_logger()


class OmVersion:
    """Vestigial. There is exactly one edition now; EE is unconditional.

    Kept only so the remaining `global_version.is_ee_version()` call sites keep working
    until they are removed (Stage 2.4). It always reports True, which is what a live
    EE deployment already reported.
    """

    def set_ee(self) -> None:
        return None

    def is_ee_version(self) -> bool:
        return True


global_version = OmVersion()


def set_is_ee_based_on_env_variable() -> None:
    """No-op. EE is no longer conditional on the environment."""
    return None


@functools.lru_cache(maxsize=128)
def fetch_versioned_implementation(module: str, attribute: str) -> Any:
    """Fetch `attribute` from `module`.

    This used to prefix `ee.` and fall back to the MIT module on ModuleNotFoundError.
    The EE tree is gone -- its implementations were merged into these very modules -- so
    the only remaining resolution is the direct one.

    NOTE: the `ee.` prefixing could not simply be left in place. With `backend/ee/`
    deleted, `import_module("ee.om.x")` raises ModuleNotFoundError("No module named
    'ee'"), and the old fallback guard was `if "ee.om" not in str(e): raise` -- which
    does NOT match that message, so every dispatch call would have re-raised instead of
    falling back. Silent on import, fatal on first use.
    """
    logger.debug("Fetching implementation for %s.%s", module, attribute)
    return getattr(importlib.import_module(module), attribute)


T = TypeVar("T")


def fetch_versioned_implementation_with_fallback(
    module: str, attribute: str, fallback: T
) -> T:
    """
    Attempts to fetch a versioned implementation of a specified attribute from a given module.
    If the attempt fails (e.g., due to an import error or missing attribute), the function logs
    a warning and returns the provided fallback implementation.

    Args:
        module (str): The name of the module from which to fetch the attribute.
        attribute (str): The name of the attribute to fetch from the module.
        fallback (T): The fallback implementation to return if fetching the attribute fails.

    Returns:
        T: The fetched implementation if successful, otherwise the provided fallback.
    """
    try:
        return fetch_versioned_implementation(module, attribute)
    except Exception:
        return fallback


def noop_fallback(*args: Any, **kwargs: Any) -> None:
    """
    A no-op (no operation) fallback function that accepts any arguments but does nothing.
    This is often used as a default or placeholder callback function.

    Args:
        *args (Any): Positional arguments, which are ignored.
        **kwargs (Any): Keyword arguments, which are ignored.

    Returns:
        None
    """


def fetch_ee_implementation_or_noop(
    module: str, attribute: str, noop_return_value: Any = None  # noqa: ARG001
) -> Any:
    """Fetch `attribute` from `module`.

    The no-op branch is gone: it only ever fired when EE was disabled, and EE is now
    unconditional. A live EE deployment always took the fetch path, so this preserves
    production behavior exactly. `noop_return_value` is retained (unused) so the ~30
    call sites that pass it keep type-checking until Stage 2.3 rewrites them.
    """
    try:
        return fetch_versioned_implementation(module, attribute)
    except Exception as e:
        logger.error(f"Failed to fetch implementation for {module}.{attribute}: {e}")
        raise


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
