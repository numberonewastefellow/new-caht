"use client";

import { ChatSession } from "@/app/app/interfaces";
import { deleteChatSession } from "@/app/app/services/lib";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import {
  moveChatSession as moveChatSessionService,
  removeChatSessionFromWorkspace as removeChatSessionFromWorkspaceService,
} from "@/app/app/workspaces/workspacesService";
import Popover, { PopoverMenu } from "@/refresh-components/Popover";
import { FiMoreHorizontal } from "react-icons/fi";
import useChatSessions from "@/hooks/useChatSessions";
import { useCallback, useState, useMemo } from "react";
import MoveCustomAgentChatModal from "@/components/modals/MoveCustomAgentChatModal";
// PopoverMenu already imported above
import { cn, noProp } from "@/lib/utils";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import Button from "@/refresh-components/buttons/Button";
import { PopoverSearchInput } from "@/sections/sidebar/ChatButton";
import LineItem from "@/refresh-components/buttons/LineItem";
import { SvgFolder, SvgFolderIn, SvgShare, SvgTrash } from "@opal/icons";
// Constants
const DEFAULT_PERSONA_ID = 0;
const LS_HIDE_MOVE_CUSTOM_AGENT_MODAL_KEY = "onyx:hideMoveCustomAgentModal";

interface ChatSessionMorePopupProps {
  chatSession: ChatSession;
  workspaceId?: number;
  isRenamingChat: boolean;
  setIsRenamingChat: (value: boolean) => void;
  showShareModal?: (chatSession: ChatSession) => void;
  afterDelete?: () => void;
  afterMove?: () => void;
  afterRemoveFromWorkspace?: () => void;
  search?: boolean;
  iconSize?: number;
  isVisible?: boolean;
}

