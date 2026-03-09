"""Unified Office MCP Server.

Combines PPT and DOCX FastMCP apps under a single server with namespaced tools:
  - ppt_*  (37 tools) — PowerPoint generation via python-pptx
  - docx_* (54 tools) — Word document generation via python-docx
  - docx_convert_to_pdf — PDF generation (converts .docx to .pdf)

Runs on port 8100 with Streamable HTTP transport.

Architecture note:
  PPT server uses mcp.server.fastmcp (built-in), DOCX uses standalone fastmcp.
  These are incompatible for mount(). Solution: use standalone fastmcp as the
  wrapper, mount DOCX natively, and re-register PPT tools by extracting the
  actual functions from ppt_app's internal tool manager.
"""

from fastmcp import FastMCP
from ppt_mcp_server import app as ppt_app
from word_document_server.main import mcp as docx_app, register_tools

# DOCX tools are lazily registered inside register_tools()
register_tools()

app = FastMCP("office-mcp-server")

# Mount DOCX directly (same standalone fastmcp package)
app.mount(docx_app, namespace="docx")

# Re-register PPT tools with ppt_ prefix (cross-package mount doesn't work)
for name, tool_obj in ppt_app._tool_manager._tools.items():
    app.tool(name=f"ppt_{name}", description=tool_obj.description or "")(tool_obj.fn)

if __name__ == "__main__":
    app.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8100,
    )
