import { create } from "zustand";

/**
 * Visibility of the workspace right-side context panel (History / Files /
 * Instructions) shown in the new workspace chat UI.
 *
 * This is intentionally a SMALL, dedicated, global, in-memory store — it does
 * NOT live on the per-session chat store (`useChatSessionStore`), so it has zero
 * effect on existing chat-session state. The banner (rendered from the app
 * Header) and the panel (rendered from AppPage) live in different React trees,
 * so they share visibility through this store. Collapsed by default; only a
 * workspace chat ever renders the panel, so the flag is inert elsewhere.
 */
interface WorkspacePanelStore {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
}

export const useWorkspacePanelStore = create<WorkspacePanelStore>((set) => ({
  open: false,
  setOpen: (open: boolean) => set({ open }),
  toggle: () => set((state) => ({ open: !state.open })),
}));
