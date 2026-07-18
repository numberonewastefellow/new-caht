"use client";

import React, { useState, memo, useMemo, useEffect } from "react";
import { useDraggable } from "@dnd-kit/core";
import useChatSessions from "@/hooks/useChatSessions";
import { deleteChatSession, renameChatSession } from "@/app/app/services/lib";
import { ChatSession } from "@/app/app/interfaces";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import Button from "@/refresh-components/buttons/Button";
import { cn, noProp } from "@/lib/utils";
import Popover, { PopoverMenu } from "@/refresh-components/Popover";
import { useAppRouter } from "@/hooks/appNavigation";
import {
  Workspace,
  removeChatSessionFromWorkspace,
  createWorkspace as createWorkspaceService,
} from "@/app/app/workspaces/workspacesService";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import MoveCustomAgentChatModal from "@/components/modals/MoveCustomAgentChatModal";
import { UNNAMED_CHAT } from "@/lib/constants";
import ShareChatSessionModal from "@/sections/modals/ShareChatSessionModal";
import SidebarTab from "@/refresh-components/buttons/SidebarTab";
import IconButton from "@/refresh-components/buttons/IconButton";
import { Button as OpalButton } from "@opal/components";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import { DRAG_TYPES, LOCAL_STORAGE_KEYS } from "@/sections/sidebar/constants";
import {
  shouldShowMoveModal,
  showErrorNotification,
  handleMoveOperation,
} from "@/sections/sidebar/sidebarUtils";
import ButtonRenaming from "@/refresh-components/buttons/ButtonRenaming";
import useAppFocus from "@/hooks/useAppFocus";
import LineItem from "@/refresh-components/buttons/LineItem";
import {
  SvgChevronLeft,
  SvgEdit,
  SvgFolder,
  SvgFolderIn,
  SvgFolderPlus,
  SvgMoreHorizontal,
  SvgShare,
  SvgTrash,
} from "@opal/icons";
import useOnMount from "@/hooks/useOnMount";
import { useAgents, usePinnedAgents } from "@/hooks/useAgents";

export interface PopoverSearchInputProps {
  setShowMoveOptions: (show: boolean) => void;
  onSearch: (term: string) => void;
}

export function PopoverSearchInput({
  setShowMoveOptions,
  onSearch,
}: PopoverSearchInputProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchTerm(value);
    onSearch(value);
  };
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setShowMoveOptions(false);
    }
  };

  const handleClickBackButton = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    setShowMoveOptions(false);
    setSearchTerm("");
  };

  return (
    <div className="flex flex-row items-center">
      <OpalButton
        icon={SvgChevronLeft}
        onClick={handleClickBackButton}
        prominence="tertiary"
        size="sm"
      />
      <InputTypeIn
        type="text"
        value={searchTerm}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Search Workspaces"
        onClick={noProp()}
        variant="internal"
        autoFocus
      />
    </div>
  );
}

export interface ChatButtonProps {
  chatSession: ChatSession;
  workspace?: Workspace;
  draggable?: boolean;
}

