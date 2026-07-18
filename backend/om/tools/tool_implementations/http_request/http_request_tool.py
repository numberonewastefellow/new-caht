"""Built-in HTTP Request tool for making arbitrary HTTP calls.

Used by the pre-built "HTTP Request" agent in workflows to call
REST APIs without requiring an OpenAPI schema.

Security:
    - SSRF protection via om.utils.url (blocks private IPs, cloud metadata)
    - Header sanitization (blocks Authorization, Cookie, Host, etc.)
    - Response size limit (10 MB default, configurable)
    - Redirects disabled by default (prevents SSRF bypass via 302)
    - Response body truncation for LLM context (50K chars)
"""

import json
from typing import Any

import requests
from sqlalchemy.orm import Session
from typing_extensions import override

from om.chat.emitter import Emitter
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import CustomToolDelta
from om.server.query_and_chat.streaming_models import CustomToolStart
from om.server.query_and_chat.streaming_models import Packet
from om.tools.interface import Tool
from om.tools.models import CustomToolCallSummary
from om.tools.models import ToolCallException
from om.tools.models import ToolResponse
from om.utils.logger import setup_logger
from om.utils.url import SSRFException
from om.utils.url import ssrf_safe_request

logger = setup_logger()

# Parameter names expected from the LLM
METHOD_FIELD = "method"
URL_FIELD = "url"
HEADERS_FIELD = "headers"
BODY_FIELD = "body"
TIMEOUT_FIELD = "timeout_seconds"

VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
DEFAULT_TIMEOUT = 30
MAX_RESPONSE_LENGTH = 50000

HTTP_REQUEST_RESPONSE_ID = "http_request_response"


