"""
Endpoint discovery from OpenAPI schema and route rename mapping.
"""
from dataclasses import dataclass
from dataclasses import field


@dataclass
class EndpointSpec:
    path: str
    method: str
    operation_id: str
    parameters: list[dict] = field(default_factory=list)
    request_body_schema: dict | None = None
    auth_type: str = "user"  # "public" | "user" | "admin"


# Old prefix -> New prefix mapping
ROUTE_RENAME_MAP = {
    "/admin/input_prompt": "/admin/prompts",
    "/user/projects": "/workspaces",
    "/input_prompt": "/prompts",
    "/notifications": "/signals",
    "/federated": "/bridges",
    "/manage": "/nexus",
    "/health": "/heartbeat",
    "/chat": "/converse",
}

# Public endpoints that don't require authentication
PUBLIC_PATHS = {
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/health",
    "/auth/type",
    "/version",
    "/versions",
    "/me",
    "/auth/refresh",
    "/auth/register",
    "/auth/login",
    "/auth/logout",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/request-verify-token",
    "/auth/verify",
    "/metrics",
}

# Endpoints to skip (file uploads, streaming SSE, etc.)
SKIP_ENDPOINTS = {
    "send_chat_message",  # SSE streaming
    "upload_files_for_workspace",  # file upload
    "upload_file_for_connector",  # file upload
    "update_connector_files",  # file upload
    "seed_chat_session_from_slack",  # requires Slack data
}


def translate_path(old_path: str, rename_map: dict[str, str] | None = None) -> str:
    """Apply longest-prefix-first replacement to translate a path."""
    if rename_map is None:
        rename_map = ROUTE_RENAME_MAP

    # Sort by length descending so longer prefixes match first
    # (e.g., /admin/input_prompt before /input_prompt)
    for old_prefix, new_prefix in sorted(
        rename_map.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if old_path == old_prefix or old_path.startswith(old_prefix + "/"):
            return new_prefix + old_path[len(old_prefix) :]
    return old_path


def parse_openapi_schema(schema: dict) -> list[EndpointSpec]:
    """Parse OpenAPI JSON schema into a list of EndpointSpec objects."""
    endpoints = []
    paths = schema.get("paths", {})
    components = schema.get("components", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ("parameters", "summary", "description"):
                continue

            method_upper = method.upper()
            operation_id = details.get("operationId", "")

            if not operation_id:
                continue

            if operation_id in SKIP_ENDPOINTS:
                continue

            # Extract parameters
            params = details.get("parameters", [])

            # Extract request body schema
            request_body_schema = None
            request_body = details.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                if json_content:
                    schema_ref = json_content.get("schema", {})
                    request_body_schema = _resolve_schema(schema_ref, components)

            # Determine auth type
            # Strip /api prefix if present for matching
            clean_path = path
            if clean_path.startswith("/api"):
                clean_path = clean_path[4:]

            if clean_path in PUBLIC_PATHS:
                auth_type = "public"
            elif "/admin/" in path or path.startswith("/api/admin"):
                auth_type = "admin"
            else:
                auth_type = "user"

            endpoints.append(
                EndpointSpec(
                    path=path,
                    method=method_upper,
                    operation_id=operation_id,
                    parameters=params,
                    request_body_schema=request_body_schema,
                    auth_type=auth_type,
                )
            )

    return endpoints


def _resolve_schema(schema: dict, components: dict) -> dict:
    """Resolve $ref references in OpenAPI schema."""
    if "$ref" in schema:
        ref_path = schema["$ref"]
        # e.g., "#/components/schemas/ChatSessionCreationRequest"
        parts = ref_path.split("/")
        resolved = components
        for part in parts[1:]:  # skip '#'
            resolved = resolved.get(part, {})
        return resolved
    return schema
