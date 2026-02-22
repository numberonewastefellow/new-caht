"use client";

import React, { useRef, RefObject, useMemo, useCallback, useState, Dispatch, SetStateAction } from "react";
import { Packet, StreamingCitation, StopReason } from "@/app/app/services/streamingModels";
import { FullChatState } from "@/app/app/message/messageComponents/interfaces";
import { FeedbackType } from "@/app/app/interfaces";
import { MinimalOnyxDocument, OnyxDocument } from "@/lib/search/interfaces";
import { handleCopy } from "@/app/app/message/copyingUtils";
import { useMessageSwitching } from "@/app/app/message/messageComponents/hooks/useMessageSwitching";
import { RendererComponent } from "@/app/app/message/messageComponents/renderMessageComponent";
import { usePacketProcessor } from "@/app/app/message/messageComponents/timeline/hooks/usePacketProcessor";
import { usePacedTurnGroups } from "@/app/app/message/messageComponents/timeline/hooks/usePacedTurnGroups";
import MessageToolbar from "@/app/app/message/messageComponents/MessageToolbar";
import { LlmDescriptor, LlmManager } from "@/lib/hooks";
import { Message } from "@/app/app/interfaces";
import Text from "@/refresh-components/texts/Text";
import { AgentTimeline } from "@/app/app/message/messageComponents/timeline/AgentTimeline";
import { citationsToSourceInfoArray } from "@/refresh-components/buttons/source-tag/sourceTagUtils";
import { SvgBookOpen } from "@opal/icons";
import { cn } from "@/lib/utils";
import { removeDuplicateDocs } from "@/lib/documentUtils";
import CitedSourcesModal from "@/sections/document-sidebar/CitedSourcesModal";

// Type for the regeneration factory function passed from ChatUI
export type RegenerationFactory = (regenerationRequest: {
  messageId: number;
  parentMessage: Message;
  forceSearch?: boolean;
}) => (modelOverride: LlmDescriptor) => Promise<void>;

export interface AgentMessageProps {
  rawPackets: Packet[];
  packetCount?: number; // Tracked separately for React memo comparison (avoids reading from mutated array)
  chatState: FullChatState;
  nodeId: number;
  messageId?: number;
  currentFeedback?: FeedbackType | null;
  llmManager: LlmManager | null;
  otherMessagesCanSwitchTo?: number[];
  onMessageSelection?: (nodeId: number) => void;
  // Stable regeneration callback - takes (parentMessage) and returns a function that takes (modelOverride)
  onRegenerate?: RegenerationFactory;
  // Parent message needed to construct regeneration request
  parentMessage?: Message | null;
  // Duration in seconds for processing this message (assistant messages only)
  processingDurationSeconds?: number;
}

/** Pill-shaped references button that opens a modal with cited sources. */
const ReferencesStrip = React.memo(function ReferencesStrip({
  citations,
  documentMap,
  allDocs,
  setPresentingDocument,
}: {
  citations: StreamingCitation[];
  documentMap: Map<string, OnyxDocument>;
  allDocs: OnyxDocument[];
  setPresentingDocument: Dispatch<SetStateAction<MinimalOnyxDocument | null>>;
}) {
  const [modalOpen, setModalOpen] = useState(false);

  const sources = useMemo(
    () => citationsToSourceInfoArray(citations, documentMap),
    [citations, documentMap]
  );

  // Build cited vs other document lists for the modal
  const { citedDocuments, otherDocuments } = useMemo(() => {
    const citedDocIds = new Set(citations.map((c) => c.document_id));
    const deduped = removeDuplicateDocs(allDocs);

    const cited = deduped
      .filter((doc) => citedDocIds.has(doc.document_id))
      .sort((a, b) => {
        const idxA = citations.findIndex((c) => c.document_id === a.document_id);
        const idxB = citations.findIndex((c) => c.document_id === b.document_id);
        return idxA - idxB;
      });

    const other = deduped.filter((doc) => !citedDocIds.has(doc.document_id));

    return { citedDocuments: cited, otherDocuments: other };
  }, [citations, allDocs]);

  if (sources.length === 0) return null;

  return (
    <div className="px-3">
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full",
          "text-sm font-medium transition-all duration-150",
          "border cursor-pointer",
          modalOpen
            ? "text-white border-transparent"
            : "bg-background-tint-02 text-text-04 border-border-02 hover:text-white hover:border-transparent"
        )}
        style={
          modalOpen
            ? { backgroundColor: "var(--virtualai-accent, var(--theme-primary-05))" }
            : undefined
        }
        onMouseEnter={(e) => {
          if (!modalOpen) {
            e.currentTarget.style.backgroundColor = "var(--virtualai-accent, var(--theme-primary-05))";
          }
        }}
        onMouseLeave={(e) => {
          if (!modalOpen) {
            e.currentTarget.style.backgroundColor = "";
          }
        }}
      >
        <SvgBookOpen className="w-4 h-4" />
        <span>
          {sources.length} {sources.length === 1 ? "Reference" : "References"}
        </span>
      </button>

      <CitedSourcesModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        citedDocuments={citedDocuments}
        otherDocuments={otherDocuments}
        setPresentingDocument={setPresentingDocument}
      />
    </div>
  );
});

