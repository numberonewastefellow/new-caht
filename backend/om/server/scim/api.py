"""SCIM 2.0 router assembly and public discovery endpoints.

``scim_router`` is mounted at ``/scim/v2`` **without** the global API prefix
(main.py: ``application.include_router(scim_router)``) because IdPs expect the
base URL to end in ``/scim/v2``.

Discovery endpoints (/ServiceProviderConfig, /ResourceTypes, /Schemas) are public
(listed in ``auth_check`` public specs) so IdPs can probe before a token exists.
Provisioning endpoints (/Users, /Groups) are guarded by ``verify_scim_token`` and
are added by the users/groups sub-routers.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import JSONResponse

from om.server.scim import constants
from om.server.scim import discovery
from om.server.scim.errors import ScimError
from om.server.scim.errors import ScimRoute
from om.server.scim.groups_api import groups_router
from om.server.scim.responses import base_url
from om.server.scim.responses import list_response
from om.server.scim.responses import scim_json
from om.server.scim.users_api import users_router

scim_router = APIRouter(prefix=constants.SCIM_ROOT_PATH, route_class=ScimRoute)


# --------------------------------------------------------------------------
# Discovery (public)
# --------------------------------------------------------------------------
@scim_router.get("/ServiceProviderConfig")
def get_service_provider_config(request: Request) -> JSONResponse:
    return scim_json(discovery.service_provider_config(base_url(request)))


@scim_router.get("/ResourceTypes")
def get_resource_types(request: Request) -> JSONResponse:
    return scim_json(list_response(discovery.resource_types(base_url(request))))


@scim_router.get("/ResourceTypes/{resource_id}")
def get_resource_type(resource_id: str, request: Request) -> JSONResponse:
    entry = discovery.resource_type(resource_id, base_url(request))
    if entry is None:
        raise ScimError.not_found(f"ResourceType '{resource_id}' not found.")
    return scim_json(entry)


@scim_router.get("/Schemas")
def get_schemas(request: Request) -> JSONResponse:
    return scim_json(list_response(discovery.schemas()))


@scim_router.get("/Schemas/{schema_id}")
def get_schema(schema_id: str, request: Request) -> JSONResponse:
    entry = discovery.schema_by_id(schema_id)
    if entry is None:
        raise ScimError.not_found(f"Schema '{schema_id}' not found.")
    return scim_json(entry)


# --------------------------------------------------------------------------
# Provisioning (bearer-token protected) — mounted from sub-routers.
# --------------------------------------------------------------------------
scim_router.include_router(users_router)
scim_router.include_router(groups_router)
