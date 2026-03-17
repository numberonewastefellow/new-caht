# Workflow Visual Builder — UI/UX Improvements (Implemented)

> **Status**: IMPLEMENTED — Ready for review
> **Date**: 2026-03-17
> **Scope**: `web/src/components/workflow-builder/` and `web/src/refresh-pages/WorkflowVisualBuilderPage.tsx`

---

## Before vs After Layout

### Before

```
┌──────────────────────────────────────────────────────────────────┐
│ GlobalConfigToolbar                                       [56px] │
│ [Back] [Name] [Mode toggle] [Settings gear popover] [JSON] [Save]│
├──────────────┬─────────────────────────┬─────────────────────────┤
│  Sidebar     │   ReactFlow Canvas      │  Config Panel           │
│  FIXED 264px │   (flex: 1)             │  FIXED 320px            │
│              │                         │  (one long scroll)      │
│  Flat list:  │                         │                         │
│  - Utils     │                         │  Agent, Name, Desc,     │
│  - Agents    │                         │  Output, Options,       │
│  (mixed)     │                         │  LLM, Tools, Knowledge, │
│              │                         │  Advanced, Description  │
│  NO TABS     │                         │  ALL IN ONE SCROLL      │
│  NO RESIZE   │                         │  NO TABS                │
│  NO COLLAPSE │                         │  NO COLLAPSE            │
└──────────────┴─────────────────────────┴─────────────────────────┘
```

### After

```
┌──────────────────────────────────────────────────────────────────┐
│ GlobalConfigToolbar                                       [56px] │
│ [Back] [Name] [Mode toggle] [Settings gear] [JSON] [Save]       │
├─┬────────────┬─┬───────────────────────┬─┬───────────────────┬───┤
│ │  Sidebar   │R│   ReactFlow Canvas    │R│  Config Panel     │   │
│ │ 200-400px  │E│   (flex: 1)           │E│  280-500px        │   │
│ │ RESIZABLE  │S│                       │S│  RESIZABLE        │   │
│ │            │I│                       │I│                   │   │
│ │[Agents][Utils][Config]               │Z│[Properties][Advanced][JSON]
│ │  Tab bar   │E│                       │E│  Tab bar          │   │
│ │  ◀ collapse│ │                       │ │  collapse ▶  [✕]  │   │
│ │            │ │                       │ │                   │   │
│ │ Tab content│ │                       │ │ Tab content       │   │
│ │ per tab    │ │                       │ │ per tab           │   │
├─┴────────────┴─┴───────────────────────┴─┴───────────────────┴───┤
│ Keyboard: [ = toggle sidebar, ] = toggle config panel            │
└──────────────────────────────────────────────────────────────────┘
```

---

## Feature 1: Tabbed Sidebar

**File**: `AgentSidebar.tsx`

The sidebar now has 3 tabs along the top:

| Tab | Label | Content |
|-----|-------|---------|
| Agents | `Agents` | Search bar, "New Agent" button, draggable agent cards (regular agents only) |
| Utilities | `Utils` | Draggable cards: Condition (If-Else), HTTP Request, Code Executor |
| Settings | `Config` | Workflow-level settings (moved from toolbar gear popover) |

**Config tab fields** (mirrors GlobalConfigToolbar settings popover exactly):
- Description (textarea)
- Orchestrator Prompt (textarea, only shown in `llm_decision` mode)
- Orchestrator Model (LLMSelector dropdown, only shown in `llm_decision` mode)
- Max Total Steps (number input, 1-50)
- Max Calls per Agent (number input, 1-10)
- Timeout in seconds (number input, 30-7200)
- Public toggle (switch)

**Note**: The toolbar gear popover still works as a secondary access point. Both locations update the same `meta` state via `onUpdateMeta`.

