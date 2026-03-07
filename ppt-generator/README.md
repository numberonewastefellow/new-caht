# PPT Generator - MCP Tool Integration for VirtualAI

AI-powered PowerPoint presentation generation integrated into VirtualAI via MCP (Model Context Protocol).

Users describe what they need in natural language, and the system plans, builds, reviews, and delivers a downloadable `.pptx` file -- all within the chat interface.

---

## Purpose

The PPT MCP Server is a **stateful MCP server** that exposes 37 PowerPoint manipulation tools. It runs as a standalone Docker container and integrates with VirtualAI's multi-agent workflow system.

**Why a separate MCP server?**

- PowerPoint generation requires `python-pptx`, a specialized library -- keeping it isolated avoids bloating the main backend image
- The MCP protocol provides a standard interface for tool discovery and invocation
- The server maintains **in-memory presentation state** per session, allowing multi-step construction (create → add slides → format → save) across sequential tool calls
- Any MCP-compatible client can use these tools, not just VirtualAI

**What it does:**

- Creates, edits, and saves `.pptx` files using 37 fine-grained tools
- Supports charts, tables, bullet points, images, shapes, connectors, and professional design themes
- Maintains presentation state in memory within a session, saving to disk on `save_presentation`
- Integrates with VirtualAI's workflow engine as a 3-agent pipeline: Planner → Builder → Reviewer

---

## How It Works

### The Big Picture

```
                         VirtualAI Application
  +-----------------------------------------------------------------+
  |                                                                 |
  |   User: "Create a 5-slide pitch deck about AI in healthcare"   |
  |                           |                                     |
  |                           v                                     |
  |                    [Orchestrator LLM]                           |
  |                    Decides which agent                          |
  |                    to call and when                             |
  |                           |                                     |
  |            +--------------+--------------+                      |
  |            |              |              |                      |
  |            v              v              v                      |
  |     [PPT Planner]  [PPT Builder]  [PPT Reviewer]               |
  |      Pure LLM        Uses MCP       Uses MCP                   |
  |      No tools         tools          tools                     |
  |            |              |              |                      |
  +-----------|--------------|--------------|-----------------------+
              |              |              |
              |              v              v
              |     +---------------------+
              |     | PPT MCP Server      |  <-- Docker container
              |     | (port 8100)         |      running separately
              |     |                     |
              |     | 37 tools:           |
              |     | - create_presentation
              |     | - add_slide         |
              |     | - manage_text       |
              |     | - add_chart         |
              |     | - add_table         |
              |     | - save_presentation |
              |     | - ...               |
              |     +---------------------+
              |              |
              v              v
        JSON outline    .pptx file
        (structured)    (PowerPoint)
```

### Step-by-Step Flow

1. **User sends a message** in VirtualAI chat (e.g., "Create a quarterly review deck with revenue charts")

2. **Orchestrator** receives the message and routes it through 3 phases:

3. **Phase 1 - Planning** (PPT Planner agent):
   - Analyzes the request
   - If too vague, asks clarifying questions (pauses for user input)
   - Produces a structured JSON outline with slide-by-slide specs:
     - Layout type (title, content, chart, table)
     - Title and content for each slide
     - Chart data (categories, series, values)
     - Table data (headers, rows)
     - Color scheme and design preferences

4. **Phase 2 - Building** (PPT Builder agent):
   - Receives the JSON outline
   - Calls MCP tools in sequence via the PPT MCP Server:
     ```
     create_presentation  -->  add_slide (x N)  -->  populate_placeholder
           |                        |                       |
           v                        v                       v
     add_chart / add_table    manage_text           apply_professional_design
           |                        |                       |
           +------------------------+-----------------------+
                                    |
                                    v
                            save_presentation
                            "/app/output/deck.pptx"
     ```
   - Reports the saved file path

5. **Phase 3 - Review** (PPT Reviewer agent, optional):
   - Opens the generated file via MCP
   - Extracts all text, checks slide count and structure
   - Fixes minor issues (text overflow, missing content)
   - Reports quality assessment
   - Skipped for quick/simple presentations (3 or fewer slides)

6. **Delivery**: Orchestrator summarizes what was created with the download path

