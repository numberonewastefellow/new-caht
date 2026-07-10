"use client";

import React, { useMemo, useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { StopReason } from "@/app/app/services/streamingModels";
import { FullChatState, RenderType } from "../interfaces";
import { TurnGroup } from "./transformers";
import { cn } from "@/lib/utils";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import Text from "@/refresh-components/texts/Text";
import { useTimelineExpansion } from "@/app/app/message/messageComponents/timeline/hooks/useTimelineExpansion";
import { useTimelineMetrics } from "@/app/app/message/messageComponents/timeline/hooks/useTimelineMetrics";
import { useTimelineHeader } from "@/app/app/message/messageComponents/timeline/hooks/useTimelineHeader";
import {
  useTimelineUIState,
  TimelineUIState,
} from "@/app/app/message/messageComponents/timeline/hooks/useTimelineUIState";
import {
  isResearchAgentPackets,
  isSearchToolPackets,
  isWorkflowPausePackets,
  isWorkflowStepPackets,
  isWorkflowOrchestratorPackets,
  stepSupportsCollapsedStreaming,
  stepHasCollapsedStreamingContent,
} from "@/app/app/message/messageComponents/timeline/packetHelpers";
import { WorkflowTraceButton } from "@/app/app/message/messageComponents/timeline/renderers/workflow/WorkflowTraceGraph";
import { useTimelineStepState } from "@/app/app/message/messageComponents/timeline/hooks/useTimelineStepState";
import { StreamingHeader } from "@/app/app/message/messageComponents/timeline/headers/StreamingHeader";
import { CompletedHeader } from "@/app/app/message/messageComponents/timeline/headers/CompletedHeader";
import { StoppedHeader } from "@/app/app/message/messageComponents/timeline/headers/StoppedHeader";
import { ParallelStreamingHeader } from "@/app/app/message/messageComponents/timeline/headers/ParallelStreamingHeader";
import {
  SpinnerRing,
  WaveDots,
} from "@/app/app/message/ThinkingIndicator";
import { useStreamingStartTime } from "@/app/app/stores/useChatSessionStore";
import { ExpandedTimelineContent } from "./ExpandedTimelineContent";
import { CollapsedStreamingContent } from "./CollapsedStreamingContent";
import { TimelineRoot } from "@/app/app/message/messageComponents/timeline/primitives/TimelineRoot";
import { TimelineHeaderRow } from "@/app/app/message/messageComponents/timeline/primitives/TimelineHeaderRow";
import { formatDurationSeconds } from "@/lib/time";
import { SvgActivity, SvgChevronRight } from "@opal/icons";
import { useAgentPanelStore } from "@/app/app/stores/useAgentPanelStore";
import { useSettingsContext } from "@/providers/SettingsProvider";
import { useStreamingDuration } from "@/app/app/message/messageComponents/timeline/hooks/useStreamingDuration";
import AgentRunPanel from "./AgentRunPanel";
import { AGENT_PANEL_SLOT_ID } from "./AgentPanelDock";

// Theme-accent CSS variables (design-system rule: never hardcode accent colors).
const PANEL_ACCENT = "var(--virtualai-accent, var(--theme-primary-05))";
const PANEL_ACCENT_SUBTLE = "var(--virtualai-accent-subtle, var(--theme-primary-04))";

// =============================================================================
// Private Wrapper Components
// =============================================================================

interface TimelineContainerProps {
  agent: FullChatState["assistant"];
  headerContent?: React.ReactNode;
  children?: React.ReactNode;
}

function TimelineContainer({
  agent,
  headerContent,
  children,
}: TimelineContainerProps) {
  return (
    <TimelineRoot>
      <TimelineHeaderRow left={<AgentAvatar agent={agent} size={24} />}>
        {headerContent}
      </TimelineHeaderRow>
      {children}
    </TimelineRoot>
  );
}

/**
 * Inline trigger chip shown in the chat for a multi-agent workflow run. Clicking
 * it opens/closes the right-side dock panel (the live agents view). Keeps the
 * execution-trace button reachable even while the panel is closed.
 */
function WorkflowTriggerChip({
  title,
  isLive,
  totalSteps,
  panelOpen,
  onToggle,
  messageId,
}: {
  title: string;
  isLive: boolean;
  totalSteps: number;
  panelOpen: boolean;
  onToggle: () => void;
  messageId?: number;
}) {
  return (
    <div className="flex flex-1 min-w-0 items-center justify-between gap-2 p-1">
      <div
        role="button"
        onClick={onToggle}
        className="flex min-w-0 cursor-pointer items-center gap-2"
      >
        <Text mainUiAction text03 nowrap className="truncate">
          {title}
        </Text>
        {isLive && (
          <span
            className="inline-flex shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium"
            style={{ backgroundColor: PANEL_ACCENT_SUBTLE, color: PANEL_ACCENT }}
          >
            <SvgActivity className="h-2.5 w-2.5" style={{ stroke: PANEL_ACCENT }} />
            live
          </span>
        )}
        <Text secondaryBody text03 nowrap className="hidden shrink-0 sm:inline">
          · {totalSteps} {totalSteps === 1 ? "agent" : "agents"}
        </Text>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <WorkflowTraceButton compact live={isLive} messageId={messageId} />
        <button
          type="button"
          onClick={onToggle}
          className="inline-flex shrink-0 items-center gap-0.5 text-[11px] font-medium hover:underline"
          style={{ color: PANEL_ACCENT }}
        >
          {panelOpen ? "Hide" : "View"}
          <SvgChevronRight className="h-3 w-3" style={{ stroke: PANEL_ACCENT }} />
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export interface AgentTimelineProps {
  /** Turn groups from usePacketProcessor */
  turnGroups: TurnGroup[];
  /** Chat state for rendering content */
  chatState: FullChatState;
  /** Whether the stop packet has been seen */
  stopPacketSeen?: boolean;
  /** Reason for stopping (if stopped) */
  stopReason?: StopReason;
  /** Whether final answer is coming (affects last connector) */
  finalAnswerComing?: boolean;
  /** Whether there is display content after timeline */
  hasDisplayContent?: boolean;
  /** Content to render after timeline (final message + toolbar) - slot pattern */
  children?: React.ReactNode;
  /** Whether the timeline is collapsible */
  collapsible?: boolean;
  /** Title of the button to toggle the timeline */
  buttonTitle?: string;
  /** Test ID for e2e testing */
  "data-testid"?: string;
  /** Processing duration in seconds (for completed messages) */
  processingDurationSeconds?: number;
  /** Whether image generation is in progress */
  isGeneratingImage?: boolean;
  /** Number of images generated */
  generatedImageCount?: number;
  /** Tool processing duration from backend (via MESSAGE_START packet) */
  toolProcessingDuration?: number;
  /** Message-tree node id — stable panel identity for the workflow dock. */
  nodeId?: number;
  /**
   * Whether the right-side workflow dock is available in this render context.
   * False for surfaces without an `AgentPanelDock` (e.g. shared chat) so workflow
   * runs fall back to the inline expanded timeline.
   */
  agentDockEnabled?: boolean;
}

/**
 * Custom prop comparison for AgentTimeline memoization.
 * Prevents unnecessary re-renders when parent renders but props haven't meaningfully changed.
 */
function areAgentTimelinePropsEqual(
  prev: AgentTimelineProps,
  next: AgentTimelineProps
): boolean {
  return (
    prev.turnGroups === next.turnGroups &&
    prev.stopPacketSeen === next.stopPacketSeen &&
    prev.stopReason === next.stopReason &&
    prev.finalAnswerComing === next.finalAnswerComing &&
    prev.hasDisplayContent === next.hasDisplayContent &&
    prev.processingDurationSeconds === next.processingDurationSeconds &&
    prev.collapsible === next.collapsible &&
    prev.buttonTitle === next.buttonTitle &&
    prev.chatState === next.chatState &&
    prev.isGeneratingImage === next.isGeneratingImage &&
    prev.generatedImageCount === next.generatedImageCount &&
    prev.toolProcessingDuration === next.toolProcessingDuration &&
    prev.nodeId === next.nodeId &&
    prev.agentDockEnabled === next.agentDockEnabled
  );
}

export const AgentTimeline = React.memo(function AgentTimeline({
  turnGroups,
  chatState,
  stopPacketSeen = false,
  stopReason,
  finalAnswerComing = false,
  hasDisplayContent = false,
  collapsible = true,
  buttonTitle,
  "data-testid": testId,
  processingDurationSeconds,
  isGeneratingImage = false,
  generatedImageCount = 0,
  toolProcessingDuration,
  nodeId,
  agentDockEnabled = true,
}: AgentTimelineProps) {
  // Header text and state flags
  const { headerText, hasPackets, userStopped } = useTimelineHeader(
    turnGroups,
    stopReason,
    isGeneratingImage
  );

  // Memoized metrics derived from turn groups
  const {
    totalSteps,
    isSingleStep,
    lastTurnGroup,
    lastStep,
    lastStepIsResearchAgent,
    lastStepSupportsCollapsedStreaming,
  } = useTimelineMetrics(turnGroups, userStopped);

  // Extract memory text, operation, and whether this is a memory-only timeline
  const { memoryText, memoryOperation, memoryId, memoryIndex, isMemoryOnly } =
    useTimelineStepState(turnGroups);

  // Check if last step is a search tool for INLINE render type
  const lastStepIsSearchTool = useMemo(
    () => lastStep && isSearchToolPackets(lastStep.packets),
    [lastStep]
  );

  // HITL: detect workflow pause — auto-expand so user sees the questions
  const lastStepIsPause = useMemo(
    () => (lastStep ? isWorkflowPausePackets(lastStep.packets) : false),
    [lastStep]
  );

  // Whether this timeline belongs to a workflow run (any step is a workflow
  // step / orchestrator / pause). Drives the always-visible "View execution
  // trace" button in the header — works live and from history (history
  // reconstructs WorkflowStepStart / WorkflowPauseForInput packets).
  const isWorkflowTimeline = useMemo(
    () =>
      turnGroups.some((tg) =>
        tg.steps.some(
          (s) =>
            isWorkflowStepPackets(s.packets) ||
            isWorkflowOrchestratorPackets(s.packets) ||
            isWorkflowPausePackets(s.packets)
        )
      ),
    [turnGroups]
  );

  const { isExpanded, handleToggle, parallelActiveTab, setParallelActiveTab } =
    useTimelineExpansion(
      stopPacketSeen,
      lastTurnGroup,
      hasDisplayContent,
      lastStepIsPause
    );

  // Streaming duration tracking
  const streamingStartTime = useStreamingStartTime();

  // Parallel step analysis for collapsed streaming view
  const parallelActiveStep = useMemo(() => {
    if (!lastTurnGroup?.isParallel) return null;
    return (
      lastTurnGroup.steps.find((s) => s.key === parallelActiveTab) ??
      lastTurnGroup.steps[0]
    );
  }, [lastTurnGroup, parallelActiveTab]);

  const parallelActiveStepSupportsCollapsedStreaming = useMemo(() => {
    if (!parallelActiveStep) return false;
    return stepSupportsCollapsedStreaming(parallelActiveStep.packets);
  }, [parallelActiveStep]);

  const lastStepHasCollapsedContent = useMemo(() => {
    if (!lastStep) return false;
    return stepHasCollapsedStreamingContent(lastStep.packets);
  }, [lastStep]);

  const parallelActiveStepHasCollapsedContent = useMemo(() => {
    if (!parallelActiveStep) return false;
    return stepHasCollapsedStreamingContent(parallelActiveStep.packets);
  }, [parallelActiveStep]);

  const stoppedStepsCount = useMemo(() => {
    if (!stopPacketSeen || !userStopped) {
      return totalSteps;
    }

    let count = 0;
    for (const turnGroup of turnGroups) {
      for (const step of turnGroup.steps) {
        if (stepHasCollapsedStreamingContent(step.packets)) {
          count += 1;
        }
      }
    }

    return count;
  }, [stopPacketSeen, userStopped, totalSteps, turnGroups]);

  // Derive all UI state from inputs
  const {
    uiState,
    showCollapsedCompact,
    showCollapsedParallel,
    showParallelTabs,
    showDoneStep,
    showStoppedStep,
    hasDoneIndicator,
    showTintedBackground,
    showRoundedBottom,
  } = useTimelineUIState({
    stopPacketSeen,
    hasPackets,
    hasDisplayContent,
    userStopped,
    isExpanded,
    lastTurnGroup,
    lastStep,
    lastStepSupportsCollapsedStreaming,
    lastStepHasCollapsedContent,
    lastStepIsResearchAgent,
    parallelActiveStepSupportsCollapsedStreaming,
    parallelActiveStepHasCollapsedContent,
    isGeneratingImage,
    finalAnswerComing,
    lastStepIsPause,
  });

  // ── Multi-agent workflow → side dock panel ────────────────────────────────
  // Workflow runs move out of the inline stack into the right-side dock; the
  // inline chat keeps only a trigger chip. Non-workflow timelines are untouched.
  // Keyed on nodeId (always present, stable) — NOT messageId, which is undefined
  // during the first streaming window. messageId is used only for the trace API.
  const messageId = chatState.messageId;
  const panelOpen = useAgentPanelStore((s) => s.open);
  const panelNodeId = useAgentPanelStore((s) => s.nodeId);
  const openPanelFor = useAgentPanelStore((s) => s.openFor);
  const togglePanelFor = useAgentPanelStore((s) => s.toggleFor);
  const closePanel = useAgentPanelStore((s) => s.close);
  const scheduleAutoClose = useAgentPanelStore((s) => s.scheduleAutoClose);
  const isMobile = useSettingsContext().isMobile;

  // Whether this timeline should use the dock (vs. the inline fallback).
  const dockActive = agentDockEnabled && isWorkflowTimeline && nodeId != null;

  const isThisPanelOpen = dockActive && panelOpen && panelNodeId === nodeId;

  // Auto-open the dock once when a live workflow run begins streaming. Skipped on
  // mobile, where the panel is a full-screen overlay — the user opens it explicitly.
  const autoOpenedRef = useRef(false);
  useEffect(() => {
    if (!dockActive || nodeId == null || isMobile) return;
    if (!stopPacketSeen && hasPackets && !autoOpenedRef.current) {
      autoOpenedRef.current = true;
      openPanelFor(nodeId, { userInitiated: false });
    }
  }, [dockActive, nodeId, stopPacketSeen, hasPackets, isMobile, openPanelFor]);

  // HITL pause: force the panel open (desktop AND mobile, overriding a prior
  // manual close) so the user can see and answer the workflow's questions.
  // Fires once per pause transition.
  const pauseForcedRef = useRef(false);
  useEffect(() => {
    if (!dockActive || nodeId == null) return;
    if (lastStepIsPause && !pauseForcedRef.current) {
      pauseForcedRef.current = true;
      openPanelFor(nodeId, { userInitiated: false });
    } else if (!lastStepIsPause) {
      pauseForcedRef.current = false;
    }
  }, [dockActive, nodeId, lastStepIsPause, openPanelFor]);

  // Auto-close ~10s after the run completes (cancelled if the user interacts).
  useEffect(() => {
    if (!dockActive || nodeId == null) return;
    if (stopPacketSeen) scheduleAutoClose(nodeId);
  }, [dockActive, nodeId, stopPacketSeen, scheduleAutoClose]);

  // Resolve the dock's portal target while this message owns the open panel.
  const [slotEl, setSlotEl] = useState<HTMLElement | null>(null);
  useEffect(() => {
    if (!isThisPanelOpen) {
      setSlotEl(null);
      return;
    }
    setSlotEl(document.getElementById(AGENT_PANEL_SLOT_ID));
  }, [isThisPanelOpen]);

  // Live elapsed time for the panel header (ticks while streaming, freezes to the
  // final backend duration when done). Reuses the same hook StreamingHeader uses.
  const panelElapsedSeconds = useStreamingDuration(
    !stopPacketSeen,
    streamingStartTime,
    stopPacketSeen
      ? (toolProcessingDuration ?? processingDurationSeconds)
      : undefined
  );

  // done/total for the panel progress bar. A step is "done" once it is no longer
  // the actively-streaming step; when the run stops, everything is done.
  const panelDoneCount = useMemo(() => {
    if (stopPacketSeen) return totalSteps;
    const activeCount = lastTurnGroup?.isParallel
      ? lastTurnGroup.steps.length
      : 1;
    return Math.max(0, totalSteps - activeCount);
  }, [stopPacketSeen, totalSteps, lastTurnGroup]);

  const panelTitle = useMemo(() => {
    if (!stopPacketSeen) return "Agents thinking";
    const dur = toolProcessingDuration ?? processingDurationSeconds;
    return dur
      ? `Thought for ${formatDurationSeconds(dur)}`
      : "Thought for some time";
  }, [stopPacketSeen, toolProcessingDuration, processingDurationSeconds]);

  const headerIsInteractive = useMemo(() => {
    if (!collapsible || isMemoryOnly) {
      return false;
    }

    if (uiState === TimelineUIState.STOPPED) {
      return stoppedStepsCount > 0;
    }

    return totalSteps > 0;
  }, [collapsible, isMemoryOnly, uiState, stoppedStepsCount, totalSteps]);

  // Determine render type override for collapsed streaming view
  const collapsedRenderTypeOverride = useMemo(() => {
    if (lastStepIsResearchAgent) return RenderType.HIGHLIGHT;
    if (lastStepIsSearchTool) return RenderType.INLINE;
    return RenderType.COMPACT;
  }, [lastStepIsResearchAgent, lastStepIsSearchTool]);

  // Header selection based on UI state
  const renderHeader = useCallback(() => {
    switch (uiState) {
      case TimelineUIState.STREAMING_PARALLEL:
        // Only show parallel header when collapsed (showParallelTabs includes !isExpanded check)
        if (showParallelTabs && lastTurnGroup) {
          return (
            <ParallelStreamingHeader
              steps={lastTurnGroup.steps}
              activeTab={parallelActiveTab}
              onTabChange={setParallelActiveTab}
              collapsible={collapsible}
              isExpanded={isExpanded}
              onToggle={handleToggle}
            />
          );
        }
      // falls through to sequential header when expanded or no lastTurnGroup
      case TimelineUIState.STREAMING_SEQUENTIAL:
        return (
          <StreamingHeader
            headerText={headerText}
            collapsible={collapsible}
            buttonTitle={buttonTitle}
            isExpanded={isExpanded}
            onToggle={handleToggle}
            streamingStartTime={streamingStartTime}
            toolProcessingDuration={toolProcessingDuration}
          />
        );

      case TimelineUIState.STOPPED:
        return (
          <StoppedHeader
            totalSteps={stoppedStepsCount}
            collapsible={collapsible}
            isExpanded={isExpanded}
            onToggle={handleToggle}
          />
        );

      case TimelineUIState.COMPLETED_COLLAPSED:
      case TimelineUIState.COMPLETED_EXPANDED:
        return (
          <CompletedHeader
            totalSteps={totalSteps}
            collapsible={collapsible}
            isExpanded={isExpanded}
            onToggle={handleToggle}
            processingDurationSeconds={
              toolProcessingDuration ?? processingDurationSeconds
            }
            generatedImageCount={generatedImageCount}
            isMemoryOnly={isMemoryOnly}
            memoryText={memoryText}
            memoryOperation={memoryOperation}
            memoryId={memoryId}
            memoryIndex={memoryIndex}
            isPaused={lastStepIsPause}
          />
        );

      default:
        return null;
    }
  }, [
    uiState,
    showParallelTabs,
    lastTurnGroup,
    parallelActiveTab,
    setParallelActiveTab,
    collapsible,
    isExpanded,
    handleToggle,
    headerText,
    buttonTitle,
    streamingStartTime,
    isMemoryOnly,
    memoryText,
    memoryOperation,
    memoryId,
    memoryIndex,
    totalSteps,
    stoppedStepsCount,
    processingDurationSeconds,
    generatedImageCount,
    toolProcessingDuration,
    lastStepIsPause,
  ]);

  // Empty state: no packets, still streaming, and not stopped
  if (uiState === TimelineUIState.EMPTY) {
    return (
      <TimelineContainer
        agent={chatState.assistant}
        headerContent={
          <div className="flex w-full h-full items-center gap-2 pl-[var(--timeline-header-padding-left)] pr-[var(--timeline-header-padding-right)]">
            <SpinnerRing size={14} />
            <span className="font-main-ui-action text-text-04">
              {headerText}
            </span>
            <WaveDots />
          </div>
        }
      />
    );
  }

  // Display content only (no timeline steps) - but show header for image generation
  if (uiState === TimelineUIState.DISPLAY_CONTENT_ONLY) {
    return <TimelineContainer agent={chatState.assistant} />;
  }

  // Multi-agent workflow run (with the dock available): render a compact trigger
  // chip inline and portal the live streaming cards into the right-side dock. When
  // the dock is disabled (e.g. shared chat), fall through to the inline path below.
  if (dockActive && nodeId != null) {
    const isLive = !stopPacketSeen;
    const handleChipToggle = () => togglePanelFor(nodeId);
    return (
      <>
        <TimelineContainer
          agent={chatState.assistant}
          headerContent={
            <WorkflowTriggerChip
              title={panelTitle}
              isLive={isLive}
              totalSteps={totalSteps}
              panelOpen={isThisPanelOpen}
              onToggle={handleChipToggle}
              messageId={messageId}
            />
          }
        />
        {isThisPanelOpen &&
          slotEl &&
          createPortal(
            <AgentRunPanel
              agent={chatState.assistant}
              isLive={isLive}
              title={panelTitle}
              doneCount={panelDoneCount}
              totalCount={totalSteps}
              elapsedSeconds={panelElapsedSeconds}
              messageId={messageId}
              onClose={() => closePanel({ userInitiated: true })}
            >
              <ExpandedTimelineContent
                turnGroups={turnGroups}
                chatState={chatState}
                stopPacketSeen={stopPacketSeen}
                stopReason={stopReason}
                isSingleStep={isSingleStep}
                userStopped={userStopped}
                showDoneStep={stopPacketSeen && !userStopped}
                showStoppedStep={userStopped}
                hasDoneIndicator={stopPacketSeen && !userStopped}
              />
            </AgentRunPanel>,
            slotEl
          )}
      </>
    );
  }

  return (
    <TimelineContainer
      agent={chatState.assistant}
      headerContent={
        <div
          className={cn(
            "flex flex-1 min-w-0 h-full items-center gap-1 p-1 rounded-t-12 transition-colors duration-300",
            headerIsInteractive && "hover:bg-background-tint-00",
            showTintedBackground && "bg-background-tint-00",
            showRoundedBottom && "rounded-b-12"
          )}
        >
          <div className="flex items-center justify-between flex-1 min-w-0 h-full">
            {renderHeader()}
          </div>
          {isWorkflowTimeline && (
            <WorkflowTraceButton
              compact
              live={!stopPacketSeen}
              messageId={chatState.messageId}
            />
          )}
        </div>
      }
    >
      {/* Collapsed streaming view - single step compact mode */}
      {showCollapsedCompact && lastStep && (
        <CollapsedStreamingContent
          step={lastStep}
          chatState={chatState}
          stopReason={stopReason}
          renderTypeOverride={collapsedRenderTypeOverride}
        />
      )}

      {/* Collapsed streaming view - parallel tools compact mode */}
      {showCollapsedParallel && parallelActiveStep && (
        <CollapsedStreamingContent
          step={parallelActiveStep}
          chatState={chatState}
          stopReason={stopReason}
          renderTypeOverride={RenderType.HIGHLIGHT}
        />
      )}

      {/* Expanded timeline view */}
      {isExpanded && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-300">
          <ExpandedTimelineContent
            turnGroups={turnGroups}
            chatState={chatState}
            stopPacketSeen={stopPacketSeen}
            stopReason={stopReason}
            isSingleStep={isSingleStep}
            userStopped={userStopped}
            showDoneStep={showDoneStep}
            showStoppedStep={showStoppedStep}
            hasDoneIndicator={hasDoneIndicator}
          />
        </div>
      )}
    </TimelineContainer>
  );
}, areAgentTimelinePropsEqual);

export default AgentTimeline;
