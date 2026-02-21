# VirtualAI Deferred UI Changes (Items 10-12)

These changes were assessed as HIGH RISK during the UI redesign planning phase
and are deferred for careful, dedicated implementation later.

---

## Item 10: AgentMessage Card Wrapper

**Risk Level:** HIGH (50% safe)
**File:** `web/src/app/app/message/messageComponents/AgentMessage.tsx`

### What We Want
Wrap the assistant's response in a visible card container with:
- Subtle `shadow-01` background
- `rounded-12` corners
- Action bar (copy, feedback, regenerate) pinned below the card

### Why It's Risky
The AgentMessage renders streaming packets via a deeply nested timeline system:

```
AgentMessage
  -> AgentTimeline (web/src/app/app/message/messageComponents/timeline/AgentTimeline.tsx)
     -> TimelineRoot (uses absolute-positioned connector lines)
        -> TimelineRow
           -> TimelineIconColumn (absolute positioned)
           -> TimelineHeaderRow
           -> TimelineStepContent
              -> [12+ specialized tool renderers]
```

**Specific breakage scenarios:**
1. **Timeline connector lines** use `absolute` positioning relative to `TimelineRoot`.
   Wrapping in a card `div` changes the offset parent and misaligns vertical lines.
2. **Step expand/collapse** animations assume content flows directly within the
   timeline. An extra wrapper may cause height calculation mismatches.
3. **Tool renderer widths** (search results, code blocks, web search) assume they
   fill the available width. A card with padding shrinks the available space, which
   may cause horizontal overflow or text truncation.
4. **Citation click targets** link to the DocumentsSidebar. These handlers bubble
   up through the timeline DOM. An extra wrapper could intercept clicks.
5. **MessageToolbar** (copy/feedback/regenerate) is currently positioned relative
   to the timeline. Moving it below a card requires re-anchoring.

### Files That Must Be Studied Before Implementing
- `web/src/app/app/message/messageComponents/AgentMessage.tsx`
- `web/src/app/app/message/messageComponents/timeline/AgentTimeline.tsx`
- `web/src/app/app/message/messageComponents/timeline/primitives/TimelineRoot.tsx`
- `web/src/app/app/message/messageComponents/timeline/primitives/TimelineRow.tsx`
- `web/src/app/app/message/messageComponents/timeline/primitives/TimelineIconColumn.tsx`
- `web/src/app/app/message/messageComponents/timeline/StepContainer.tsx`

### Implementation Approach (When Ready)
1. Read all timeline primitive components to understand positioning model
2. Add the card wrapper OUTSIDE the `TimelineRoot`, not inside it
3. Ensure the card does NOT add padding that affects timeline width calculations
4. Test with: single message, streaming message, multi-step tool use, code blocks,
   search results with citations, deep research mode
5. Test in both light and dark mode
6. Test responsive behavior at mobile widths

---

## Item 11: Sidebar Date Grouping

**Risk Level:** HIGH (40% safe)
**File:** `web/src/sections/sidebar/AppSidebar.tsx`

### What We Want
Group chat sessions in the sidebar by date:
- Today
- Yesterday
- Last 7 Days
- Last 30 Days
- Older

With collapsible group headers and an active chat highlight with left accent border.

### Why It's Risky
**This is NOT a CSS-only change.** It requires JavaScript logic changes:

1. **Optimistic chat search** (`useChatSearchOptimistic.ts`) returns a flat array
   of chat sessions. Grouping by date means transforming this data structure.
2. **Drag behavior** - if the sidebar supports drag-to-reorder or drag-to-folder,
   grouping breaks the flat list assumption.
3. **Project folders** (`ProjectFolderButton.tsx`) render alongside regular chats.
   Date grouping must exclude or specially handle project items.
4. **Agent buttons** are interleaved with chat buttons. They don't have timestamps
   in the same way.
5. **Responsive collapse** - the sidebar collapses at mobile widths. Date group
   headers add height that may push content off-screen.
6. **Virtual scrolling** - if the chat list is virtualized for performance, adding
   group headers changes the item count and row height calculations.

