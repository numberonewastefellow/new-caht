# VirtualAI Agent Creator Toolkit

Scripts for bulk creating, updating, and managing AI agents (assistants) on a VirtualAI instance.

## Prerequisites

- Python 3.11+
- `pip install requests Pillow`
- A running VirtualAI instance (default: `http://localhost:3000`)
- An API key

## Setup

### 1. API Key

Place your API key in **one** of these locations (checked in order):

| Priority | Location | Example |
|----------|----------|---------|
| 1 | `apikey.txt` | Paste the key as the first line |
| 2 | `.env` file | `VIRTUALAI_API_KEY=vai-xxxxx` |
| 3 | Environment variable | `export VIRTUALAI_API_KEY=vai-xxxxx` |

### 2. Custom URL (optional)

All scripts accept `--url` to point to a different instance:

```bash
python create_assistants.py --list --url http://192.168.1.10:3000
```

## Directory Structure

```
agents_creator/
  config.py               # Shared API client, defaults, label helpers
  create_assistants.py    # Create & update agents from JSON
  import_open_webui.py    # Import Open WebUI exports into VirtualAI
  generate_icon_v2.py     # Generate icons from Iconify SVGs (recommended)
  generate_icon.py        # Generate text-based avatar icons (legacy)
  migrate_labels.py       # Bulk label consolidation tool
  menu.bat                # Windows interactive menu
  apikey.txt              # Your API key (not committed)
  .env                    # Alternative API key location
  assistants/             # Agent JSON definitions (source of truth)
    01_police.json
    02_mro_revenue.json
    ...
    29_universal_agent.json
  open_web_ui/            # Drop Open WebUI exports here for import
  icon_cache/             # Cached SVGs from Iconify (auto-created)
  icons_v2_preview/       # V2 icon previews (local only)
  icons_preview/          # V1 icon previews (local only)
```

---

## Creating Agents from JSON

### JSON Format

Each file in `assistants/` is an array of agent objects:

```json
[
  {
    "name": "FIR Drafting Assistant",
    "description": "Helps police officers draft FIRs in proper legal format.",
    "system_prompt": "You are an FIR Drafting Assistant for Indian police officers...",
    "tool_ids": [1],
    "starter_messages": [
      {
        "name": "Draft FIR from complaint",
        "description": "Provide a complaint narrative",
        "message": "A person has come to the station to file a complaint..."
      }
    ],
    "labels": ["Police & Law", "Legal"]
  }
]
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name of the agent |
| `description` | Yes | Short description shown to users |
| `system_prompt` | Yes | The system instructions for the LLM |
| `tool_ids` | No | List of tool IDs (default: `[1]` = Internal Search) |
| `starter_messages` | No | Up to 4 conversation starters with `name`, `description`, `message` |
| `labels` | No | Category labels (created automatically if they don't exist) |

### Available Tool IDs

| ID | Tool |
|----|------|
| 1 | Internal Search |
| 2 | Image Generation |
| 3 | Web Search |
| 7 | Open URL |

Run `python create_assistants.py --list-tools` to see all tools on your instance.

### Commands

**Create all agents** from `assistants/` folder:

```bash
python create_assistants.py
```

**Create from a specific file:**

```bash
python create_assistants.py --file assistants/01_police.json
```

**Skip duplicates** (default) or **force recreate**:

```bash
python create_assistants.py               # Skips if name already exists
python create_assistants.py --force        # Creates even if duplicate name
```

**List all agents on the server:**

```bash
python create_assistants.py --list
```

**Export all agents to a backup file:**

```bash
python create_assistants.py --export backup.json
```

**Delete an agent by ID:**

```bash
python create_assistants.py --delete 42
```

---

## Updating Existing Agents

Update mode reads JSON files and patches existing agents (matched by name). Only fields present in the JSON are changed; everything else stays intact.

**Update all agents** from `assistants/` folder:

```bash
python create_assistants.py --update
```

**Update from a specific file:**

```bash
python create_assistants.py --update --file assistants/01_police.json
```

**Update a single agent by server ID:**

```bash
python create_assistants.py --update --id 42
```

This is useful for bulk-updating system prompts or labels without recreating agents.

---

## Importing from Open WebUI

Convert and import assistants exported from Open WebUI.

### Step 1: Export from Open WebUI

In Open WebUI, go to **Settings > Models/Assistants > Export** and download the JSON file(s).

### Step 2: Place files

Drop the exported JSON file(s) into the `open_web_ui/` folder.

### Step 3: Preview the conversion

```bash
python import_open_webui.py
```

This shows what will be imported without making any changes.

### Step 4: Import

**Option A** - Save as VirtualAI JSON files (for review before creating):

```bash
python import_open_webui.py --save-only
```

This writes converted files to `assistants/` so you can review and edit them before creating.

**Option B** - Create directly on the server:

```bash
python import_open_webui.py --create
```

**Import a specific file:**

```bash
python import_open_webui.py --file open_web_ui/marketing_expert.json --create
```

### Field Mapping

| Open WebUI | VirtualAI |
|------------|-----------|
| `name` | `name` (underscores/hyphens cleaned up) |
| `meta.description` | `description` |
| `params.system` | `system_prompt` |
| `meta.suggestion_prompts[]` | `starter_messages[]` |
| `meta.tags[]` | Appended to description |
| `meta.capabilities.vision` | Adds Image Generation tool |

---

## Generating Agent Icons

Two icon generators are available:

### `generate_icon_v2.py` — Real SVG Icons (Recommended)

Downloads professional vector icons from the [Iconify API](https://iconify.design/) (200k+ icons from Material Design, Fluent, Carbon, etc.), renders them on vibrant gradient backgrounds, and uploads to the server.

**Dependencies:** `pip install Pillow svglib reportlab requests`

**How it works:**
1. Extracts search keywords from agent name + labels (150+ domain term mappings)
2. Searches Iconify API across preferred icon sets (Fluent, Material Design, Carbon, etc.)
3. Downloads SVG → renders with svglib → creates alpha mask → composites white icon on gradient background
4. Caches SVGs locally in `icon_cache/` to avoid re-downloading

**Commands:**

```bash
python generate_icon_v2.py --search "cybersecurity"  # Test icon search
python generate_icon_v2.py --test                     # Test one agent
python generate_icon_v2.py --preview                  # Preview all (save to icons_v2_preview/)
python generate_icon_v2.py --all                      # Generate & upload for all agents
python generate_icon_v2.py --id 42                    # Single agent
python generate_icon_v2.py --icon mdi:shield-lock     # Force specific icon
python generate_icon_v2.py --style flat               # Colored icon, no background
```

**Styles:**
- `monochrome` (default) — white icon on vibrant gradient background
- `flat` — colored icon on transparent background

### `generate_icon.py` — Text-Based Icons (Legacy)

Generates simple 256x256 avatars with 2-letter initials on colored backgrounds. No internet required.

```bash
python generate_icon.py --all                              # Generate & upload all
python generate_icon.py --file assistants/01_police.json   # From specific file
python generate_icon.py --id 42                            # Single agent
python generate_icon.py --preview                          # Preview only
```

Icons are colored based on the agent's first label. Colors are defined in `DEPARTMENT_COLORS` inside each script.

---

## Managing Labels

### Migrate / Consolidate Labels

The `migrate_labels.py` script handles bulk label reorganization.

**Preview what would change:**

```bash
python migrate_labels.py --dry-run
```

**Apply the migration** (creates new labels, updates all agents):

```bash
python migrate_labels.py --apply
```

**Delete orphaned labels** (labels with zero agents):

```bash
python migrate_labels.py --cleanup
```

### How Labels Work

- Labels are specified by name in JSON files (`"labels": ["Education", "Government"]`)
- `create_assistants.py` automatically creates labels that don't exist yet
- Each agent typically has 1-2 labels for categorization
- The current taxonomy has **45 labels** across these groups:

| Group | Labels |
|-------|--------|
| Government | Police & Law, District Administration, Village & Panchayat, Municipal Services, Government, Legal, Disaster Management, Water & Irrigation |
| Social | Healthcare, Education, Competitive Exams, Sports & Youth, Welfare |
| Infrastructure | Infrastructure, Transport, Labour & Industry, Permits & Licenses, Environment |
| Finance | Finance & Tax, Stock Market, Investment, Banking & Loans, Insurance, Personal Finance, Crypto & Forex, Startups & Business |
| Real Estate | Real Estate, Interior & Renovation |
| Entertainment | Entertainment, Creative Writing, Gaming, Photography & Visual Arts |
| Science | Science, AI & Robotics |
| Technology | Technology, Web & Mobile Dev, Networking & Sysadmin, Cybersecurity, Cloud & DevOps |
| Marketing | Digital Marketing, Social Media, Content Creation, LinkedIn, Twitter & Instagram |
| Religious | Religious Affairs |

---

## Windows Menu

Double-click `menu.bat` for an interactive menu:

```
  ============================================
       VirtualAI Agent Creator
  ============================================

   1. List all assistants
   2. List available tools
   3. Create assistants from assistants\ folder
   4. Import from Open WebUI (preview)
   5. Import from Open WebUI (create directly)
   6. Export all assistants to JSON
   7. Delete an assistant by ID
   8. Exit
