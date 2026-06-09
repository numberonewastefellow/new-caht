# Multi-Model "Compare Side-by-Side" Chat — Implementation Plan

> Status: **Implemented (web-only), type-checks clean; runtime verification pending.**
> Decisions: **N parallel real sessions** · **keep comparing every turn + "Use this" pick** · **up to 3 columns** · **web-only (no backend/API/DB changes)**.

## Implementation notes
- **Files added:** `web/src/app/app/stores/useCompareStore.ts`, `web/src/hooks/useCompareController.ts`, `web/src/sections/chat/CompareView.tsx`.
- **Files changed:** `useChatSessionStore.ts` (session-scoped selectors), `ChatUI.tsx` (reads its `chatSessionId` prop + optional `overriddenModelName`), `LLMPopover.tsx` ("Compare models" multi-select, ≤3), `AppPage.tsx` (renders `CompareView` in compare mode; routes submit to `submitCompare`).
- **Deviation from plan:** `onSubmit` was left **untouched** (it is ~600 lines, deeply bound to current-session state — extracting in place risked regressing single chat, which must not break). Instead `useCompareController` has its own lean drain loop that reuses the same primitives (FIFO, message-tree builders, session-keyed store actions). Trade-off: ~150 lines of drain-loop logic duplicated; single chat is provably unaffected. Extract a shared `streamAssistantResponse` later once compare is proven at runtime.
- **Abort isolation:** each panel's stop calls `abortSession(sessionId)` (per-panel), not the shared single-chat `stopGenerating`.

## Known MVP limitations (by design / deferred — revisit later)
- **Inline edit/regenerate disabled in compare panels** (panels pass a no-op `onSubmit`); the prompt only fans out via the shared composer.
- **Composer model button still shows the primary model name** — the multi-select count is shown inside the model picker ("n/3 selected"), not on the trigger button.
- **Secondary compare sessions appear in sidebar history** (they are real chat sessions; grouping/hiding them is deferred).
- **Temperature is shared across panels** (global `llmManager.temperature`); per-model temperature is deferred.

## Context
Users want to send one prompt to multiple models at once (e.g. GPT-4.1 + GPT-5 Mini + a Llama/Anthropic model) and see the answers **side-by-side** to compare and pick one — the OpenWebUI / ChatGPT-compare pattern. Two goals:
1. **UI** — split the answer area into N panels (up to 3) as models are selected, reusing existing components.
2. **Sends** — fan the prompt out to N models **concurrently without blocking** each other.

## Why this design fits the codebase (key findings)
- **Per-session isolation already exists**: `useChatSessionStore` holds `sessions: Map<sessionId, ChatSessionData>` and **every action takes an explicit `sessionId`** (`updateChatState(sessionId,…)`, `setAbortController(sessionId,…)`, `upsertToCompleteMessageTree({chatSessionId})`). The "current" variants just wrap these. → N sessions update independently with zero contention.
- **Model is per-request**: `send-chat-message` body carries `llm_override: {temperature, model_provider, model_version}` (`web/src/app/app/services/lib.tsx:131-184`). No backend change needed to target a specific model.
- **Streaming is already per-stream**: each send uses its own `CurrentMessageFIFO` + async generator `sendMessage()` + `AbortController`. N concurrent browser `fetch`es to `/api/converse/send-chat-message` are naturally non-blocking; the API route (`web/src/app/api/[...path]/route.ts`) streams each NDJSON response independently.
- **Reusable render units**: `AgentMessage` (self-contained assistant turn) and `HumanMessage`; `Tabs`/`ParallelTimelineTabs` for a narrow-screen fallback. No split-pane library needed (Tailwind grid).

**Net: implementable as pure web/frontend orchestration of existing endpoints — no backend/API/DB changes.**

## Endpoints reused (existing, unchanged)
1. `POST /api/converse/create-chat-session` → returns `chat_session_id` (one per model panel).
2. `PUT  /api/converse/update-chat-session-model` → sets the panel session's model.
3. `POST /api/converse/send-chat-message` → streams NDJSON; `llm_override` targets the model per request.

## Architecture
A **CompareController** fans one prompt out to 1-3 sessions; each panel is a normal single-session chat rendered with existing components.

### New state — `web/src/app/app/stores/useCompareStore.ts` (zustand)
- `compareModels: LlmDescriptor[]` (1-3; selected in the picker)
- `panelSessionIds: string[]` (created lazily on first send, one per model)
- derived `isCompareMode = compareModels.length > 1`
- `reset()` / `pick(sessionId)` (collapse to a single chat)

