"""
MCP (Model Context Protocol) Client Implementation

This module provides a proper MCP client that follows the JSON-RPC 2.0 specification
and handles connection initialization, session management, and protocol communication.

Session Persistence (Pattern A — Client-Side Session Pool)
==========================================================
MCP servers like the PowerPoint MCP Server maintain state in-memory per session.
Multiple tool calls from the same agent step (e.g., create_presentation → add_slide
→ save_presentation) must reuse the same ClientSession so the server-side state
persists across calls.

MCPSessionManager keeps sessions alive for the duration of an agent step, keyed by
(scope_id, server_url). When the agent step finishes, all sessions for that scope
are closed. This follows the same pattern as LangChain MCP Adapters' persistent
session mode and is compliant with the MCP specification's Mcp-Session-Id header
requirements.

See office-mcp-server/MCP_SESSION_PERSISTENCE.md for the full design rationale.
"""

import asyncio
import concurrent.futures
import contextvars
import threading
import time as _time
from collections.abc import Awaitable
from collections.abc import Callable
from enum import Enum
from typing import Any
from typing import Dict
from typing import TypeVar

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client  # or use stdio_client
from mcp.types import CallToolResult
from mcp.types import InitializeResult
from mcp.types import ListResourcesResult
from mcp.types import TextResourceContents
from mcp.types import Tool as MCPLibTool
from pydantic import BaseModel

from onyx.db.enums import MCPTransport
from onyx.utils.logger import setup_logger
from onyx.utils.threadpool_concurrency import run_async_sync_no_cancel

logger = setup_logger()

T = TypeVar("T", covariant=True)

MCPClientFunction = Callable[[ClientSession], Awaitable[T]]


class MCPMessageType(str, Enum):
    """MCP message types"""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class ContentBlockTypes(str, Enum):
    """MCP content block types"""  # Unfortunstely these aren't exposed by the mcp library

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    RESOURCE = "resource"
    RESOURCE_LINK = "resource_link"


