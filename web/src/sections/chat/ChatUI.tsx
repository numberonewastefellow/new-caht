"use client";

import React, { useCallback, useMemo, useRef } from "react";
import { Message } from "@/app/app/interfaces";
import { OmDocument, MinimalOnyxDocument } from "@/lib/search/interfaces";
import HumanMessage from "@/app/app/message/HumanMessage";
import { ErrorBanner } from "@/app/app/message/Resubmit";
import { MinimalAgentSnapshot } from "@/app/admin/assistants/interfaces";
import { LlmDescriptor, LlmManager } from "@/lib/hooks";
import AgentMessage from "@/app/app/message/messageComponents/AgentMessage";
import Spacer from "@/refresh-components/Spacer";
import DynamicBottomSpacer from "@/components/chat/DynamicBottomSpacer";
import {
  useChatSessionStore,
  useSessionMessageHistory,
  useSessionMessageTree,
  useSessionLoadingError,
  useSessionUncaughtError,
} from "@/app/app/stores/useChatSessionStore";
import { upsertMessages, setMessageAsLatest } from "@/app/app/services/messageTree";
import { patchMessageToBeLatest } from "@/app/app/services/lib";
import type { Packet } from "@/app/app/services/streamingModels";

export interface ChatUIProps {
  liveAssistant: MinimalAgentSnapshot;
  llmManager: LlmManager;
  setPresentingDocument: (doc: MinimalOnyxDocument | null) => void;
  onMessageSelection: (nodeId: number) => void;
  stopGenerating: () => void;
  chatSessionId: string;

  // Submit handlers
  onSubmit: (args: {
    message: string;
    messageIdToResend?: number;
    currentMessageFiles: any[];
    deepResearch: boolean;
    modelOverride?: LlmDescriptor;
    regenerationRequest?: {
      messageId: number;
      parentMessage: Message;
      forceSearch?: boolean;
    };
    forceSearch?: boolean;
  }) => Promise<void>;
  deepResearchEnabled: boolean;
  currentMessageFiles: any[];

  onResubmit: () => void;

  /**
   * Node ID of the message to use as scroll anchor.
   * Used by DynamicBottomSpacer to position the push-up effect.
   */
  anchorNodeId?: number;

  /**
   * Per-panel model label (compare mode). When set, overrides the model name
   * shown on assistant messages so panels 2/3 display their own model rather
   * than the single `llmManager.currentLlm`. Undefined for normal single chat.
   */
  overriddenModelName?: string;
}

