# Office MCP Server — PPT, DOCX & PDF Generation

Unified AI-powered document generation integrated into VirtualAI via MCP (Model Context Protocol). Supports **PowerPoint presentations**, **Word documents**, and **PDF reports** — all from a single Docker container.

Users describe what they need in natural language, and the system plans, builds, reviews, and delivers downloadable files — all within the chat interface.

---

## What It Does

| Format | Tools | Library | Output |
|--------|-------|---------|--------|
| **PowerPoint** | 37 `ppt_*` tools | [python-pptx](https://github.com/scanny/python-pptx) | `.pptx` files with slides, charts, tables, shapes, images, professional themes |
| **Word** | 54 `docx_*` tools | [python-docx](https://github.com/python-openxml/python-docx) | `.docx` files with headings, paragraphs, tables, lists, custom styles |
| **PDF** | `docx_convert_to_pdf` | [LibreOffice](https://www.libreoffice.org/) (headless) | `.pdf` files converted from Word documents |

**91 total MCP tools** exposed via a single Streamable HTTP endpoint on port 8100.

---

## How It Works

```
                        VirtualAI Application
  +-------------------------------------------------------------------+
  |                                                                   |
  |  User: "Create a quarterly report with charts" (or PPT/PDF)      |
  |                           |                                       |
  |                           v                                       |
  |                    [Orchestrator LLM]                              |
  |                    Routes to the right                             |
  |                    agents for the format                           |
  |                           |                                       |
  |         +-----------------+-----------------+                     |
  |         |                 |                 |                     |
  |         v                 v                 v                     |
  |   [Planner]          [Builder]         [Reviewer]                 |
  |    Pure LLM         Uses MCP tools     Uses MCP tools             |
  |    No tools          to create file     to check quality          |
  |         |                 |                 |                     |
  +---------|-----------------|-----------------|---------------------+
            |                 |                 |
            |                 v                 v
            |        +-------------------------------+
            |        |   Office MCP Server           |  Docker container
            |        |   (port 8100)                 |  running separately
            |        |                               |
            |        |   37 ppt_* tools (PowerPoint) |
            |        |   54 docx_* tools (Word/PDF)  |
            |        +-------------------------------+
            |                 |
            v                 v
      JSON outline      .pptx / .docx / .pdf
      (structured)      (downloadable files)
```

### Workflows

There are **two workflows** that use this server:

| Workflow | Agents | Output | JSON Definition |
|----------|--------|--------|-----------------|
| **Presentation Generator** | PPT Planner → PPT Builder → PPT Reviewer | `.pptx` | `workflows/29_ppt_generator.json` |
| **Document Generator** | Document Planner → DOCX Builder → DOCX Reviewer | `.docx` / `.pdf` | `workflows/32_document_generator.json` |

Both follow the same 3-phase pattern:

1. **Planning** — Planner analyzes the request, asks clarifying questions if needed, produces a structured JSON outline
2. **Building** — Builder calls MCP tools in sequence to create the file (create → add content → format → save)
3. **Review** — Reviewer inspects the output, checks quality, fixes minor issues (skipped for simple/quick requests)

### PDF Generation

PDF is not a separate workflow — it's built into the Document Generator. When the user mentions "PDF" in their request:

1. The Document Planner sets `output_format: "pdf"` in the outline
2. The Orchestrator instructs the DOCX Builder to convert after creating the document
3. The DOCX Builder calls `docx_convert_to_pdf` which uses LibreOffice headless to convert `.docx` → `.pdf`
4. Both `.docx` and `.pdf` files are saved

---

## Architecture

### Why a Unified Server?

The PPT and DOCX MCP packages use **incompatible versions of FastMCP** (built-in `mcp.server.fastmcp` vs standalone `fastmcp`). The solution:

- Use standalone `fastmcp` as the wrapper
- Mount the DOCX server natively (same package)
- Re-register PPT tools by extracting actual Python functions from the PPT server's internal tool manager

This gives all 91 tools under a single `/mcp` endpoint with namespace prefixes (`ppt_*` and `docx_*`) to avoid name collisions.

### server.py

```python
from fastmcp import FastMCP
from ppt_mcp_server import app as ppt_app
from word_document_server.main import mcp as docx_app, register_tools

register_tools()  # DOCX tools are lazily registered

app = FastMCP("office-mcp-server")
app.mount(docx_app, namespace="docx")  # 54 docx_* tools

# Cross-package mount doesn't work, so re-register PPT tools manually
for name, tool_obj in ppt_app._tool_manager._tools.items():
    app.tool(name=f"ppt_{name}", description=tool_obj.description or "")(tool_obj.fn)

if __name__ == "__main__":
    app.run(transport="streamable-http", host="0.0.0.0", port=8100)
```

### Docker Container

| Property | Value |
|----------|-------|
| Base image | `python:3.11-slim` + LibreOffice Writer |
| Python packages | `office-powerpoint-mcp-server`, `office-word-mcp-server` |
| MCP framework | [FastMCP](https://github.com/modelcontextprotocol/python-sdk) (standalone) |
| Transport | Streamable HTTP (JSON-RPC 2.0 with SSE responses) |
| Port | 8100 |
| State | In-memory per MCP session; saved to disk on save |
| Auth | None (internal Docker network only) |
| Volumes | `office_output` → `/app/output`, `office_templates` → `/app/templates`, `office_documents` → `/app/documents` |
| Health check | TCP socket connection to port 8100 every 30s |

---

## Setup Guide

### Step 1: Build and Start the Container

**Option A: Using dev.bat (Recommended)**

```bash
cd deployment/docker_compose

# Start everything (Onyx + Office MCP server)
dev up

# Or build everything from scratch
dev build

# Start only the Office MCP server
dev up office       # also: dev up ppt, dev up docx

# Build and restart only the Office MCP server
dev build office

# View logs
dev logs office

# Restart
dev restart office

# Stop everything
dev down
```

**Option B: Manual Docker Compose**

```bash
cd office-mcp-server

# Build and start
docker compose up -d

# Connect to Onyx network (required for API server to reach it)
docker network connect onyx_default office-mcp-server

# Verify it's running (should show 91 tools)
docker exec office-mcp-server python -c "
from server import app
print(f'Tools: {len(app._tool_manager._tools)}')
"
```

### Step 2: Register the MCP Server in VirtualAI

```bash
cd backend/tests/workflow_creator

# Register server + discover all 91 tools
python register_office_mcp.py --mcp-url http://localhost:8100
```

This creates an MCP server entry in VirtualAI's database and discovers all available tools.

> **Note:** When registering, the URL `http://localhost:8100` is for the registration script running on the host. The API server accesses it via Docker DNS at `http://office-mcp-server:8100/mcp`. The `/mcp` path is required — without it, tool calls will 404.

### Step 3: Deploy the Workflows

```bash
# Deploy the Presentation Generator workflow (3 PPT agents)
python create_workflows.py --file workflows/29_ppt_generator.json

# Deploy the Document Generator workflow (3 DOCX agents)
python create_workflows.py --file workflows/32_document_generator.json
```

Each creates:
- Agent personas (Planner, Builder, Reviewer) with specialized system prompts
- A workflow linking the agents together with orchestrator routing
- A wrapper persona visible in the VirtualAI chat UI
- Starter messages for quick testing

### Step 4: Attach MCP Tools to Agents

```bash
# Attach tools: ppt_* → PPT agents, docx_* → DOCX agents
python register_office_mcp.py --attach-to-personas
```

This patches the Builder and Reviewer personas with the appropriate MCP tool IDs:

| Persona | Gets Tools |
|---------|------------|
| WF PPT Builder | 37 `ppt_*` tools |
| WF PPT Reviewer | 37 `ppt_*` tools |
| WF DOCX Builder | 54 `docx_*` tools |
| WF DOCX Reviewer | 54 `docx_*` tools |

### Step 5: Use It

Open VirtualAI in your browser. You should see two new workflows in the agent list:

- **Presentation Generator** — for PowerPoint files
- **Document Generator** — for Word documents and PDFs

Click either one and try the starter messages, or describe your own document.

---

## Available MCP Tools (91 total)

### PowerPoint Tools (37 `ppt_*`)

#### Presentation Lifecycle
| Tool | What It Does |
|------|-------------|
| `ppt_create_presentation` | Create a new blank presentation |
| `ppt_create_presentation_from_template` | Create from an existing .pptx template |
| `ppt_open_presentation` | Open an existing .pptx file |
| `ppt_save_presentation` | Save to a file path |
| `ppt_get_presentation_info` | Get slide count, dimensions, metadata |
| `ppt_set_core_properties` | Set title, author, keywords |

#### Slides & Content
| Tool | What It Does |
|------|-------------|
| `ppt_add_slide` | Add a new slide with a layout |
| `ppt_get_slide_info` | Inspect a slide's shapes and placeholders |
| `ppt_populate_placeholder` | Fill a placeholder with text |
| `ppt_add_bullet_points` | Add bullet points to a placeholder |
| `ppt_manage_text` | Create/edit text boxes with full formatting |
| `ppt_extract_slide_text` | Extract all text from one slide |
| `ppt_extract_presentation_text` | Extract all text from all slides |

#### Visual Elements
| Tool | What It Does |
|------|-------------|
| `ppt_add_chart` | Add column, bar, line, or pie chart |
| `ppt_update_chart_data` | Update existing chart data |
| `ppt_add_table` | Add a data table |
| `ppt_format_table_cell` | Format individual table cells |
| `ppt_add_shape` | Add rectangles, circles, arrows, etc. |
| `ppt_add_connector` | Add lines/arrows between points |
| `ppt_manage_image` | Add and enhance images |

#### Design & Templates
| Tool | What It Does |
|------|-------------|
| `ppt_apply_professional_design` | Apply professional styling to slides |
| `ppt_apply_picture_effects` | Shadow, glow, reflection on images |
| `ppt_list_slide_templates` | List available built-in templates |
| `ppt_apply_slide_template` | Apply a template to a slide |
| `ppt_create_slide_from_template` | Create a new slide from a template |
| `ppt_create_presentation_from_templates` | Build full presentation from template sequence |
| `ppt_auto_generate_presentation` | Auto-generate a presentation from a topic |
| `ppt_optimize_slide_text` | Auto-resize text to fit |
| `ppt_manage_fonts` | Analyze and manage fonts |
| `ppt_manage_slide_transitions` | Add slide transitions |
| `ppt_manage_slide_masters` | Inspect slide masters and layouts |
| `ppt_manage_hyperlinks` | Add clickable links |
| `ppt_get_template_file_info` | Get template file properties |
| `ppt_get_template_info` | Get template layout details |

#### Server Management
| Tool | What It Does |
|------|-------------|
| `ppt_list_presentations` | List all open presentations |
| `ppt_switch_presentation` | Switch active presentation |
| `ppt_get_server_info` | Server version and status |

### Word Document Tools (54 `docx_*`)

#### Document Lifecycle
| Tool | What It Does |
|------|-------------|
| `docx_create_document` | Create a new Word document |
| `docx_copy_document` | Copy an existing document |
| `docx_list_available_documents` | List all documents on the server |
| `docx_get_document_info` | Page count, paragraph count, metadata |
| `docx_get_document_text` | Extract all text content |
| `docx_get_document_xml` | Get raw document XML |
| `docx_get_document_outline` | Get heading hierarchy |
| `docx_convert_to_pdf` | **Convert DOCX to PDF** (via LibreOffice) |

#### Content
| Tool | What It Does |
|------|-------------|
| `docx_add_heading` | Add a heading (levels 1-4) |
| `docx_add_paragraph` | Add a paragraph (also: bullet lists, numbered lists via `style` param) |
| `docx_add_table` | Add a data table |
| `docx_add_picture` | Add an image |
| `docx_add_page_break` | Insert a page break |

#### Formatting
| Tool | What It Does |
|------|-------------|
| `docx_format_text` | Bold, italic, underline, font size, color |
| `docx_create_custom_style` | Create reusable styles |
| `docx_search_and_replace` | Find and replace text |
| `docx_delete_paragraph` | Remove a paragraph |

#### Tables (15 tools)
| Tool | What It Does |
|------|-------------|
| `docx_highlight_table_header` | Style header row |
| `docx_auto_fit_table_columns` | Auto-size columns |
| `docx_format_table` | Apply table-wide formatting |
| `docx_set_table_cell_shading` | Color individual cells |
| `docx_merge_table_cells` | Merge cells |
| `docx_set_table_column_width` | Set column widths |
| `docx_add_row_to_table` | Add rows |
| `docx_delete_table_row` | Remove rows |
| `docx_set_table_cell_text` | Set cell content |
| `docx_get_table_data` | Read table content |
| `docx_set_table_borders` | Configure borders |
| ... | *(and more table tools)* |

#### Search & Insert
| Tool | What It Does |
|------|-------------|
| `docx_find_text_in_document` | Search for text |
| `docx_get_paragraph_text_from_document` | Get paragraph by index |
| `docx_insert_header_near_text` | Insert heading near found text |
| `docx_insert_line_or_paragraph_near_text` | Insert content near found text |
| `docx_insert_numbered_list_near_text` | Insert numbered list near text |
| `docx_insert_bullet_list_near_text` | Insert bullet list near text |
| `docx_insert_table_near_text` | Insert table near text |

#### Comments
| Tool | What It Does |
|------|-------------|
| `docx_get_all_comments` | List all comments |
| `docx_get_comments_by_author` | Filter comments by author |
| `docx_get_comments_for_paragraph` | Get comments on a paragraph |

---

## Customization

### Custom PPT Templates

Place `.pptx` template files in the `office_templates` Docker volume (mounted at `/app/templates`). The MCP server discovers them automatically.

```bash
# Copy a template into the container
docker cp my-template.pptx office-mcp-server:/app/templates/
```

### Changing the LLM Model

Edit the workflow JSON and redeploy:

```json
"orchestrator_llm_provider": "v",
"orchestrator_llm_model": "gpt-4.1"
```

### Adding Extra Tools to Agents

To give agents additional tools (e.g., WebSearch for researching content):
1. Find the tool ID from the VirtualAI admin panel
2. Add it to the agent's `tool_ids` via the persona editor or API

---

## Management Commands

```bash
cd backend/tests/workflow_creator

# List all discovered tools with IDs
python register_office_mcp.py --list-tools

# Re-register (if server URL changed)
python register_office_mcp.py --delete
python register_office_mcp.py --mcp-url http://new-host:8100

# Re-attach tools after re-registration
python register_office_mcp.py --attach-to-personas

# Deploy or update a workflow
python create_workflows.py --file workflows/29_ppt_generator.json
python create_workflows.py --file workflows/32_document_generator.json

# List all workflows
python create_workflows.py --list
```

---

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Office MCP Server | `office-mcp-server/` | Docker container with 91 PPT + DOCX + PDF tools |
| Registration Script | `backend/tests/workflow_creator/register_office_mcp.py` | Registers MCP server, discovers tools, attaches to personas |
| PPT Workflow | `backend/tests/workflow_creator/workflows/29_ppt_generator.json` | 3-agent PPT workflow (Planner, Builder, Reviewer) |
| DOCX Workflow | `backend/tests/workflow_creator/workflows/32_document_generator.json` | 3-agent DOCX/PDF workflow (Planner, Builder, Reviewer) |
| Deployment Script | `backend/tests/workflow_creator/create_workflows.py` | Deploys workflows to VirtualAI |
| Dev Helper | `deployment/docker_compose/dev.bat` | Build/start/stop the server alongside Onyx |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP server won't start | Check `dev logs office` or `docker compose logs`. Ensure port 8100 is free. |
| Tool discovery returns 0 tools | Ensure the MCP server is running. Test: `curl -X POST http://localhost:8100/mcp -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'` |
| API server can't reach MCP server | Run `docker network connect onyx_default office-mcp-server` or use `dev up` which does this automatically |
| "421 Misdirected Request" | DNS rebinding protection issue. The server disables this by default — rebuild with `dev build office` |
| Tool calls return 404 | The MCP server URL must include `/mcp` path. Check that the registered URL is `http://office-mcp-server:8100/mcp` (not just port 8100) |
| PDF conversion fails | LibreOffice must be installed in the container. Check: `docker exec office-mcp-server libreoffice --version`. Rebuild if missing: `dev build office` |
| PDF conversion not triggered | The Builder LLM may run out of output tokens on complex documents before reaching the conversion step. Use simpler documents or split into fewer sections. |
| Personas not found when attaching | Deploy the workflows first (Step 3), then attach tools (Step 4) |
| `docx_add_page_break` fails | The Builder must pass `filename` to every tool call. This is a known prompt issue — the persona prompt has been updated to emphasize this. |
| Generated PPTX looks basic | python-pptx has styling limitations. Use `ppt_apply_professional_design` and `ppt_apply_slide_template` for better results. |
| Container healthcheck failing | The healthcheck uses TCP socket (not HTTP) because the `/mcp` endpoint returns 406 for plain GET requests. This is expected. |

---

## Technical Details

### MCP Session Persistence

VirtualAI implements **Pattern A: Client-Side Session Pool** for MCP session management. All MCP tool calls within a single agent step share the same persistent session, preserving in-memory state (loaded presentations/documents) across sequential tool calls. See [MCP_SESSION_PERSISTENCE.md](MCP_SESSION_PERSISTENCE.md) for the full architecture.

### Based On

- [GongRzhe/Office-PowerPoint-MCP-Server](https://github.com/GongRzhe/Office-PowerPoint-MCP-Server) (PPT tools, MIT license)
- [GongRzhe/Office-Word-MCP-Server](https://github.com/GongRzhe/Office-Word-MCP-Server) (DOCX tools, MIT license)
- [LibreOffice](https://www.libreoffice.org/) (PDF conversion, MPL-2.0 license)