**New props added to AgentSidebar**:
- `meta?: WorkflowMeta` — workflow settings data
- `onUpdateMeta?: (partial: Partial<WorkflowMeta>) => void` — settings update callback
- `llmProviders?: LLMProviderDescriptor[]` — for LLM selector dropdown
- `collapsed?: boolean` — collapse state
- `onToggleCollapse?: () => void` — collapse toggle callback

---

## Feature 2: Tabbed Config Panel

**File**: `NodeConfigPanel.tsx`

When an **agent node** is selected, the config panel now has 3 tabs:

| Tab | Label | Content |
|-----|-------|---------|
| Properties | `Properties` | Agent selector, Step name, Description, Output key, HTTP/Code utility config, Options (Terminal, HITL, Promote), Agent description |
| Advanced | `Advanced` | LLM override, Tools override, Knowledge override, Advanced section (Input mapping JSON, Condition JSON) |
| JSON | `JSON` | Read-only JSON view of the node's full configuration (for debugging/copying) |

**For utility agents** (HTTP Request, Code Executor): The `Advanced` tab is hidden since utility agents don't support LLM/Tools/Knowledge overrides.

**For Conditional Router nodes**: The existing `ConditionConfigPanel` renders as before (no tabs needed — it's already focused on a single concern).

**New props added to NodeConfigPanel**:
- `collapsed?: boolean` — collapse state
- `onToggleCollapse?: () => void` — collapse toggle callback

The header now has both a collapse chevron (`▶`) and the existing close button (`✕`).

---

## Feature 3: Resizable Panels

**File**: `WorkflowVisualBuilderPage.tsx`, `WorkflowCanvas.css`

Both the sidebar and config panel are now **resizable via drag handles**.

| Panel | Default | Min | Max | localStorage key |
|-------|---------|-----|-----|-----------------|
| Sidebar | 264px | 200px | 400px | `wfb-sidebar-width` |
| Config Panel | 320px | 280px | 500px | `wfb-config-width` |

**Behavior**:
- 4px transparent vertical bar between panels — turns accent-colored on hover
- Click and drag to resize
- **Double-click** the handle to reset to default width
- Widths persist across sessions via `localStorage`
- Canvas (flex: 1) automatically fills remaining space
- No external library used — pure mousedown/mousemove/mouseup handlers

**CSS**: `.wfb-resize-handle` — transparent by default, accent color on hover/active, `col-resize` cursor.

**Implementation detail**: The sidebar/config panel no longer have fixed CSS `width`/`min-width`. Instead, widths are controlled via inline `style` from the parent page component.

---

## Feature 4: Collapsible Panels

**Files**: `AgentSidebar.tsx`, `NodeConfigPanel.tsx`, `WorkflowVisualBuilderPage.tsx`

Both panels can be collapsed to a 36px thin strip with an expand icon.

**Collapse buttons**:
- Sidebar: `◀` chevron in the tab bar (rightmost position)
- Config panel: `▶` chevron in the header (next to the `✕` close button)

**Collapsed state**:
- Panel renders as a 36px-wide strip with a centered chevron icon
- Clicking the chevron expands back to the previous width
- Canvas auto-fills the freed space

**Keyboard shortcuts**:
- `[` — Toggle sidebar collapsed/expanded
- `]` — Toggle config panel collapsed/expanded
- Shortcuts are **disabled** when focus is in an `<input>`, `<textarea>`, or `<select>` field

**Persistence**: Collapsed states saved to `localStorage` keys `wfb-sidebar-collapsed` and `wfb-config-collapsed`.

---

## Feature 5: Visual Polish

**File**: `WorkflowCanvas.css`

| Element | Change |
|---------|--------|
| Agent nodes | 4px accent-colored left border (`var(--virtualai-accent)`) |
| Agent nodes (selected) | Accent glow box-shadow (`var(--virtualai-accent-glow)`) |
| Condition nodes | 4px amber left border (`#f59e0b`) |
| Condition nodes (selected) | Amber glow box-shadow |
| All nodes | `border-radius: 12px` |
| Tab bars | Accent-colored bottom border on active tab |
| Resize handles | Accent-colored on hover |
| Dark mode | All new styles use CSS variables, no hardcoded colors |

---

## Files Changed

| File | What Changed |
|------|-------------|
| `AgentSidebar.tsx` | Rewrote with 3-tab layout, Settings tab with LLMSelector, collapse support. New imports: `LLMSelector`, `parseLlmDescriptor`, `structureValue`, `WorkflowMeta`, `LLMProviderDescriptor`. `CONDITION_DRAG_TYPE` still exported. |
| `NodeConfigPanel.tsx` | Added `ConfigTab` state, split body into Properties/Advanced/JSON tabs, added collapse support, added JSON view with `useMemo`. `ConditionConfigPanel` receives new `onToggleCollapse` prop. All sub-components (LlmSection, ToolsSection, KnowledgeSection, AdvancedSection, HttpRequestConfigSection, CodeExecutorConfigSection) are **unchanged**. |
| `WorkflowVisualBuilderPage.tsx` | Added panel width state (`sidebarWidth`, `configWidth`), collapse state (`sidebarCollapsed`, `configCollapsed`), localStorage persistence, keyboard shortcuts (`[`, `]`), resize handlers (`handleSidebarResize`, `handleConfigResize`). Sidebar and config panel wrapped in `<div style={...}>` for dynamic widths. Resize handles rendered between panels. |
| `WorkflowCanvas.css` | Removed fixed `width`/`min-width` from `.wfb-sidebar` and `.wfb-config-panel`. Added: `.wfb-sidebar-tabs`, `.wfb-sidebar-tab`, `.wfb-sidebar-tab--active`, `.wfb-sidebar-settings`, `.wfb-config-tabs`, `.wfb-config-tab`, `.wfb-config-tab--active`, `.wfb-resize-handle`, `.wfb-sidebar--collapsed`, `.wfb-config-panel--collapsed`, `.wfb-sidebar-collapse-btn`. Added dark mode variants. Added accent border/glow styles for nodes. |
| `GlobalConfigToolbar.tsx` | **NOT changed** — settings popover remains as secondary access point |
| `ConditionalRouterNode.tsx` | **NOT changed** — already had condition summary display |

---

## What Was NOT Changed (preserved as-is)

- All drag-and-drop logic (agent cards, condition cards)
- `CONDITION_DRAG_TYPE` export
- `DragPersonaData` format
- All `onUpdate(nodeId, partial)` signatures
- All sub-components inside NodeConfigPanel (LLM, Tools, Knowledge, Advanced, HTTP, Code)
- WorkflowCanvas component (nodes, edges, ReactFlow config)
- GlobalConfigToolbar (still works, settings popover still functional)
- useWorkflowGraph hook
- All modals (AgentTest, QuickCreate, JsonView)
- Agent enrichment logic
- Save/load workflow logic
- All existing CSS classes (only added new ones, removed only `width`/`min-width` from sidebar and config panel)

---

## How to Test

1. Open `http://localhost:3000/admin/workflows/visual-builder`
2. **Tabs**: Click Agents / Utils / Config tabs in the sidebar. Click Properties / Advanced / JSON tabs in the config panel (select a node first).
3. **Resize**: Hover between sidebar and canvas — see accent-colored bar. Drag to resize. Double-click to reset.
4. **Collapse**: Click `◀` in sidebar tab bar to collapse. Click `▶` to expand. Press `[` key. Same for config panel with `]`.
5. **Settings**: Click Config tab in sidebar — verify all settings match the gear popover.
6. **Persistence**: Resize panels, collapse sidebar, refresh page — widths and collapse state should persist.
7. **Dark mode**: Toggle dark mode — verify all tabs, handles, and collapsed strips use theme variables.
8. **Existing workflows**: Load an existing workflow — verify all nodes, edges, and config panels still work.