### Files That Must Be Studied Before Implementing
- `web/src/sections/sidebar/AppSidebar.tsx`
- `web/src/sections/sidebar/ChatButton.tsx`
- `web/src/sections/sidebar/useChatSearchOptimistic.ts`
- `web/src/sections/sidebar/ProjectFolderButton.tsx`
- `web/src/sections/sidebar/AgentButton.tsx`
- `web/src/sections/sidebar/SidebarWrapper.tsx`

### Implementation Approach (When Ready)
1. Read all sidebar components to understand the rendering pipeline
2. Create a utility function to group sessions by date bucket
3. Add collapsible group headers using existing `collapsible-down`/`collapsible-up`
   animations from Tailwind config
4. Keep the data source (API response) flat - only transform at render time
5. Ensure search still works across groups (search should flatten back to a list)
6. Active highlight: use a left `border-l-2 border-theme-primary-04` on the
   active chat button - this is the SAFE part and can be done independently
7. Test with: 0 chats, 1 chat, 100+ chats, project folders, agent buttons,
   search filtering, mobile responsive view

### Safe Sub-task (Can Do Now)
The active chat highlight (left accent border) can be done independently as a
CSS-only change on `ChatButton.tsx`. This does NOT require data restructuring.

---

## Item 12: Button Shape Changes (Pill Buttons)

**Risk Level:** MEDIUM (60% safe)
**File:** `web/src/app/css/button.css`

### What We Want
Change buttons from rounded-rectangle to pill shape (`border-radius: 9999px`)
with updated hover states.

### Why It's Risky
The button CSS system has a complex variant matrix:

```
Variants:     primary, secondary, tertiary, internal
Types:        main, action, danger
States:       normal, hover, active, transient, disabled
Components:   background, text, icon (stroke)
```

**Specific breakage scenarios:**
1. **Icon-only buttons** (copy, edit, feedback, close) are currently square-ish.
   Making them pill-shaped turns them into ovals instead of circles.
2. **Square buttons** (`square-button.css`) have their own sizing. Pill radius
   on fixed-width buttons looks wrong.
3. **Button groups** (e.g., message switcher prev/next) have tight spacing.
   Pill shapes add horizontal padding that may cause overflow.
4. **Select variant buttons** (`variant="select"`) like the Deep Research toggle
   have specific width constraints. Pill shape may clip text.
5. **`foldable` buttons** animate width changes. The pill radius during animation
   mid-state may look strange.

### Files That Must Be Studied Before Implementing
- `web/src/app/css/button.css`
- `web/src/app/css/square-button.css`
- `web/lib/opal/components/Button.tsx` (the Opal component library Button)
- `web/src/refresh-components/buttons/Button.tsx`
- All components using `icon`-only buttons (search for `icon={Svg` patterns)

### Implementation Approach (When Ready)
1. Read the button CSS and identify all variant combinations
2. ONLY change text-containing buttons to pill shape
3. Keep icon-only buttons with `rounded-full` (circle, not pill)
4. Keep square buttons unchanged
5. Test with: all button variants visible in the app, sidebar buttons, input bar
   buttons, message action buttons, modal buttons, settings page buttons
6. Test text truncation on pill buttons at various widths
7. Test button groups (message switcher, toolbar) for spacing overflow

---

## General Testing Checklist (For All Deferred Items)

- [ ] Light mode
- [ ] Dark mode
- [ ] System theme (auto)
- [ ] VirtualAI Ocean theme (once implemented)
- [ ] VirtualAI Emerald theme (once implemented)
- [ ] VirtualAI Violet theme (once implemented)
- [ ] Mobile viewport (< 768px)
- [ ] Desktop viewport (>= 768px)
- [ ] Wide viewport (>= 1420px)
- [ ] Streaming state (while AI is generating)
- [ ] Empty state (no messages)
- [ ] Long conversation (50+ messages)
- [ ] With file attachments
- [ ] With code blocks in responses
- [ ] With citations and document sidebar open
