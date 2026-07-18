import React, { useCallback, useMemo } from "react";
import { SvgUser, SvgSparkle } from "@opal/icons";

import {
  PacketType,
  WorkflowStepPacket,
  WorkflowStepStart,
  WorkflowStepDelta,
  WorkflowStepReasoningDelta,
} from "@/app/app/services/streamingModels";
import {
  MessageRenderer,
  FullChatState,
  RendererResult,
} from "@/app/app/message/messageComponents/interfaces";
import MinimalMarkdown from "@/components/chat/MinimalMarkdown";
import ExpandableTextDisplay from "@/refresh-components/texts/ExpandableTextDisplay";
import {
  mutedTextMarkdownComponents,
  collapsedMarkdownComponents,
} from "@/app/app/message/messageComponents/timeline/renderers/sharedMarkdownComponents";
export const WorkflowStepRenderer: MessageRenderer<
  WorkflowStepPacket,
  FullChatState
> = ({ packets, stopPacketSeen, children }) => {
  // Extract step metadata from the start packet
  const startPacket = packets.find(
    (p) => p.obj.type === PacketType.WORKFLOW_STEP_START
  );
  const stepStart = startPacket?.obj as WorkflowStepStart | undefined;
  const personaName = stepStart?.persona_name || "Agent";
  const stepName = stepStart?.step_name || "";

  // Check completion. Only an explicit WorkflowStepEnd (or ERROR) means the step
  // is done — deliberately NOT SECTION_END. packetProcessor injects a synthetic
  // SECTION_END into this (now-prior) group the instant a sub-agent's tool packet
  // opens a higher turn_index; treating that as completion would flip the step to
  // "complete" mid-run and freeze live streaming of the final answer. Every
  // terminal path (complete/cancel/pause) and the reload reconstructor emit an
  // explicit WorkflowStepEnd, so this is both correct and reload-safe.
  const isComplete = packets.some(
    (p) =>
      p.obj.type === PacketType.WORKFLOW_STEP_END ||
      p.obj.type === PacketType.ERROR
  );

  // Build content from delta packets. Live sub-agent prose streams as append
  // deltas (replace=false); the final authoritative agent_output arrives as a
  // replace=true delta that resets the accumulator (reconcile). This lets the
  // step render token-by-token, then snap to the canonical output on complete.
  const fullContent = useMemo(() => {
    let acc = "";
    for (const p of packets) {
      if (p.obj.type !== PacketType.WORKFLOW_STEP_DELTA) continue;
      const delta = p.obj as WorkflowStepDelta;
      if (delta.replace) {
        acc = delta.content;
      } else {
        acc += delta.content;
      }
    }
    return acc;
  }, [packets]);

  // Live sub-agent reasoning ("thinking"). Ephemeral — only present during a
  // live run (not reconstructed on session reload).
  const reasoningContent = useMemo(
    () =>
      packets
        .filter((p) => p.obj.type === PacketType.WORKFLOW_STEP_REASONING_DELTA)
        .map((p) => (p.obj as WorkflowStepReasoningDelta).content)
        .join(""),
    [packets]
  );

  const statusText = isComplete ? `${personaName}` : personaName;

  // Markdown renderer callback
  const renderMarkdown = useCallback(
    (text: string, isExpanded?: boolean) => (
      <MinimalMarkdown
        content={text}
        components={
          isExpanded ? mutedTextMarkdownComponents : collapsedMarkdownComponents
        }
      />
    ),
    []
  );

  const stepContent = fullContent ? (
    <div className="pl-[var(--timeline-common-text-padding)]">
      <ExpandableTextDisplay
        title={`${personaName}: ${stepName}`}
        content={fullContent}
        renderContent={renderMarkdown}
        isStreaming={!isComplete && !stopPacketSeen}
      />
    </div>
  ) : (
    <></>
  );

  const results: RendererResult[] = [];

  // Collapsible "thinking" row above the prose (only when reasoning streamed).
  if (reasoningContent) {
    const reasoningBlock = (
      <div className="pl-[var(--timeline-common-text-padding)]">
        <ExpandableTextDisplay
          title={`${personaName}: Reasoning`}
          content={reasoningContent}
          renderContent={renderMarkdown}
          isStreaming={!isComplete && !stopPacketSeen}
          maxLines={3}
        />
      </div>
    );
    results.push({
      icon: SvgSparkle,
      status: isComplete ? "Reasoned" : "Reasoning",
      content: reasoningBlock,
      expandedText: reasoningBlock,
      accent: "purple",
    });
  }

  results.push({
    icon: SvgUser,
    status: statusText,
    content: stepContent,
  });

  return children(results);
};
