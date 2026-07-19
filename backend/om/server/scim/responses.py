"""Shared HTTP response helpers for the SCIM routers.

Kept separate from ``api.py`` so the /Users and /Groups sub-routers can reuse it
without a circular import (``api.py`` imports the sub-routers). Request bodies are
parsed by FastAPI's declarative Pydantic params (which accept
``application/scim+json``); a malformed body raises ``RequestValidationError``,
rendered as a SCIM ``400 invalidSyntax`` by :class:`ScimRoute`.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from om.server.scim import constants
from om.server.scim.resources import ScimListResponse


def base_url(request: Request) -> str:
    """Absolute base URL of the SCIM service, e.g. ``https://host/scim/v2``."""
    return str(request.base_url).rstrip("/") + constants.SCIM_ROOT_PATH


def scim_json(
    content: dict[str, Any] | list[Any], status_code: int = 200
) -> JSONResponse:
    return JSONResponse(
        content=content,
        media_type=constants.SCIM_CONTENT_TYPE,
        status_code=status_code,
    )


def list_response(resources: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap already-materialised resources in an unpaginated ListResponse."""
    return ScimListResponse(
        total_results=len(resources),
        start_index=1,
        items_per_page=len(resources),
        resources=resources,
    ).model_dump(by_alias=True)
