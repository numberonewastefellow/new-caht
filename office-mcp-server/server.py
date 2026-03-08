"""Unified Office MCP Server.

Mounts PPT and DOCX FastMCP apps under a single server with namespaced tools:
  - ppt_*  (37 tools) — PowerPoint generation via python-pptx
  - docx_* (40+ tools) — Word document generation via python-docx

Runs on port 8100 with Streamable HTTP transport.
"""

from mcp.server.fastmcp import FastMCP
from ppt_mcp_server import app as ppt_app
from word_mcp_server import app as docx_app

app = FastMCP("office-mcp-server")
app.mount("ppt", ppt_app)
app.mount("docx", docx_app)

if __name__ == "__main__":
    app.settings.port = 8100
    app.settings.host = "0.0.0.0"
    app.settings.transport_security.enable_dns_rebinding_protection = False
    app.run(transport="streamable-http")
