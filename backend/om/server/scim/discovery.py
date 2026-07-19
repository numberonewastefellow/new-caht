"""SCIM discovery payloads: /ServiceProviderConfig, /ResourceTypes, /Schemas.

These describe the capabilities and schemas of this service provider (RFC 7643
§5, RFC 7644 §4). They are tenant-neutral and safe to serve publicly so IdPs can
probe the endpoint before a bearer token is configured.
"""

from __future__ import annotations

from typing import Any

from om.server.scim import constants


def _attr(
    name: str,
    attr_type: str = "string",
    *,
    multi_valued: bool = False,
    required: bool = False,
    case_exact: bool = False,
    mutability: str = "readWrite",
    returned: str = "default",
    uniqueness: str = "none",
    sub_attributes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one attribute definition for a Schema resource (RFC 7643 §7)."""
    definition: dict[str, Any] = {
        "name": name,
        "type": attr_type,
        "multiValued": multi_valued,
        "required": required,
        "caseExact": case_exact,
        "mutability": mutability,
        "returned": returned,
        "uniqueness": uniqueness,
    }
    if attr_type == "string":
        definition["caseExact"] = case_exact
    if sub_attributes is not None:
        definition["subAttributes"] = sub_attributes
    return definition


def service_provider_config(base_url: str) -> dict[str, Any]:
    """/ServiceProviderConfig — capabilities of this SCIM SP (RFC 7644 §5)."""
    return {
        "schemas": [constants.SCHEMA_SERVICE_PROVIDER_CONFIG],
        "documentationUri": "https://datatracker.ietf.org/doc/html/rfc7644",
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": constants.MAX_PAGE_SIZE},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": (
                    "Authentication via an admin-issued SCIM bearer token in the "
                    "Authorization header."
                ),
                "specUri": "https://datatracker.ietf.org/doc/html/rfc6750",
                "documentationUri": "https://datatracker.ietf.org/doc/html/rfc7644",
                "primary": True,
            }
        ],
        "meta": {
            "resourceType": "ServiceProviderConfig",
            "location": f"{base_url}/ServiceProviderConfig",
        },
    }


def _user_resource_type(base_url: str) -> dict[str, Any]:
    return {
        "schemas": [constants.SCHEMA_RESOURCE_TYPE],
        "id": constants.RESOURCE_TYPE_USER,
        "name": constants.RESOURCE_TYPE_USER,
        "endpoint": "/Users",
        "description": "SCIM User",
        "schema": constants.SCHEMA_USER,
        "schemaExtensions": [
            {"schema": constants.SCHEMA_ENTERPRISE_USER, "required": False}
        ],
        "meta": {
            "resourceType": "ResourceType",
            "location": f"{base_url}/ResourceTypes/{constants.RESOURCE_TYPE_USER}",
        },
    }


def _group_resource_type(base_url: str) -> dict[str, Any]:
    return {
        "schemas": [constants.SCHEMA_RESOURCE_TYPE],
        "id": constants.RESOURCE_TYPE_GROUP,
        "name": constants.RESOURCE_TYPE_GROUP,
        "endpoint": "/Groups",
        "description": "SCIM Group (mapped to an internal Team)",
        "schema": constants.SCHEMA_GROUP,
        "meta": {
            "resourceType": "ResourceType",
            "location": f"{base_url}/ResourceTypes/{constants.RESOURCE_TYPE_GROUP}",
        },
    }


def resource_types(base_url: str) -> list[dict[str, Any]]:
    return [_user_resource_type(base_url), _group_resource_type(base_url)]


def resource_type(name: str, base_url: str) -> dict[str, Any] | None:
    for entry in resource_types(base_url):
        if entry["id"].lower() == name.lower():
            return entry
    return None


def _user_schema() -> dict[str, Any]:
    name_sub = [
        _attr("formatted"),
        _attr("familyName"),
        _attr("givenName"),
        _attr("middleName"),
        _attr("honorificPrefix"),
        _attr("honorificSuffix"),
    ]
    email_sub = [
        _attr("value"),
        _attr("display"),
        _attr("type"),
        _attr("primary", "boolean"),
    ]
    group_sub = [
        _attr("value", mutability="readOnly"),
        _attr("$ref", "reference", mutability="readOnly"),
        _attr("display", mutability="readOnly"),
        _attr("type", mutability="readOnly"),
    ]
    return {
        "schemas": [constants.SCHEMA_SCHEMA],
        "id": constants.SCHEMA_USER,
        "name": "User",
        "description": "SCIM core User (RFC 7643 §4.1)",
        "attributes": [
            _attr("userName", required=True, uniqueness="server"),
            _attr("name", "complex", sub_attributes=name_sub),
            _attr("displayName"),
            _attr("active", "boolean"),
            _attr("emails", "complex", multi_valued=True, sub_attributes=email_sub),
            _attr(
                "groups",
                "complex",
                multi_valued=True,
                mutability="readOnly",
                sub_attributes=group_sub,
            ),
        ],
        "meta": {"resourceType": "Schema", "location": constants.SCHEMA_USER},
    }


def _group_schema() -> dict[str, Any]:
    member_sub = [
        _attr("value"),
        _attr("$ref", "reference"),
        _attr("display", mutability="immutable"),
        _attr("type"),
    ]
    return {
        "schemas": [constants.SCHEMA_SCHEMA],
        "id": constants.SCHEMA_GROUP,
        "name": "Group",
        "description": "SCIM core Group (RFC 7643 §4.2), mapped to a Team",
        "attributes": [
            _attr("displayName", required=True),
            _attr(
                "members",
                "complex",
                multi_valued=True,
                sub_attributes=member_sub,
            ),
        ],
        "meta": {"resourceType": "Schema", "location": constants.SCHEMA_GROUP},
    }


def schemas() -> list[dict[str, Any]]:
    return [_user_schema(), _group_schema()]


def schema_by_id(schema_id: str) -> dict[str, Any] | None:
    for entry in schemas():
        if entry["id"] == schema_id:
            return entry
    return None
