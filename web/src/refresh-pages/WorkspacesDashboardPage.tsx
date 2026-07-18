"use client";

import { useEffect, useMemo, useState } from "react";
import { useWorkspaces } from "@/lib/hooks/useWorkspaces";
import { useAppRouter } from "@/hooks/appNavigation";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import CreateWorkspaceModal from "@/components/modals/CreateWorkspaceModal";
import type { Workspace } from "@/app/app/workspaces/workspacesService";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/app/app/components/workspaces/workspace_utils";
import { workspaceUpdatedAt } from "@/app/app/components/workspaces/workspace-v2/workspaceTheme";
import WorkspaceCard from "@/app/app/components/workspaces/workspace-v2/WorkspaceCard";
import WorkspaceGlyph from "@/app/app/components/workspaces/workspace-v2/WorkspaceGlyph";
import { usePinnedWorkspaces } from "@/app/app/components/workspaces/workspace-v2/usePinnedWorkspaces";
import {
  SvgSparkle,
  SvgSearch,
  SvgPlus,
  SvgStar,
  SvgClock,
  SvgUser,
  SvgFilter,
  SvgDashboard,
  SvgMenu,
  SvgChevronRight,
  SvgBubbleText,
} from "@opal/icons";

type WorkspaceFilter = "all" | "pinned" | "recent" | "shared";

function updatedMs(workspace: Workspace): number {
  const ms = new Date(workspaceUpdatedAt(workspace)).getTime();
  return Number.isNaN(ms) ? 0 : ms;
}

export default function WorkspacesDashboardPage() {
  const route = useAppRouter();
  const { workspaces, isLoading } = useWorkspaces();
  const { isPinned, togglePin, prune } = usePinnedWorkspaces();
  const createModal = useCreateModal();

  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<WorkspaceFilter>("all");
  const [view, setView] = useState<"grid" | "list">("grid");

  // Once workspaces have loaded, drop pins for any that were deleted.
  useEffect(() => {
    if (!isLoading) prune(workspaces.map((p) => p.id));
  }, [isLoading, workspaces, prune]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const base = q
      ? workspaces.filter(
          (p) =>
            p.name.toLowerCase().includes(q) ||
            (p.description ?? "").toLowerCase().includes(q)
        )
      : workspaces;
    return base;
  }, [workspaces, query]);

  const pinned = useMemo(
    () => filtered.filter((p) => isPinned(p.id)),
    [filtered, isPinned]
  );
  const others = useMemo(
    () => filtered.filter((p) => !isPinned(p.id)),
    [filtered, isPinned]
  );
  const recent = useMemo(
    () => [...filtered].sort((a, b) => updatedMs(b) - updatedMs(a)),
    [filtered]
  );

  const openWorkspace = (p: Workspace) => route({ workspaceId: p.id });

  function renderGrid(list: Workspace[], withCreateCard = false) {
    return (
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((p) => (
          <WorkspaceCard
            key={p.id}
            workspace={p}
            pinned={isPinned(p.id)}
            onOpen={() => openWorkspace(p)}
            onTogglePin={() => togglePin(p.id)}
          />
        ))}
        {withCreateCard && (
          <button
            onClick={() => createModal.toggle(true)}
            className={cn(
              "flex min-h-[170px] flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border-02 bg-background-tint-01/40 p-4 text-text-03",
              "transition hover:border-border-03 hover:text-text-05"
            )}
          >
            <span
              className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{ backgroundColor: "var(--virtualai-accent-subtle)" }}
            >
              <SvgPlus
                className="h-5 w-5 stroke-current"
                style={{ color: "var(--virtualai-accent)" }}
              />
            </span>
            <span className="text-sm font-medium">New workspace</span>
            <span className="text-[11px]">Start fresh with files &amp; instructions</span>
          </button>
        )}
      </div>
    );
  }

  function renderList(list: Workspace[]) {
    return (
      <div className="mt-3 overflow-hidden rounded-xl border border-border-01 bg-background-tint-01">
        {list.map((p, i) => (
          <button
            key={p.id}
            onClick={() => openWorkspace(p)}
            className={cn(
              "flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-background-tint-02",
              i > 0 && "border-t border-border-01"
            )}
          >
            <WorkspaceGlyph id={p.id} size={32} radius={8} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-text-05">
                {p.name}
              </div>
              <div className="truncate text-xs text-text-03">
                {p.description?.trim() ||
                  "Files, chats, and instructions scoped to this workspace."}
              </div>
            </div>
            <div className="hidden gap-4 text-xs text-text-03 md:flex">
              <span className="inline-flex items-center gap-1">
                <SvgBubbleText className="h-3 w-3 stroke-text-02" />
                {p.chat_sessions?.length ?? 0}
              </span>
              <span>{formatRelativeTime(workspaceUpdatedAt(p))}</span>
            </div>
            <SvgChevronRight className="h-4 w-4 stroke-text-02" />
          </button>
        ))}
      </div>
    );
  }

  const mainList = filter === "recent" ? recent : others;

  return (
    <>
      <createModal.Provider>
        <CreateWorkspaceModal />
      </createModal.Provider>

      <div className="mx-auto max-w-[1200px] px-8 py-10">
        {/* Hero / search */}
        <div className="flex flex-col items-center text-center">
          <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-border-01 bg-background-tint-01/60 px-3 py-1 text-[11px] text-text-03 backdrop-blur">
            <SvgSparkle
              className="h-3 w-3 stroke-current"
              style={{ color: "var(--virtualai-accent)" }}
            />
            Workspaces · {workspaces.length} total
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-text-05">
            Your AI workspaces
          </h1>
          <p className="mt-2 max-w-xl text-sm text-text-03">
            Each workspace bundles files, chats, instructions, and the models
            you&apos;ve chosen — everything stays scoped to the workspace.
          </p>

          <div className="mt-6 w-full max-w-2xl">
            <div
              className={cn(
                "group flex items-center gap-2 rounded-2xl border border-border-01 bg-background-tint-01 px-4 py-3 shadow-lg",
                "focus-within:border-border-03"
              )}
            >
              <SvgSearch className="h-4 w-4 stroke-text-02" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search workspaces, files, or chats…"
                className="flex-1 bg-transparent text-sm text-text-05 placeholder:text-text-02 focus:outline-none"
              />
              <button
                onClick={() => createModal.toggle(true)}
                className="ml-1 flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium text-white"
                style={{ backgroundColor: "var(--virtualai-accent)" }}
              >
                <SvgPlus className="h-3.5 w-3.5 stroke-current" /> New workspace
              </button>
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-xs text-text-03">
              <Chip
                icon={SvgStar}
                label="Pinned"
                active={filter === "pinned"}
                onClick={() => setFilter("pinned")}
              />
              <Chip
                icon={SvgClock}
                label="Recent"
                active={filter === "recent"}
                onClick={() => setFilter("recent")}
              />
              <Chip
                icon={SvgUser}
                label="Shared with me"
                active={filter === "shared"}
                onClick={() => setFilter("shared")}
              />
              <Chip
                icon={SvgFilter}
                label="All"
                active={filter === "all"}
                onClick={() => setFilter("all")}
              />
            </div>
          </div>
        </div>

        {/* Body */}
        {isLoading ? (
          <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-[170px] rounded-2xl border border-border-01 bg-background-tint-02 animate-pulse"
              />
            ))}
          </div>
        ) : filter === "shared" ? (
          <EmptyState
            title="Nothing shared with you yet"
            body="Workspaces shared by teammates will show up here."
          />
        ) : filter === "pinned" ? (
          <>
            <SectionToolbar
              title="Pinned"
              view={view}
              onViewChange={setView}
            />
            {pinned.length === 0 ? (
              <EmptyState
                title="No pinned workspaces"
                body="Pin a workspace from its card to keep it handy here."
              />
            ) : view === "grid" ? (
              renderGrid(pinned)
            ) : (
              renderList(pinned)
            )}
          </>
        ) : (
          <>
            {/* Pinned section (only in All view) */}
            {filter === "all" && pinned.length > 0 && (
              <>
                <SectionToolbar
                  title="Pinned"
                  view={view}
                  onViewChange={setView}
                />
                {view === "grid" ? renderGrid(pinned) : renderList(pinned)}
              </>
            )}

            <SectionToolbar
              title={filter === "recent" ? "Recent" : "All workspaces"}
              view={view}
              onViewChange={setView}
              showViewToggle={!(filter === "all" && pinned.length > 0)}
            />
            {mainList.length === 0 ? (
              <EmptyState
                title="No workspaces yet"
                body="Create your first workspace to bundle files, chats, and instructions."
              />
            ) : view === "grid" ? (
              renderGrid(mainList, filter === "all")
            ) : (
              renderList(mainList)
            )}
          </>
        )}
      </div>
    </>
  );
}