// TODO: Consider more robust comparisons:
// - `chatState.docs`, `chatState.citations`, and `otherMessagesCanSwitchTo` use
//   reference equality. Shallow array/object comparison would be more robust if
//   these are recreated with the same values.
function arePropsEqual(
  prev: AgentMessageProps,
  next: AgentMessageProps
): boolean {
  return (
    prev.nodeId === next.nodeId &&
    prev.messageId === next.messageId &&
    prev.currentFeedback === next.currentFeedback &&
    // Compare packetCount (primitive) instead of rawPackets.length
    // The array is mutated in place, so reading .length from prev and next would return same value
    prev.packetCount === next.packetCount &&
    prev.chatState.assistant?.id === next.chatState.assistant?.id &&
    prev.chatState.docs === next.chatState.docs &&
    prev.chatState.citations === next.chatState.citations &&
    prev.chatState.overriddenModel === next.chatState.overriddenModel &&
    prev.chatState.researchType === next.chatState.researchType &&
    prev.otherMessagesCanSwitchTo === next.otherMessagesCanSwitchTo &&
    prev.onRegenerate === next.onRegenerate &&
    prev.parentMessage?.messageId === next.parentMessage?.messageId &&
    prev.llmManager?.isLoadingProviders ===
      next.llmManager?.isLoadingProviders &&
    prev.processingDurationSeconds === next.processingDurationSeconds
    // Skip: chatState.regenerate, chatState.setPresentingDocument,
    //       most of llmManager, onMessageSelection (function/object props)
  );
}

