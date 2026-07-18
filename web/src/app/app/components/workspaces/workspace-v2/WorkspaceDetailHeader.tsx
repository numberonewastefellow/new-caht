"use client";

import { useState } from "react";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "../workspace_utils";
import { workspaceUpdatedAt, type WorkspaceTab } from "./workspaceTheme";
import WorkspaceGlyph from "./WorkspaceGlyph";
import IconButton from "@/refresh-components/buttons/IconButton";
import ButtonRenaming from "@/refresh-components/buttons/ButtonRenaming";
import {
  SvgEdit,
  SvgFileText,
  SvgBubbleText,
  SvgUser,
  SvgClock,
} from "@opal/icons";

const TABS: WorkspaceTab[] = ["overview", "files", "chats"];

function Stat({
  icon: Icon,
  children,
}: {
  icon: React.FunctionComponent<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <span className="inline-flex items-center gap-1">
      <Icon className="h-3 w-3 stroke-text-02" />
      {children}
    </span>
  );
}

export interface WorkspaceDetailHeaderProps {
  tab: WorkspaceTab;
  setTab: (tab: WorkspaceTab) => void;
}

export default function WorkspaceDetailHeader({
  tab,
  setTab,
}: WorkspaceDetailHeaderProps) {
  const {
    currentWorkspaceId,
    currentWorkspaceDetails,
    workspaces,
    renameWorkspace,
    allCurrentWorkspaceFiles,
  } = useWorkspacesContext();
  const [isEditingName, setIsEditingName] = useState(false);

  if (!currentWorkspaceId) return null;

  const workspace =
    currentWorkspaceDetails?.workspace ??
    workspaces.find((p) => p.id === currentWorkspaceId);
  const workspaceName = workspace?.name || "Loading workspace...";
  const description = workspace?.description?.trim();
  const fileCount = allCurrentWorkspaceFiles.length;
  const chatCount = workspace?.chat_sessions?.length ?? 0;

  return (
    <div className="mx-auto w-full max-w-[72rem] px-4 pt-6">
      {/* Breadcrumb + Classic-view toggle now live in the workspace top banner */}
      {/* Title block */}
      <div className="mt-4 rounded-2xl border border-border-01 bg-background-tint-01 p-5">
        <div className="group flex items-start gap-4">
          <WorkspaceGlyph id={currentWorkspaceId} size={56} radius={16} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              {isEditingName ? (
                <ButtonRenaming
                  initialName={workspaceName}
                  onRename={async (newName) => {
                    await renameWorkspace(currentWorkspaceId, newName);
                  }}
                  onClose={() => setIsEditingName(false)}
                  className="text-xl font-semibold text-text-05"
                />
              ) : (
                <>
                  <h1 className="text-xl font-semibold text-text-05 truncate">
                    {workspaceName}
                  </h1>
                  <IconButton
                    icon={SvgEdit}
                    internal
                    onClick={() => setIsEditingName(true)}
                    className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity"
                    tooltip="Rename workspace"
                  />
                </>
              )}
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  backgroundColor: "var(--virtualai-accent-subtle)",
                  color: "var(--virtualai-accent)",
                }}
              >
                Active
              </span>
            </div>
            <p className="mt-1 text-sm text-text-03">
              {description ||
                "Files, chats, and instructions scoped to this workspace."}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-text-03">
              <Stat icon={SvgFileText}>{fileCount} files</Stat>
              <Stat icon={SvgBubbleText}>{chatCount} chats</Stat>
              <Stat icon={SvgUser}>1 member</Stat>
              {workspace && (
                <Stat icon={SvgClock}>
                  Updated {formatRelativeTime(workspaceUpdatedAt(workspace))}
                </Stat>
              )}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="mt-5 flex items-center gap-1 border-b border-border-01">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "relative px-3 py-2 text-xs font-medium capitalize transition-colors",
                tab === t ? "text-text-05" : "text-text-03 hover:text-text-05"
              )}
            >
              {t}
              {tab === t && (
                <span
                  className="absolute inset-x-2 -bottom-px h-0.5 rounded-full"
                  style={{ backgroundColor: "var(--virtualai-accent)" }}
                />
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
