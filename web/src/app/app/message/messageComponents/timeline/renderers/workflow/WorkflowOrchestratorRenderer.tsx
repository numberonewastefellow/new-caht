import React, { useCallback, useMemo } from "react";
import { SvgWorkflow } from "@opal/icons";

import {
  PacketType,
  WorkflowOrchestratorPacket,
  WorkflowOrchestratorThinking,
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

export const WorkflowOrchestratorRenderer: MessageRenderer<
  WorkflowOrchestratorPacket,
  FullChatState
> = ({ packets, stopPacketSeen, children }) => {
  const isComplete = packets.some(
    (p) =>
      p.obj.type === PacketType.SECTION_END ||
      p.obj.type === PacketType.ERROR
  );

  // Build content from all thinking packets
  const fullContent = useMemo(
    () =>
      packets
        .filter(
          (p) => p.obj.type === PacketType.WORKFLOW_ORCHESTRATOR_THINKING
        )
        .map((p) => (p.obj as WorkflowOrchestratorThinking).content)
        .join(""),
    [packets]
  );

  const statusText = isComplete ? "Orchestrated" : "Orchestrating";

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

  if (!fullContent) {
    return children([
      {
        icon: SvgWorkflow,
        status: null,
        content: <></>,
        accent: "purple",
      },
    ]);
  }

  const orchestratorContent = (
    <div className="pl-[var(--timeline-common-text-padding)]">
      <ExpandableTextDisplay
        title="Orchestrator Thinking"
        content={fullContent}
        renderContent={renderMarkdown}
        isStreaming={!isComplete && !stopPacketSeen}
      />
    </div>
  );

  return children([
    {
      icon: SvgWorkflow,
      status: statusText,
      content: orchestratorContent,
      expandedText: orchestratorContent,
      accent: "purple",
    },
  ]);
};
