import json
import re
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any

import requests

from om.chat.emitter import Emitter
from om.configs.constants import FileOrigin
from om.db.enums import MCPAuthenticationType
from om.db.enums import MCPTransport
from om.db.models import MCPConnectionConfig
from om.db.models import MCPServer
from om.file_store.file_store import get_default_file_store
from om.server.query_and_chat.placement import Placement
from om.server.query_and_chat.streaming_models import CustomToolDelta
from om.server.query_and_chat.streaming_models import CustomToolStart
from om.server.query_and_chat.streaming_models import Packet
from om.tools.interface import Tool
from om.tools.models import CustomToolCallSummary
from om.tools.models import ToolResponse
from om.tools.tool_implementations.mcp.mcp_client import call_mcp_tool
from om.utils.logger import setup_logger

logger = setup_logger()

# ---------------------------------------------------------------------------
# MCP file download → MinIO helpers
# ---------------------------------------------------------------------------
_OFFICE_MIME_TYPES = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_OFFICE_EXTENSIONS = set(_OFFICE_MIME_TYPES.keys())

# Regex: absolute path like /app/output/deck.pptx or /app/my_doc.docx
_ABS_PATH_RE = re.compile(r"/app/[\w./+-]+\.(?:pptx|docx|pdf|xlsx)\b", re.IGNORECASE)
# Regex: bare filename like cloud_computing_benefits.docx (no spaces allowed)
_BARE_FILE_RE = re.compile(
    r"\b([\w][\w.+-]*\.(?:pptx|docx|pdf|xlsx))\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Filename tracking — collect filenames mentioned in tool results during a step.
# At step end, `collect_pending_files()` fetches the final versions from the
# MCP server and saves them to MinIO.  This avoids depending on the LLM
# calling any specific tool — every tool that mentions a file contributes.
# ---------------------------------------------------------------------------
# Thread-safe registry: scope_id → set of (server_url, file_path) tuples
import threading
_pending_files_lock = threading.Lock()
_pending_files: dict[str, set[tuple[str, str]]] = {}


# Read-only tools that should NOT trigger file tracking — they inspect
# existing files but don't create or modify them.
_READ_ONLY_TOOLS = {
    "docx_list_available_documents",
    "docx_get_document_info",
    "docx_get_document_text",
    "docx_get_document_outline",
    "docx_find_text_in_document",
    "docx_get_table_data",
    "ppt_list_presentations",
    "ppt_get_slide_info",
}


def _track_file_paths(
    tool_result: str,
    tool_name: str,
    server_url: str,
    scope_id: str | None,
) -> None:
    """Extract file paths from a tool result and add them to the pending set
    for the given scope (agent step).  No downloads happen here."""
    if not scope_id:
        return
    # Skip read-only tools — they mention filenames but don't create files
    if tool_name in _READ_ONLY_TOOLS:
        return

    paths: list[str] = []

    # 1. Regex: absolute /app/... paths
    paths.extend(_ABS_PATH_RE.findall(tool_result))

    # 2. Bare filenames (from any tool, not just _FILE_PRODUCING_TOOLS)
    for fname in _BARE_FILE_RE.findall(tool_result):
        ext = PurePosixPath(fname).suffix.lower()
        if ext in _OFFICE_EXTENSIONS:
            if tool_name.startswith("ppt_"):
                paths.append(f"/app/output/{fname}")
            else:
                paths.append(f"/app/{fname}")

    # When converting DOCX→PDF, also track the source .docx
    if tool_name == "docx_convert_to_pdf":
        for p in list(paths):
            if p.lower().endswith(".pdf"):
                docx_path = p.rsplit(".pdf", 1)[0] + ".docx"
                paths.append(docx_path)

    if not paths:
        return

    with _pending_files_lock:
        bucket = _pending_files.setdefault(scope_id, set())
        for p in paths:
            bucket.add((server_url, p))


def collect_pending_files(
    scope_id: str,
    emitter: Any = None,
    placement: Any = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """Called at step end — fetch all tracked files, save to MinIO, emit
    download links.  Returns (file_ids, file_details) where file_details
    is a list of {"file_path": ..., "filename": ...} dicts for passing
    structured file metadata between workflow steps."""
    with _pending_files_lock:
        pending = _pending_files.pop(scope_id, set())
    if not pending:
        return [], []

    file_store = get_default_file_store()
    file_ids: list[str] = []
    file_details: list[dict[str, str]] = []

    for server_url, fpath in pending:
        ext = PurePosixPath(fpath).suffix.lower()
        if ext not in _OFFICE_MIME_TYPES:
            continue

        base_url = server_url.rsplit("/mcp", 1)[0].rstrip("/")
        rel_path = fpath.replace("/app/", "", 1)
        download_url = f"{base_url}/files/{rel_path}"

        try:
            resp = requests.get(download_url, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"Failed to download MCP file {download_url}: {e}")
            continue

        filename = PurePosixPath(fpath).name
        mime_type = _OFFICE_MIME_TYPES[ext]

        file_id = file_store.save_file(
            content=BytesIO(resp.content),
            display_name=filename,
            file_origin=FileOrigin.CHAT_UPLOAD,
            file_type=mime_type,
        )
        file_ids.append(file_id)
        file_details.append({"file_path": fpath, "filename": filename})
        logger.info(f"[post-step] Saved MCP file to MinIO: {filename} -> {file_id}")

    # Emit a single CustomToolDelta with all file_ids so the UI shows
    # download links grouped together at step end.
    if file_ids and emitter and placement:
        from om.server.query_and_chat.streaming_models import CustomToolDelta
        from om.server.query_and_chat.streaming_models import CustomToolStart
        from om.server.query_and_chat.streaming_models import Packet

        tool_result_dict: dict[str, Any] = {
            "tool_result": "Generated document files",
            "_file_ids": file_ids,
            "_file_details": file_details,
        }
        emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolStart(tool_name="document_files"),
            )
        )
        emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolDelta(
                    tool_name="document_files",
                    response_type="json",
                    data=tool_result_dict,
                    file_ids=file_ids,
                ),
            )
        )
        from om.server.query_and_chat.streaming_models import SectionEnd
        emitter.emit(Packet(placement=placement, obj=SectionEnd()))

    return file_ids, file_details