export function ChatSessionMorePopup({
  chatSession,
  workspaceId,
  isRenamingChat: _isRenamingChat,
  setIsRenamingChat: _setIsRenamingChat,
  showShareModal,
  afterDelete,
  afterMove,
  afterRemoveFromWorkspace,
  search,
  iconSize = 16,
  isVisible = false,
}: ChatSessionMorePopupProps) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const { refreshChatSessions } = useChatSessions();
  const { fetchWorkspaces, workspaces } = useWorkspacesContext();

  const [pendingMoveWorkspaceId, setPendingMoveWorkspaceId] = useState<
    number | null
  >(null);
  const [showMoveCustomAgentModal, setShowMoveCustomAgentModal] =
    useState(false);

  const isChatUsingDefaultAssistant =
    chatSession.persona_id === DEFAULT_PERSONA_ID;

  const [showMoveOptions, setShowMoveOptions] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const filteredWorkspaces = workspaces.filter((workspace) =>
    workspace.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handlePopoverOpenChange = useCallback((open: boolean) => {
    setPopoverOpen(open);
  }, []);

  const handleConfirmDelete = useCallback(
    async (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      await deleteChatSession(chatSession.id);
      await refreshChatSessions();
      await fetchWorkspaces();
      setIsDeleteModalOpen(false);
      setPopoverOpen(false);
      afterDelete?.();
    },
    [chatSession, refreshChatSessions, fetchWorkspaces, afterDelete]
  );

  const performMove = useCallback(
    async (targetWorkspaceId: number) => {
      await moveChatSessionService(targetWorkspaceId, chatSession.id);
      await fetchWorkspaces();
      await refreshChatSessions();
      setPopoverOpen(false);
      afterMove?.();
    },
    [chatSession.id, fetchWorkspaces, refreshChatSessions, afterMove]
  );

  const handleMoveChatSession = useCallback(
    async (item: { id: number; label: string }) => {
      const targetWorkspaceId = item.id;
      const hideModal =
        typeof window !== "undefined" &&
        window.localStorage.getItem(LS_HIDE_MOVE_CUSTOM_AGENT_MODAL_KEY) ===
          "true";

      if (!isChatUsingDefaultAssistant && !hideModal) {
        setPendingMoveWorkspaceId(targetWorkspaceId);
        setShowMoveCustomAgentModal(true);
        return;
      }

      await performMove(targetWorkspaceId);
    },
    [isChatUsingDefaultAssistant, performMove]
  );

  const handleRemoveChatSessionFromWorkspace = useCallback(async () => {
    await removeChatSessionFromWorkspaceService(chatSession.id);
    await fetchWorkspaces();
    await refreshChatSessions();
    afterRemoveFromWorkspace?.();
    setPopoverOpen(false);
  }, [
    chatSession.id,
    fetchWorkspaces,
    refreshChatSessions,
    removeChatSessionFromWorkspaceService,
    afterRemoveFromWorkspace,
  ]);

  // Build popover items similar to AppSidebar (no rename here)
  const popoverItems = useMemo(() => {
    if (!showMoveOptions) {
      return [
        showShareModal && (
          <LineItem
            key="share"
            icon={SvgShare}
            onClick={noProp(() => showShareModal(chatSession))}
          >
            Share
          </LineItem>
        ),
        <LineItem
          key="move"
          icon={SvgFolderIn}
          onClick={noProp(() => setShowMoveOptions(true))}
        >
          Move to Workspace
        </LineItem>,
        workspaceId && (
          <LineItem
            key="remove"
            icon={SvgFolder}
            onClick={noProp(() => handleRemoveChatSessionFromWorkspace())}
          >
            {`Remove from ${
              workspaces.find((p) => p.id === workspaceId)?.name ?? "Workspace"
            }`}
          </LineItem>
        ),
        null,
        <LineItem
          key="delete"
          icon={SvgTrash}
          onClick={noProp(() => setIsDeleteModalOpen(true))}
          danger
        >
          Delete
        </LineItem>,
      ];
    }
    return [
      <PopoverSearchInput
        key="search"
        setShowMoveOptions={setShowMoveOptions}
        onSearch={setSearchTerm}
      />,
      ...filteredWorkspaces
        .filter((candidate) => candidate.id !== workspaceId)
        .map((target) => (
          <LineItem
            key={target.id}
            icon={SvgFolder}
            onClick={noProp(() =>
              handleMoveChatSession({ id: target.id, label: target.name })
            )}
          >
            {target.name}
          </LineItem>
        )),
    ];
  }, [
    showMoveOptions,
    showShareModal,
    workspaces,
    workspaceId,
    filteredWorkspaces,
    chatSession,
    setShowMoveOptions,
    setSearchTerm,
    handleMoveChatSession,
    handleRemoveChatSessionFromWorkspace,
  ]);

  return (
    <div>
      <div className="-my-1">
        <Popover open={popoverOpen} onOpenChange={handlePopoverOpenChange}>
          <Popover.Trigger
            asChild
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              handlePopoverOpenChange(!popoverOpen);
            }}
          >
            <div
              className={cn(
                "p-1 rounded cursor-pointer select-none transition-opacity duration-150",
                isVisible || popoverOpen
                  ? "opacity-100 pointer-events-auto"
                  : "opacity-0 pointer-events-none"
              )}
            >
              <FiMoreHorizontal size={iconSize} />
            </div>
          </Popover.Trigger>
          <Popover.Content
            align="end"
            side="right"
            avoidCollisions
            sideOffset={8}
          >
            <PopoverMenu>{popoverItems}</PopoverMenu>
          </Popover.Content>
        </Popover>
      </div>
      {isDeleteModalOpen && (
        <ConfirmationModalLayout
          title="Delete Chat"
          icon={SvgTrash}
          onClose={() => setIsDeleteModalOpen(false)}
          submit={
            <Button danger onClick={handleConfirmDelete}>
              Delete
            </Button>
          }
        >
          Are you sure you want to delete this chat? This action cannot be
          undone.
        </ConfirmationModalLayout>
      )}

      {showMoveCustomAgentModal && (
        <MoveCustomAgentChatModal
          onCancel={() => {
            setShowMoveCustomAgentModal(false);
            setPendingMoveWorkspaceId(null);
          }}
          onConfirm={async (doNotShowAgain: boolean) => {
            if (doNotShowAgain && typeof window !== "undefined") {
              window.localStorage.setItem(
                LS_HIDE_MOVE_CUSTOM_AGENT_MODAL_KEY,
                "true"
              );
            }
            const target = pendingMoveWorkspaceId;
            setShowMoveCustomAgentModal(false);
            setPendingMoveWorkspaceId(null);
            if (target != null) {
              await performMove(target);
            }
          }}
        />
      )}
    </div>
  );
}
