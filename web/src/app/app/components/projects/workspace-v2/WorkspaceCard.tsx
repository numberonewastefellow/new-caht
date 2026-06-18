"use client";

import { memo, useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import type { Project, ProjectFile } from "@/app/app/projects/projectsService";
import { cn, noProp } from "@/lib/utils";
import { swatchForId, workspaceUpdatedAt } from "./workspaceTheme";
import { formatRelativeTime } from "../project_utils";
import WorkspaceGlyph from "./WorkspaceGlyph";
import { SvgStar, SvgPin, SvgFileText, SvgBubbleText, SvgUser } from "@opal/icons";

export interface WorkspaceCardProps {
  project: Project;
  pinned: boolean;
  onOpen: () => void;
  onTogglePin: () => void;
}

function Stat({
  icon: Icon,
  value,
}: {
  icon: React.FunctionComponent<{ className?: string }>;
  value: React.ReactNode;
}) {
  return (
    <span className="inline-flex items-center gap-1">
      <Icon className="h-3 w-3 stroke-text-02" />
      {value}
    </span>
  );
}

const WorkspaceCard = memo(function WorkspaceCard({
  project,
  pinned,
  onOpen,
  onTogglePin,
}: WorkspaceCardProps) {
  const { from, to } = swatchForId(project.id);

  // Only fetch the file count once the card scrolls into view, so a dashboard
  // with many workspaces doesn't fire N requests on load.
  const rootRef = useRef<HTMLButtonElement>(null);
  const [inView, setInView] = useState(
    typeof IntersectionObserver === "undefined"
  );
  useEffect(() => {
    const el = rootRef.current;
    if (!el || inView || typeof IntersectionObserver === "undefined") return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          obs.disconnect();
        }
      },
      { rootMargin: "200px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [inView]);

  // Lazy, cached file count (not present in the workspace-list payload).
  const { data: files } = useSWR<ProjectFile[]>(
    inView ? `/api/workspaces/files/${project.id}` : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false, dedupingInterval: 60_000 }
  );
  const fileCount = files?.length;
  const chatCount = project.chat_sessions?.length ?? 0;

  return (
    <button
      ref={rootRef}
      onClick={onOpen}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-2xl border border-border-01 bg-background-tint-01 p-4 text-left",
        "transition-all hover:-translate-y-0.5 hover:border-border-03 hover:shadow-lg"
      )}
    >
      {/* Decorative gradient glow */}
      <div
        className="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full opacity-30 blur-2xl"
        style={{ backgroundImage: `linear-gradient(135deg, ${from}, ${to})` }}
      />

      <div className="relative flex items-start justify-between">
        <WorkspaceGlyph id={project.id} size={40} />
        <div className="flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
          <span
            role="button"
            tabIndex={0}
            aria-label={pinned ? "Unpin workspace" : "Pin workspace"}
            onClick={noProp(onTogglePin)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                e.stopPropagation();
                onTogglePin();
              }
            }}
            className="rounded-md p-1 text-text-03 hover:bg-background-tint-02 hover:text-text-05"
          >
            <SvgPin
              className={cn("h-3.5 w-3.5", pinned && "fill-current text-text-05")}
            />
          </span>
        </div>
      </div>

      <div className="relative mt-3">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-semibold text-text-05 truncate">
            {project.name}
          </span>
          {pinned && (
            <SvgStar
              className="h-3 w-3 flex-shrink-0"
              style={{
                fill: "var(--virtualai-accent)",
                color: "var(--virtualai-accent)",
              }}
            />
          )}
        </div>
        <p className="mt-1 line-clamp-2 text-xs text-text-03">
          {project.description?.trim() ||
            "Files, chats, and instructions scoped to this workspace."}
        </p>
      </div>

      <div className="relative mt-4 flex items-center justify-between border-t border-border-01 pt-3 text-[11px] text-text-03">
        <div className="flex items-center gap-3">
          <Stat icon={SvgFileText} value={fileCount ?? "—"} />
          <Stat icon={SvgBubbleText} value={chatCount} />
          {/* Members: owner only (no backend membership) */}
          <Stat icon={SvgUser} value={1} />
        </div>
        <span>{formatRelativeTime(workspaceUpdatedAt(project))}</span>
      </div>
    </button>
  );
});

export default WorkspaceCard;
