import { ChatSession } from "@/app/app/interfaces";
import { LOCAL_STORAGE_KEYS, DEFAULT_PERSONA_ID } from "./constants";
import { moveChatSession } from "@/app/app/workspaces/workspacesService";
import { toast } from "@/hooks/useToast";

export const shouldShowMoveModal = (chatSession: ChatSession): boolean => {
  const hideModal =
    typeof window !== "undefined" &&
    window.localStorage.getItem(
      LOCAL_STORAGE_KEYS.HIDE_MOVE_CUSTOM_AGENT_MODAL
    ) === "true";

  return !hideModal && chatSession.persona_id !== DEFAULT_PERSONA_ID;
};

export const showErrorNotification = (message: string) => {
  toast.error(message);
};

export interface MoveOperationParams {
  chatSession: ChatSession;
  targetWorkspaceId: number;
  refreshChatSessions: () => Promise<any>;
  refreshCurrentWorkspaceDetails: () => Promise<any>;
  fetchWorkspaces: () => Promise<any>;
  currentWorkspaceId: number | null;
}

export const handleMoveOperation = async ({
  chatSession,
  targetWorkspaceId,
  refreshChatSessions,
  refreshCurrentWorkspaceDetails,
  fetchWorkspaces,
  currentWorkspaceId,
}: MoveOperationParams) => {
  try {
    await moveChatSession(targetWorkspaceId, chatSession.id);
    const workspaceRefreshPromise = currentWorkspaceId
      ? refreshCurrentWorkspaceDetails()
      : fetchWorkspaces();
    await Promise.all([refreshChatSessions(), workspaceRefreshPromise]);
  } catch (error) {
    console.error("Failed to perform move operation:", error);
    toast.error("Failed to move chat. Please try again.");
    throw error;
  }
};
