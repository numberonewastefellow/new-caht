import React, { useCallback, useMemo } from "react";
import { SvgUser } from "@opal/icons";

import {
  PacketType,
  WorkflowStepPacket,
  WorkflowStepStart,
  WorkflowStepDelta,
} from "@/app/app/services/streamingModels";
import {
  MessageRenderer,
  FullChatState,
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

  // Check completion
  const isComplete = packets.some(
    (p) =>
      p.obj.type === PacketType.SECTION_END ||
      p.obj.type === PacketType.WORKFLOW_STEP_END ||
      p.obj.type === PacketType.ERROR
  );

  // Build content from delta packets
  const fullContent = useMemo(
    () =>
      packets
        .filter((p) => p.obj.type === PacketType.WORKFLOW_STEP_DELTA)
        .map((p) => (p.obj as WorkflowStepDelta).content)
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

  return children([
    {
      icon: SvgUser,
      status: statusText,
      content: stepContent,
    },
  ]);
};
