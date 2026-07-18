"use client";

import React, { useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import type { Route } from "next";
import ChatUI from "@/sections/chat/ChatUI";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { LlmManager } from "@/lib/hooks";
import { MinimalAgentSnapshot } from "@/app/admin/assistants/interfaces";
import { MinimalOnyxDocument } from "@/lib/search/interfaces";
import { useChatSessionStore } from "@/app/app/stores/useChatSessionStore";
import {
  useCompareStore,
  CompareModel,
} from "@/app/app/stores/useCompareStore";
import { ScrollContainerProvider } from "@/components/chat/ScrollContainerContext";
import { getProviderIcon } from "@/app/admin/configuration/llm/utils";
import LLMPopover from "@/refresh-components/popovers/LLMPopover";
import { SvgPlus } from "@opal/icons";

interface CompareViewProps {
  liveAssistant: MinimalAgentSnapshot;
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
  model: CompareModel;
  sessionId: string | undefined;
  liveAssistant: MinimalAgentSnapshot;
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

  const ProviderIcon = getProviderIcon(model.provider, model.modelName);

  return (
    <div className="flex flex-col min-w-0 min-h-0 border border-line-01 rounded-12 bg-background-tint-00 overflow-hidden transition-shadow hover:shadow-[0_2px_20px_var(--virtualai-accent-glow)]">
      <div
        className="flex items-center justify-between gap-2 px-3 py-2.5 border-b border-line-01 flex-shrink-0"
        style={{
          backgroundColor:
            "var(--virtualai-accent-subtle, var(--background-tint-01))",
        }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className="size-7 rounded-08 virtualai-accent-icon-badge flex items-center justify-center shrink-0">
            <ProviderIcon size={15} />
          </div>
          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-1.5 min-w-0">
              <Text mainContentEmphasis className="truncate">
                {model.displayName || model.modelName}
              </Text>
              {(model.supportsReasoning || model.supportsImageInput) && (
                <span className="flex items-center gap-1 shrink-0">
                  {model.supportsReasoning && (
                    <span className="virtualai-capability-pill virtualai-capability-pill--reasoning">
                      Reasoning
                    </span>
                  )}
                  {model.supportsImageInput && (
                    <span className="virtualai-capability-pill virtualai-capability-pill--vision">
                      Vision
                    </span>
                  )}
                </span>
              )}
            </div>
            <Text secondaryBody text03 className="text-xs truncate">
              {model.providerDisplayName || model.provider}
            </Text>
          </div>
        </div>
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
    <div className="h-full w-full flex flex-col min-h-0 px-3 pt-2 gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-shrink-0">
        <div className="flex flex-col min-w-0">
          <Text as="p" headingH2 className="virtualai-gradient-text">
            Side-by-side comparison
          </Text>
          <Text secondaryBody text03>
            Same prompt, {compareModels.length} models. Pick a winner or merge
            the best parts.
          </Text>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span
            className="text-xs font-medium px-2 py-1 rounded-full whitespace-nowrap"
            style={{
              backgroundColor:
                "var(--virtualai-accent-subtle, color-mix(in srgb, var(--theme-primary-05) 12%, transparent))",
              color: "var(--virtualai-accent, var(--theme-primary-05))",
            }}
          >
            {compareModels.length} models · comparing
          </span>
          <Text secondaryBody text03 className="text-xs whitespace-nowrap">
            Temperature {(llmManager.temperature ?? 0).toFixed(1)}
          </Text>
          <LLMPopover
            llmManager={llmManager}
            folded
            foldedIcon={SvgPlus}
            foldedTooltip="Add model to compare"
          />
        </div>
      </div>

      {/* Panels */}
      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 overflow-hidden">
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
    </div>
  );
}
