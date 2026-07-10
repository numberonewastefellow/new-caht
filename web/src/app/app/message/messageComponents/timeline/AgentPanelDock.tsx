"use client";

import { useAgentPanelStore } from "@/app/app/stores/useAgentPanelStore";
import { useSettingsContext } from "@/providers/SettingsProvider";
import { cn } from "@/lib/utils";

/**
 * DOM id of the portal target that the live "Agents thinking" panel is rendered
 * into. `AgentTimeline` (which owns the per-message streaming data) portals its
 * `AgentRunPanel` here, so the panel lives in this AppPage-level dock while its
 * content is still driven by the message's live timeline state.
 */
export const AGENT_PANEL_SLOT_ID = "agent-run-panel-slot";

/**
 * Right-side dock that hosts the multi-agent workflow "Agents thinking" panel.
 * Mirrors the document-sidebar / workspace-context dock pattern in AppPage:
 * an animated-width flex sibling on desktop, a full-screen overlay drawer on
 * mobile. Visibility is owned by `useAgentPanelStore`; the actual panel content
 * is portaled in from the active message's `AgentTimeline`.
 */
export default function AgentPanelDock() {
  const open = useAgentPanelStore((s) => s.open);
  const close = useAgentPanelStore((s) => s.close);
  const settings = useSettingsContext();

  // Mobile: only render the slot while open, as a full-screen overlay drawer.
  // Keeping a single slot element in the DOM at a time makes the portal target
  // unambiguous (desktop and mobile never render the slot simultaneously).
  if (settings.isMobile) {
    if (!open) return null;
    return (
      <div className="fixed inset-0 z-modal lg:hidden">
        <div
          className="absolute inset-0 bg-black/40"
          onClick={() => close({ userInitiated: true })}
        />
        <div className="absolute inset-y-0 right-0 flex w-full max-w-[92%] flex-col bg-background-tint-01 shadow-lg">
          <div id={AGENT_PANEL_SLOT_ID} className="h-full w-full" />
        </div>
      </div>
    );
  }

  // Desktop: animated-width right dock. The slot always exists (width 0 when
  // closed); the timeline only portals content into it while open.
  return (
    <div
      className={cn(
        "hidden lg:block flex-shrink-0 overflow-hidden transition-all duration-300 ease-in-out",
        open ? "w-[32rem]" : "w-[0rem]"
      )}
    >
      <div className="h-full w-[32rem]">
        <div id={AGENT_PANEL_SLOT_ID} className="h-full w-full" />
      </div>
    </div>
  );
}
