"use client";

import { useCallback } from "react";
import { FilterManager, LlmDescriptor, LlmManager } from "@/lib/hooks";
import { MinimalPersonaSnapshot } from "@/app/admin/assistants/interfaces";
import { OmDocument } from "@/lib/search/interfaces";
import {
  createChatSession,
  updateLlmOverrideForChatSession,
} from "@/app/app/services/lib";
import { structureValue } from "@/lib/llm/utils";
import {
  buildImmediateMessages,
  getLatestMessageChain,
  getLastSuccessfulMessageId,
  upsertMessages,
  SYSTEM_NODE_ID,
} from "@/app/app/services/messageTree";
import {
  CurrentMessageFIFO,
  updateCurrentMessageFIFO,
} from "@/app/app/services/currentMessageFIFO";
import { buildFilters } from "@/lib/search/utils";
import { projectFilesToFileDescriptors } from "@/app/app/services/fileUtils";
import { ProjectFile } from "@/providers/ProjectsContext";
import {
  BackendMessage,
  ChatFileType,
  CitationMap,
  FileChatDisplay,
  FileDescriptor,
  Message,
  MessageResponseIDInfo,
  StreamingError,
  UserKnowledgeFilePacket,
} from "@/app/app/interfaces";
import { Packet, MessageStart } from "@/app/app/services/streamingModels";
import { useChatSessionStore } from "@/app/app/stores/useChatSessionStore";
import { useCompareStore } from "@/app/app/stores/useCompareStore";

const SYSTEM_MESSAGE_ID = -3;

interface UseCompareControllerProps {
  filterManager: FilterManager;
  llmManager: LlmManager;
  liveAssistant: MinimalPersonaSnapshot | undefined;
  selectedDocuments: OmDocument[];
  resetInputBar: () => void;
}

interface CompareSubmitProps {
  message: string;
  currentMessageFiles: ProjectFile[];
  deepResearch: boolean;
}

/**
 * Fans one prompt out to N models in parallel — one real chat session per
 * model, streamed independently into its own panel (no blocking between
 * panels at the network OR the React layer; see MULTI_MODEL_COMPARE_PLAN.md).
 *
 * Deliberately self-contained (does NOT touch `useChatController.onSubmit`) so
 * the single-chat path cannot regress. It reuses the same lower-level
 * primitives (FIFO stream, message-tree builders, session-keyed store actions)
 * as the single path, with a lean drain loop (no regeneration / error-message
 * cleanup / auto-naming — those belong to single chat only).
 */
export function useCompareController({
  filterManager,
  llmManager,
  liveAssistant,
  selectedDocuments,
  resetInputBar,
}: UseCompareControllerProps) {
  const submitCompare = useCallback(
    async ({ message, currentMessageFiles, deepResearch }: CompareSubmitProps) => {
      const { compareModels, panelSessionIds, setPanelSessionId } =
        useCompareStore.getState();
      if (compareModels.length === 0) return;

      // Clear the composer once, up front (not per-panel).
      resetInputBar();

      // Fire every model concurrently. Each task owns its own session id, FIFO,
      // abort controller, and store slice → fully independent streams.
      await Promise.all(
        compareModels.map((model, index) =>
          streamOnePanel({
            model,
            index,
            existingSessionId: panelSessionIds[index],
            message,
            files: currentMessageFiles,
            deepResearch,
            filterManager,
            llmManager,
            liveAssistant,
            selectedDocuments,
            setPanelSessionId,
          })
        )
      );
    },
    [filterManager, llmManager, liveAssistant, selectedDocuments, resetInputBar]
  );

  return { submitCompare };
}

interface StreamOnePanelArgs {
  model: LlmDescriptor;
  index: number;
  existingSessionId: string | undefined;
  message: string;
  files: ProjectFile[];
  deepResearch: boolean;
  filterManager: FilterManager;
  llmManager: LlmManager;
  liveAssistant: MinimalPersonaSnapshot | undefined;
  selectedDocuments: OmDocument[];
  setPanelSessionId: (index: number, sessionId: string) => void;
}