const ChatUI = React.memo(
  ({
    liveAssistant,
    llmManager,
    setPresentingDocument,
    onMessageSelection,
    stopGenerating,
    onSubmit,
    deepResearchEnabled,
    currentMessageFiles,
    onResubmit,
    anchorNodeId,
    chatSessionId,
    overriddenModelName,
  }: ChatUIProps) => {
    // Get messages and error state from the store, scoped to THIS panel's
    // session id. (Compare panels each pass their own session so a packet in
    // one panel re-renders only that panel — not the others.)
    const messages = useSessionMessageHistory(chatSessionId);
    const messageTree = useSessionMessageTree(chatSessionId);
    const error = useSessionUncaughtError(chatSessionId);
    const loadError = useSessionLoadingError(chatSessionId);
    // Stable fallbacks to avoid changing prop identities on each render
    const emptyDocs = useMemo<OmDocument[]>(() => [], []);
    const emptyChildrenIds = useMemo<number[]>(() => [], []);

    // Use refs to keep callbacks stable while always using latest values
    const onSubmitRef = useRef(onSubmit);
    const deepResearchEnabledRef = useRef(deepResearchEnabled);
    const currentMessageFilesRef = useRef(currentMessageFiles);
    onSubmitRef.current = onSubmit;
    deepResearchEnabledRef.current = deepResearchEnabled;
    currentMessageFilesRef.current = currentMessageFiles;

    const createRegenerator = useCallback(
      (regenerationRequest: {
        messageId: number;
        parentMessage: Message;
        forceSearch?: boolean;
      }) => {
        return async function (modelOverride: LlmDescriptor) {
          return await onSubmitRef.current({
            message: regenerationRequest.parentMessage.message,
            currentMessageFiles: currentMessageFilesRef.current,
            deepResearch: deepResearchEnabledRef.current,
            modelOverride,
            messageIdToResend: regenerationRequest.parentMessage.messageId,
            regenerationRequest,
            forceSearch: regenerationRequest.forceSearch,
          });
        };
      },
      []
    );

    // Callback for "Run" button: inserts execution result as sibling message
    const handleCodeExecutionResult = useCallback(
      (
        parentNodeId: number,
        result: {
          messageId: number;
          parentMessageId: number;
          content: string;
          files: Array<{ id: string; type: string; name?: string }>;
        }
      ) => {
        // Create a new message node for the execution result
        const newNodeId = -Date.now(); // Unique negative ID for temp node
        const placement = { turn_index: 0, tab_index: 0, sub_turn_index: null };

        // Build streaming packets so AgentMessage renders as complete (not "Thinking...")
        const execPackets: Packet[] = [
          {
            placement,
            obj: {
              type: "message_start" as const,
              id: `exec-${result.messageId}`,
              content: "",
              final_documents: null,
            },
          },
          {
            placement,
            obj: {
              type: "message_delta" as const,
              content: result.content,
            },
          },
          {
            placement,
            obj: {
              type: "stop" as const,
              stop_reason: undefined,
            },
          },
        ];

        const newMessage: Message = {
          messageId: result.messageId,
          nodeId: newNodeId,
          message: result.content,
          type: "assistant",
          files: result.files.map((f) => ({
            id: f.id,
            type: f.type as any,
            name: f.name,
          })),
          toolCall: null,
          parentNodeId: parentNodeId,
          childrenNodeIds: [],
          latestChildNodeId: null,
          packets: execPackets,
          packetCount: execPackets.length,
        };

        // Insert into message tree as a sibling (same parent), make it latest
        const currentTree = messageTree || new Map();
        const updatedTree = upsertMessages(currentTree, [newMessage], true);
        const finalTree = setMessageAsLatest(updatedTree, newNodeId);
        const { updateSessionMessageTree } = useChatSessionStore.getState();
        updateSessionMessageTree(chatSessionId, finalTree);

        // Persist to backend
        patchMessageToBeLatest(result.messageId);
      },
      [messageTree, chatSessionId]
    );

    const handleEditWithMessageId = useCallback(
      (editedContent: string, msgId: number) => {
        onSubmitRef.current({
          message: editedContent,
          messageIdToResend: msgId,
          currentMessageFiles: [],
          deepResearch: deepResearchEnabledRef.current,
        });
      },
      []
    );

    return (
      <div className="w-full max-w-[var(--app-page-main-content-width)] h-full">
        <Spacer />
        {messages.map((message, i) => {
          const messageReactComponentKey = `message-${message.nodeId}`;
          const parentMessage = message.parentNodeId
            ? messageTree?.get(message.parentNodeId)
            : null;
          if (message.type === "user") {
            const nextMessage =
              messages.length > i + 1 ? messages[i + 1] : null;

            return (
              <div id={messageReactComponentKey} key={messageReactComponentKey}>
                <HumanMessage
                  disableSwitchingForStreaming={
                    (nextMessage && nextMessage.is_generating) || false
                  }
                  stopGenerating={stopGenerating}
                  content={message.message}
                  files={message.files}
                  messageId={message.messageId}
                  nodeId={message.nodeId}
                  onEdit={handleEditWithMessageId}
                  otherMessagesCanSwitchTo={
                    parentMessage?.childrenNodeIds ?? emptyChildrenIds
                  }
                  onMessageSelection={onMessageSelection}
                />
              </div>
            );
          } else if (message.type === "assistant") {
            if ((error || loadError) && i === messages.length - 1) {
              return (
                <div key={`error-${message.nodeId}`} className="p-4">
                  <ErrorBanner
                    resubmit={onResubmit}
                    error={error || loadError || ""}
                    errorCode={message.errorCode || undefined}
                    isRetryable={message.isRetryable ?? true}
                    details={message.errorDetails || undefined}
                    stackTrace={message.stackTrace || undefined}
                  />
                </div>
              );
            }

            const previousMessage = i !== 0 ? messages[i - 1] : null;
            const chatStateData = {
              assistant: liveAssistant,
              docs: message.documents ?? emptyDocs,
              citations: message.citations,
              setPresentingDocument,
              overriddenModel:
                overriddenModelName ?? llmManager.currentLlm?.modelName,
              researchType: message.researchType,
            };

            return (
              <div
                id={`message-${message.nodeId}`}
                key={messageReactComponentKey}
              >
                <AgentMessage
                  rawPackets={message.packets}
                  packetCount={message.packetCount}
                  chatState={chatStateData}
                  nodeId={message.nodeId}
                  messageId={message.messageId}
                  currentFeedback={message.currentFeedback}
                  llmManager={llmManager}
                  otherMessagesCanSwitchTo={
                    parentMessage?.childrenNodeIds ?? emptyChildrenIds
                  }
                  onMessageSelection={onMessageSelection}
                  onRegenerate={createRegenerator}
                  parentMessage={previousMessage}
                  processingDurationSeconds={message.processingDurationSeconds}
                  chatSessionId={chatSessionId}
                  onCodeExecutionResult={handleCodeExecutionResult}
                />
              </div>
            );
          }
          return null;
        })}

        {/* Error banner when last message is user message or error type */}
        {(((error !== null || loadError !== null) &&
          messages[messages.length - 1]?.type === "user") ||
          messages[messages.length - 1]?.type === "error") && (
          <div className="p-4">
            <ErrorBanner
              resubmit={onResubmit}
              error={error || loadError || ""}
              errorCode={messages[messages.length - 1]?.errorCode || undefined}
              isRetryable={messages[messages.length - 1]?.isRetryable ?? true}
              details={messages[messages.length - 1]?.errorDetails || undefined}
              stackTrace={
                messages[messages.length - 1]?.stackTrace || undefined
              }
            />
          </div>
        )}

        {/* Dynamic spacer for "fresh chat" effect - pushes content up when new message is sent */}
        <DynamicBottomSpacer anchorNodeId={anchorNodeId} />
      </div>
    );
  }
);
ChatUI.displayName = "ChatUI";

export default ChatUI;
