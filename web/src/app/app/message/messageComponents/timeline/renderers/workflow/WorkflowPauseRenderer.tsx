import React from "react";
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

  // The full questions text is emitted as main message content
  // (AgentResponseStart/Delta), so the timeline only shows a compact status.
  return children([
    {
      icon: SvgCircle,
      status: `${personaName} — Waiting for input`,
      content: <></>,
      accent: "blue",
    },
  ]);
};