### How MCP Connects Everything

VirtualAI already has built-in MCP support. The PPT MCP Server is just another MCP server registered in the admin panel. At runtime:

```
Agent LLM decides to call "create_presentation"
        |
        v
VirtualAI MCPTool class (backend/onyx/tools/tool_implementations/mcp/)
        |
        v
MCP Client opens persistent session to http://ppt-mcp-server:8100/mcp
        |
        v
JSON-RPC 2.0: {"method": "tools/call", "params": {"name": "create_presentation", ...}}
        |
        v
PPT MCP Server executes python-pptx code, returns result
        |
        v
MCPTool wraps result in ToolResponse, streams back to chat UI
```

**Session Persistence:** The VirtualAI MCP client uses a client-side session pool (Pattern A from [MCP_SESSION_PERSISTENCE.md](MCP_SESSION_PERSISTENCE.md)). All tool calls within one agent step share the same `ClientSession`, so the PPT MCP Server's in-memory presentation state persists across `create_presentation` → `add_slide` → `save_presentation` calls. Sessions are automatically cleaned up when the agent step finishes.

---

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| PPT MCP Server | `ppt-generator/` | Docker container running the MCP server with 37 PowerPoint tools |
| Registration Script | `backend/tests/workflow_creator/register_ppt_mcp.py` | Registers MCP server in VirtualAI, discovers tools, attaches to personas |
| Workflow Definition | `backend/tests/workflow_creator/workflows/29_ppt_generator.json` | Defines the 3-agent workflow (Planner, Builder, Reviewer) |
| Deployment Script | `backend/tests/workflow_creator/create_workflows.py` | Deploys the workflow to VirtualAI (shared with all workflows) |

---

## Docker Container

### Image Details

