"""Constants for the SCIM 2.0 service-provider implementation.

All URN strings are quoted verbatim from RFC 7643 (core schema) and RFC 7644
(protocol). SCIM attribute/URN names are case-preserving; keep the canonical
casing below.
"""

from typing import Final

# --- Router mount ---------------------------------------------------------
# SCIM 2.0 is mounted at ``/scim/v2`` WITHOUT the global API prefix, because
# IdPs (Okta, Entra) expect the base URL to end in ``/scim/v2``.
SCIM_ROOT_PATH: Final = "/scim/v2"

# --- Media type (RFC 7644 §3.1) ------------------------------------------
SCIM_CONTENT_TYPE: Final = "application/scim+json"

# --- Core resource schema URNs (RFC 7643) --------------------------------
SCHEMA_USER: Final = "urn:ietf:params:scim:schemas:core:2.0:User"
SCHEMA_GROUP: Final = "urn:ietf:params:scim:schemas:core:2.0:Group"
SCHEMA_ENTERPRISE_USER: Final = (
    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
)
SCHEMA_SERVICE_PROVIDER_CONFIG: Final = (
    "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
)
SCHEMA_RESOURCE_TYPE: Final = "urn:ietf:params:scim:schemas:core:2.0:ResourceType"
SCHEMA_SCHEMA: Final = "urn:ietf:params:scim:schemas:core:2.0:Schema"

# --- Protocol message URNs (RFC 7644) ------------------------------------
SCHEMA_LIST_RESPONSE: Final = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCHEMA_PATCH_OP: Final = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
SCHEMA_ERROR: Final = "urn:ietf:params:scim:api:messages:2.0:Error"
SCHEMA_SEARCH_REQUEST: Final = "urn:ietf:params:scim:api:messages:2.0:SearchRequest"

# --- Resource type names --------------------------------------------------
RESOURCE_TYPE_USER: Final = "User"
RESOURCE_TYPE_GROUP: Final = "Group"

# --- Bearer token ---------------------------------------------------------
# Prefix on every issued SCIM token, e.g. ``scim_<random>`` (single-tenant) or
# ``scim_<url-encoded-tenant>.<random>`` (multi-tenant).
SCIM_TOKEN_PREFIX: Final = "scim_"
# Bytes of CSPRNG entropy for the random segment (token_urlsafe → ~1.33 chars/byte).
SCIM_TOKEN_ENTROPY_BYTES: Final = 48

# --- Pagination defaults (RFC 7644 §3.4.2.4) -----------------------------
DEFAULT_PAGE_SIZE: Final = 100
MAX_PAGE_SIZE: Final = 500

# --- scimType error keywords (RFC 7644 §3.12) ----------------------------
SCIM_TYPE_INVALID_FILTER: Final = "invalidFilter"
SCIM_TYPE_TOO_MANY: Final = "tooMany"
SCIM_TYPE_UNIQUENESS: Final = "uniqueness"
SCIM_TYPE_MUTABILITY: Final = "mutability"
SCIM_TYPE_INVALID_SYNTAX: Final = "invalidSyntax"
SCIM_TYPE_INVALID_PATH: Final = "invalidPath"
SCIM_TYPE_NO_TARGET: Final = "noTarget"
SCIM_TYPE_INVALID_VALUE: Final = "invalidValue"
SCIM_TYPE_INVALID_VERS: Final = "invalidVers"