### Send orchestration — `web/src/hooks/useCompareController.ts`
On submit in compare mode, for each model i **in parallel** (independent async tasks, not awaited serially):
1. First turn: `createChatSession(personaId,…)` → `sessionId_i`; `createSession(sessionId_i)` in the store; `updateLlmOverrideForChatSession(sessionId_i, model_i)` (reuse `web/src/app/app/services/lib.tsx:28-80`).
2. Stream via the **shared helper** below, keyed to `sessionId_i` + `model_i`.

Each task has its own session id, FIFO, abort controller, and store keys → the fastest model renders immediately and the slowest never blocks the others.

### Reuse the streaming loop — refactor in `web/src/hooks/useChatController.ts`
Extract the inner "stream one assistant response into one session" block of `onSubmit` (~lines 530-910: build `CurrentMessageFIFO` → `updateCurrentMessageFIFO` → drain loop → `upsertToCompleteMessageTree({chatSessionId})` → per-session store updates) into a reusable `streamAssistantResponse({ sessionId, model, message, parentMessageId, … })`. Both the normal single-chat path **and** the compare controller call it. Keep the existing single path behavior identical (regression-safe).

### UI
- **`web/src/sections/chat/CompareView.tsx`** — shown by `AppPage`/`ChatUI` when `isCompareMode`. Renders the shared user prompt once, then a responsive grid `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` of panels. Narrow screens fall back to `Tabs` (reuse `ParallelTimelineTabs` pattern).
- **`web/src/sections/chat/ComparePanel.tsx`** — one column bound to `sessionId_i`: header (provider icon + model name + **"Use this"** + per-panel stop/regenerate) and body rendering that session's latest assistant turn via the existing **`AgentMessage`** + `HumanMessage`.
- **Per-session selector** — add `useSessionMessageHistory(sessionId)` to `useChatSessionStore.ts` (mirror `useCurrentMessageHistory` but parameterized) so a panel renders an arbitrary session.

### Model multi-select — `web/src/refresh-components/popovers/LLMPopover.tsx`
Add a multi-select mode (toggle each model card up to 3; show "Selected n/3"). Writes to `useCompareStore.compareModels`; the first stays the primary `llmManager.currentLlm` (single-select path unchanged when only one is chosen). Trigger button shows e.g. "3 models".

### "Use this" (pick) and follow-ups
- Every prompt fans out to all selected models (multi-turn compare).
- **"Use this"** on panel i → `useCompareStore.pick(sessionId_i)`: set it as `currentSessionId`, exit compare mode, route to `/app?chatId=sessionId_i` → continues as a normal single chat. Other panel sessions remain (optional later: group/hide in sidebar).

## Files
**Create:** `web/src/app/app/stores/useCompareStore.ts`, `web/src/hooks/useCompareController.ts`, `web/src/sections/chat/CompareView.tsx`, `web/src/sections/chat/ComparePanel.tsx`.
**Modify:** `useChatController.ts` (extract `streamAssistantResponse`), `useChatSessionStore.ts` (add `useSessionMessageHistory`), `LLMPopover.tsx` (multi-select), `AppPage.tsx`/`ChatUI.tsx` (render `CompareView` in compare mode), `AppInputBar.tsx` (route submit to compare controller + show model chips).
**Reuse unchanged:** `createChatSession`/`updateLlmOverrideForChatSession`/`sendMessage` (lib.tsx), `CurrentMessageFIFO`, per-session store actions, `AgentMessage`, `HumanMessage`, `Tabs`/`ParallelTimelineTabs`.

## Non-blocking guarantee (task 2)
N independent `fetch`es (browser concurrency) → N `CurrentMessageFIFO`s → N drain loops (independent async tasks) → store writes keyed by distinct `sessionId` → N `AbortController`s. No shared mutable bottleneck; aborting one panel doesn't touch others. Guaranteed by the existing per-session store design, not new infrastructure.

## Scope / phasing
- **MVP**: multi-select (≤3), fan-out via CompareController, 3-column CompareView with `AgentMessage`, "Use this" pick, per-panel stop. No backend changes.
- **Later (optional)**: hide/group the secondary compare sessions in the sidebar; per-model temperature; narrow-screen tabbed view polish; "regenerate this panel".

## Verification
1. Select 2-3 models, send a prompt → **3 panels stream concurrently**. In DevTools Network, 3 simultaneous `send-chat-message` requests; the fastest panel finishes without waiting on the slowest.
2. **"Use this"** on a panel → continues that model's thread as a normal single chat at `/app?chatId=…`.
3. **Single model selected → unchanged** single-chat behavior (no regression in `onSubmit` after the refactor).
4. **Abort isolation**: stop one panel mid-stream; others keep streaming.
5. `npm run types:check` clean; web-only diff (no backend files touched).