```

---

## Typical Workflow

### New agents from scratch

1. Create a JSON file in `assistants/` (e.g., `28_my_category.json`)
2. Define agents with name, description, system_prompt, starters, and labels
3. Run `python create_assistants.py --file assistants/28_my_category.json`
4. Run `python generate_icon.py --file assistants/28_my_category.json`
5. Verify on the VirtualAI UI

### Importing from Open WebUI

1. Export assistants from Open WebUI as JSON
2. Drop files into `open_web_ui/`
3. Run `python import_open_webui.py` to preview
4. Run `python import_open_webui.py --save-only` to convert to VirtualAI format
5. Edit the generated files in `assistants/` (add labels, refine prompts)
6. Run `python create_assistants.py --file assistants/<file>.json`
7. Run `python generate_icon.py --file assistants/<file>.json`

### Updating existing agents

1. Edit the JSON file in `assistants/` (change system_prompt, labels, etc.)
2. Run `python create_assistants.py --update --file assistants/<file>.json`
3. Changes are applied without recreating the agent (preserves ID, chat history)

### Full deployment (all agents)

```bash
python create_assistants.py                # Create all agents
python generate_icon_v2.py --all           # Upload real SVG icons (recommended)
python create_assistants.py --list         # Verify
```

---

## Related: Workflow Creator

Multi-agent workflows (sequential pipelines, LLM-decision routing, HITL) are managed in a separate toolkit:

- **Workflow definitions & deployment:** `backend/tests/workflow_creator/`
- **Workflow JSON files:** `backend/tests/workflow_creator/workflows/` (28 workflows)
- **Test data & sample questions:** `backend/tests/workflow_creator/test_data/README.md`
- **Workflow patterns guide:** `backend/tests/workflow_creator/README_new_workflows.md`
- **Universal Solver docs:** `backend/tests/workflow_creator/UNIVERSAL_SOLVER_README.md`

Quick start:

```bash
cd backend/tests/workflow_creator
python create_workflows.py --list                              # List workflows
python create_workflows.py --file workflows/22_medical_diagnosis.json  # Deploy
python create_workflows.py --run <ID> "Your question here"     # Test run
```