# Headers that cannot be overridden by user requests to prevent security issues
# Host header is particularly critical - it can be used for Host Header Injection attacks
# to route requests to unintended internal servers
DENYLISTED_MCP_HEADERS = {
    "host",  # Prevents Host Header Injection attacks
}

# TODO: for now we're fitting MCP tool responses into the CustomToolCallSummary class
# In the future we may want custom handling for MCP tool responses
# class MCPToolCallSummary(BaseModel):
#     tool_name: str
#     server_url: str
#     tool_result: Any
#     server_name: str


class MCPTool(Tool[None]):
    """Tool implementation for MCP (Model Context Protocol) servers"""

    def __init__(
        self,
        tool_id: int,
        emitter: Emitter,
        mcp_server: MCPServer,  # TODO: these should be basemodels instead of db objects
        tool_name: str,
        tool_description: str,
        tool_definition: dict[str, Any],
        connection_config: MCPConnectionConfig | None = None,
        user_email: str = "",
        user_oauth_token: str | None = None,
        additional_headers: dict[str, str] | None = None,
        session_scope_id: str | None = None,
    ) -> None:
        super().__init__(emitter=emitter)

        self._id = tool_id
        self.mcp_server = mcp_server
        self.connection_config = connection_config
        self.user_email = user_email
        self._user_oauth_token = user_oauth_token
        self._additional_headers = additional_headers or {}
        self._session_scope_id = session_scope_id

        self._name = tool_name
        self._tool_definition = tool_definition
        self._description = tool_description
        self._display_name = tool_definition.get("displayName", tool_name)
        self._llm_name = f"mcp:{mcp_server.name}:{tool_name}"

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def llm_name(self) -> str:
        return self._llm_name

    def tool_definition(self) -> dict:
        """Return the tool definition from the MCP server"""
        # Convert MCP tool definition to OpenAI function calling format
        return {
            "type": "function",
            "function": {
                "name": self._name,
                "description": self._description,
                "parameters": self._tool_definition,
            },
        }

    def emit_start(self, placement: Placement) -> None:
        self.emitter.emit(
            Packet(
                placement=placement,
                obj=CustomToolStart(tool_name=self._name),
            )
        )

    def run(
        self,
        placement: Placement,
        override_kwargs: None = None,  # noqa: ARG002
        **llm_kwargs: Any,
    ) -> ToolResponse:
        """Execute the MCP tool by calling the MCP server"""
        try:
            # Build headers with proper precedence:
            # 1. Start with additional headers from API request (filled in first, excluding denylisted)
            # 2. Override with connection config headers (from DB) - these take precedence
            # 3. Override Authorization header with OAuth token if present
            headers: dict[str, str] = {}

            # Priority 1: Additional headers from API request (filled in first)
            # Filter out denylisted headers to prevent security issues (e.g., Host Header Injection)
            if self._additional_headers:
                filtered_headers = {
                    k: v
                    for k, v in self._additional_headers.items()
                    if k.lower() not in DENYLISTED_MCP_HEADERS
                }
                if filtered_headers:
                    headers.update(filtered_headers)
                # Log if any denylisted headers were provided (for security monitoring)
                denylisted_provided = [
                    k
                    for k in self._additional_headers.keys()
                    if k.lower() in DENYLISTED_MCP_HEADERS
                ]
                if denylisted_provided:
                    logger.warning(
                        f"MCP tool '{self._name}' received denylisted headers that were filtered: "
                        f"{denylisted_provided}"
                    )

            # Priority 2: Base headers from connection config (DB) - overrides request
            if self.connection_config and self.connection_config.config:
                config_dict = self.connection_config.config.get_value(apply_mask=False)
                headers.update(config_dict.get("headers", {}))

            # Priority 3: For pass-through OAuth, use the user's login OAuth token
            if self._user_oauth_token:
                headers["Authorization"] = f"Bearer {self._user_oauth_token}"

            # Check if this is an authentication issue before making the call
            is_passthrough_oauth = (
                self.mcp_server.auth_type == MCPAuthenticationType.PT_OAUTH
            )
            requires_auth = (
                self.mcp_server.auth_type != MCPAuthenticationType.NONE
                and self.mcp_server.auth_type is not None
            )
            has_auth_config = (
                (self.connection_config is not None and bool(headers))
                or bool(self._additional_headers)
            ) or (is_passthrough_oauth and self._user_oauth_token is not None)

            if requires_auth and not has_auth_config:
                # Authentication required but not configured
                auth_error_msg = (
                    f"The {self._name} tool from {self.mcp_server.name} requires authentication "
                    f"but no credentials have been provided. Tell the user to use the MCP dropdown in the "
                    f"chat bar to authenticate with the {self.mcp_server.name} server before "
                    f"using this tool."
                )
                logger.warning(
                    f"Authentication required for MCP tool '{self._name}' but no credentials found"
                )

                error_result = {"error": auth_error_msg}
                llm_facing_response = json.dumps(error_result)

                # Emit CustomToolDelta packet
                self.emitter.emit(
                    Packet(
                        placement=placement,
                        obj=CustomToolDelta(
                            tool_name=self._name,
                            response_type="json",
                            data=error_result,
                        ),
                    )
                )

                return ToolResponse(
                    rich_response=CustomToolCallSummary(
                        tool_name=self._name,
                        response_type="json",
                        tool_result=error_result,
                    ),
                    llm_facing_response=llm_facing_response,
                )

            tool_result = call_mcp_tool(
                self.mcp_server.server_url,
                self._name,
                llm_kwargs,
                connection_headers=headers,
                transport=self.mcp_server.transport or MCPTransport.STREAMABLE_HTTP,
                session_scope_id=self._session_scope_id,
            )

            logger.info(f"MCP tool '{self._name}' executed successfully")

            # Track any filenames mentioned in the result for post-step capture.
            # Actual download happens at step end via collect_pending_files().
            _track_file_paths(
                tool_result,
                self._name,
                self.mcp_server.server_url,
                self._session_scope_id,
            )

            # Format the tool result for response
            tool_result_dict: dict[str, Any] = {"tool_result": tool_result}
            llm_facing_response = json.dumps(tool_result_dict)

            # Emit CustomToolDelta packet
            self.emitter.emit(
                Packet(
                    placement=placement,
                    obj=CustomToolDelta(
                        tool_name=self._name,
                        response_type="json",
                        data=tool_result_dict,
                    ),
                )
            )

            return ToolResponse(
                rich_response=CustomToolCallSummary(
                    tool_name=self._name,
                    response_type="json",
                    tool_result=tool_result_dict,
                ),
                llm_facing_response=llm_facing_response,
            )

        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"Failed to execute MCP tool '{self._name}': {e}")

            # Check for authentication-related errors
            auth_error_indicators = [
                "401",
                "unauthorized",
                "authentication",
                "auth",
                "forbidden",
                "access denied",
                "invalid token",
                "invalid api key",
                "invalid credentials",
            ]

            is_auth_error = any(
                indicator in error_str for indicator in auth_error_indicators
            )

            if is_auth_error:
                auth_error_msg = (
                    f"Authentication failed for the {self._name} tool from {self.mcp_server.name}. "
                    f"Please use the MCP dropdown in the chat bar to update your credentials "
                    f"for the {self.mcp_server.name} server. Original error: {str(e)}"
                )
                error_result = {"error": auth_error_msg}
            else:
                error_result = {"error": f"Tool execution failed: {str(e)}"}

            llm_facing_response = json.dumps(error_result)

            # Emit CustomToolDelta packet
            self.emitter.emit(
                Packet(
                    placement=placement,
                    obj=CustomToolDelta(
                        tool_name=self._name,
                        response_type="json",
                        data=error_result,
                    ),
                )
            )

            return ToolResponse(
                rich_response=CustomToolCallSummary(
                    tool_name=self._name,
                    response_type="json",
                    tool_result=error_result,
                ),
                llm_facing_response=llm_facing_response,
            )
