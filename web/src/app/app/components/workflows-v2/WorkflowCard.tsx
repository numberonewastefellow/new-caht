"use client";

import { memo, useMemo } from "react";
import type { WorkflowSnapshot } from "@/lib/workflows/interfaces";
import { cn, noProp } from "@/lib/utils";
import { swatchForId } from "@/app/app/components/workspaces/workspace-v2/workspaceTheme";
import { formatRelativeTime } from "@/app/app/components/workspaces/workspace_utils";
import WorkflowGlyph from "./WorkflowGlyph";
import { SvgStar, SvgPin, SvgUser } from "@opal/icons";

export interface WorkflowCardProps {
  workflow: WorkflowSnapshot;
  pinned: boolean;
  /** Whether a wrapper persona exists so the workflow can actually be launched. */
  launchable: boolean;
  onOpen: () => void;
  onTogglePin: () => void;
}

function ModeBadge({ mode }: { mode: string }) {
  const isAutonomous = mode === "llm_decision";
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium"
      style={{
        backgroundColor: "var(--virtualai-accent-subtle)",
        color: "var(--virtualai-accent)",
      }}
    >
      {isAutonomous ? "Autonomous" : "Sequential"}
    </span>
  );
}

const WorkflowCard = memo(function WorkflowCard({
  workflow,
  pinned,
  launchable,
  onOpen,
  onTogglePin,
}: WorkflowCardProps) {
  const { from, to } = swatchForId(workflow.id);

  // Only real agent steps get a persona chip / count (skip conditional routers).
  const agentSteps = useMemo(
    () =>
      workflow.steps.filter(
        (s) => s.step_type === "agent" && !!s.persona_name
      ),
    [workflow.steps]
  );
  const chainNames = agentSteps.slice(0, 4).map((s) => s.persona_name as string);
  const overflow = agentSteps.length - chainNames.length;

  return (
    <button
      onClick={launchable ? onOpen : undefined}
      disabled={!launchable}
      title={
        launchable
          ? undefined
          : "Not yet available — this workflow needs a persona backfill by an admin."
      }
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-2xl border border-border-01 bg-background-tint-01 p-4 text-left",
        launchable
          ? "transition-all hover:-translate-y-0.5 hover:border-border-03 hover:shadow-lg"
          : "cursor-not-allowed opacity-60"
      )}
    >
      {/* Decorative gradient glow */}
      <div
        className="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full opacity-30 blur-2xl"
        style={{ backgroundImage: `linear-gradient(135deg, ${from}, ${to})` }}
      />

      <div className="relative flex items-start justify-between">
        <WorkflowGlyph id={workflow.id} size={40} />
        <div className="flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
          <span
            role="button"
            tabIndex={0}
            aria-label={pinned ? "Unpin workflow" : "Pin workflow"}
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
            {workflow.name}
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
          {workflow.description?.trim() ||
            "A multi-agent workflow that coordinates specialized agents to complete a task."}
        </p>
      </div>

      {/* Agent chain */}
      {chainNames.length > 0 && (
        <div className="relative mt-3 flex flex-wrap items-center gap-1">
          {chainNames.map((name, i) => (
            <span
              key={`${name}-${i}`}
              className="inline-flex max-w-[9rem] items-center truncate rounded-md border border-border-01 bg-background-tint-02 px-1.5 py-0.5 text-[10px] text-text-03"
            >
              {name}
            </span>
          ))}
          {overflow > 0 && (
            <span className="text-[10px] text-text-02">+{overflow}</span>
          )}
        </div>
      )}

      <div className="relative mt-4 flex items-center justify-between border-t border-border-01 pt-3 text-[11px] text-text-03">
        <div className="flex items-center gap-3">
          <ModeBadge mode={workflow.orchestration_mode} />
          <span className="inline-flex items-center gap-1">
            <SvgUser className="h-3 w-3 stroke-text-02" />
            {agentSteps.length} {agentSteps.length === 1 ? "agent" : "agents"}
          </span>
        </div>
        <span>{formatRelativeTime(workflow.updated_at)}</span>
      </div>
    </button>
  );
});

export default WorkflowCard;
