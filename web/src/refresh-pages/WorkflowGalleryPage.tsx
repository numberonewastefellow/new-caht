"use client";

import { useEffect, useMemo, useState } from "react";
import { useWorkflows } from "@/hooks/useWorkflows";
import { useAgents } from "@/hooks/useAgents";
import { useAppRouter } from "@/hooks/appNavigation";
import type { WorkflowSnapshot } from "@/lib/workflows/interfaces";
import { cn } from "@/lib/utils";
import WorkflowCard from "@/app/app/components/workflows-v2/WorkflowCard";
import WorkflowGlyph from "@/app/app/components/workflows-v2/WorkflowGlyph";
import { usePinnedWorkflows } from "@/app/app/components/workflows-v2/usePinnedWorkflows";
import { formatRelativeTime } from "@/app/app/components/workspaces/workspace_utils";
import {
  SvgSparkle,
  SvgSearch,
  SvgStar,
  SvgFilter,
  SvgMenu,
  SvgDashboard,
  SvgChevronRight,
  SvgUser,
} from "@opal/icons";

type WorkflowFilter = "all" | "autonomous" | "sequential" | "pinned";

function updatedMs(w: WorkflowSnapshot): number {
  const ms = new Date(w.updated_at).getTime();
  return Number.isNaN(ms) ? 0 : ms;
}

export default function WorkflowGalleryPage() {
  const route = useAppRouter();
  const { workflows, isLoading } = useWorkflows();
  const { agents } = useAgents();
  const { isPinned, togglePin, prune } = usePinnedWorkflows();

  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<WorkflowFilter>("all");
  const [view, setView] = useState<"grid" | "list">("grid");

  // Once workflows have loaded, drop pins for any that were deleted.
  useEffect(() => {
    if (!isLoading) prune(workflows.map((w) => w.id));
  }, [isLoading, workflows, prune]);

  // Map workflow id -> wrapper persona id, so a card can launch the workflow by
  // opening its wrapper assistant in chat. Personas expose `workflow_id`.
  const workflowToPersona = useMemo(() => {
    const map = new Map<number, number>();
    for (const a of agents) {
      if (a.workflow_id != null) map.set(a.workflow_id, a.id);
    }
    return map;
  }, [agents]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const bySearch = q
      ? workflows.filter(
          (w) =>
            w.name.toLowerCase().includes(q) ||
            (w.description ?? "").toLowerCase().includes(q)
        )
      : workflows;
    if (filter === "autonomous")
      return bySearch.filter((w) => w.orchestration_mode === "llm_decision");
    if (filter === "sequential")
      return bySearch.filter((w) => w.orchestration_mode === "sequential");
    return bySearch;
  }, [workflows, query, filter]);

  const pinned = useMemo(
    () => filtered.filter((w) => isPinned(w.id)),
    [filtered, isPinned]
  );
  const others = useMemo(
    () => filtered.filter((w) => !isPinned(w.id)),
    [filtered, isPinned]
  );

  const launchWorkflow = (w: WorkflowSnapshot) => {
    const personaId = workflowToPersona.get(w.id);
    if (personaId != null) route({ assistantId: personaId });
  };

  function renderGrid(list: WorkflowSnapshot[]) {
    return (
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((w) => (
          <WorkflowCard
            key={w.id}
            workflow={w}
            pinned={isPinned(w.id)}
            launchable={workflowToPersona.has(w.id)}
            onOpen={() => launchWorkflow(w)}
            onTogglePin={() => togglePin(w.id)}
          />
        ))}
      </div>
    );
  }

  function renderList(list: WorkflowSnapshot[]) {
    return (
      <div className="mt-3 overflow-hidden rounded-xl border border-border-01 bg-background-tint-01">
        {list.map((w, i) => {
          const launchable = workflowToPersona.has(w.id);
          const agentCount = w.steps.filter(
            (s) => s.step_type === "agent" && !!s.persona_name
          ).length;
          return (
            <button
              key={w.id}
              onClick={launchable ? () => launchWorkflow(w) : undefined}
              disabled={!launchable}
              title={
                launchable
                  ? undefined
                  : "Not yet available — needs a persona backfill by an admin."
              }
              className={cn(
                "flex w-full items-center gap-3 px-4 py-3 text-left",
                launchable
                  ? "hover:bg-background-tint-02"
                  : "cursor-not-allowed opacity-60",
                i > 0 && "border-t border-border-01"
              )}
            >
              <WorkflowGlyph id={w.id} size={32} radius={8} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-text-05">
                  {w.name}
                </div>
                <div className="truncate text-xs text-text-03">
                  {w.description?.trim() ||
                    "A multi-agent workflow that coordinates specialized agents."}
                </div>
              </div>
              <div className="hidden gap-4 text-xs text-text-03 md:flex">
                <span className="inline-flex items-center gap-1">
                  <SvgUser className="h-3 w-3 stroke-text-02" />
                  {agentCount}
                </span>
                <span>{formatRelativeTime(w.updated_at)}</span>
              </div>
              <SvgChevronRight className="h-4 w-4 stroke-text-02" />
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1200px] px-8 py-10">
      {/* Hero / search */}
      <div className="flex flex-col items-center text-center">
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-border-01 bg-background-tint-01/60 px-3 py-1 text-[11px] text-text-03 backdrop-blur">
          <SvgSparkle
            className="h-3 w-3 stroke-current"
            style={{ color: "var(--virtualai-accent)" }}
          />
          Workflows · {workflows.length} total
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-text-05">
          Explore workflows
        </h1>
        <p className="mt-2 max-w-xl text-sm text-text-03">
          Ready-made multi-agent workflows. Pick one to launch it in a new chat —
          each coordinates specialized agents to complete a task.
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
              placeholder="Search workflows…"
              className="flex-1 bg-transparent text-sm text-text-05 placeholder:text-text-02 focus:outline-none"
            />
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-xs text-text-03">
            <Chip
              icon={SvgStar}
              label="Pinned"
              active={filter === "pinned"}
              onClick={() => setFilter("pinned")}
            />
            <Chip
              icon={SvgSparkle}
              label="Autonomous"
              active={filter === "autonomous"}
              onClick={() => setFilter("autonomous")}
            />
            <Chip
              icon={SvgMenu}
              label="Sequential"
              active={filter === "sequential"}
              onClick={() => setFilter("sequential")}
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
      ) : filter === "pinned" ? (
        <>
          <SectionToolbar title="Pinned" view={view} onViewChange={setView} />
          {pinned.length === 0 ? (
            <EmptyState
              title="No pinned workflows"
              body="Pin a workflow from its card to keep it handy here."
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
            title={
              filter === "autonomous"
                ? "Autonomous workflows"
                : filter === "sequential"
                  ? "Sequential workflows"
                  : "All workflows"
            }
            view={view}
            onViewChange={setView}
            showViewToggle={!(filter === "all" && pinned.length > 0)}
          />
          {(filter === "all" ? others : filtered).length === 0 ? (
            <EmptyState
              title="No workflows found"
              body="Try a different search or filter. Public workflows created by your team appear here."
            />
          ) : view === "grid" ? (
            renderGrid(filter === "all" ? others : filtered)
          ) : (
            renderList(filter === "all" ? others : filtered)
          )}
        </>
      )}
    </div>
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
  icon: React.FunctionComponent<{
    className?: string;
    style?: React.CSSProperties;
  }>;
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
