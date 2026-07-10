import { create } from "zustand";

/**
 * Visibility of the right-side "Agents thinking" dock panel used by multi-agent
 * workflow runs. The live thinking timeline (owned per-message by
 * `AgentTimeline`) is portaled into a dock rendered from `AppPage`, so the chip
 * (inside a chat message) and the dock (a different React subtree) share
 * open-state through this small, dedicated, in-memory store — mirroring
 * `useWorkspacePanelStore`.
 *
 * Keyed on the message-tree `nodeId` (not the backend `messageId`): `nodeId` is
 * always present and stable, whereas `messageId` is `undefined` during the first
 * streaming window (it arrives via `reserved_assistant_message_id`). Keying on
 * `nodeId` avoids a flip from inline → panel mid-stream and lets the panel open
 * immediately. `messageId` is only needed by the execution-trace API, which falls
 * back to the session id when it is missing.
 *
 * Auto-close: a workflow that finishes streaming schedules the panel to close
 * after `AUTO_CLOSE_MS`. Any manual interaction (toggling, or the user having
 * explicitly opened/hidden) cancels the pending close.
 */

const AUTO_CLOSE_MS = 10_000;

// Module-level timer handle — intentionally outside the store so it is never
// part of React state and survives re-renders.
let autoCloseTimer: ReturnType<typeof setTimeout> | null = null;

function clearAutoCloseTimer() {
  if (autoCloseTimer !== null) {
    clearTimeout(autoCloseTimer);
    autoCloseTimer = null;
  }
}

interface AgentPanelStore {
  /** Whether the dock is visible. */
  open: boolean;
  /** Which message's workflow panel is currently docked (null when closed). */
  nodeId: number | null;
  /**
   * Whether the user manually toggled the panel for the active message. When
   * true, we stop auto-opening/auto-closing so we respect their intent.
   */
  userInteracted: boolean;

  /** Open the dock for a specific message node (trigger chip / auto-open). */
  openFor: (nodeId: number, opts?: { userInitiated?: boolean }) => void;
  /** Close the dock. */
  close: (opts?: { userInitiated?: boolean }) => void;
  /** Toggle the dock for a specific message node (trigger chip). User-initiated. */
  toggleFor: (nodeId: number) => void;

  /**
   * Schedule an auto-close for `nodeId` once its run completes. No-op if the user
   * already interacted, the panel is closed, or a different message owns it.
   */
  scheduleAutoClose: (nodeId: number) => void;
  /** Cancel a pending auto-close (e.g. the user interacted). */
  cancelAutoClose: () => void;
}

export const useAgentPanelStore = create<AgentPanelStore>((set, get) => ({
  open: false,
  nodeId: null,
  userInteracted: false,

  openFor: (nodeId, opts) => {
    clearAutoCloseTimer();
    set({
      open: true,
      nodeId,
      userInteracted: opts?.userInitiated ?? false,
    });
  },

  close: (opts) => {
    clearAutoCloseTimer();
    set((state) => ({
      open: false,
      userInteracted: opts?.userInitiated ? true : state.userInteracted,
    }));
  },

  toggleFor: (nodeId) => {
    clearAutoCloseTimer();
    set((state) => {
      // Same message → toggle; different message (or closed) → open this one.
      const openingSame = state.open && state.nodeId === nodeId;
      return {
        open: !openingSame,
        nodeId: openingSame ? state.nodeId : nodeId,
        userInteracted: true,
      };
    });
  },

  scheduleAutoClose: (nodeId) => {
    const state = get();
    if (state.userInteracted || !state.open || state.nodeId !== nodeId) {
      return;
    }
    clearAutoCloseTimer();
    autoCloseTimer = setTimeout(() => {
      autoCloseTimer = null;
      const latest = get();
      // Re-check: only close if still the same, still open, still untouched.
      if (!latest.userInteracted && latest.open && latest.nodeId === nodeId) {
        set({ open: false });
      }
    }, AUTO_CLOSE_MS);
  },

  cancelAutoClose: () => {
    clearAutoCloseTimer();
  },
}));
