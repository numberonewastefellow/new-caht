"use client";

import React, { useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import ChatUI from "@/sections/chat/ChatUI";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { LlmDescriptor, LlmManager } from "@/lib/hooks";
import { MinimalPersonaSnapshot } from "@/app/admin/assistants/interfaces";
import { MinimalOnyxDocument } from "@/lib/search/interfaces";
import { useChatSessionStore } from "@/app/app/stores/useChatSessionStore";
import { useCompareStore } from "@/app/app/stores/useCompareStore";
import { ScrollContainerProvider } from "@/components/chat/ScrollContainerContext";

interface CompareViewProps {
  liveAssistant: MinimalPersonaSnapshot;
  llmManager: LlmManager;
  setPresentingDocument: (doc: MinimalOnyxDocument | null) => void;
  onMessageSelection: (nodeId: number) => void;
  deepResearchEnabled: boolean;
  currentMessageFiles: any[];
}

/**
 * Side-by-side compare layout: one session-scoped <ChatUI> per selected model
 * (up to 3, responsive columns). Each panel subscribes only to its own
 * session's store slice, so a streamed packet in one panel re-renders only
 * that panel. "Use this" collapses to that model's session and continues as a
 * normal single chat. See MULTI_MODEL_COMPARE_PLAN.md.
 */
interface ComparePanelProps {
  model: LlmDescriptor;
  sessionId: string | undefined;
  liveAssistant: MinimalPersonaSnapshot;
  llmManager: LlmManager;
  setPresentingDocument: (doc: MinimalOnyxDocument | null) => void;
  onMessageSelection: (nodeId: number) => void;
  deepResearchEnabled: boolean;
  currentMessageFiles: any[];
  onPick: (sessionId: string) => void;
  onStop: (sessionId: string) => void;
}

// One column. Holds its own scroll-container refs so <ChatUI>'s
// DynamicBottomSpacer (which calls useScrollContainer) has a provider.
function ComparePanel({
  model,
  sessionId,
  liveAssistant,
  llmManager,
  setPresentingDocument,
  onMessageSelection,
  deepResearchEnabled,
  currentMessageFiles,
  onPick,
  onStop,
}: ComparePanelProps) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const contentWrapperRef = useRef<HTMLDivElement | null>(null);
  const spacerHeightRef = useRef(0);

  const noopSubmit = useCallback(async () => {}, []);
  const noopResubmit = useCallback(() => {}, []);

  return (
    <div className="flex flex-col min-w-0 min-h-0 border border-line-01 rounded-12 bg-background-tint-00 overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-line-01 bg-background-tint-01 flex-shrink-0">
        <Text mainContentEmphasis className="truncate">
          {model.modelName || model.name}
        </Text>
        {sessionId && (
          <Button secondary onClick={() => onPick(sessionId)}>
            Use this
          </Button>
        )}
      </div>
      <div
        ref={scrollContainerRef}
        className="flex-1 min-h-0 overflow-y-auto"
      >
        <div ref={contentWrapperRef} className="flex flex-col items-center">
          {sessionId ? (
            <ScrollContainerProvider
              scrollContainerRef={scrollContainerRef}
              contentWrapperRef={contentWrapperRef}
              spacerHeightRef={spacerHeightRef}
            >
              <ChatUI
                chatSessionId={sessionId}
                overriddenModelName={model.modelName}
                liveAssistant={liveAssistant}
                llmManager={llmManager}
                setPresentingDocument={setPresentingDocument}
                onMessageSelection={onMessageSelection}
                stopGenerating={() => onStop(sessionId)}
                onSubmit={noopSubmit}
                deepResearchEnabled={deepResearchEnabled}
                currentMessageFiles={currentMessageFiles}
                onResubmit={noopResubmit}
              />
            </ScrollContainerProvider>
          ) : (
            <div className="p-4 w-full">
              <Text secondaryBody text03>
                Waiting…
              </Text>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function CompareView({
  liveAssistant,
  llmManager,
  setPresentingDocument,
  onMessageSelection,
  deepResearchEnabled,
  currentMessageFiles,
}: CompareViewProps) {
  const router = useRouter();
  const compareModels = useCompareStore((s) => s.compareModels);
  const panelSessionIds = useCompareStore((s) => s.panelSessionIds);
  const reset = useCompareStore((s) => s.reset);
  const setCurrentSession = useChatSessionStore((s) => s.setCurrentSession);
  const abortSession = useChatSessionStore((s) => s.abortSession);

  const handlePick = useCallback(
    (sessionId: string) => {
      setCurrentSession(sessionId);
      reset();
      router.push(`/app?chatId=${sessionId}` as Route);
    },
    [router, setCurrentSession, reset]
  );

  return (
    <div className="h-full w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 px-3 overflow-hidden">
      {compareModels.map((model, i) => (
        <ComparePanel
          key={`${model.provider}-${model.modelName}-${i}`}
          model={model}
          sessionId={panelSessionIds[i]}
          liveAssistant={liveAssistant}
          llmManager={llmManager}
          setPresentingDocument={setPresentingDocument}
          onMessageSelection={onMessageSelection}
          deepResearchEnabled={deepResearchEnabled}
          currentMessageFiles={currentMessageFiles}
          onPick={handlePick}
          onStop={abortSession}
        />
      ))}
    </div>
  );
}
