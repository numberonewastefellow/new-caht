# AgentViewerModal — Redesign Plan

## Layout

```
┌─────────────────────────────────────────┐
│  [Avatar]  Agent Name            [×]    │  ← Modal.Header (unchanged)
├─────────────────────────────────────────┤
│  ⭐ Featured  👤 owner@acme  🏢 Public  │  ← Metadata pills (accent-aware)
│  "Description text..."                  │  ← Tinted description card
│                                         │
│  [Overview]  [Tools (N)]  [Knowledge(N)]│  ← Tab strip (accent active indicator)
├─────────────────────────────────────────┤
│  Tab content (scrollable)               │
│                                         │
│  OVERVIEW: Conversation Starters grid   │
│            More Info (model, prompt...) │
│                                         │
│  TOOLS:    MCP server cards (expandable)│
│            OpenAPI tool cards           │
│                                         │
│  KNOWLEDGE: Document set chips          │
│             File cards (with icon/thumb)│
└─────────────────────────────────────────┘
│  Message VertualAI...      [send]       │  ← AgentChatInput (unchanged)
└─────────────────────────────────────────┘
```

## Design Tokens Used
- `--virtualai-accent` — active tab text color, count badge bg, starter card border
- `--virtualai-accent-subtle` — active tab bg, Featured badge bg, starter card hover bg
- `--virtualai-accent-glow` — Featured badge glow, active tab indicator
- `--theme-primary-05` — fallback for above

## Tab Order
1. **Overview** — Conversation starters, Prompt reminders, More Info
2. **Tools (N)** — MCP servers (expandable) + OpenAPI tools
3. **Knowledge (N)** — Document sets + User files

## Key Rules
- All existing hooks, handlers, and data logic unchanged
- No new external dependencies
- Fully light/dark/accent-aware via CSS variables only
- Empty states for each tab section
