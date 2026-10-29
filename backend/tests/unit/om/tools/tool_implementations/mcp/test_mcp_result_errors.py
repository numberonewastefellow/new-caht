"""Unit tests for MCP tool-execution error handling.

MCP reports two distinct kinds of failure (see the Tools spec, "Error
Handling"):

  * protocol errors  -> JSON-RPC error, surfaced as a raised exception
  * tool execution errors -> a *successful* response whose result carries
    ``isError: true``, with the error message as ordinary content

The second kind used to be discarded: ``process_mcp_result`` flattened the
content to a bare string, so a rejected call was indistinguishable from a
successful one and was logged as ``executed successfully``.

These tests pin the two guarantees we rely on:
  1. the error flag survives, so logs/UI can tell the difference
  2. the text is passed through untouched, because the spec requires clients
     to hand tool errors to the model so it can self-correct and retry
"""

from mcp.types import CallToolResult
from mcp.types import TextContent

from om.tools.tool_implementations.mcp.mcp_client import MCPToolCallResult
from om.tools.tool_implementations.mcp.mcp_client import process_mcp_result


def _text_result(text: str, is_error: bool) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        isError=is_error,
    )


def test_successful_call_is_not_flagged() -> None:
    result = process_mcp_result(_text_result("Document created", False))

    assert isinstance(result, MCPToolCallResult)
    assert result.text == "Document created"
    assert result.is_error is False


def test_tool_execution_error_is_flagged() -> None:
    """A rejected call must not look like a success."""
    message = (
        "Invalid arguments for tool 'docx_create_document': "
        "[{'loc': ('author',), 'msg': 'Input should be a valid string'}]"
    )

    result = process_mcp_result(_text_result(message, True))

    assert result.is_error is True


def test_error_text_is_passed_through_unchanged() -> None:
    """The model needs the verbatim error in order to self-correct."""
    message = "Invalid departure date: must be in the future."

    result = process_mcp_result(_text_result(message, True))

    assert result.text == message


def test_is_error_defaults_to_false_when_omitted() -> None:
    """Servers may omit isError entirely; that means success, not failure."""
    result = process_mcp_result(
        CallToolResult(content=[TextContent(type="text", text="ok")])
    )

    assert result.is_error is False


def test_multiple_content_blocks_are_joined_and_flag_preserved() -> None:
    result = process_mcp_result(
        CallToolResult(
            content=[
                TextContent(type="text", text="first"),
                TextContent(type="text", text="second"),
            ],
            isError=True,
        )
    )

    assert result.text == "first\n\nsecond"
    assert result.is_error is True


def test_result_unpacks_as_text_then_flag() -> None:
    """Callers destructure this; lock the order so a swap can't slip through."""
    text, is_error = process_mcp_result(_text_result("boom", True))

    assert text == "boom"
    assert is_error is True
