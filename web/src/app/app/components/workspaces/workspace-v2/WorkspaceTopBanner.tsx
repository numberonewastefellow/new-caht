"use client";

import React from "react";
import Link from "next/link";
import type { Route } from "next";
import { cn } from "@/lib/utils";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import useChatSessions from "@/hooks/useChatSessions";
import useAppFocus from "@/hooks/useAppFocus";
import { useWorkspacePanelStore } from "@/app/app/stores/useWorkspacePanelStore";
import { UNNAMED_CHAT } from "@/lib/constants";
import WorkspaceGlyph from "./WorkspaceGlyph";
import IconButton from "@/refresh-components/buttons/IconButton";
import Button from "@/refresh-components/buttons/Button";
import {
  SvgArrowLeft,
  SvgHash,
  SvgFiles,
  SvgBubbleText,
  SvgBookOpen,
  SvgSparkle,
  SvgPanelLeftOpen,
  SvgPanelLeftClose,
  SvgShare,
} from "@opal/icons";

export interface WorkspaceTopBannerProps {
  /** Open the share-chat modal (chat mode only). */
  onShare: () => void;
  /** The "more actions" popover built by the Header (rename/move/delete). */
  moreMenu?: React.ReactNode;
  isMobile: boolean;
  onOpenMobileSidebar: () => void;
}

/**
 * Full-width workspace top banner shown above the chat/detail content (rendered
 * from the app Header). Replaces the in-content workspace header so the chat
 * gets more vertical space. Reads workspace + chat context via hooks; only the
 * Header-owned bits (share trigger, more menu, mobile toggle) are passed in.
 */
export default function WorkspaceTopBanner({
  onShare,
  moreMenu,
  isMobile,
  onOpenMobileSidebar,
}: WorkspaceTopBannerProps) {
  const {
    currentWorkspaceId,
    currentWorkspaceDetails,
    workspaces,
    allCurrentWorkspaceFiles,
  } = useWorkspacesContext();
  const { currentChatSession } = useChatSessions();
  const appFocus = useAppFocus();
  const { open: panelOpen, toggle: togglePanel } = useWorkspacePanelStore();

  const chatMode = appFocus.isChat();

  // Use the chat's workspace id even before the URL-sync sets ?workspaceId=, so
  // the banner appears immediately; name/glyph fall back to the workspaces list.
  const workspaceId = currentChatSession?.workspace_id ?? currentWorkspaceId;
  const workspace =
    currentWorkspaceDetails?.workspace ??
    workspaces.find((p) => p.id === workspaceId);
  const workspaceName = workspace?.name || "Workspace";
  const fileCount = allCurrentWorkspaceFiles.length;
  const chatCount = workspace?.chat_sessions?.length ?? 0;
  const instructionsActive = Boolean(
    currentWorkspaceDetails?.workspace?.instructions?.trim()
  );
  const modelName = currentChatSession?.current_alternate_model;

  if (workspaceId == null) return null;

  return (
    <div className="w-full border-b border-border-01 bg-background-tint-00">
      {/* Row 1 — breadcrumb + workspace + chat title + actions */}
      <div className="flex h-14 items-center gap-2.5 px-4">
        {isMobile && (
          <IconButton
            icon={SvgPanelLeftOpen}
            onClick={onOpenMobileSidebar}
            internal
          />
        )}
        <Link
          href={"/app/workspaces" as Route}
          className="inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-sm text-text-03 transition-colors hover:bg-background-tint-02 hover:text-text-05"
        >
          <SvgArrowLeft className="h-4 w-4 stroke-current" />
          {!isMobile && "Workspaces"}
        </Link>

        <div className="h-5 w-px bg-border-01" />

        {/* Workspace identity + meta */}
        <div className="flex min-w-0 items-center gap-2">
          <WorkspaceGlyph id={workspaceId} size={28} radius={8} />
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-text-05">
              {workspaceName}
            </div>
            <div className="flex items-center gap-2 text-[11px] text-text-03">
              <span className="inline-flex items-center gap-1">
                <SvgFiles className="h-3 w-3 stroke-current" /> {fileCount} files
              </span>
              <span>·</span>
              <span className="inline-flex items-center gap-1">
                <SvgBubbleText className="h-3 w-3 stroke-current" /> {chatCount}{" "}
                chats
              </span>
            </div>
          </div>
        </div>

        {/* Current chat title (chat mode) */}
        {chatMode && currentChatSession && (
          <>
            <div className="hidden h-5 w-px bg-border-01 sm:block" />
            <div className="hidden min-w-0 items-center gap-1.5 text-sm text-text-03 sm:flex">
              <SvgHash className="h-3.5 w-3.5 stroke-current" />
              <span className="truncate text-text-04">
                {currentChatSession.name || UNNAMED_CHAT}
              </span>
            </div>
          </>
        )}

        {/* Right actions */}
        <div className="ml-auto flex items-center gap-1.5">
          {chatMode && currentChatSession && (
            <>
              <Button leftIcon={SvgShare} tertiary onClick={onShare}>
                {isMobile ? "" : "Share"}
              </Button>
              {moreMenu}
              <IconButton
                icon={panelOpen ? SvgPanelLeftClose : SvgPanelLeftOpen}
                onClick={togglePanel}
                internal
                tooltip={panelOpen ? "Hide panel" : "Show panel"}
              />
            </>
          )}
        </div>
      </div>

      {/* Row 2 — chips (chat mode) */}
      {chatMode && (
        <div className="flex items-center gap-2 overflow-x-auto px-4 pb-2.5 text-[11px]">
          {instructionsActive && (
            <span
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium"
              style={{
                backgroundColor: "var(--virtualai-accent-subtle)",
                color: "var(--virtualai-accent)",
              }}
            >
              <SvgBookOpen className="h-3 w-3 stroke-current" /> Workspace
              instructions active
            </span>
          )}
          <span className="inline-flex items-center gap-1 rounded-full bg-background-tint-02 px-2 py-0.5 text-text-03">
            <SvgFiles className="h-3 w-3 stroke-current" /> {fileCount} files in
            context
          </span>
          {modelName && (
            <span className="inline-flex items-center gap-1 rounded-full bg-background-tint-02 px-2 py-0.5 text-text-03">
              <SvgSparkle className="h-3 w-3 stroke-current" /> {modelName}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
