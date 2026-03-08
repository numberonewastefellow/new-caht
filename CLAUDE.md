AGENTS.md

## Design System — Accent Theme Rules

This project uses a theme system with **light/dark color modes** and **accent themes** (Default, Ocean, Emerald, Violet).

### Accent Theme CSS Variables
All accent-aware colors are defined in `web/src/app/css/colors.css` via CSS classes (`.virtualai-ocean`, `.virtualai-emerald`, `.virtualai-violet`) with separate light and dark mode overrides (e.g. `.dark.virtualai-ocean`).

Key variables to use:
- `--theme-primary-05` / `--theme-primary-04` / `--theme-primary-06` — primary accent colors (adapt to theme)
- `--theme-gradient-00` / `--theme-gradient-05` — gradient endpoints for text effects
- `--virtualai-accent` — single resolved accent color for icons, badges, glows
- `--virtualai-accent-glow` / `--virtualai-accent-glow-strong` / `--virtualai-accent-subtle` — accent with opacity for backgrounds/glows

### Rules when writing UI code
1. **Never hardcode accent colors.** Always use the CSS variables above so colors automatically adapt to the user's chosen accent theme and color mode.
2. **Dark mode gradient text must be readable.** Both `--theme-gradient-00` (bright end) and `--theme-gradient-05` (darker end) must be visible on dark backgrounds. Never set gradient-05 to near-black in dark mode.
3. **When defining new accent-specific colors**, always provide both light and dark mode variants in `colors.css` under each `.virtualai-*` and `.dark.virtualai-*` rule.
4. **Swatches / previews** that show accent colors should be theme-aware — use brighter shades in dark mode (e.g. Ocean: light `#3b82f6`, dark `#60a5fa`).
5. **Use `var(--virtualai-accent)` with fallback** for one-off accent coloring: `style={{ color: "var(--virtualai-accent, var(--theme-primary-05))" }}`.
6. **The `.virtualai-gradient-text` class** (defined in `globals.css`) applies gradient text using the theme variables — prefer this class over inline gradient styles for consistency.

## Database Migrations — Alembic Rules

1. **Never run `alembic upgrade` or `alembic downgrade` directly.** Migrations must be applied by restarting the Docker container or redeploying the backend service — the backend applies pending migrations on startup automatically.
2. **Do not manually invoke Alembic CLI commands** (`alembic upgrade head`, `alembic downgrade -1`, etc.) against any environment. This can cause state mismatches between the running backend and the database schema.

## Workflow Editor — Dual Editor Rule

There are **two workflow editors** that must stay in sync:

1. **Wizard Editor** — `web/src/refresh-pages/WorkflowEditorPage.tsx` (form-based, step-by-step)
2. **Visual Builder** — `web/src/components/workflow-builder/` (node-based, drag-and-drop canvas)

Any change to workflow fields, validation, API payloads, or UI controls in one editor **must** be reflected in the other. Key Visual Builder files to update:
- `web/src/components/workflow-builder/types.ts` — node/edge data types
- `web/src/components/workflow-builder/graphUtils.ts` — snapshot ↔ graph conversion, validation
- `web/src/components/workflow-builder/useWorkflowGraph.ts` — state management, `toPayload()`
- `web/src/components/workflow-builder/NodeConfigPanel.tsx` — per-step config fields
- `web/src/components/workflow-builder/GlobalConfigToolbar.tsx` — workflow-level settings