async function streamOnePanel({
  model,
  index,
  existingSessionId,
  message,
  files: projectFiles,
  deepResearch,
  filterManager,
  llmManager,
  liveAssistant,
  selectedDocuments,
  setPanelSessionId,
}: StreamOnePanelArgs): Promise<void> {
  const store = useChatSessionStore.getState();

  // 1. Ensure this panel has a session (created lazily on first turn).
  let sessionId = existingSessionId;
  if (!sessionId) {
    sessionId = await createChatSession(
      liveAssistant?.id || 0,
      null,
      null
    );
    store.createSession(sessionId);
    setPanelSessionId(index, sessionId);
    // Persist the panel's model on its session (background; not awaited).
    updateLlmOverrideForChatSession(
      sessionId,
      structureValue(
        model.name || "",
        model.provider || "",
        model.modelName || ""
      )
    );
  }

  const fileDescriptors = projectFilesToFileDescriptors(projectFiles);

  // 2. Compute parent + insert the user + (empty) assistant nodes immediately.
  const startTree =
    store.sessions.get(sessionId)?.messageTree || new Map<number, Message>();
  const history = getLatestMessageChain(startTree);
  const parentMessage = history.length > 0 ? history[history.length - 1] : null;
  const parentNodeId = parentMessage?.nodeId ?? SYSTEM_NODE_ID;

  const { initialUserNode, initialAssistantNode } = buildImmediateMessages(
    parentNodeId,
    message,
    fileDescriptors,
    undefined
  );

  let localTree = upsertMessages(
    startTree,
    [initialUserNode, initialAssistantNode],
    false
  );
  store.updateSessionMessageTree(sessionId, localTree);
  store.updateChatState(sessionId, "loading");

  // 3. Own abort controller for this panel.
  const controller = new AbortController();
  store.setAbortController(sessionId, controller);

  // Accumulators (mirror the single-chat drain loop).
  let answer = "";
  let documents: OmDocument[] = selectedDocuments;
  let citations: CitationMap | null = null;
  let aiMessageImages: FileDescriptor[] | null = null;
  let error: string | null = null;
  let stackTrace: string | null = null;
  let finalMessage: BackendMessage | null = null;
  let files: FileDescriptor[] = fileDescriptors;
  let packets: Packet[] = [];
  let newUserMessageId: number | null = null;
  let newAssistantMessageId: number | null = null;

  const writeTree = () => {
    localTree = upsertMessages(
      localTree,
      [
        { ...initialUserNode, messageId: newUserMessageId ?? undefined, files },
        {
          ...initialAssistantNode,
          messageId: newAssistantMessageId ?? undefined,
          message: error || answer,
          type: error ? "error" : "assistant",
          documents,
          citations: finalMessage?.citations || citations || {},
          files: finalMessage?.files || aiMessageImages || [],
          toolCall: finalMessage?.tool_call || null,
          stackTrace,
          overridden_model: finalMessage?.overridden_model,
          packets,
          packetCount: packets.length,
        },
      ],
      false
    );
    useChatSessionStore.getState().updateSessionMessageTree(sessionId!, localTree);
  };

  try {
    const lastSuccessfulMessageId = getLastSuccessfulMessageId(localTree);
    const stack = new CurrentMessageFIFO();
    updateCurrentMessageFIFO(stack, {
      signal: controller.signal,
      message,
      fileDescriptors,
      parentMessageId:
        lastSuccessfulMessageId === SYSTEM_MESSAGE_ID
          ? null
          : lastSuccessfulMessageId,
      chatSessionId: sessionId,
      filters: buildFilters(
        filterManager.selectedSources,
        filterManager.selectedDocumentSets,
        filterManager.timeRange,
        filterManager.selectedTags
      ),
      modelProvider: model.name || undefined,
      modelVersion: model.modelName || undefined,
      temperature: llmManager.temperature || undefined,
      deepResearch,
      enabledToolIds: undefined,
      forcedToolId: null,
      origin: "webapp",
    });

    const delay = (ms: number) =>
      new Promise((resolve) => setTimeout(resolve, ms));

    await delay(50);
    while (!stack.isComplete || !stack.isEmpty()) {
      if (stack.isEmpty()) {
        await delay(0.5);
      }
      if (stack.isEmpty() || controller.signal.aborted) continue;

      const packet = stack.nextPacket();
      if (!packet) continue;

      store.updateChatState(sessionId, "streaming");

      if ((packet as MessageResponseIDInfo).user_message_id) {
        newUserMessageId = (packet as MessageResponseIDInfo).user_message_id;
      }
      if ((packet as MessageResponseIDInfo).reserved_assistant_message_id) {
        newAssistantMessageId = (packet as MessageResponseIDInfo)
          .reserved_assistant_message_id;
      }

      if (Object.hasOwn(packet, "user_files")) {
        const userFiles = (packet as UserKnowledgeFilePacket).user_files;
        files = files.concat(
          userFiles.filter((nf) => !files.some((ef) => ef.id === nf.id))
        );
      }

      if (Object.hasOwn(packet, "file_ids")) {
        aiMessageImages = (packet as FileChatDisplay).file_ids.map((id) => ({
          id,
          type: ChatFileType.IMAGE,
        }));
      } else if (Object.hasOwn(packet, "error") && (packet as any).error != null) {
        const streamingError = packet as StreamingError;
        error = streamingError.error;
        stackTrace = streamingError.stack_trace || null;
        useChatSessionStore.getState().setUncaughtError(sessionId, error);
        useChatSessionStore.getState().updateChatState(sessionId, "input");
        throw new Error(streamingError.error);
      } else if (Object.hasOwn(packet, "message_id")) {
        finalMessage = packet as BackendMessage;
      } else if (Object.hasOwn(packet, "obj")) {
        packets.push(packet as Packet);
        const packetObj = (packet as Packet).obj;
        if (packetObj.type === "citation_info") {
          const ci = packetObj as {
            citation_number: number;
            document_id: string;
          };
          citations = { ...(citations || {}), [ci.citation_number]: ci.document_id };
        } else if (packetObj.type === "message_start") {
          const ms = packetObj as MessageStart;
          if (ms.final_documents) documents = ms.final_documents;
        }
      }

      writeTree();
    }
  } catch (e: any) {
    error = error || e?.message || String(e);
    writeTree();
  }

  const finalStore = useChatSessionStore.getState();
  finalStore.setStreamingStartTime(sessionId, null);
  finalStore.updateChatState(sessionId, "input");
}
