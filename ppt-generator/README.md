# PPT Generator - MCP Tool Integration for VirtualAI

AI-powered PowerPoint presentation generation integrated into VirtualAI via MCP (Model Context Protocol).

Users describe what they need in natural language, and the system plans, builds, reviews, and delivers a downloadable `.pptx` file -- all within the chat interface.

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
MCP Client opens session to http://ppt-mcp-server:8100/mcp
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

The LLM agent calls multiple MCP tools within one session, so the presentation state (in-memory `Presentation` object) persists across calls.

---

## Components

| Component | Location | Purpose |
|-----------|----------|---------|
| PPT MCP Server | `ppt-generator/` | Docker container running the MCP server with 37 PowerPoint tools |
| Registration Script | `backend/tests/workflow_creator/register_ppt_mcp.py` | Registers MCP server in VirtualAI, discovers tools, attaches to personas |
| Workflow Definition | `backend/tests/workflow_creator/workflows/29_ppt_generator.json` | Defines the 3-agent workflow (Planner, Builder, Reviewer) |
| Deployment Script | `backend/tests/workflow_creator/create_workflows.py` | Deploys the workflow to VirtualAI (shared with all workflows) |

---

## Setup Guide

### Prerequisites

- VirtualAI application running (backend API accessible)
- Docker installed
- Python 3.10+ with `requests` package
- API key for VirtualAI admin (in `backend/tests/agents_creator/apikey.txt` or `VIRTUALAI_API_KEY` env var)

### Step 1: Start the PPT MCP Server

```bash
cd ppt-generator

# Build and start
docker compose up -d

# Verify it's running
docker compose logs -f
# Should show: "Uvicorn running on http://0.0.0.0:8100"
```

The server exposes 37 MCP tools via Streamable HTTP transport on port 8100.

### Step 2: Register the MCP Server in VirtualAI

```bash
cd backend/tests/workflow_creator

# Register server + discover all 37 tools
python register_ppt_mcp.py --url http://localhost:8100
```

This will:
- Create an MCP server entry in VirtualAI's database
- Connect to the server and discover all available tools
- Print the tool IDs for reference

**If your VirtualAI instance runs on a different host/port:**
```bash
python register_ppt_mcp.py --url http://localhost:8100 --base-url http://your-virtualai:3000
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
# List discovered tools
python register_ppt_mcp.py --list-tools

# Re-register (if server URL changed)
python register_ppt_mcp.py --delete
python register_ppt_mcp.py --url http://new-host:8100

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
| MCP server won't start | Check `docker compose logs`. Ensure port 8100 is free. |
| "Transport not configured" error | Server was created without transport. Delete and re-register: `python register_ppt_mcp.py --delete && python register_ppt_mcp.py` |
| Tool discovery returns 0 tools | Ensure the MCP server is running and accessible from the VirtualAI backend. Test with `curl -X POST http://localhost:8100/mcp -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'` |
| Personas not found when attaching | Deploy the workflow first (Step 3), then attach tools (Step 4) |
| "No presentation loaded" errors | This is normal for inter-session calls. The Onyx MCP client handles session management -- all tool calls within one agent turn share a session. |
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

### Workflow
- **Orchestration**: LLM-decision mode (orchestrator LLM decides agent routing)
- **Max steps**: 15 (enough for plan + build + review + revisions)
- **Timeout**: 3000 seconds (50 min -- complex presentations can take time)
- **HITL**: PPT Planner can pause for user input when requests are vague

### Based On
- [GongRzhe/Office-PowerPoint-MCP-Server](https://github.com/GongRzhe/Office-PowerPoint-MCP-Server) (1.5k stars, MIT license)
