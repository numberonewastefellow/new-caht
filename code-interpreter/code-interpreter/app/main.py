from __future__ import annotations

import logging
import subprocess
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from shutil import which
from typing import Final

from fastapi import FastAPI

from app.api.routes import router as api_router
from app.api.routes import set_function_runner, set_session_manager
from app.api.security import BearerAuthMiddleware, log_auth_mode_at_startup
from app.app_configs import (
    EXECUTOR_BACKEND,
    HOST,
    PORT,
    PYTHON_EXECUTOR_DOCKER_IMAGE_REF,
    get_settings,
)
from app.models.schemas import HealthResponse
from app.services.executor_factory import get_executor
from app.services.run_function import FunctionRunner, build_function_runner
from app.services.session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def _ensure_docker_image_available() -> None:
    """Ensure the Docker executor image is available locally.

    This checks if the image exists locally, and if not, attempts to pull it.
    This runs during application startup to ensure the image is ready before
    accepting requests.
    """
    docker_bin = which("docker")
    if not docker_bin:
        logger.warning("Docker binary not found, skipping image check")
        return

    image_with_tag = PYTHON_EXECUTOR_DOCKER_IMAGE_REF

    # Check if image exists locally
    logger.info(f"Checking for Docker image: {image_with_tag}")
    check_result = subprocess.run(
        [docker_bin, "image", "inspect", image_with_tag],
        capture_output=True,
        timeout=10,
        check=False,
    )

    if check_result.returncode == 0:
        logger.info(f"Docker image {image_with_tag} is already available locally")
        return

    # Image doesn't exist, try to pull it
    logger.info(f"Docker image {image_with_tag} not found locally, attempting to pull...")
    try:
        pull_result = subprocess.run(
            [docker_bin, "pull", image_with_tag],
            capture_output=True,
            timeout=300,  # 5 minutes timeout for pulling
            check=False,
        )

        if pull_result.returncode == 0:
            logger.info(f"Successfully pulled {image_with_tag}")
        else:
            error_msg = (
                pull_result.stderr.decode("utf-8", errors="replace") if pull_result.stderr else ""
            )
            logger.error(f"Failed to pull {image_with_tag}: {error_msg}")
            raise RuntimeError(
                f"Docker executor image {image_with_tag} is not available locally "
                f"and could not be pulled. Error: {error_msg}"
            )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"Timeout while pulling Docker image {image_with_tag}. "
            "This may indicate network issues or the image is very large."
        ) from e


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    log_auth_mode_at_startup()

    # Startup: Ensure Docker executor image is available before accepting requests
    if EXECUTOR_BACKEND == "docker":
        logger.info("Ensuring Docker executor image is available...")
        _ensure_docker_image_available()
        logger.info("Docker executor image is ready")

    # Start session manager
    session_mgr = SessionManager()
    set_session_manager(session_mgr)
    session_mgr.start_cleanup_loop()
    logger.info("Session manager started")

    # run_function: single-use sandboxes + warm pool (Docker backend only). Startup
    # removes containers an earlier process left behind, then fills the pool.
    runner: FunctionRunner | None = None
    if EXECUTOR_BACKEND.lower() == "docker":
        runner = build_function_runner(get_settings())
        runner.start()
        set_function_runner(runner)
        pool_state = "enabled" if runner.pool is not None else "disabled"
        logger.info(f"run_function started (warm pool {pool_state})")

    yield

    # Shutdown: destroy pooled run_function containers, then clean up all sessions
    if runner is not None:
        logger.info("Shutting down run_function pool...")
        set_function_runner(None)
        runner.shutdown()
    logger.info("Shutting down session manager...")
    session_mgr.shutdown()
    logger.info("Session manager shut down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Code Interpreter API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> HealthResponse:
        """Health check that verifies the executor backend is operational."""
        result = get_executor().check_health()
        return HealthResponse(status=result.status, message=result.message)

    app.include_router(api_router, prefix="/v1")
    # Bearer-token guard for /v1/* (health + docs stay open). See app/api/security.py.
    app.add_middleware(BearerAuthMiddleware)
    return app


app: Final[FastAPI] = create_app()


def run() -> None:
    """Run the API using Uvicorn.

    This is for local/dev usage. Production deployments should use a process manager
    and configure workers according to their environment.
    """
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")
