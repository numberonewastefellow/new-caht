import { useMemo } from "react";
import {
  TurnGroup,
  TransformedStep,
} from "@/app/app/message/messageComponents/timeline/transformers";
import {
  isResearchAgentPackets,
  isWorkflowStepPackets,
  stepSupportsCollapsedStreaming,
} from "@/app/app/message/messageComponents/timeline/packetHelpers";

export interface TimelineMetrics {
  totalSteps: number;
  /**
   * Number of actual agent steps, excluding tool-call groups. Timeline steps
   * include one group per tool call, so totalSteps over-counts when used as an
   * "agents" figure. Only meaningful for workflow runs.
   */
  totalAgents: number;
  isSingleStep: boolean;
  lastTurnGroup: TurnGroup | undefined;
  lastStep: TransformedStep | undefined;
  lastStepIsResearchAgent: boolean;
  lastStepSupportsCollapsedStreaming: boolean;
}

/**
 * Memoizes derived metrics from turn groups to avoid recomputation on every render.
 * Single-pass computation where possible for performance with large packet counts.
 */
export function useTimelineMetrics(
  turnGroups: TurnGroup[],
  userStopped: boolean
): TimelineMetrics {
  return useMemo(() => {
    // Compute in single pass
    let totalSteps = 0;
    let totalAgents = 0;
    for (const tg of turnGroups) {
      totalSteps += tg.steps.length;
      for (const s of tg.steps) {
        if (isWorkflowStepPackets(s.packets)) totalAgents++;
      }
    }

    const lastTurnGroup = turnGroups[turnGroups.length - 1];
    const lastStep = lastTurnGroup?.steps[lastTurnGroup.steps.length - 1];

    // Analyze last step packets once
    const lastStepIsResearchAgent = lastStep
      ? isResearchAgentPackets(lastStep.packets)
      : false;
    const lastStepSupportsCollapsedStreaming = lastStep
      ? stepSupportsCollapsedStreaming(lastStep.packets)
      : false;

    return {
      totalSteps,
      totalAgents,
      isSingleStep: totalSteps === 1 && !userStopped,
      lastTurnGroup,
      lastStep,
      lastStepIsResearchAgent,
      lastStepSupportsCollapsedStreaming,
    };
  }, [turnGroups, userStopped]);
}
