import { useState, useEffect, useCallback, useRef } from "react";
import { TurnGroup } from "../transformers";

export interface TimelineExpansionState {
  isExpanded: boolean;
  handleToggle: () => void;
  parallelActiveTab: string;
  setParallelActiveTab: (tab: string) => void;
}

/**
 * Manages expansion state for the timeline.
 * Auto-collapses when streaming completes or message content starts, and syncs parallel tab selection.
 *
 * Special handling for HITL (Human-in-the-Loop) workflows:
 * When the last step is a workflow pause, the timeline auto-expands and stays
 * expanded so the user can see the questions they need to answer.
 */
export function useTimelineExpansion(
  stopPacketSeen: boolean,
  lastTurnGroup: TurnGroup | undefined,
  hasDisplayContent: boolean = false,
  lastStepIsPause: boolean = false
): TimelineExpansionState {
  const [isExpanded, setIsExpanded] = useState(false);
  const [parallelActiveTab, setParallelActiveTab] = useState<string>("");
  const userHasToggled = useRef(false);

  const handleToggle = useCallback(() => {
    userHasToggled.current = true;
    setIsExpanded((prev) => !prev);
  }, []);

  // Auto-collapse when streaming completes or message content starts
  // BUT respect user intent - if they've manually toggled, don't auto-collapse
  // HITL: Never auto-collapse when workflow is paused — user needs to see questions
  useEffect(() => {
    if (lastStepIsPause) {
      // Auto-expand for workflow pause — user needs to see the questions
      if (!userHasToggled.current) {
        setIsExpanded(true);
      }
    } else if (
      (stopPacketSeen || hasDisplayContent) &&
      !userHasToggled.current
    ) {
      setIsExpanded(false);
    }
  }, [stopPacketSeen, hasDisplayContent, lastStepIsPause]);

  // Sync active tab when parallel turn group changes
  useEffect(() => {
    if (lastTurnGroup?.isParallel && lastTurnGroup.steps.length > 0) {
      const validTabs = lastTurnGroup.steps.map((s) => s.key);
      const firstStep = lastTurnGroup.steps[0];
      if (firstStep && !validTabs.includes(parallelActiveTab)) {
        setParallelActiveTab(firstStep.key);
      }
    }
  }, [lastTurnGroup, parallelActiveTab]);

  return {
    isExpanded,
    handleToggle,
    parallelActiveTab,
    setParallelActiveTab,
  };
}
