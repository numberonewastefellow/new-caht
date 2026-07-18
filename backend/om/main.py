import logging
import sys
import traceback
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from typing import cast

import sentry_sdk
import uvicorn
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.clients.openid import BASE_SCOPES
from httpx_oauth.clients.openid import OpenID
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from starlette.types import Lifespan

from om import __version__
from om.auth.schemas import UserCreate
from om.auth.schemas import UserRead
from om.auth.schemas import UserUpdate
from om.auth.users import auth_backend
from om.auth.users import create_onyx_oauth_router
from om.auth.users import fastapi_users
from om.configs.app_configs import APP_API_PREFIX
from om.configs.app_configs import APP_HOST
from om.configs.app_configs import APP_PORT
from om.configs.app_configs import AUTH_RATE_LIMITING_ENABLED
from om.configs.app_configs import AUTH_TYPE
from om.configs.app_configs import LOG_ENDPOINT_LATENCY
from om.configs.app_configs import OAUTH_CLIENT_ID
from om.configs.app_configs import OAUTH_CLIENT_SECRET
from om.configs.app_configs import OAUTH_ENABLED
from om.configs.app_configs import OIDC_SCOPE_OVERRIDE
from om.configs.app_configs import OPENID_CONFIG_URL
from om.configs.app_configs import POSTGRES_API_SERVER_POOL_OVERFLOW
from om.configs.app_configs import POSTGRES_API_SERVER_POOL_SIZE
from om.configs.app_configs import POSTGRES_API_SERVER_READ_ONLY_POOL_OVERFLOW
from om.configs.app_configs import POSTGRES_API_SERVER_READ_ONLY_POOL_SIZE
from om.configs.app_configs import SYSTEM_RECURSION_LIMIT
from om.configs.app_configs import USER_AUTH_SECRET
from om.configs.app_configs import WEB_DOMAIN
from om.configs.constants import AuthType
from om.configs.constants import POSTGRES_WEB_APP_NAME
from om.db.engine.async_sql_engine import get_sqlalchemy_async_engine
from om.db.engine.connection_warmup import warm_up_connections
from om.db.engine.sql_engine import get_session_with_current_tenant
from om.db.engine.sql_engine import SqlEngine
from om.file_store.file_store import get_default_file_store
from om.server.api_key.api import router as api_key_router
from om.server.auth_check import check_ee_router_auth
from om.server.analytics.api import router as analytics_router
from om.server.billing.api import router as billing_router
from om.server.enterprise_settings.api import (
    admin_router as enterprise_settings_admin_router,
)
from om.server.enterprise_settings.api import (
    basic_router as enterprise_settings_router,
)
from om.server.evals.api import router as evals_router
from om.server.license.api import router as license_router
from om.server.manage.standard_answer import router as standard_answer_router
from om.server.middleware.license_enforcement import (
    add_license_enforcement_middleware,
)
from om.server.middleware.tenant_tracking import (
    add_api_server_tenant_id_middleware,
)
from om.server.oauth.api import router as ee_oauth_router
from om.server.query_and_chat.search_backend import router as search_router
from om.server.query_history.api import router as query_history_router
from om.server.reporting.usage_export_api import router as usage_export_router
from om.server.scim.api import scim_router
from om.server.seeding import seed_db
from om.server.tenants.api import router as tenants_router
from om.server.user_group.api import router as user_group_router
from om.utils.encryption import test_encryption
from om.server.documents.cc_pair import router as cc_pair_router
from om.server.documents.connector import router as connector_router
from om.server.documents.credential import router as credential_router
from om.server.documents.document import router as document_router
from om.server.documents.standard_oauth import router as standard_oauth_router
from om.server.features.build.api.api import public_build_router
from om.server.features.build.api.api import router as build_router
from om.server.features.default_assistant.api import (
    router as default_assistant_router,
)
from om.server.features.document_set.api import router as document_set_router
from om.server.features.hierarchy.api import router as hierarchy_router
from om.server.features.input_prompt.api import (
    admin_router as admin_input_prompt_router,
)
from om.server.features.input_prompt.api import (
    basic_router as input_prompt_router,
)
from om.server.features.mcp.api import admin_router as mcp_admin_router
from om.server.features.mcp.api import router as mcp_router
from om.server.features.notifications.api import router as notification_router
from om.server.features.oauth_config.api import (
    admin_router as admin_oauth_config_router,
)
from om.server.features.oauth_config.api import router as oauth_config_router
from om.server.features.password.api import router as password_router
from om.server.features.persona.api import admin_agents_router
from om.server.features.persona.api import admin_router as admin_persona_router
from om.server.features.persona.api import agents_router
from om.server.features.persona.api import basic_router as persona_router
from om.server.features.projects.api import router as projects_router
from om.server.features.tool.api import admin_router as admin_tool_router
from om.server.features.tool.api import router as tool_router
from om.server.features.user_oauth_token.api import router as user_oauth_token_router
from om.server.features.web_search.api import router as web_search_router
from om.server.features.workflow.api import admin_router as admin_workflow_router
from om.server.features.workflow.api import router as workflow_router
from om.server.federated.api import router as federated_router
from om.server.kg.api import admin_router as kg_admin_router
from om.server.manage.administrative import router as admin_router
from om.server.manage.discord_bot.api import router as discord_bot_router
from om.server.manage.embedding.api import admin_router as embedding_admin_router
from om.server.manage.embedding.api import basic_router as embedding_router
from om.server.manage.get_state import router as state_router
from om.server.manage.image_generation.api import (
    admin_router as image_generation_admin_router,
)
from om.server.manage.llm.api import admin_router as llm_admin_router
from om.server.manage.llm.api import basic_router as llm_router
from om.server.manage.search_settings import router as search_settings_router
from om.server.manage.slack_bot import router as slack_bot_management_router
from om.server.manage.users import router as user_router
from om.server.manage.web_search.api import (
    admin_router as web_search_admin_router,
)
from om.server.metrics.postgres_connection_pool import (
    setup_postgres_connection_pool_metrics,
)
from om.server.metrics.prometheus_setup import setup_prometheus_metrics
from om.server.middleware.latency_logging import add_latency_logging_middleware
from om.server.middleware.rate_limiting import close_auth_limiter
from om.server.middleware.rate_limiting import get_auth_rate_limiters
from om.server.middleware.rate_limiting import setup_auth_limiter
from om.server.onyx_api.ingestion import router as onyx_api_router
from om.server.pat.api import router as pat_router
from om.server.query_and_chat.chat_backend import router as chat_router
from om.server.query_and_chat.query_backend import (
    admin_router as admin_query_router,
)
from om.server.query_and_chat.query_backend import basic_router as query_router
from om.server.saml import router as saml_router
from om.server.settings.api import admin_router as settings_admin_router
from om.server.settings.api import basic_router as settings_router
from om.server.token_rate_limits.api import (
    router as token_rate_limit_settings_router,
)
from om.server.utils import BasicAuthenticationError
from om.setup import setup_multitenant_onyx
from om.setup import setup_onyx
from om.tracing.setup import setup_tracing
from om.utils.logger import setup_logger
from om.utils.logger import setup_uvicorn_logger
from om.utils.middleware import add_endpoint_context_middleware
from om.utils.middleware import add_onyx_request_id_middleware
from om.utils.telemetry import get_or_generate_uuid
from om.utils.telemetry import optional_telemetry
from om.utils.telemetry import RecordType
from shared_configs.configs import CORS_ALLOWED_ORIGIN
from shared_configs.configs import MULTI_TENANT
from shared_configs.configs import POSTGRES_DEFAULT_SCHEMA
from shared_configs.configs import SENTRY_DSN
from shared_configs.contextvars import CURRENT_TENANT_ID_CONTEXTVAR

