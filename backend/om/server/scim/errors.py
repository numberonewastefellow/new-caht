"""SCIM error handling (RFC 7644 §3.12).

A single :class:`ScimError` exception carries an HTTP status, an optional
``scimType`` keyword and a human-readable detail. :class:`ScimRoute` is a custom
FastAPI route class that renders any :class:`ScimError` (and any unexpected
exception) as an ``application/scim+json`` error body — this keeps all SCIM error
formatting inside the SCIM package with **no edits to main.py** (routers cannot
register exception handlers; a route class can).
"""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Coroutine
from typing import Any

from fastapi import Request
from fastapi import Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from om.server.scim import constants
from om.server.scim.resources import ScimErrorResponse
from om.utils.logger import setup_logger

logger = setup_logger()


class ScimError(Exception):
    """Raised anywhere in the SCIM stack to return a SCIM-formatted error."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        scim_type: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.scim_type = scim_type

    # --- Convenience constructors for the common cases ---
    @classmethod
    def unauthorized(cls, detail: str = "Invalid or missing SCIM token.") -> "ScimError":
        return cls(401, detail)

    @classmethod
    def not_found(cls, detail: str = "Resource not found.") -> "ScimError":
        return cls(404, detail)

    @classmethod
    def uniqueness(cls, detail: str) -> "ScimError":
        return cls(409, detail, constants.SCIM_TYPE_UNIQUENESS)

    @classmethod
    def invalid_value(cls, detail: str) -> "ScimError":
        return cls(400, detail, constants.SCIM_TYPE_INVALID_VALUE)

    @classmethod
    def invalid_syntax(cls, detail: str) -> "ScimError":
        return cls(400, detail, constants.SCIM_TYPE_INVALID_SYNTAX)

    @classmethod
    def invalid_filter(cls, detail: str) -> "ScimError":
        return cls(400, detail, constants.SCIM_TYPE_INVALID_FILTER)

    @classmethod
    def invalid_path(cls, detail: str) -> "ScimError":
        return cls(400, detail, constants.SCIM_TYPE_INVALID_PATH)

    @classmethod
    def no_target(cls, detail: str) -> "ScimError":
        return cls(400, detail, constants.SCIM_TYPE_NO_TARGET)

    @classmethod
    def mutability(cls, detail: str) -> "ScimError":
        return cls(400, detail, constants.SCIM_TYPE_MUTABILITY)


def scim_error_response(error: ScimError) -> JSONResponse:
    """Render a :class:`ScimError` as an ``application/scim+json`` response."""
    body = ScimErrorResponse(
        status=str(error.status_code),
        scim_type=error.scim_type,
        detail=error.detail,
    )
    headers = {}
    if error.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        status_code=error.status_code,
        content=body.model_dump(by_alias=True, exclude_none=True),
        media_type=constants.SCIM_CONTENT_TYPE,
        headers=headers,
    )


class ScimRoute(APIRoute):
    """Route class that renders SCIM errors uniformly for the whole router."""

    def get_route_handler(
        self,
    ) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_handler = super().get_route_handler()

        async def scim_route_handler(request: Request) -> Response:
            try:
                return await original_handler(request)
            except ScimError as exc:
                return scim_error_response(exc)
            except RequestValidationError as exc:
                # Malformed SCIM request body → SCIM 400 invalidSyntax.
                return scim_error_response(
                    ScimError.invalid_syntax(f"Malformed request: {exc.errors()}")
                )
            except Exception:
                # Never leak internals to an external IdP; log with context.
                logger.exception(
                    f"Unhandled error in SCIM route {request.method} {request.url.path}"
                )
                return scim_error_response(
                    ScimError(500, "Internal server error.")
                )

        return scim_route_handler
