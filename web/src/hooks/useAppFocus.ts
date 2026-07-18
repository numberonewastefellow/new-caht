"use client";

// "AppFocus" is the current part of the main application which is active / focused on.
// Namely, if the URL is pointing towards a "chat", then a `{ type: "chat", id: "..." }` is returned.
//
// This is useful in determining what `SidebarTab` should be active, for example.

import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { usePathname, useSearchParams } from "next/navigation";

export type AppFocusType =
  | { type: "agent" | "workspace" | "chat"; id: string }
  | "new-session"
  | "more-agents"
  | "workspaces-dashboard"
  | "workflows-gallery"
  | "user-settings"
  | "shared-chat";

export class AppFocus {
  constructor(public value: AppFocusType) {}

  isAgent(): boolean {
    return typeof this.value === "object" && this.value.type === "agent";
  }

  isWorkspace(): boolean {
    return typeof this.value === "object" && this.value.type === "workspace";
  }

  isChat(): boolean {
    return typeof this.value === "object" && this.value.type === "chat";
  }

  isSharedChat(): boolean {
    return this.value === "shared-chat";
  }

  isNewSession(): boolean {
    return this.value === "new-session";
  }

  isMoreAgents(): boolean {
    return this.value === "more-agents";
  }

  isWorkspacesDashboard(): boolean {
    return this.value === "workspaces-dashboard";
  }

  isWorkflowsGallery(): boolean {
    return this.value === "workflows-gallery";
  }

  isUserSettings(): boolean {
    return this.value === "user-settings";
  }

  getId(): string | null {
    return typeof this.value === "object" ? this.value.id : null;
  }

  getType():
    | "agent"
    | "workspace"
    | "chat"
    | "shared-chat"
    | "new-session"
    | "more-agents"
    | "workspaces-dashboard"
    | "workflows-gallery"
    | "user-settings" {
    return typeof this.value === "object" ? this.value.type : this.value;
  }
}

export default function useAppFocus(): AppFocus {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Check if we're viewing a shared chat
  if (pathname.startsWith("/app/shared/")) {
    return new AppFocus("shared-chat");
  }

  // Check if we're on the user settings page
  if (pathname.startsWith("/app/settings")) {
    return new AppFocus("user-settings");
  }

  // Check if we're on the agents page
  if (pathname.startsWith("/app/agents")) {
    return new AppFocus("more-agents");
  }

  // Check if we're on the workspaces dashboard
  if (pathname.startsWith("/app/workspaces")) {
    return new AppFocus("workspaces-dashboard");
  }

  // Check if we're on the workflows gallery
  if (pathname.startsWith("/app/workflows")) {
    return new AppFocus("workflows-gallery");
  }

  // Check search params for chat, agent, or workspace
  const chatId = searchParams.get(SEARCH_PARAM_NAMES.CHAT_ID);
  if (chatId) return new AppFocus({ type: "chat", id: chatId });

  const agentId = searchParams.get(SEARCH_PARAM_NAMES.PERSONA_ID);
  if (agentId) return new AppFocus({ type: "agent", id: agentId });

  const workspaceId = searchParams.get(SEARCH_PARAM_NAMES.PROJECT_ID);
  if (workspaceId) return new AppFocus({ type: "workspace", id: workspaceId });

  // No search params means we're on a new session
  return new AppFocus("new-session");
}