warnings.filterwarnings(
    "ignore", category=ResourceWarning, message=r"Unclosed client session"
)
warnings.filterwarnings(
    "ignore", category=ResourceWarning, message=r"Unclosed connector"
)

logger = setup_logger()

file_handlers = [
    h for h in logger.logger.handlers if isinstance(h, logging.FileHandler)
]

setup_uvicorn_logger(shared_file_handlers=file_handlers)


def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        logger.error(
            f"Unexpected exception type in validation_exception_handler - {type(exc)}"
        )
        raise exc

    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    logger.exception(f"{request}: {exc_str}")
    content = {"status_code": 422, "message": exc_str, "data": None}
    return JSONResponse(content=content, status_code=422)


def value_error_handler(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ValueError):
        logger.error(f"Unexpected exception type in value_error_handler - {type(exc)}")
        raise exc

    try:
        raise (exc)
    except Exception:
        # log stacktrace
        logger.exception("ValueError")
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


def use_route_function_names_as_operation_ids(app: FastAPI) -> None:
    """
    OpenAPI generation defaults to naming the operation with the
    function + route + HTTP method, which usually looks very redundant.

    This function changes the operation IDs to be just the function name.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


def include_router_with_global_prefix_prepended(
    application: FastAPI, router: APIRouter, **kwargs: Any
) -> None:
    """Adds the global prefix to all routes in the router."""
    processed_global_prefix = f"/{APP_API_PREFIX.strip('/')}" if APP_API_PREFIX else ""

    passed_in_prefix = cast(str | None, kwargs.get("prefix"))
    if passed_in_prefix:
        final_prefix = f"{processed_global_prefix}/{passed_in_prefix.strip('/')}"
    else:
        final_prefix = f"{processed_global_prefix}"
    final_kwargs: dict[str, Any] = {
        **kwargs,
        "prefix": final_prefix,
    }

    application.include_router(router, **final_kwargs)


def include_auth_router_with_prefix(
    application: FastAPI,
    router: APIRouter,
    prefix: str | None = None,
    tags: list[str] | None = None,
) -> None:
    """Wrapper function to include an 'auth' router with prefix + rate-limiting dependencies."""
    final_tags = tags or ["auth"]
    include_router_with_global_prefix_prepended(
        application,
        router,
        prefix=prefix,
        tags=final_tags,
        dependencies=get_auth_rate_limiters(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    # Set recursion limit
    from om.auth.users import verify_auth_setting as _impl_verify_auth_setting
    if SYSTEM_RECURSION_LIMIT is not None:
        sys.setrecursionlimit(SYSTEM_RECURSION_LIMIT)
        logger.notice(f"System recursion limit set to {SYSTEM_RECURSION_LIMIT}")

    SqlEngine.set_app_name(POSTGRES_WEB_APP_NAME)

    SqlEngine.init_engine(
        pool_size=POSTGRES_API_SERVER_POOL_SIZE,
        max_overflow=POSTGRES_API_SERVER_POOL_OVERFLOW,
    )
    SqlEngine.get_engine()

    SqlEngine.init_readonly_engine(
        pool_size=POSTGRES_API_SERVER_READ_ONLY_POOL_SIZE,
        max_overflow=POSTGRES_API_SERVER_READ_ONLY_POOL_OVERFLOW,
    )

    # Register pool metrics now that engines are created.
    # HTTP instrumentation is set up earlier in get_application() since it
    # adds middleware (which Starlette forbids after the app has started).
    setup_postgres_connection_pool_metrics(
        engines={
            "sync": SqlEngine.get_engine(),
            "async": get_sqlalchemy_async_engine(),
            "readonly": SqlEngine.get_readonly_engine(),
        },
    )

    verify_auth = _impl_verify_auth_setting

    # Will throw exception if an issue is found
    verify_auth()

    if OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET:
        logger.notice("Both OAuth Client ID and Secret are configured.")

    # Initialize tracing if credentials are provided
    setup_tracing()

    # fill up Postgres connection pools
    await warm_up_connections()

    if not MULTI_TENANT:
        # We cache this at the beginning so there is no delay in the first telemetry
        CURRENT_TENANT_ID_CONTEXTVAR.set(POSTGRES_DEFAULT_SCHEMA)
        get_or_generate_uuid()

        # If we are multi-tenant, we need to only set up initial public tables
        with get_session_with_current_tenant() as db_session:
            setup_onyx(db_session, POSTGRES_DEFAULT_SCHEMA)
            # set up the file store (e.g. create bucket if needed). On multi-tenant,
            # this is done via IaC
            get_default_file_store().initialize()
    else:
        setup_multitenant_onyx()

    if not MULTI_TENANT:
        # don't emit a metric for every pod rollover/restart
        optional_telemetry(
            record_type=RecordType.VERSION, data={"version": __version__}
        )

    if AUTH_RATE_LIMITING_ENABLED:
        await setup_auth_limiter()

    # seed the environment with LLMs, Assistants, etc. based on an optional environment
    # variable. Used to automate deployment for multiple environments. (Merged from the
    # former ee/om/main.py lifespan, which wrapped this one purely to append this call.)
    seed_db()

    yield

    SqlEngine.reset_engine()

    if AUTH_RATE_LIMITING_ENABLED:
        await close_auth_limiter()


def log_http_error(request: Request, exc: Exception) -> JSONResponse:
    status_code = getattr(exc, "status_code", 500)

    if isinstance(exc, BasicAuthenticationError):
        # For BasicAuthenticationError, just log a brief message without stack trace
        # (almost always spammy)
        logger.debug(f"Authentication failed: {str(exc)}")

    elif status_code == 404 and request.url.path == "/metrics":
        # Log 404 errors for the /metrics endpoint with debug level
        logger.debug(f"404 error for /metrics endpoint: {str(exc)}")

    elif status_code >= 400:
        error_msg = f"{str(exc)}\n"
        error_msg += "".join(traceback.format_tb(exc.__traceback__))
        logger.error(error_msg)

    detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


def get_application(lifespan_override: Lifespan | None = None) -> FastAPI:
    # Merged from the former ee/om/main.py: fail fast at startup if the encryption key
    # is misconfigured, rather than at first use.
    test_encryption()

    application = FastAPI(
        title="VertualAI Backend",
        version=__version__,
        description="VertualAI API for AI-powered chat with search, document indexing, agents, actions, and more",
        servers=[
            {"url": f"{WEB_DOMAIN.rstrip('/')}/api", "description": "VertualAI API Server"}
        ],
        lifespan=lifespan_override or lifespan,
    )
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            traces_sample_rate=0.1,
        )
        logger.info("Sentry initialized")
    else:
        logger.debug("Sentry DSN not provided, skipping Sentry initialization")

    application.add_exception_handler(status.HTTP_400_BAD_REQUEST, log_http_error)
    application.add_exception_handler(status.HTTP_401_UNAUTHORIZED, log_http_error)
    application.add_exception_handler(status.HTTP_403_FORBIDDEN, log_http_error)
    application.add_exception_handler(status.HTTP_404_NOT_FOUND, log_http_error)
    application.add_exception_handler(
        status.HTTP_500_INTERNAL_SERVER_ERROR, log_http_error
    )

    include_router_with_global_prefix_prepended(application, password_router)
    include_router_with_global_prefix_prepended(application, chat_router)
    include_router_with_global_prefix_prepended(application, query_router)
    include_router_with_global_prefix_prepended(application, document_router)
    include_router_with_global_prefix_prepended(application, user_router)
    include_router_with_global_prefix_prepended(application, admin_query_router)
    include_router_with_global_prefix_prepended(application, admin_router)
    include_router_with_global_prefix_prepended(application, connector_router)
    include_router_with_global_prefix_prepended(application, credential_router)
    include_router_with_global_prefix_prepended(application, input_prompt_router)
    include_router_with_global_prefix_prepended(application, admin_input_prompt_router)
    include_router_with_global_prefix_prepended(application, cc_pair_router)
    include_router_with_global_prefix_prepended(application, projects_router)
    include_router_with_global_prefix_prepended(application, public_build_router)
    include_router_with_global_prefix_prepended(application, build_router)
    include_router_with_global_prefix_prepended(application, document_set_router)
    include_router_with_global_prefix_prepended(application, hierarchy_router)
    include_router_with_global_prefix_prepended(application, search_settings_router)
    include_router_with_global_prefix_prepended(
        application, slack_bot_management_router
    )
    include_router_with_global_prefix_prepended(application, discord_bot_router)
    include_router_with_global_prefix_prepended(application, persona_router)
    include_router_with_global_prefix_prepended(application, admin_persona_router)
    include_router_with_global_prefix_prepended(application, agents_router)
    include_router_with_global_prefix_prepended(application, admin_agents_router)
    include_router_with_global_prefix_prepended(application, default_assistant_router)
    include_router_with_global_prefix_prepended(application, notification_router)
    include_router_with_global_prefix_prepended(application, tool_router)
    include_router_with_global_prefix_prepended(application, admin_tool_router)
    include_router_with_global_prefix_prepended(application, oauth_config_router)
    include_router_with_global_prefix_prepended(application, admin_oauth_config_router)
    include_router_with_global_prefix_prepended(application, user_oauth_token_router)
    include_router_with_global_prefix_prepended(application, state_router)
    include_router_with_global_prefix_prepended(application, onyx_api_router)
    include_router_with_global_prefix_prepended(application, settings_router)
    include_router_with_global_prefix_prepended(application, settings_admin_router)
    include_router_with_global_prefix_prepended(application, llm_admin_router)
    include_router_with_global_prefix_prepended(application, kg_admin_router)
    include_router_with_global_prefix_prepended(application, llm_router)
    include_router_with_global_prefix_prepended(
        application, image_generation_admin_router
    )
    include_router_with_global_prefix_prepended(application, embedding_admin_router)
    include_router_with_global_prefix_prepended(application, embedding_router)
    include_router_with_global_prefix_prepended(application, web_search_router)
    include_router_with_global_prefix_prepended(application, web_search_admin_router)
    include_router_with_global_prefix_prepended(
        application, token_rate_limit_settings_router
    )
    include_router_with_global_prefix_prepended(application, api_key_router)
    include_router_with_global_prefix_prepended(application, standard_oauth_router)
    include_router_with_global_prefix_prepended(application, federated_router)
    include_router_with_global_prefix_prepended(application, mcp_router)
    include_router_with_global_prefix_prepended(application, mcp_admin_router)
    include_router_with_global_prefix_prepended(application, workflow_router)
    include_router_with_global_prefix_prepended(application, admin_workflow_router)

    include_router_with_global_prefix_prepended(application, pat_router)

    # --- Merged from the former ee/om/main.py (EE removal, Stage 2.2) ---------------
    # NOTE: query_router, cc_pair_router and token_rate_limit_settings_router are NOT
    # re-included here. The EE overrides of those three modules were merged into their
    # MIT counterparts, so the EE routes now live on the very same router objects that
    # are already included above. Including them again would double-register every route.

    # RBAC / group access control
    include_router_with_global_prefix_prepended(application, user_group_router)
    # Analytics endpoints
    include_router_with_global_prefix_prepended(application, analytics_router)
    include_router_with_global_prefix_prepended(application, query_history_router)
    include_router_with_global_prefix_prepended(application, search_router)
    include_router_with_global_prefix_prepended(application, standard_answer_router)
    include_router_with_global_prefix_prepended(application, ee_oauth_router)
    include_router_with_global_prefix_prepended(application, evals_router)

    # Global settings
    include_router_with_global_prefix_prepended(
        application, enterprise_settings_admin_router
    )
    include_router_with_global_prefix_prepended(application, enterprise_settings_router)
    include_router_with_global_prefix_prepended(application, usage_export_router)
    # License management
    include_router_with_global_prefix_prepended(application, license_router)

    # Unified billing API - always registered so frontend doesn't get 404.
    # Works for both self-hosted and cloud deployments.
    include_router_with_global_prefix_prepended(application, billing_router)

    if MULTI_TENANT:
        # Tenant management
        include_router_with_global_prefix_prepended(application, tenants_router)

    # SCIM 2.0 - protocol endpoints (unauthenticated by session auth; they use their own
    # SCIM bearer token auth). Not behind APP_API_PREFIX because IdPs expect
    # /scim/v2/... directly.
    application.include_router(scim_router)

    if AUTH_TYPE == AuthType.BASIC or AUTH_TYPE == AuthType.CLOUD:
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_auth_router(auth_backend),
            prefix="/auth",
        )

        include_auth_router_with_prefix(
            application,
            fastapi_users.get_register_router(UserRead, UserCreate),
            prefix="/auth",
        )

        include_auth_router_with_prefix(
            application,
            fastapi_users.get_reset_password_router(),
            prefix="/auth",
        )
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_verify_router(UserRead),
            prefix="/auth",
        )
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_users_router(UserRead, UserUpdate),
            prefix="/users",
        )

    # Merged from the former ee/om/main.py. The MIT Google-OAuth block below covers
    # GOOGLE_OAUTH and BASIC-with-OAuth but deliberately NOT CLOUD, so CLOUD needs its
    # own registration. For Google OAuth, refresh tokens are requested by:
    #   1. adding the right scopes
    #   2. configuring OAuth in Google Cloud Console to allow offline access
    if AUTH_TYPE == AuthType.CLOUD:
        cloud_oauth_client = GoogleOAuth2(
            OAUTH_CLIENT_ID,
            OAUTH_CLIENT_SECRET,
            # Use standard scopes that include profile and email
            scopes=["openid", "email", "profile"],
        )
        include_auth_router_with_prefix(
            application,
            create_onyx_oauth_router(
                cloud_oauth_client,
                auth_backend,
                USER_AUTH_SECRET,
                associate_by_email=True,
                is_verified_by_default=True,
                # Points the user back to the login page
                redirect_url=f"{WEB_DOMAIN}/auth/oauth/callback",
            ),
            prefix="/auth/oauth",
        )

        # Need basic auth router for `logout` endpoint
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_logout_router(auth_backend),
            prefix="/auth",
        )

    # Register Google OAuth when AUTH_TYPE is GOOGLE_OAUTH, or when
    # AUTH_TYPE is BASIC and OAuth credentials are configured
    if AUTH_TYPE == AuthType.GOOGLE_OAUTH or (
        AUTH_TYPE == AuthType.BASIC and OAUTH_ENABLED
    ):
        oauth_client = GoogleOAuth2(
            OAUTH_CLIENT_ID,
            OAUTH_CLIENT_SECRET,
            scopes=["openid", "email", "profile"],
        )
        include_auth_router_with_prefix(
            application,
            create_onyx_oauth_router(
                oauth_client,
                auth_backend,
                USER_AUTH_SECRET,
                associate_by_email=True,
                is_verified_by_default=True,
                redirect_url=f"{WEB_DOMAIN}/auth/oauth/callback",
            ),
            prefix="/auth/oauth",
        )

        # Need logout router for GOOGLE_OAUTH only (BASIC already has it from above)
        if AUTH_TYPE == AuthType.GOOGLE_OAUTH:
            include_auth_router_with_prefix(
                application,
                fastapi_users.get_logout_router(auth_backend),
                prefix="/auth",
            )

    if AUTH_TYPE == AuthType.OIDC:
        # Ensure we request offline_access for refresh tokens
        try:
            oidc_scopes = list(OIDC_SCOPE_OVERRIDE or BASE_SCOPES)
            if "offline_access" not in oidc_scopes:
                oidc_scopes.append("offline_access")
        except Exception as e:
            logger.warning(f"Error configuring OIDC scopes: {e}")
            # Fall back to default scopes if there's an error
            oidc_scopes = BASE_SCOPES

        include_auth_router_with_prefix(
            application,
            create_onyx_oauth_router(
                OpenID(
                    OAUTH_CLIENT_ID,
                    OAUTH_CLIENT_SECRET,
                    OPENID_CONFIG_URL,
                    # Use the configured scopes
                    base_scopes=oidc_scopes,
                ),
                auth_backend,
                USER_AUTH_SECRET,
                associate_by_email=True,
                is_verified_by_default=True,
                redirect_url=f"{WEB_DOMAIN}/auth/oidc/callback",
            ),
            prefix="/auth/oidc",
        )

        # need basic auth router for `logout` endpoint
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_auth_router(auth_backend),
            prefix="/auth",
        )

    elif AUTH_TYPE == AuthType.SAML:
        include_auth_router_with_prefix(
            application,
            saml_router,
        )

    if (
        AUTH_TYPE == AuthType.CLOUD
        or AUTH_TYPE == AuthType.BASIC
        or AUTH_TYPE == AuthType.GOOGLE_OAUTH
        or AUTH_TYPE == AuthType.OIDC
    ):
        # Add refresh token endpoint for OAuth as well
        include_auth_router_with_prefix(
            application,
            fastapi_users.get_refresh_router(auth_backend),
            prefix="/auth",
        )

    application.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )

    application.add_exception_handler(ValueError, value_error_handler)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWED_ORIGIN,  # Configurable via environment variable
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if LOG_ENDPOINT_LATENCY:
        add_latency_logging_middleware(application, logger)

    add_onyx_request_id_middleware(application, "API", logger)

    # Set endpoint context for per-endpoint DB pool attribution metrics.
    # Must be registered after all routes are added.
    add_endpoint_context_middleware(application)

    # HTTP request metrics (latency histograms, in-progress gauge, slow request
    # counter). Must be called here — before the app starts — because the
    # instrumentator adds middleware via app.add_middleware().
    setup_prometheus_metrics(application)

    # Merged from the former ee/om/main.py.
    if MULTI_TENANT:
        add_api_server_tenant_id_middleware(application, logger)
    else:
        # License enforcement middleware for self-hosted deployments only.
        # Checks LICENSE_ENFORCEMENT_ENABLED at runtime (can be toggled without a
        # restart). MT deployments use control-plane gating via is_tenant_gated().
        add_license_enforcement_middleware(application, logger)

    # Ensure all routes have auth enabled or are explicitly marked as public
    check_ee_router_auth(application)

    use_route_function_names_as_operation_ids(application)

    return application


# NOTE: needs to be outside of the `if __name__ == "__main__"` block so that the
# app is exportable
app = get_application


if __name__ == "__main__":
    logger.notice(
        f"Starting VertualAi Backend version {__version__} on http://{APP_HOST}:{str(APP_PORT)}/"
    )

    logger.notice("Running Enterprise Edition")

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