class HttpRequestTool(Tool[None]):
    """Built-in tool for making HTTP requests.

    Accepts method, URL, headers, body, and timeout as parameters
    from the LLM and executes the HTTP request, returning the response.
    """

    NAME = "http_request"
    DISPLAY_NAME = "HTTP Request"
    DESCRIPTION = (
        "Make an HTTP request to any URL. Supports GET, POST, PUT, DELETE, PATCH methods. "
        "Use this to call REST APIs, webhooks, or any HTTP endpoint."
    )

    def __init__(
        self,
        tool_id: int,
        emitter: Emitter,
    ) -> None:
        super().__init__(emitter=emitter)
        self._id = tool_id

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def description(self) -> str:
        return self.DESCRIPTION

    @property
    def display_name(self) -> str:
        return self.DISPLAY_NAME

    @override
    @classmethod
    def is_available(cls, db_session: Session) -> bool:
        # Always available — no external service dependency
        return True

    def tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        METHOD_FIELD: {
                            "type": "string",
                            "enum": list(VALID_METHODS),
                            "description": "HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)",
                        },
                        URL_FIELD: {
                            "type": "string",
                            "description": "The full URL to send the request to (must be a public URL, internal/private IPs are blocked)",
                        },
                        HEADERS_FIELD: {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": (
                                "Optional HTTP headers as key-value pairs. "
                                "Note: Authorization, Cookie, and Host headers are "
                                "blocked for security."
                            ),
                        },
                        BODY_FIELD: {
                            "type": "string",
                            "description": "Optional request body (for POST, PUT, PATCH). Send as JSON string.",
                        },
                        TIMEOUT_FIELD: {
                            "type": "integer",
                            "description": f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
                        },
                    },
                    "required": [METHOD_FIELD, URL_FIELD],
                },
            },
        }

    def emit_start(self, placement: Placement) -> None:
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolStart(tool_name=self.name),
            )
        )

    def run(
        self,
        placement: Placement,
        override_kwargs: None = None,  # noqa: ARG002
        **llm_kwargs: Any,
    ) -> ToolResponse:
        # Validate required fields
        if URL_FIELD not in llm_kwargs:
            raise ToolCallException(
                message="Missing required 'url' parameter in http_request tool call",
                llm_facing_message=(
                    "The http_request tool requires a 'url' parameter. "
                    'Please provide like: {"method": "GET", "url": "https://example.com/api"}'
                ),
            )

        method = str(llm_kwargs.get(METHOD_FIELD, "GET")).upper()
        url = str(llm_kwargs[URL_FIELD])
        headers = llm_kwargs.get(HEADERS_FIELD) or {}
        body_raw = llm_kwargs.get(BODY_FIELD)
        timeout = int(llm_kwargs.get(TIMEOUT_FIELD, DEFAULT_TIMEOUT))

        if method not in VALID_METHODS:
            raise ToolCallException(
                message=f"Invalid HTTP method: {method}",
                llm_facing_message=f"Invalid HTTP method '{method}'. Use one of: {', '.join(VALID_METHODS)}",
            )

        # Warn if body provided for methods that don't use it
        if body_raw and method not in ("POST", "PUT", "PATCH"):
            logger.warning(
                "HttpRequestTool: body provided for %s request (will be ignored)",
                method,
            )

        # Parse body if it's a JSON string
        json_body = None
        str_body = None
        if body_raw and method in ("POST", "PUT", "PATCH"):
            if isinstance(body_raw, dict):
                json_body = body_raw
            elif isinstance(body_raw, str):
                try:
                    json_body = json.loads(body_raw)
                except json.JSONDecodeError:
                    str_body = body_raw

        # Make the request with SSRF protection, header sanitization, and size limits
        logger.info("HttpRequestTool: %s %s", method, url)
        try:
            response = ssrf_safe_request(
                method=method,
                url=url,
                headers=headers,
                json_body=json_body,
                data=str_body,
                timeout=timeout,
                follow_redirects=False,
            )
        except SSRFException as e:
            error_msg = f"Blocked by security policy: {e}"
            return self._build_error_response(placement, error_msg)
        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {timeout} seconds"
            return self._build_error_response(placement, error_msg)
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error: {e}"
            return self._build_error_response(placement, error_msg)
        except requests.exceptions.ContentDecodingError as e:
            error_msg = f"Response too large: {e}"
            return self._build_error_response(placement, error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            return self._build_error_response(placement, error_msg)

        # Build response
        status_code = response.status_code
        content_type = response.headers.get("Content-Type", "")

        # Try to parse as JSON, fall back to text
        response_data: Any
        response_type: str
        try:
            response_data = response.json()
            response_type = "json"
            # Truncate JSON responses too (serialize, check length, re-parse if needed)
            json_str = json.dumps(response_data, default=str)
            if len(json_str) > MAX_RESPONSE_LENGTH:
                response_data = (
                    json_str[:MAX_RESPONSE_LENGTH]
                    + f"\n... [truncated, {len(json_str) - MAX_RESPONSE_LENGTH} chars omitted]"
                )
                response_type = "text"  # downgrade to text since JSON is now partial
        except (json.JSONDecodeError, ValueError):
            response_data = response.text[:MAX_RESPONSE_LENGTH]
            if len(response.text) > MAX_RESPONSE_LENGTH:
                response_data += f"\n... [truncated, {len(response.text) - MAX_RESPONSE_LENGTH} chars omitted]"
            response_type = "text"

        # Emit delta packet
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolDelta(
                    tool_name=self.name,
                    response_type=response_type,
                    data=response_data,
                ),
            )
        )

        # Build LLM-facing response with consistent schema
        llm_response = json.dumps(
            {
                "status_code": status_code,
                "content_type": content_type,
                "body": response_data,
                "error": None,
            },
            indent=2,
            default=str,
        )

        return ToolResponse(
            rich_response=CustomToolCallSummary(
                tool_name=self.name,
                response_type=response_type,
                tool_result=response_data,
            ),
            llm_facing_response=llm_response,
        )

    def _build_error_response(
        self, placement: Placement, error_msg: str
    ) -> ToolResponse:
        """Build an error response without crashing the workflow."""
        logger.error("HttpRequestTool error: %s", error_msg)

        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolDelta(
                    tool_name=self.name,
                    response_type="error",
                    data=error_msg,
                ),
            )
        )

        return ToolResponse(
            rich_response=CustomToolCallSummary(
                tool_name=self.name,
                response_type="error",
                tool_result=error_msg,
            ),
            llm_facing_response=json.dumps(
                {
                    "status_code": None,
                    "content_type": None,
                    "body": None,
                    "error": error_msg,
                }
            ),
        )
