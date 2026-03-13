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

  A FastAPI wrapper is used to add a /files/{path} endpoint for serving
  generated files (PPT, DOCX, PDF) so the backend can fetch them and
  save to MinIO for user downloads.
"""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from ppt_mcp_server import app as ppt_app
from word_document_server.main import mcp as docx_app, register_tools

# DOCX tools are lazily registered inside register_tools()
register_tools()

mcp = FastMCP("office-mcp-server")

# Mount DOCX directly (same standalone fastmcp package)
mcp.mount(docx_app, namespace="docx")

# Re-register PPT tools with ppt_ prefix (cross-package mount doesn't work)
for name, tool_obj in ppt_app._tool_manager._tools.items():
    mcp.tool(name=f"ppt_{name}", description=tool_obj.description or "")(tool_obj.fn)

# ---------------------------------------------------------------------------
# File serving endpoint — lets the backend download generated files via HTTP
# ---------------------------------------------------------------------------
ALLOWED_DIRS = [Path("/app/output"), Path("/app/documents"), Path("/app")]
MIME_TYPES = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

mcp_app = mcp.http_app(path="/mcp")

app = FastAPI(title="Office MCP Server", lifespan=mcp_app.lifespan)


@app.get("/files/{path:path}")
async def serve_file(path: str):
    """Serve generated files for download. Path is relative to /app/."""
    file_path = (Path("/app") / path).resolve()

    # Security: only allow known office file extensions
    if file_path.suffix.lower() not in MIME_TYPES:
        return JSONResponse({"error": "File type not allowed"}, status_code=403)

    # Security: prevent path traversal — must stay inside allowed dirs
    if not any(str(file_path).startswith(str(d.resolve())) for d in ALLOWED_DIRS):
        return JSONResponse({"error": "Access denied"}, status_code=403)
    if not file_path.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)

    mime = MIME_TYPES[file_path.suffix.lower()]
    return FileResponse(
        file_path,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


# Mount MCP app last (catch-all)
app.mount("/", mcp_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)