const ChatButton = memo(
  ({ chatSession, workspace, draggable = false }: ChatButtonProps) => {
    const route = useAppRouter();
    const activeSidebarTab = useAppFocus();
    const active = useMemo(
      () =>
        activeSidebarTab.isChat() &&
        activeSidebarTab.getId() === chatSession.id,
      [activeSidebarTab, chatSession.id]
    );
    const mounted = useOnMount();
    const [displayName, setDisplayName] = useState(
      chatSession.name || UNNAMED_CHAT
    );
    const [renaming, setRenaming] = useState(false);
    const [deleteConfirmationModalOpen, setDeleteConfirmationModalOpen] =
      useState(false);
    const [showMoveOptions, setShowMoveOptions] = useState(false);
    const [showShareModal, setShowShareModal] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");
    const [popoverItems, setPopoverItems] = useState<React.ReactNode[]>([]);
    const { refreshChatSessions } = useChatSessions();
    const {
      refreshCurrentWorkspaceDetails,
      workspaces,
      fetchWorkspaces,
      currentWorkspaceId,
      createWorkspace,
    } = useWorkspacesContext();
    const { agents } = useAgents();
    const { pinnedAgents, togglePinnedAgent } = usePinnedAgents();
    const [popoverOpen, setPopoverOpen] = useState(false);
    const [pendingMoveWorkspaceId, setPendingMoveWorkspaceId] = useState<
      number | null
    >(null);
    const [showMoveCustomAgentModal, setShowMoveCustomAgentModal] =
      useState(false);
    const [navigateAfterMoveWorkspaceId, setNavigateAfterMoveWorkspaceId] =
      useState<number | null>(null);

    // Drag and drop setup for chat sessions
    const dragId = `${DRAG_TYPES.CHAT}-${chatSession.id}`;
    const { attributes, listeners, setNodeRef, transform, isDragging } =
      useDraggable({
        id: dragId,
        data: {
          type: DRAG_TYPES.CHAT,
          chatSession,
          workspaceId: workspace?.id,
        },
        disabled: !draggable || renaming,
      });

    // Sync local name state when chatSession.name changes (e.g., after auto-naming)
    useEffect(() => {
      const newName = chatSession.name || UNNAMED_CHAT;
      const oldName = displayName;

      // Only animate if transitioning from UNNAMED_CHAT to a real name
      if (oldName === UNNAMED_CHAT && newName !== UNNAMED_CHAT && mounted) {
        // Type out the name character by character
        let currentIndex = 0;
        const typingInterval = setInterval(() => {
          currentIndex++;
          setDisplayName(newName.slice(0, currentIndex));

          if (currentIndex >= newName.length) {
            clearInterval(typingInterval);
          }
        }, 30); // 30ms per character

        return () => clearInterval(typingInterval);
      } else {
        // No animation for other changes (manual rename, initial load, etc.)
        setDisplayName(newName);
      }
    }, [chatSession.name, mounted]);

    const filteredWorkspaces = useMemo(() => {
      if (!searchTerm) return workspaces;
      const term = searchTerm.toLowerCase();
      return workspaces.filter((workspace) =>
        workspace.name.toLowerCase().includes(term)
      );
    }, [workspaces, searchTerm]);

    useEffect(() => {
      if (!showMoveOptions) {
        const popoverItems = [
          <LineItem
            key="share"
            icon={SvgShare}
            onClick={noProp(() => setShowShareModal(true))}
          >
            Share
          </LineItem>,
          <LineItem
            key="rename"
            icon={SvgEdit}
            onClick={noProp(() => setRenaming(true))}
          >
            Rename
          </LineItem>,
          <LineItem
            key="move"
            icon={SvgFolderIn}
            onClick={noProp(() => setShowMoveOptions(true))}
          >
            Move to Workspace
          </LineItem>,
          workspace && (
            <LineItem
              key="remove"
              icon={SvgFolder}
              onClick={noProp(() => handleRemoveFromWorkspace())}
            >
              {`Remove from ${workspace.name}`}
            </LineItem>
          ),
          null,
          <LineItem
            key="delete"
            icon={SvgTrash}
            danger
            onClick={noProp(() => setDeleteConfirmationModalOpen(true))}
          >
            Delete
          </LineItem>,
        ];
        setPopoverItems(popoverItems);
      } else {
        const availableWorkspaces = filteredWorkspaces.filter(
          (candidateWorkspace) => candidateWorkspace.id !== workspace?.id
        );

        const popoverItems = [
          <PopoverSearchInput
            key="search"
            setShowMoveOptions={setShowMoveOptions}
            onSearch={setSearchTerm}
          />,
          ...availableWorkspaces.map((targetWorkspace) => (
            <LineItem
              key={targetWorkspace.id}
              icon={SvgFolder}
              onClick={noProp(() => handleChatMove(targetWorkspace))}
            >
              {targetWorkspace.name}
            </LineItem>
          )),
          // Show "Create New Workspace" option when no workspaces match the search
          ...(availableWorkspaces.length === 0 && searchTerm.trim() !== ""
            ? [
                null,
                <LineItem
                  key="create-new"
                  icon={SvgFolderPlus}
                  onClick={noProp(() =>
                    handleCreateWorkspaceAndMove(searchTerm.trim())
                  )}
                >
                  {`Create ${searchTerm.trim()}`}
                </LineItem>,
              ]
            : []),
        ];
        setPopoverItems(popoverItems);
      }
    }, [
      showMoveOptions,
      filteredWorkspaces,
      refreshChatSessions,
      fetchWorkspaces,
      currentWorkspaceId,
      refreshCurrentWorkspaceDetails,
      workspace,
      chatSession.id,
      searchTerm,
      createWorkspace,
    ]);

    // Pin the chat's agent when clicking on the conversation
    async function handleClick() {
      const agent = agents.find((a) => a.id === chatSession.agent_id);
      if (agent) {
        const isAlreadyPinned = pinnedAgents.some((a) => a.id === agent.id);
        if (!isAlreadyPinned) {
          await togglePinnedAgent(agent, true);
        }
      }
    }

    async function handleRename(newName: string) {
      setDisplayName(newName);
      await renameChatSession(chatSession.id, newName);
      await refreshChatSessions();
    }

    async function handleChatDelete() {
      try {
        await deleteChatSession(chatSession.id);

        if (workspace) {
          await fetchWorkspaces();
          await refreshCurrentWorkspaceDetails();

          // Only route if the deleted chat is the currently opened chat session
          if (active) {
            route({ workspaceId: workspace.id });
          }
        }
        await refreshChatSessions();
      } catch (error) {
        console.error("Failed to delete chat:", error);
        showErrorNotification("Failed to delete chat. Please try again.");
      }
    }

    async function performMove(targetWorkspaceId: number) {
      try {
        await handleMoveOperation({
          chatSession,
          targetWorkspaceId,
          refreshChatSessions,
          refreshCurrentWorkspaceDetails,
          fetchWorkspaces,
          currentWorkspaceId,
        });
        setShowMoveOptions(false);
        setSearchTerm("");
      } catch (error) {
        // handleMoveOperation already handles error notification
        console.error("Failed to move chat:", error);
      }
    }

    async function handleChatMove(targetWorkspace: Workspace) {
      if (shouldShowMoveModal(chatSession)) {
        setPendingMoveWorkspaceId(targetWorkspace.id);
        setShowMoveCustomAgentModal(true);
        return;
      }
      await performMove(targetWorkspace.id);
    }

    async function handleRemoveFromWorkspace() {
      try {
        await removeChatSessionFromWorkspace(chatSession.id);
        const workspaceRefreshPromise = currentWorkspaceId
          ? refreshCurrentWorkspaceDetails()
          : fetchWorkspaces();
        await Promise.all([refreshChatSessions(), workspaceRefreshPromise]);
        setShowMoveOptions(false);
        setSearchTerm("");
      } catch (error) {
        console.error("Failed to remove chat from workspace:", error);
      }
    }

    async function handleCreateWorkspaceAndMove(workspaceName: string) {
      try {
        // Create the new workspace using the service directly (without navigation)
        const newWorkspace = await createWorkspaceService(workspaceName);

        // Refresh workspaces list to include the new workspace
        await fetchWorkspaces();

        // Mark that we want to navigate to this workspace after moving
        setNavigateAfterMoveWorkspaceId(newWorkspace.id);

        // Check if we should show the move modal for custom agents
        if (shouldShowMoveModal(chatSession)) {
          setPendingMoveWorkspaceId(newWorkspace.id);
          setShowMoveCustomAgentModal(true);
          setShowMoveOptions(false);
          setSearchTerm("");
          return;
        }

        // Move the chat to the newly created workspace
        await performMove(newWorkspace.id);

        // Navigate to the new workspace to see the chat
        route({ workspaceId: newWorkspace.id });
        setNavigateAfterMoveWorkspaceId(null);
      } catch (error) {
        console.error("Failed to create workspace and move chat:", error);
        showErrorNotification("Failed to create workspace. Please try again.");
        setNavigateAfterMoveWorkspaceId(null);
      }
    }

    const rightMenu = (
      <>
        <Popover.Trigger asChild onClick={noProp()}>
          <div>
            <IconButton
              icon={SvgMoreHorizontal}
              className={cn(
                !popoverOpen && "hidden",
                !renaming && "group-hover/SidebarTab:flex"
              )}
              transient={popoverOpen}
              internal
            />
          </div>
        </Popover.Trigger>
        <Popover.Content side="right" align="start" width="md">
          <PopoverMenu>{popoverItems}</PopoverMenu>
        </Popover.Content>
      </>
    );

    const popover = (
      <Popover
        onOpenChange={(state) => {
          setPopoverOpen(state);
          if (!state) {
            setShowMoveOptions(false);
            setSearchTerm("");
          }
        }}
      >
        <Popover.Anchor>
          <SidebarTab
            href={isDragging ? undefined : `/app?chatId=${chatSession.id}`}
            onClick={handleClick}
            transient={active}
            rightChildren={rightMenu}
            focused={renaming}
            nested={!!workspace}
          >
            {renaming ? (
              <ButtonRenaming
                initialName={chatSession.name}
                onRename={handleRename}
                onClose={() => setRenaming(false)}
              />
            ) : (
              displayName
            )}
          </SidebarTab>
        </Popover.Anchor>
      </Popover>
    );

    return (
      <>
        {deleteConfirmationModalOpen && (
          <ConfirmationModalLayout
            title="Delete Chat"
            icon={SvgTrash}
            onClose={() => setDeleteConfirmationModalOpen(false)}
            submit={
              <Button
                danger
                onClick={() => {
                  setDeleteConfirmationModalOpen(false);
                  handleChatDelete();
                }}
              >
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
              setNavigateAfterMoveWorkspaceId(null);
            }}
            onConfirm={async (doNotShowAgain: boolean) => {
              if (doNotShowAgain && typeof window !== "undefined") {
                window.localStorage.setItem(
                  LOCAL_STORAGE_KEYS.HIDE_MOVE_CUSTOM_AGENT_MODAL,
                  "true"
                );
              }
              const target = pendingMoveWorkspaceId;
              const shouldNavigate = navigateAfterMoveWorkspaceId;
              setShowMoveCustomAgentModal(false);
              setPendingMoveWorkspaceId(null);
              if (target != null) {
                await performMove(target);
                // Navigate if this was triggered by creating a new workspace
                if (shouldNavigate != null) {
                  route({ workspaceId: shouldNavigate });
                  setNavigateAfterMoveWorkspaceId(null);
                }
              }
            }}
          />
        )}

        {showShareModal && (
          <ShareChatSessionModal
            chatSession={chatSession}
            onClose={() => setShowShareModal(false)}
          />
        )}

        {draggable ? (
          <div
            ref={setNodeRef}
            style={{
              transform: transform
                ? `translate3d(0px, ${transform.y}px, 0)`
                : undefined,
              opacity: isDragging ? 0.5 : 1,
            }}
            {...(mounted ? attributes : {})}
            {...(mounted ? listeners : {})}
          >
            {popover}
          </div>
        ) : (
          popover
        )}
      </>
    );
  }
);
ChatButton.displayName = "ChatButton";

export default ChatButton;
