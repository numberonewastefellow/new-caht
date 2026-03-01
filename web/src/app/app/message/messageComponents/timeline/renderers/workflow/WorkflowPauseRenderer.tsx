import React, { useCallback, useMemo } from "react";
import { SvgCircle } from "@opal/icons";

import {
  PacketType,
  WorkflowPausePacket,
  WorkflowPauseForInput,
} from "@/app/app/services/streamingModels";
import {
  MessageRenderer,
  FullChatState,
} from "@/app/app/message/messageComponents/interfaces";
import MinimalMarkdown from "@/components/chat/MinimalMarkdown";
import { mutedTextMarkdownComponents } from "@/app/app/message/messageComponents/timeline/renderers/sharedMarkdownComponents";

export const WorkflowPauseRenderer: MessageRenderer<
  WorkflowPausePacket,
  FullChatState
> = ({ packets, children }) => {
  // Extract pause metadata
  const pausePacket = packets.find(
    (p) => p.obj.type === PacketType.WORKFLOW_PAUSE_FOR_INPUT
  );
  const pauseData = pausePacket?.obj as WorkflowPauseForInput | undefined;
  const personaName = pauseData?.persona_name || "Agent";
  const questions = pauseData?.questions || "";

  const renderMarkdown = useCallback(
    (text: string) => (
      <MinimalMarkdown
        content={text}
        components={mutedTextMarkdownComponents}
      />
    ),
    []
  );

  const pauseContent = useMemo(
    () => (
      <div className="pl-[var(--timeline-common-text-padding)]">
        <div
          className="rounded-lg p-3 mt-1"
          style={{
            border: "1px solid var(--virtualai-accent-subtle, rgba(245, 158, 11, 0.2))",
            backgroundColor: "var(--virtualai-accent-subtle, rgba(245, 158, 11, 0.05))",
          }}
        >
          <div className="text-xs font-medium mb-2 opacity-70">
            {personaName} needs more information
          </div>
          {renderMarkdown(questions)}
        </div>
      </div>
    ),
    [personaName, questions, renderMarkdown]
  );

  return children([
    {
      icon: SvgCircle,
      status: `${personaName} — Waiting for input`,
      content: pauseContent,
      accent: "blue",
    },
  ]);
};
