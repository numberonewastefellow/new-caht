"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { MinimalOnyxDocument } from "@/lib/search/interfaces";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import { useWorkspacePanelStore } from "@/app/app/stores/useWorkspacePanelStore";
import IconButton from "@/refresh-components/buttons/IconButton";
import WorkspaceChatSessionList from "../WorkspaceChatSessionList";
import { FilesSection, InstructionsSection } from "./WorkspaceDetailBody";
import { SvgHistory, SvgFiles, SvgBookOpen, SvgSearch, SvgX } from "@opal/icons";

type PanelTab = "history" | "files" | "instructions";

/**
 * Right-side workspace context dock shown in the new workspace chat UI.
 * Tabs reuse the exact same data-bound sections as the workspace detail page
 * (WorkspaceChatSessionList, FilesSection, InstructionsSection) — no new bindings.
 * Visibility is owned by the dedicated `useWorkspacePanelStore`.
 */
export default function WorkspaceContextPanel({
  setPresentingDocument,
}: {
  setPresentingDocument?: (document: MinimalOnyxDocument) => void;
}) {
  const { allCurrentWorkspaceFiles } = useWorkspacesContext();
  const setOpen = useWorkspacePanelStore((s) => s.setOpen);
  const [tab, setTab] = useState<PanelTab>("history");
  const [search, setSearch] = useState("");

  return (
    <div className="flex h-full w-full flex-col border-l border-border-01 bg-background-tint-01">
      {/* Tabs + close */}
      <div className="flex shrink-0 items-center justify-between border-b border-border-01 pl-1 pr-2 pt-2">
        <div className="flex items-center gap-0.5">
          <PanelTabBtn
            icon={SvgHistory}
            label="History"
            active={tab === "history"}
            onClick={() => setTab("history")}
          />
          <PanelTabBtn
            icon={SvgFiles}
            label="Files"
            count={allCurrentWorkspaceFiles.length}
            active={tab === "files"}
            onClick={() => setTab("files")}
          />
          <PanelTabBtn
            icon={SvgBookOpen}
            label="Instructions"
            active={tab === "instructions"}
            onClick={() => setTab("instructions")}
          />
        </div>
        <IconButton
          icon={SvgX}
          internal
          onClick={() => setOpen(false)}
          tooltip="Hide panel"
        />
      </div>

      {/* Content */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {tab === "history" && (
          <div className="px-2 pt-3">
            <div className="flex items-center gap-2 rounded-lg border border-border-01 bg-background-tint-00 px-2.5 py-1.5">
              <SvgSearch className="h-3.5 w-3.5 stroke-text-02" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search chats in this workspace"
                className="flex-1 bg-transparent text-xs text-text-05 placeholder:text-text-02 outline-none"
              />
            </div>
            <WorkspaceChatSessionList searchQuery={search} />
          </div>
        )}
        {tab === "files" && (
          <div className="p-3">
            <FilesSection
              variant="full"
              setPresentingDocument={setPresentingDocument}
            />
          </div>
        )}
        {tab === "instructions" && (
          <div className="p-3">
            <InstructionsSection />
          </div>
        )}
      </div>
    </div>
  );
}

function PanelTabBtn({
  icon: Icon,
  label,
  count,
  active,
  onClick,
}: {
  icon: React.FunctionComponent<{ className?: string }>;
  label: string;
  count?: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative inline-flex items-center gap-1.5 rounded-t-md px-2.5 pb-2.5 pt-1 text-xs transition-colors",
        active ? "text-text-05" : "text-text-03 hover:text-text-05"
      )}
    >
      <Icon className="h-3.5 w-3.5 stroke-current" />
      {label}
      {count != null && (
        <span className="rounded-full bg-background-tint-02 px-1.5 py-0.5 text-[10px] text-text-03">
          {count}
        </span>
      )}
      {active && (
        <span
          className="absolute inset-x-1 -bottom-px h-0.5 rounded-full"
          style={{ backgroundColor: "var(--virtualai-accent)" }}
        />
      )}
    </button>
  );
}