function SectionToolbar({
  title,
  view,
  onViewChange,
  showViewToggle = true,
}: {
  title: string;
  view: "grid" | "list";
  onViewChange: (v: "grid" | "list") => void;
  showViewToggle?: boolean;
}) {
  return (
    <div className="mt-10 flex items-center justify-between">
      <h2 className="text-sm font-semibold text-text-04">{title}</h2>
      {showViewToggle && (
        <div className="flex items-center gap-1 rounded-lg border border-border-01 bg-background-tint-01 p-0.5">
          <ToggleBtn
            active={view === "grid"}
            onClick={() => onViewChange("grid")}
            icon={SvgDashboard}
          />
          <ToggleBtn
            active={view === "list"}
            onClick={() => onViewChange("list")}
            icon={SvgMenu}
          />
        </div>
      )}
    </div>
  );
}

function Chip({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: React.FunctionComponent<{ className?: string; style?: React.CSSProperties }>;
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 transition",
        active
          ? "border-transparent text-text-05"
          : "border-border-01 bg-background-tint-01 text-text-03 hover:bg-background-tint-02"
      )}
      style={
        active ? { backgroundColor: "var(--virtualai-accent-subtle)" } : undefined
      }
    >
      <Icon className="h-3 w-3 stroke-current" /> {label}
    </button>
  );
}

function ToggleBtn({
  active,
  onClick,
  icon: Icon,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.FunctionComponent<{ className?: string }>;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-md p-1.5 transition",
        active
          ? "bg-background-tint-02 text-text-05"
          : "text-text-02 hover:text-text-05"
      )}
    >
      <Icon className="h-3.5 w-3.5 stroke-current" />
    </button>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="mt-10 flex flex-col items-center justify-center rounded-2xl border border-dashed border-border-02 bg-background-tint-01/40 py-16 text-center">
      <div className="text-sm font-medium text-text-04">{title}</div>
      <div className="mt-1 max-w-sm text-xs text-text-03">{body}</div>
    </div>
  );
}