class MCPMessage(BaseModel):
    """Base MCP message following JSON-RPC 2.0"""

    jsonrpc: str = "2.0"
    method: str | None = None
    params: Dict[str, Any] | None = None
    id: Any | None = None
    result: Any | None = None
    error: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-RPC message dict"""
        msg: Dict[str, Any] = {"jsonrpc": self.jsonrpc}

        if self.id is not None:
            msg["id"] = self.id

        if self.method is not None:
            msg["method"] = self.method

        if self.params is not None:
            msg["params"] = self.params

        if self.result is not None:
            msg["result"] = self.result

        if self.error is not None:
            msg["error"] = self.error

        return msg


# ── Persistent Session Manager ──────────────────────────────────────────────
#
# Keeps MCP sessions alive across multiple tool calls within the same scope
# (e.g., a workflow agent step). This is required for stateful MCP servers
# that maintain in-memory state per session (PowerPoint, file editors, etc.).


class _SessionEntry:
    """Holds a live MCP session with its async resources."""

    __slots__ = ("session", "loop", "thread", "_cleanup_task", "created_at")

    def __init__(
        self,
        session: ClientSession,
        loop: asyncio.AbstractEventLoop,
        thread: threading.Thread,
        cleanup_task: Any,
        created_at: float,
    ) -> None:
        self.session = session
        self.loop = loop
        self.thread = thread
        self._cleanup_task = cleanup_task
        self.created_at = created_at


class MCPSessionManager:
    """Thread-safe pool of persistent MCP sessions keyed by (scope_id, server_url).

    Usage:
        # At agent step start — scope_id is assigned automatically
        session = mcp_session_manager.get_or_create(scope_id, server_url, ...)
        result = mcp_session_manager.call_tool(scope_id, server_url, tool_name, args)

        # At agent step end — cleanup all sessions for the scope
        mcp_session_manager.close_scope(scope_id)

    Sessions auto-expire after SESSION_TTL_SECONDS to prevent leaks.
    """

    SESSION_TTL_SECONDS = 600  # 10 minutes

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Key: f"{scope_id}::{server_url}" → _SessionEntry
        self._sessions: dict[str, _SessionEntry] = {}
        # Key: same → asyncio.Event that signals the session is ready
        self._pending: dict[str, threading.Event] = {}

    @staticmethod
    def _key(scope_id: str, server_url: str) -> str:
        return f"{scope_id}::{server_url}"

    def _start_session_loop(
        self,
        key: str,
        server_url: str,
        connection_headers: dict[str, str] | None,
        transport: MCPTransport,
        auth: OAuthClientProvider | None,
        ready_event: threading.Event,
    ) -> None:
        """Runs in a dedicated daemon thread. Opens the async transport + session
        and keeps the event loop alive until the session is closed."""

        async def _run() -> None:
            auth_headers = connection_headers or {}
            auth_for_request = (
                auth if transport == MCPTransport.STREAMABLE_HTTP else None
            )
            client_func = (
                streamablehttp_client
                if transport == MCPTransport.STREAMABLE_HTTP
                else sse_client
            )

            try:
                async with client_func(
                    server_url, headers=auth_headers, auth=auth_for_request
                ) as client_tuple:
                    if len(client_tuple) == 3:
                        read, write, _ = client_tuple
                    elif len(client_tuple) == 2:
                        read, write = client_tuple  # type: ignore[misc]
                    else:
                        raise ValueError(
                            f"Unexpected client tuple length: {len(client_tuple)}"
                        )

                    from datetime import timedelta

                    async with ClientSession(
                        read, write, read_timeout_seconds=timedelta(seconds=300)
                    ) as session:
                        await session.initialize()
                        loop = asyncio.get_running_loop()
                        stop_event = asyncio.Event()

                        entry = _SessionEntry(
                            session=session,
                            loop=loop,
                            thread=threading.current_thread(),
                            cleanup_task=stop_event,
                            created_at=_time.time(),
                        )

                        with self._lock:
                            self._sessions[key] = entry

                        ready_event.set()
                        # Keep the loop alive until close is requested
                        await stop_event.wait()

            except Exception as e:
                logger.error(f"MCP session loop error for {key}: {e}")
                with self._lock:
                    self._sessions.pop(key, None)
                ready_event.set()  # unblock waiters even on failure

        asyncio.run(_run())

    def get_or_create(
        self,
        scope_id: str,
        server_url: str,
        connection_headers: dict[str, str] | None = None,
        transport: MCPTransport = MCPTransport.STREAMABLE_HTTP,
        auth: OAuthClientProvider | None = None,
    ) -> ClientSession | None:
        """Return a persistent session, creating one if needed."""
        key = self._key(scope_id, server_url)

        with self._lock:
            entry = self._sessions.get(key)
            if entry is not None:
                # Check TTL
                if _time.time() - entry.created_at < self.SESSION_TTL_SECONDS:
                    return entry.session
                else:
                    # Expired — close and recreate
                    self._close_entry(key, entry)

            # Check if another thread is already creating this session
            if key in self._pending:
                pending_event = self._pending[key]
            else:
                pending_event = threading.Event()
                self._pending[key] = pending_event

        # If we set the pending event, we are the creator
        if not pending_event.is_set():
            thread = threading.Thread(
                target=self._start_session_loop,
                args=(key, server_url, connection_headers, transport, auth, pending_event),
                daemon=True,
                name=f"mcp-session-{key[:40]}",
            )
            thread.start()

        # Wait for session to be ready (with timeout)
        if not pending_event.wait(timeout=30):
            logger.error(f"Timeout waiting for MCP session: {key}")
            with self._lock:
                self._pending.pop(key, None)
            return None

        with self._lock:
            self._pending.pop(key, None)
            entry = self._sessions.get(key)
            return entry.session if entry else None

    def call_tool(
        self,
        scope_id: str,
        server_url: str,
        tool_name: str,
        arguments: dict[str, Any],
        connection_headers: dict[str, str] | None = None,
        transport: MCPTransport = MCPTransport.STREAMABLE_HTTP,
        auth: OAuthClientProvider | None = None,
    ) -> str:
        """Call a tool using a persistent session. Creates the session if needed."""
        session = self.get_or_create(
            scope_id, server_url, connection_headers, transport, auth
        )
        if session is None:
            raise RuntimeError(
                f"Failed to establish persistent MCP session to {server_url}"
            )

        key = self._key(scope_id, server_url)
        with self._lock:
            entry = self._sessions.get(key)
        if entry is None:
            raise RuntimeError(f"MCP session vanished for {key}")

        async def _call() -> str:
            result = await session.call_tool(tool_name, arguments)
            return process_mcp_result(result)

        # Submit the coroutine to the session's event loop
        future = asyncio.run_coroutine_threadsafe(_call(), entry.loop)
        try:
            return future.result(timeout=300)
        except Exception as e:
            logger.error(
                f"MCP persistent session tool call failed ({tool_name}): {e}"
            )
            raise

    def _close_entry(self, key: str, entry: _SessionEntry) -> None:
        """Signal the session loop to stop (non-blocking)."""
        try:
            entry.loop.call_soon_threadsafe(entry._cleanup_task.set)
        except RuntimeError:
            pass  # loop already closed
        self._sessions.pop(key, None)

    def close_scope(self, scope_id: str) -> None:
        """Close all sessions for a given scope (called when agent step ends)."""
        to_close: list[tuple[str, _SessionEntry]] = []
        with self._lock:
            for key in list(self._sessions.keys()):
                if key.startswith(f"{scope_id}::"):
                    entry = self._sessions.pop(key)
                    to_close.append((key, entry))

        for key, entry in to_close:
            logger.info(f"Closing MCP session: {key}")
            self._close_entry(key, entry)

    def close_all(self) -> None:
        """Close all sessions (for shutdown)."""
        with self._lock:
            entries = list(self._sessions.items())
            self._sessions.clear()
        for key, entry in entries:
            self._close_entry(key, entry)


# Global singleton — shared across the application
mcp_session_manager = MCPSessionManager()


def _create_mcp_client_function_runner(
    function: Callable[[ClientSession], Awaitable[T]],
    server_url: str,
    connection_headers: dict[str, str] | None = None,
    transport: MCPTransport = MCPTransport.STREAMABLE_HTTP,
    auth: OAuthClientProvider | None = None,  # TODO: maybe used this for all auth types
    **kwargs: Any,
) -> Callable[[], Awaitable[T]]:
    auth_headers = connection_headers or {}
    # WARNING: httpx.Auth with requires_response_body=True (as in the MCP OAuth
    # provider) forces httpx to fully read the response body. That is incompatible
    # with SSE (infinite stream). Avoid passing auth for SSE; rely on headers.
    auth_for_request = auth if transport == MCPTransport.STREAMABLE_HTTP else None

    # doing this here for mypy
    client_func = (
        streamablehttp_client
        if transport == MCPTransport.STREAMABLE_HTTP
        else sse_client
    )

    async def run_client_function() -> T:
        async with client_func(
            server_url, headers=auth_headers, auth=auth_for_request
        ) as client_tuple:
            if len(client_tuple) == 3:
                read, write, _ = client_tuple
            elif len(client_tuple) == 2:
                assert isinstance(client_tuple, tuple)  # mypy
                read, write = client_tuple
            else:
                raise ValueError(
                    f"Unexpected number of client tuple elements: {len(client_tuple)}"
                )
            from datetime import timedelta

            async with ClientSession(
                read, write, read_timeout_seconds=timedelta(seconds=300)
            ) as session:
                return await function(session, **kwargs)

    return run_client_function


def log_exception_group(e: ExceptionGroup) -> Exception | None:
    logger.error(e)
    saved_e = None
    for err in e.exceptions:
        if isinstance(err, ExceptionGroup):
            saved_e = log_exception_group(err) or saved_e
        else:
            logger.error(err)
            saved_e = err

    return saved_e


def _call_mcp_client_function_sync(
    function: Callable[[ClientSession], Awaitable[T]],
    server_url: str,
    connection_headers: dict[str, str] | None = None,
    transport: MCPTransport = MCPTransport.STREAMABLE_HTTP,
    auth: OAuthClientProvider | None = None,
    **kwargs: Any,
) -> T:
    run_client_function = _create_mcp_client_function_runner(
        function, server_url, connection_headers, transport, auth, **kwargs
    )
    try:
        return run_async_sync_no_cancel(run_client_function())
    except Exception as e:
        logger.error(f"Failed to call MCP client function: {e}")
        if isinstance(e, ExceptionGroup):
            original_exception = e
            saved_e = log_exception_group(e)
            if saved_e:
                raise saved_e
            raise original_exception
        raise e


async def _call_mcp_client_function_async(
    function: Callable[[ClientSession], Awaitable[T]],
    server_url: str,
    connection_headers: dict[str, str] | None = None,
    transport: MCPTransport = MCPTransport.STREAMABLE_HTTP,
    auth: OAuthClientProvider | None = None,
    **kwargs: Any,
) -> T:
    run_client_function = _create_mcp_client_function_runner(
        function, server_url, connection_headers, transport, auth, **kwargs
    )
    return await run_client_function()


def process_mcp_result(call_tool_result: CallToolResult) -> str:
    """Flatten MCP CallToolResult->text (prefers text content blocks)."""
    # TODO: use structured_content if available
    parts = []
    for content_block in call_tool_result.content:
        if content_block.type == ContentBlockTypes.TEXT.value:
            parts.append(content_block.text or "")
        if content_block.type == ContentBlockTypes.RESOURCE.value:
            if isinstance(content_block.resource, TextResourceContents):
                parts.append(content_block.resource.text or "")
            # TODO: handle blob resource content
        if content_block.type == ContentBlockTypes.RESOURCE_LINK.value:
            parts.append(
                f"link: {content_block.uri} title: {content_block.title} description: {content_block.description}"
            )
        # TODO: handle other content block types

    return "\n\n".join(p for p in parts if p) or str(call_tool_result.structuredContent)


def _call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> MCPClientFunction[str]:
    async def call_tool(session: ClientSession) -> str:
        await session.initialize()
        result = await session.call_tool(tool_name, arguments)
        return process_mcp_result(result)

    return call_tool


def call_mcp_tool(
    server_url: str,
    tool_name: str,
    arguments: dict[str, Any],
    connection_headers: dict[str, str] | None = None,
    transport: MCPTransport = MCPTransport.STREAMABLE_HTTP,
    auth: OAuthClientProvider | None = None,
    session_scope_id: str | None = None,
) -> str:
    """Call a specific tool on the MCP server.

    If session_scope_id is provided, uses a persistent session from the
    MCPSessionManager. All tool calls with the same (scope_id, server_url)
    share the same MCP session, enabling stateful multi-tool workflows
    (e.g., create_presentation → add_slide → save_presentation).

    If session_scope_id is None, falls back to the original behavior of
    creating a disposable session per call.
    """
    if session_scope_id is not None:
        return mcp_session_manager.call_tool(
            scope_id=session_scope_id,
            server_url=server_url,
            tool_name=tool_name,
            arguments=arguments,
            connection_headers=connection_headers,
            transport=transport,
            auth=auth,
        )

    # Fallback: disposable session (original behavior)
    return _call_mcp_client_function_sync(
        _call_mcp_tool(tool_name, arguments),
        server_url,
        connection_headers,
        transport,
        auth,
    )


async def initialize_mcp_client(
    server_url: str,
    connection_headers: dict[str, str] | None = None,
    transport: MCPTransport = MCPTransport.STREAMABLE_HTTP,
    auth: OAuthClientProvider | None = None,
) -> InitializeResult:
    return await _call_mcp_client_function_async(
        lambda session: session.initialize(),
        server_url,
        connection_headers,
        transport,
        auth,
    )


async def _discover_mcp_tools(session: ClientSession) -> list[MCPLibTool]:
    # 1) initialize
    import time

    t1 = time.time()
    init_result = await session.initialize()  # sends JSON-RPC "initialize"
    logger.info(f"Initialized with server: {init_result.serverInfo}")
    logger.info(f"Initialized with server time: {time.time() - t1}")
    # 2) tools/list
    t2 = time.time()
    tools_response = await session.list_tools()  # sends JSON-RPC "tools/list"
    logger.info(f"Listed tools with server time: {time.time() - t2}")
    return tools_response.tools


def discover_mcp_tools(
    server_url: str,
    connection_headers: dict[str, str] | None = None,
    transport: MCPTransport = MCPTransport.STREAMABLE_HTTP,
    auth: OAuthClientProvider | None = None,
) -> list[MCPLibTool]:
    """
    Synchronous wrapper for discovering MCP tools.
    """
    return _call_mcp_client_function_sync(
        _discover_mcp_tools,
        server_url,
        connection_headers,
        transport,
        auth,
    )


async def _discover_mcp_resources(session: ClientSession) -> ListResourcesResult:
    return await session.list_resources()


def discover_mcp_resources_sync(
    server_url: str,
    connection_headers: dict[str, str] | None = None,
    transport: str = "streamable-http",
    auth: OAuthClientProvider | None = None,
) -> ListResourcesResult:
    """
    Synchronous wrapper for discovering MCP resources.
    This is for compatibility with the existing codebase.
    """
    return _call_mcp_client_function_sync(
        _discover_mcp_resources,
        server_url,
        connection_headers,
        MCPTransport(transport),
        auth,
    )
