"""Pydantic models for SCIM 2.0 wire representations (RFC 7643 / RFC 7644).

These model the JSON on the wire. Field names use SCIM's canonical camelCase
where that is a valid Python identifier; the two protocol containers
(``Resources``, ``Operations``) and ``$ref`` are exposed via aliases. All models
tolerate unknown attributes on input (``extra="ignore"``) because IdPs send
attributes (phoneNumbers, addresses, the enterprise extension, …) that this
service does not persist. Serialize responses with
``model_dump(by_alias=True, exclude_none=True)``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from om.server.scim.constants import SCHEMA_ERROR
from om.server.scim.constants import SCHEMA_GROUP
from om.server.scim.constants import SCHEMA_LIST_RESPONSE
from om.server.scim.constants import SCHEMA_PATCH_OP
from om.server.scim.constants import SCHEMA_USER


class ScimModel(BaseModel):
    """Base for all SCIM wire models: alias-friendly, tolerant of extras."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ScimMeta(ScimModel):
    """Common ``meta`` complex attribute (RFC 7643 §3.1). All read-only."""

    resource_type: str = Field(serialization_alias="resourceType", alias="resourceType")
    created: str | None = None
    last_modified: str | None = Field(
        default=None, serialization_alias="lastModified", alias="lastModified"
    )
    location: str | None = None
    version: str | None = None


class ScimName(ScimModel):
    """User ``name`` complex attribute (RFC 7643 §4.1.1)."""

    formatted: str | None = None
    family_name: str | None = Field(
        default=None, serialization_alias="familyName", alias="familyName"
    )
    given_name: str | None = Field(
        default=None, serialization_alias="givenName", alias="givenName"
    )
    middle_name: str | None = Field(
        default=None, serialization_alias="middleName", alias="middleName"
    )
    honorific_prefix: str | None = Field(
        default=None, serialization_alias="honorificPrefix", alias="honorificPrefix"
    )
    honorific_suffix: str | None = Field(
        default=None, serialization_alias="honorificSuffix", alias="honorificSuffix"
    )


class ScimValueEntry(ScimModel):
    """Generic multi-valued entry (emails, phoneNumbers, …)."""

    value: str | None = None
    display: str | None = None
    type: str | None = None
    primary: bool | None = None


class ScimMember(ScimModel):
    """A member entry inside a Group's ``members`` array (RFC 7643 §4.2)."""

    value: str | None = None
    ref: str | None = Field(default=None, serialization_alias="$ref", alias="$ref")
    display: str | None = None
    type: str | None = None


class ScimUserResource(ScimModel):
    """SCIM ``User`` resource (RFC 7643 §4.1).

    Used for both input (POST/PUT bodies) and output. ``id``/``groups``/``meta``
    are server-controlled (read-only) and only populated on output.
    """

    schemas: list[str] = Field(default_factory=lambda: [SCHEMA_USER])
    id: str | None = None
    external_id: str | None = Field(
        default=None, serialization_alias="externalId", alias="externalId"
    )
    user_name: str | None = Field(
        default=None, serialization_alias="userName", alias="userName"
    )
    name: ScimName | None = None
    display_name: str | None = Field(
        default=None, serialization_alias="displayName", alias="displayName"
    )
    active: bool | None = None
    emails: list[ScimValueEntry] | None = None
    # readOnly on the wire — the SP derives group membership; never persisted here.
    groups: list[ScimMember] | None = None
    meta: ScimMeta | None = None

    @field_validator("active", mode="before")
    @classmethod
    def _coerce_active(cls, value: Any) -> Any:
        """Accept Entra legacy string ``"True"``/``"False"`` for ``active``."""
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "1"):
                return True
            if lowered in ("false", "0"):
                return False
        return value


class ScimGroupResource(ScimModel):
    """SCIM ``Group`` resource (RFC 7643 §4.2). Maps to an internal Team."""

    schemas: list[str] = Field(default_factory=lambda: [SCHEMA_GROUP])
    id: str | None = None
    external_id: str | None = Field(
        default=None, serialization_alias="externalId", alias="externalId"
    )
    display_name: str | None = Field(
        default=None, serialization_alias="displayName", alias="displayName"
    )
    members: list[ScimMember] | None = None
    meta: ScimMeta | None = None


class ScimListResponse(ScimModel):
    """Paginated query result (RFC 7644 §3.4.2). Note capital ``Resources``.

    Output-only: fields carry a ``serialization_alias`` (emitted with
    ``by_alias=True``) but no input ``alias``, so the model is constructed by
    field name in code.
    """

    schemas: list[str] = Field(default_factory=lambda: [SCHEMA_LIST_RESPONSE])
    total_results: int = Field(serialization_alias="totalResults")
    start_index: int = Field(serialization_alias="startIndex")
    items_per_page: int = Field(serialization_alias="itemsPerPage")
    resources: list[dict[str, Any]] = Field(
        default_factory=list, serialization_alias="Resources"
    )


class ScimPatchOperation(ScimModel):
    """A single PATCH operation (RFC 7644 §3.5.2).

    ``op`` is normalised to lowercase because Entra emits ``Add``/``Replace``/
    ``Remove`` capitalised. ``path`` is optional (required only for ``remove``).
    """

    op: str
    path: str | None = None
    value: Any = None

    @field_validator("op", mode="before")
    @classmethod
    def _normalise_op(cls, value: Any) -> Any:
        return value.lower() if isinstance(value, str) else value


class ScimPatchOp(ScimModel):
    """PATCH request body (RFC 7644 §3.5.2). Note capital ``Operations``."""

    schemas: list[str] = Field(default_factory=lambda: [SCHEMA_PATCH_OP])
    operations: list[ScimPatchOperation] = Field(
        serialization_alias="Operations", alias="Operations"
    )


class ScimErrorResponse(ScimModel):
    """SCIM error body (RFC 7644 §3.12). ``status`` is the HTTP code as a string.

    Output-only: constructed by field name; serialized with ``by_alias=True``.
    """

    schemas: list[str] = Field(default_factory=lambda: [SCHEMA_ERROR])
    status: str
    scim_type: str | None = Field(default=None, serialization_alias="scimType")
    detail: str | None = None
