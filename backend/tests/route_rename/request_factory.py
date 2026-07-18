"""
Builds minimal valid request bodies for each endpoint.
Auto-generates defaults from OpenAPI schemas with manual overrides.
"""
import uuid


# Manual overrides keyed by operation_id
REQUEST_OVERRIDES: dict[str, dict] = {
    "create_chat_session": {
        "body": {"agent_id": 0, "description": "snapshot-test"},
    },
    "rename_chat_session": {
        "body": {
            "chat_session_id": 0,
            "name": "test",
        },
    },
    "update_chat_session_model": {
        "body": {
            "chat_session_id": 0,
            "new_model": "test",
        },
    },
    "update_chat_session_temperature": {
        "body": {
            "chat_session_id": 0,
            "temperature": 0.5,
        },
    },
    "create_chat_message_feedback": {
        "body": {
            "chat_message_id": 0,
            "is_positive": True,
        },
    },
    "set_message_as_latest": {
        "body": {
            "message_id": 0,
        },
    },
    "execute_code": {
        "body": {
            "code": "print('hello')",
            "language": "python",
        },
    },
}

# Sentinel values by OpenAPI type
SENTINEL_VALUES = {
    "string": "test",
    "integer": 0,
    "number": 0.0,
    "boolean": False,
    "array": [],
    "object": {},
}

# Sentinel values for path parameters by format
PATH_PARAM_SENTINELS = {
    "uuid": str(uuid.UUID(int=0)),
    "int": 0,
    "integer": 0,
    "string": "test",
    "path": "test",
}


def generate_default_body(schema: dict | None) -> dict | None:
    """Walk OpenAPI schema and produce a minimal valid request body."""
    if not schema:
        return None

    if schema.get("type") != "object":
        return None

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    result = {}

    for prop_name, prop_schema in properties.items():
        # Only fill required fields for minimal body
        if prop_name not in required and not properties:
            continue

        prop_type = prop_schema.get("type", "string")
        prop_format = prop_schema.get("format", "")

        if prop_format == "uuid":
            result[prop_name] = str(uuid.UUID(int=0))
        elif prop_type == "string":
            if prop_format == "date-time":
                result[prop_name] = "2024-01-01T00:00:00Z"
            elif prop_format == "email":
                result[prop_name] = "test@test.com"
            else:
                result[prop_name] = "test"
        elif prop_type == "integer":
            result[prop_name] = 0
        elif prop_type == "number":
            result[prop_name] = 0.0
        elif prop_type == "boolean":
            result[prop_name] = False
        elif prop_type == "array":
            result[prop_name] = []
        elif prop_type == "object":
            result[prop_name] = {}
        else:
            result[prop_name] = None

    return result if result else None


def build_request(
    operation_id: str,
    path: str,
    parameters: list[dict],
    request_body_schema: dict | None,
) -> dict:
    """Build a complete request spec for an endpoint.

    Returns dict with keys: url, body, query_params, path_params
    """
    # Check for manual override
    override = REQUEST_OVERRIDES.get(operation_id, {})

    # Build path params from OpenAPI parameters
    path_params = override.get("path_params", {})
    query_params = override.get("query_params", {})

    for param in parameters:
        name = param.get("name", "")
        location = param.get("in", "")
        param_schema = param.get("schema", {})
        param_type = param_schema.get("type", "string")
        param_format = param_schema.get("format", "")

        if location == "path" and name not in path_params:
            if param_format == "uuid" or "uuid" in name.lower():
                path_params[name] = str(uuid.UUID(int=0))
            elif param_type == "integer" or param_type == "int":
                path_params[name] = 0
            else:
                path_params[name] = "test"
        elif location == "query" and name not in query_params:
            # Only add required query params
            if param.get("required", False):
                query_params[name] = SENTINEL_VALUES.get(param_type, "test")

    # Resolve URL with path params
    url = path
    for param_name, param_value in path_params.items():
        # Handle FastAPI path param syntax: {param_name} or {param_name:path}
        url = url.replace(f"{{{param_name}}}", str(param_value))
        url = url.replace(f"{{{param_name}:path}}", str(param_value))

    # Build request body
    body = override.get("body", None)
    if body is None and request_body_schema:
        body = generate_default_body(request_body_schema)

    return {
        "url": url,
        "body": body,
        "query_params": query_params,
        "path_params": path_params,
    }