const AgentMessage = React.memo(function AgentMessage({
  rawPackets,
  chatState,
  nodeId,
  messageId,
  currentFeedback,
  llmManager,
  otherMessagesCanSwitchTo,
  onMessageSelection,
  onRegenerate,
  parentMessage,
  processingDurationSeconds,
}: AgentMessageProps) {
  const markdownRef = useRef<HTMLDivElement>(null);
  const finalAnswerRef = useRef<HTMLDivElement>(null);

  // Process streaming packets: returns data and callbacks
  // Hook handles all state internally, exposes clean API
  const {
    citations,
    citationMap,
    documentMap,
    toolGroups,
    toolTurnGroups,
    displayGroups,
    hasSteps,
    stopPacketSeen,
    stopReason,
    isGeneratingImage,
    generatedImageCount,
    isComplete,
    onRenderComplete,
    finalAnswerComing,
    toolProcessingDuration,
  } = usePacketProcessor(rawPackets, nodeId);

  // Apply pacing delays between different tool types for smoother visual transitions
  const { pacedTurnGroups, pacedDisplayGroups, pacedFinalAnswerComing } =
    usePacedTurnGroups(
      toolTurnGroups,
      displayGroups,
      stopPacketSeen,
      nodeId,
      finalAnswerComing
    );

  // Memoize merged citations separately to avoid creating new object when neither source changed
  const mergedCitations = useMemo(
    () => ({
      ...chatState.citations,
      ...citationMap,
    }),
    [chatState.citations, citationMap]
  );

  // Create a chatState that uses streaming citations for immediate rendering
  // This merges the prop citations with streaming citations, preferring streaming ones
  // Memoized with granular dependencies to prevent cascading re-renders
  // Note: chatState object is recreated upstream on every render, so we depend on
  // individual fields instead of the whole object for proper memoization
  const effectiveChatState = useMemo<FullChatState>(
    () => ({
      ...chatState,
      citations: mergedCitations,
    }),
    [
      chatState.assistant,
      chatState.docs,
      chatState.setPresentingDocument,
      chatState.overriddenModel,
      chatState.researchType,
      mergedCitations,
    ]
  );

  // Message switching logic
  const {
    currentMessageInd,
    includeMessageSwitcher,
    getPreviousMessage,
    getNextMessage,
  } = useMessageSwitching({
    nodeId,
    otherMessagesCanSwitchTo,
    onMessageSelection,
  });

  return (
    <div
      className="pb-6 md:pt-6 flex flex-col gap-3 pr-1"
      data-testid={isComplete ? "onyx-ai-message" : undefined}
    >
      {/* Row 1: Two-column layout for tool steps */}

      <AgentTimeline
        turnGroups={pacedTurnGroups}
        chatState={effectiveChatState}
        stopPacketSeen={stopPacketSeen}
        stopReason={stopReason}
        hasDisplayContent={pacedDisplayGroups.length > 0}
        processingDurationSeconds={processingDurationSeconds}
        isGeneratingImage={isGeneratingImage}
        generatedImageCount={generatedImageCount}
        finalAnswerComing={pacedFinalAnswerComing}
        toolProcessingDuration={toolProcessingDuration}
      />

      {/* Row 2: Display content + MessageToolbar */}
      <div
        ref={markdownRef}
        className="overflow-x-visible focus:outline-none select-text cursor-text px-3"
        onCopy={(e) => {
          if (markdownRef.current) {
            handleCopy(e, markdownRef as RefObject<HTMLDivElement>);
          }
        }}
      >
        {pacedDisplayGroups.length > 0 && (
          <div ref={finalAnswerRef}>
            {pacedDisplayGroups.map((displayGroup, index) => (
              <RendererComponent
                key={`${displayGroup.turn_index}-${displayGroup.tab_index}`}
                packets={displayGroup.packets}
                chatState={effectiveChatState}
                onComplete={() => {
                  // Only mark complete on the last display group
                  // Hook handles the finalAnswerComing check internally
                  if (index === pacedDisplayGroups.length - 1) {
                    onRenderComplete();
                  }
                }}
                animate={false}
                stopPacketSeen={stopPacketSeen}
                stopReason={stopReason}
              >
                {(results) => (
                  <>
                    {results.map((r, i) => (
                      <div key={i}>{r.content}</div>
                    ))}
                  </>
                )}
              </RendererComponent>
            ))}
          </div>
        )}
        {/* Show stopped message when user cancelled and no display content */}
        {pacedDisplayGroups.length === 0 &&
          stopReason === StopReason.USER_CANCELLED && (
            <Text as="p" secondaryBody text04>
              User has stopped generation
            </Text>
          )}
      </div>

      {/* References — between content and action buttons */}
      {isComplete && (citations.length > 0 || documentMap.size > 0) && (
        <ReferencesStrip
          citations={citations}
          documentMap={documentMap}
          allDocs={chatState.docs ?? []}
          setPresentingDocument={
            (chatState.setPresentingDocument ?? (() => {})) as Dispatch<SetStateAction<MinimalOnyxDocument | null>>
          }
        />
      )}

      {/* Action buttons — only show when streaming and rendering complete */}
      {isComplete && (
        <MessageToolbar
          nodeId={nodeId}
          messageId={messageId}
          includeMessageSwitcher={includeMessageSwitcher}
          currentMessageInd={currentMessageInd}
          otherMessagesCanSwitchTo={otherMessagesCanSwitchTo}
          getPreviousMessage={getPreviousMessage}
          getNextMessage={getNextMessage}
          onMessageSelection={onMessageSelection}
          rawPackets={rawPackets}
          finalAnswerRef={finalAnswerRef}
          currentFeedback={currentFeedback}
          onRegenerate={onRegenerate}
          parentMessage={parentMessage}
          llmManager={llmManager}
          currentModelName={chatState.overriddenModel}
        />
      )}
    </div>
  );
}, arePropsEqual);

export default AgentMessage;