| Property | Value |
|----------|-------|
| Base image | `python:3.11-slim` |
| Core library | [python-pptx](https://github.com/scanny/python-pptx) via `office-powerpoint-mcp-server` (PyPI) |
| MCP framework | [FastMCP](https://github.com/modelcontextprotocol/python-sdk) |
| Transport | Streamable HTTP (JSON-RPC 2.0 over HTTP with SSE responses) |
| Port | 8100 |
| State | In-memory per session; saved to disk on `save_presentation` |
| Auth | None (intended for internal Docker network only) |
| Volumes | `ppt_output` → `/app/output` (generated files), `ppt_templates` → `/app/templates` (custom templates) |
| Health check | HTTP GET to `http://localhost:8100/` every 30s |

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir office-powerpoint-mcp-server
RUN mkdir -p /app/templates /app/output
ENV PPT_TEMPLATE_PATH=/app/templates
EXPOSE 8100
CMD ["python", "-c", "from ppt_mcp_server import app; \
  app.settings.port = 8100; \
  app.settings.host = '0.0.0.0'; \
  app.settings.transport_security.enable_dns_rebinding_protection = False; \
  app.run(transport='streamable-http')"]
```

**Note:** DNS rebinding protection is disabled because the container is accessed via Docker DNS hostname (`ppt-mcp-server`) rather than `localhost`. This is safe because the container is only accessible on the internal Docker network.

### docker-compose.yml

```yaml
services:
  ppt-mcp-server:
    build: .
    container_name: ppt-mcp-server
    ports:
      - "8100:8100"
    volumes:
      - ppt_output:/app/output
      - ppt_templates:/app/templates
    environment:
      - PPT_TEMPLATE_PATH=/app/templates
    restart: unless-stopped

volumes:
  ppt_output:
  ppt_templates:
```

### Network Connectivity

The PPT MCP server runs in its own Docker Compose project (`ppt-generator/`), separate from the main Onyx stack (`deployment/docker_compose/`). For the API server to reach it by hostname, the container must be connected to the `onyx_default` network:

```bash
docker network connect onyx_default ppt-mcp-server
```

The `dev.bat` helper does this automatically on `dev up` and `dev build`. If you start the container manually, run the network connect command after `docker compose up -d`.

---

## Setup Guide

### Option A: Using dev.bat (Recommended)

The `dev.bat` helper in `deployment/docker_compose/` manages the PPT MCP server alongside the main Onyx stack.

```bash
cd deployment/docker_compose

# Start everything (Onyx + PPT MCP server)
dev up

# Or build everything from scratch
dev build

# Start only the PPT MCP server
dev up ppt

# Build and restart only the PPT MCP server
dev build ppt

# View PPT MCP server logs
dev logs ppt

# Restart just the PPT MCP server
dev restart ppt

# Stop everything (including PPT MCP server)
dev down
```

After the services are up, proceed to [Step 2: Register](#step-2-register-the-mcp-server-in-virtualai).

### Option B: Manual Docker Compose

```bash
cd ppt-generator

# Build and start
docker compose up -d

# Connect to Onyx network (required for API server to reach it)
docker network connect onyx_default ppt-mcp-server

# Verify it's running
docker compose logs -f
# Should show: "Uvicorn running on http://0.0.0.0:8100"
```

The server exposes 37 MCP tools via Streamable HTTP transport on port 8100.

### Step 2: Register the MCP Server in VirtualAI

```bash
cd backend/tests/workflow_creator

# Register server + discover all 37 tools
python register_ppt_mcp.py --mcp-url http://localhost:8100
```

This will:
- Create an MCP server entry in VirtualAI's database
- Connect to the server and discover all available tools
- Print the tool IDs for reference

**If your VirtualAI instance runs on a different host/port:**
```bash
python register_ppt_mcp.py --mcp-url http://localhost:8100 --url http://your-virtualai:3000
```

### Step 3: Deploy the Workflow

```bash
# Deploy the Presentation Generator workflow (creates 3 agent personas)
python create_workflows.py --file workflows/29_ppt_generator.json
```

This creates:
- **WF PPT Planner** persona (no tools, pure LLM planning)
- **WF PPT Builder** persona (will get MCP tools attached)
- **WF PPT Reviewer** persona (will get MCP tools attached)
- **Presentation Generator** workflow linking them together
- A wrapper persona visible in the VirtualAI chat UI

### Step 4: Attach MCP Tools to Agents

```bash
# Attach the 37 MCP tools to the PPT Builder and Reviewer personas
python register_ppt_mcp.py --attach-to-personas
```

This patches the `WF PPT Builder` and `WF PPT Reviewer` personas to include all discovered MCP tool IDs, so they can call the PowerPoint manipulation tools at runtime.

### Step 5: Use It

Open VirtualAI in your browser. You should see "Presentation Generator" in the agent/workflow list. Click it and try one of the starter messages, or describe your own presentation.

---

## Available MCP Tools (37 total)

### Presentation Lifecycle
| Tool | What It Does |
|------|-------------|
| `create_presentation` | Create a new blank presentation |
| `create_presentation_from_template` | Create from an existing .pptx template |
| `open_presentation` | Open an existing .pptx file |
| `save_presentation` | Save to a file path |
| `get_presentation_info` | Get slide count, dimensions, metadata |
| `set_core_properties` | Set title, author, keywords |

### Slides & Content
| Tool | What It Does |
|------|-------------|
| `add_slide` | Add a new slide with a layout |
| `get_slide_info` | Inspect a slide's shapes and placeholders |
| `populate_placeholder` | Fill a placeholder with text |
| `add_bullet_points` | Add bullet points to a placeholder |
| `manage_text` | Create/edit text boxes with full formatting |
| `extract_slide_text` | Extract all text from one slide |
| `extract_presentation_text` | Extract all text from all slides |

### Visual Elements
| Tool | What It Does |
|------|-------------|
| `add_chart` | Add column, bar, line, or pie chart |
| `update_chart_data` | Update existing chart data |
| `add_table` | Add a data table |
| `format_table_cell` | Format individual table cells |
| `add_shape` | Add rectangles, circles, arrows, etc. |
| `add_connector` | Add lines/arrows between points |
| `manage_image` | Add and enhance images |

### Design & Templates
| Tool | What It Does |
|------|-------------|
| `apply_professional_design` | Apply professional styling to slides |
| `apply_picture_effects` | Add shadow, glow, reflection to images |
| `list_slide_templates` | List available built-in templates |
| `apply_slide_template` | Apply a template to a slide |
| `create_slide_from_template` | Create a new slide from a template |
| `auto_generate_presentation` | Auto-generate a full presentation from a topic |
| `optimize_slide_text` | Auto-resize text to fit |
| `manage_fonts` | Analyze and manage fonts |
| `manage_slide_transitions` | Add slide transitions |
| `manage_slide_masters` | Inspect slide masters and layouts |
| `manage_hyperlinks` | Add clickable links |

### Server Management
| Tool | What It Does |
|------|-------------|
| `list_presentations` | List all open presentations |
| `switch_presentation` | Switch active presentation |
| `get_server_info` | Server version and status |

---

## Management Commands

```bash
cd backend/tests/workflow_creator

# List discovered tools
python register_ppt_mcp.py --list-tools

# Re-register (if server URL changed)
python register_ppt_mcp.py --delete
python register_ppt_mcp.py --mcp-url http://new-host:8100

# Re-attach tools after re-registration
python register_ppt_mcp.py --attach-to-personas

# Update workflow definition
python create_workflows.py --update --file workflows/29_ppt_generator.json

# List all workflows
python create_workflows.py --list
```

---

## Customization

### Custom Templates

Place `.pptx` template files in the `ppt_templates` Docker volume (mounted at `/app/templates`). The MCP server will discover them and make them available via `create_presentation_from_template` and `list_slide_templates`.

### Changing the LLM Model

Edit `workflows/29_ppt_generator.json` and change:
```json
"orchestrator_llm_provider": "v",
"orchestrator_llm_model": "gpt-4.1"
```

### Adding More Agent Capabilities

To give agents additional tools (e.g., WebSearch for researching content):
1. Note the tool ID for WebSearch from the VirtualAI admin panel
2. Add it to the agent's `tool_ids` via the persona editor or API

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP server won't start | Check `dev logs ppt` or `docker compose logs`. Ensure port 8100 is free. |
| "Transport not configured" error | Server was created without transport. Delete and re-register: `python register_ppt_mcp.py --delete && python register_ppt_mcp.py` |
| Tool discovery returns 0 tools | Ensure the MCP server is running and accessible from the VirtualAI backend. Test with `curl -X POST http://localhost:8100/mcp -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'` |
| Personas not found when attaching | Deploy the workflow first (Step 3), then attach tools (Step 4) |
| API server can't reach MCP server | Run `docker network connect onyx_default ppt-mcp-server` or use `dev up` which does this automatically |
| "421 Misdirected Request" error | DNS rebinding protection is blocking Docker hostnames. The Dockerfile already disables this -- rebuild with `dev build ppt` |
| Generated PPTX looks basic | The MCP server uses python-pptx which has limitations. For richer designs, use `apply_professional_design` and `apply_slide_template` tools. |

---

## Technical Details

### MCP Server
- **Image**: `python:3.11-slim` + `office-powerpoint-mcp-server` (PyPI)
- **Core library**: [python-pptx](https://github.com/scanny/python-pptx) (3.2k stars)
- **MCP framework**: [FastMCP](https://github.com/modelcontextprotocol/python-sdk)
- **Transport**: Streamable HTTP (JSON-RPC 2.0 over HTTP with SSE responses)
- **State**: In-memory per session (presentations are Python objects, saved to disk on `save_presentation`)
- **Auth**: None (intended for internal network only)

### MCP Session Persistence

VirtualAI implements **Pattern A: Client-Side Session Pool** for MCP session management. This ensures all MCP tool calls within a single agent step share the same persistent session, preserving in-memory state (like loaded presentations) across sequential tool calls. See [MCP_SESSION_PERSISTENCE.md](MCP_SESSION_PERSISTENCE.md) for the full architecture analysis.

### Workflow
- **Orchestration**: LLM-decision mode (orchestrator LLM decides agent routing)
- **Max steps**: 15 (enough for plan + build + review + revisions)
- **Timeout**: 3000 seconds (50 min -- complex presentations can take time)
- **HITL**: PPT Planner can pause for user input when requests are vague

### Based On
- [GongRzhe/Office-PowerPoint-MCP-Server](https://github.com/GongRzhe/Office-PowerPoint-MCP-Server) (1.5k stars, MIT license)
