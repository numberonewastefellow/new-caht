"use client";

import React from "react";
import { SvgActivity, SvgSparkle, SvgClockHandsSmall, SvgX } from "@opal/icons";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import Text from "@/refresh-components/texts/Text";
import IconButton from "@/refresh-components/buttons/IconButton";
import { WorkflowTraceButton } from "@/app/app/message/messageComponents/timeline/renderers/workflow/WorkflowTraceGraph";
import { formatDurationSeconds } from "@/lib/time";
import { FullChatState } from "../interfaces";

// All accent coloring uses theme CSS variables (per the workspace design-system
// rules) so the panel follows the active accent theme + light/dark mode.
const ACCENT = "var(--virtualai-accent, var(--theme-primary-05))";
const ACCENT_SUBTLE = "var(--virtualai-accent-subtle, var(--theme-primary-04))";

export interface AgentRunPanelProps {
  /** Assistant agent, for the avatar. */
  agent: FullChatState["assistant"];
  /** Whether the run is still streaming (drives live badge + title). */
  isLive: boolean;
  /** Header title ("Agents thinking" while live, "Thought for Xs" when done). */
  title: string;
  /** Number of agents/steps that have completed. */
  doneCount: number;
  /** Total number of agents/steps. */
  totalCount: number;
  /** Elapsed seconds (ticks while live, frozen final duration when done). */
  elapsedSeconds?: number;
  /** Message id, for the execution-trace graph button. */
  messageId?: number;
  /** Close the panel. */
  onClose: () => void;
  /** The live timeline content (portaled in from AgentTimeline). */
  children: React.ReactNode;
}

/**
 * Right-dock "Agents thinking" panel shell — the ChatGPT/Gemini-style side panel
 * that replaces the inline stacked timeline for multi-agent workflow runs. It is
 * presentational: the streaming agent cards are passed in as `children` (the same
 * `ExpandedTimelineContent` used inline), so token-by-token streaming is preserved.
 */
export default function AgentRunPanel({
  agent,
  isLive,
  title,
  doneCount,
  totalCount,
  elapsedSeconds,
  messageId,
  onClose,
  children,
}: AgentRunPanelProps) {
  const progressPct =
    totalCount > 0 ? Math.min(100, (doneCount / totalCount) * 100) : 0;

  return (
    <div className="flex h-full w-full flex-col border-l border-border-01 bg-background-tint-01">
      {/* Sticky header */}
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border-01 px-3 py-2.5">
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="relative shrink-0">
            <AgentAvatar agent={agent} size={28} />
            {isLive && (
              <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5">
                <span
                  className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
                  style={{ backgroundColor: ACCENT }}
                />
                <span
                  className="relative inline-flex h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: ACCENT }}
                />
              </span>
            )}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Text mainUiAction text05 nowrap className="truncate">
                {title}
              </Text>
              {isLive && (
                <span
                  className="inline-flex shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                  style={{ backgroundColor: ACCENT_SUBTLE, color: ACCENT }}
                >
                  <SvgActivity className="h-2.5 w-2.5" style={{ stroke: ACCENT }} />
                  live
                </span>
              )}
            </div>
            <div className="mt-0.5 flex items-center gap-2 text-[11px] text-text-03">
              <span className="inline-flex items-center gap-1">
                <SvgSparkle className="h-3 w-3 stroke-text-03" />
                {totalCount} {totalCount === 1 ? "agent" : "agents"}
              </span>
              {elapsedSeconds != null && elapsedSeconds > 0 && (
                <span className="inline-flex items-center gap-1">
                  <SvgClockHandsSmall className="h-3 w-3 stroke-text-03" />
                  {formatDurationSeconds(elapsedSeconds)}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {totalCount > 0 && (
            <div className="hidden items-center gap-1.5 rounded-full border border-border-01 bg-background-tint-00 px-2 py-1 text-[11px] text-text-03 sm:flex">
              <div className="h-1.5 w-14 overflow-hidden rounded-full bg-background-tint-00">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${progressPct}%`, backgroundColor: ACCENT }}
                />
              </div>
              <span className="font-medium text-text-05">
                {doneCount}/{totalCount}
              </span>
            </div>
          )}
          {messageId != null && (
            <WorkflowTraceButton compact live={isLive} messageId={messageId} />
          )}
          <IconButton
            icon={SvgX}
            internal
            onClick={onClose}
            tooltip="Hide panel"
          />
        </div>
      </div>

      {/* Scrollable body — the live streaming agent cards */}
      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">{children}</div>
    </div>
  );
}
