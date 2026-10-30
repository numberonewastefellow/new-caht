"""Request authentication, tenant scoping, and execution admission control.

* **Auth** — every ``/v1/*`` route requires ``Authorization: Bearer <token>`` where the
  token equals ``CODE_INTERPRETER_API_TOKEN``. The comparison is constant time over
  SHA-256 digests (the same pattern as ``backend/om/auth/api_key.py``). With no token
  configured the service fails closed (503) unless the dev-only escape hatch
  ``CODE_INTERPRETER_ALLOW_UNAUTHENTICATED=true`` is set.
* **Tenancy** — the caller names its tenant in ``X-OM-Tenant``. Sessions and files
  record it at creation and are invisible (404) to every other tenant.
* **Admission** — :class:`ExecutionLimiter` bounds concurrent executions plus a wait
  queue; overflow is answered with 503 + ``Retry-After``.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import threading
from collections.abc import Callable

from fastapi import Header, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app import app_configs

logger = logging.getLogger(__name__)

TENANT_HEADER = "X-OM-Tenant"
# Bucket for callers that send no tenant header. It never equals a real tenant id
# (those can't start with "__"), so header-less callers can't see tenant data.
UNSCOPED_TENANT = "__unscoped__"
_TENANT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,127}$")

_BEARER_PREFIX = "bearer "


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def _extract_bearer_token(authorization: str | None) -> str | None:
    """Return the token from an ``Authorization: Bearer <token>`` header, or None."""
    if not authorization:
        return None
    if authorization[: len(_BEARER_PREFIX)].lower() != _BEARER_PREFIX:
        return None
    token = authorization[len(_BEARER_PREFIX) :].strip()
    return token or None


def tokens_match(presented: str, expected: str) -> bool:
    """Constant-time comparison of two tokens via their SHA-256 digests."""
    return hmac.compare_digest(_digest(presented), _digest(expected))


# Template placeholder (env.prod.template ships `CODE_INTERPRETER_API_TOKEN=change-me`).
# A copied-but-unedited template must not become a well-known shared secret.
_PLACEHOLDER_PREFIX = "change-me"


def _configured_token() -> str:
    token = app_configs.CODE_INTERPRETER_API_TOKEN
    if token.lower().startswith(_PLACEHOLDER_PREFIX):
        return ""
    return token


def auth_mode() -> str:
    """'token' | 'unauthenticated' (dev override) | 'misconfigured' (fail closed)."""
    if _configured_token():
        return "token"
    if app_configs.CODE_INTERPRETER_ALLOW_UNAUTHENTICATED:
        return "unauthenticated"
    return "misconfigured"


def log_auth_mode_at_startup() -> None:
    mode = auth_mode()
    if mode == "token":
        logger.info("Code-interpreter API auth: bearer token required on /v1/*")
    elif mode == "unauthenticated":
        logger.warning(
            "!!! CODE_INTERPRETER_ALLOW_UNAUTHENTICATED=true and no "
            "CODE_INTERPRETER_API_TOKEN is set: /v1/* is OPEN to anyone who can reach "
            "this port. This is a DEV-ONLY escape hatch; never use it in production. !!!"
        )
    else:
        logger.error(
            "!!! CODE_INTERPRETER_API_TOKEN is not set (or is the 'change-me' "
            "placeholder): every /v1/* request will be rejected with 503 (fail closed). "
            "Set CODE_INTERPRETER_API_TOKEN on this service AND on every backend "
            "service that calls it. !!!"
        )


def check_api_token(authorization: str | None) -> None:
    """Raise ``HTTPException`` unless the request may use ``/v1/*``."""
    mode = auth_mode()
    if mode == "unauthenticated":
        return
    if mode == "misconfigured":
        logger.error(
            "Rejecting /v1 request: CODE_INTERPRETER_API_TOKEN is not configured (fail closed)"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Code interpreter API token is not configured on the service.",
        )

    presented = _extract_bearer_token(authorization)
    if presented is None or not tokens_match(presented, _configured_token()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _is_protected_path(path: str) -> bool:
    return path == "/v1" or path.startswith("/v1/")


class BearerAuthMiddleware:
    """Pure-ASGI guard for ``/v1/*``.

    Runs before routing and before any request body is read, so an unauthenticated
    caller can't make the service buffer a large multipart upload. Pure ASGI (not
    ``BaseHTTPMiddleware``) so SSE streaming and disconnect detection are untouched.
    Paths outside ``/v1`` (``/health``, docs) stay open.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and _is_protected_path(scope.get("path", "")):
            authorization: str | None = None
            for name, value in scope.get("headers") or []:
                if name.lower() == b"authorization":
                    authorization = value.decode("latin-1")
                    break
            try:
                check_api_token(authorization)
            except HTTPException as exc:
                response = JSONResponse(
                    {"detail": exc.detail},
                    status_code=exc.status_code,
                    headers=exc.headers,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def get_tenant_id(
    x_om_tenant: str | None = Header(default=None, alias=TENANT_HEADER),  # noqa: B008
) -> str:
    """FastAPI dependency returning the caller's tenant id (validated)."""
    if x_om_tenant is None or not x_om_tenant.strip():
        return UNSCOPED_TENANT
    tenant = x_om_tenant.strip()
    if not _TENANT_RE.match(tenant):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {TENANT_HEADER} header.",
        )
    return tenant


# ----------------------------------------------------------------------------
# Admission control
# ----------------------------------------------------------------------------


class CapacityExceededError(Exception):
    """Raised when the execution queue is full or the queue wait timed out."""


class ExecutionSlot:
    """A held execution slot; :meth:`release` is idempotent."""

    def __init__(self, release_fn: Callable[[], None]) -> None:
        self._release_fn = release_fn
        self._released = False
        self._lock = threading.Lock()

    def release(self) -> None:
        with self._lock:
            if self._released:
                return
            self._released = True
        self._release_fn()


class ExecutionLimiter:
    """Bounded concurrency (``max_workers``) plus a bounded wait queue (``max_queue``).

    ``acquire`` blocks (in a worker thread) for up to ``queue_timeout_sec`` waiting for
    a free worker. A request that arrives when ``max_workers + max_queue`` requests are
    already admitted is rejected immediately.
    """

    def __init__(self, max_workers: int, max_queue: int, queue_timeout_sec: float) -> None:
        self.max_workers = max(1, max_workers)
        self.max_queue = max(0, max_queue)
        self.queue_timeout_sec = queue_timeout_sec
        self._sem = threading.BoundedSemaphore(self.max_workers)
        self._lock = threading.Lock()
        self._admitted = 0

    @property
    def admitted(self) -> int:
        with self._lock:
            return self._admitted

    def acquire(self) -> ExecutionSlot:
        with self._lock:
            if self._admitted >= self.max_workers + self.max_queue:
                raise CapacityExceededError("execution queue is full")
            self._admitted += 1
        if not self._sem.acquire(timeout=self.queue_timeout_sec):
            with self._lock:
                self._admitted -= 1
            raise CapacityExceededError("timed out waiting for an execution slot")
        return ExecutionSlot(self._release)

    def _release(self) -> None:
        self._sem.release()
        with self._lock:
            self._admitted -= 1


def capacity_http_exception(exc: CapacityExceededError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Code interpreter is at capacity ({exc}); retry later.",
        headers={"Retry-After": str(app_configs.EXECUTION_RETRY_AFTER_SEC)},
    )


_limiter: ExecutionLimiter | None = None
_limiter_lock = threading.Lock()


def get_execution_limiter() -> ExecutionLimiter:
    global _limiter
    with _limiter_lock:
        if _limiter is None:
            _limiter = ExecutionLimiter(
                max_workers=app_configs.EXECUTION_MAX_WORKERS,
                max_queue=app_configs.EXECUTION_MAX_QUEUE,
                queue_timeout_sec=app_configs.EXECUTION_QUEUE_TIMEOUT_SEC,
            )
        return _limiter


def set_execution_limiter(limiter: ExecutionLimiter | None) -> None:
    """Replace the process-wide limiter (tests)."""
    global _limiter
    with _limiter_lock:
        _limiter = limiter
