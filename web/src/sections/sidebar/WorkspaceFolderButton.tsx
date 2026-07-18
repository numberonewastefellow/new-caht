"use client";

import React, { useState, memo } from "react";
import { Workspace, useWorkspacesContext } from "@/providers/WorkspacesContext";
import { useDroppable } from "@dnd-kit/core";
import LineItem from "@/refresh-components/buttons/LineItem";
import Popover, { PopoverMenu } from "@/refresh-components/Popover";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import Button from "@/refresh-components/buttons/Button";
import ChatButton from "@/sections/sidebar/ChatButton";
import { useAppRouter } from "@/hooks/appNavigation";
import { cn, noProp } from "@/lib/utils";
import { DRAG_TYPES } from "./constants";
import SidebarTab from "@/refresh-components/buttons/SidebarTab";
import IconButton from "@/refresh-components/buttons/IconButton";
import { Button as OpalButton } from "@opal/components";
import ButtonRenaming from "@/refresh-components/buttons/ButtonRenaming";
import type { IconProps } from "@opal/types";
import useAppFocus from "@/hooks/useAppFocus";
import {
  SvgEdit,
  SvgMoreHorizontal,
  SvgTrash,
} from "@opal/icons";

/* ── Colorful workspace icon — colored rounded square with grid inside ── */
const ColorfulWorkspaceIcon: React.FunctionComponent<IconProps> = () => (
  <span
    className="inline-flex items-center justify-center rounded-[5px] w-5 h-5 flex-shrink-0 bg-emerald-500"
  >
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      className="text-white"
    >
      <rect x="1.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="9.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="1.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  </span>
);

const ColorfulWorkspaceIconOpen: React.FunctionComponent<IconProps> = () => (
  <span
    className="inline-flex items-center justify-center rounded-[5px] w-5 h-5 flex-shrink-0 bg-emerald-600"
  >
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      className="text-white"
    >
      <rect x="1.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="9.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="1.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" fill="currentColor" opacity="0.3" />
    </svg>
  </span>
);

export interface WorkspaceFolderButtonProps {
  workspace: Workspace;
}

const WorkspaceFolderButton = memo(({ workspace }: WorkspaceFolderButtonProps) => {
  const route = useAppRouter();
  const [open, setOpen] = useState(false);
  const [deleteConfirmationModalOpen, setDeleteConfirmationModalOpen] =
    useState(false);
  const { renameWorkspace, deleteWorkspace } = useWorkspacesContext();
  const [isEditing, setIsEditing] = useState(false);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [isHoveringIcon, setIsHoveringIcon] = useState(false);
  const [allowHoverEffect, setAllowHoverEffect] = useState(true);
  const activeSidebar = useAppFocus();

  // Make workspace droppable
  const dropId = `workspace-${workspace.id}`;
  const { setNodeRef, isOver } = useDroppable({
    id: dropId,
    data: {
      type: DRAG_TYPES.PROJECT,
      workspace,
    },
  });

  function getFolderIcon(): React.FunctionComponent<IconProps> {
    if (open) {
      return ColorfulWorkspaceIconOpen;
    } else {
      return isHoveringIcon && allowHoverEffect
        ? ColorfulWorkspaceIconOpen
        : ColorfulWorkspaceIcon;
    }
  }

  function handleIconClick() {
    setOpen((prev) => !prev);
    setAllowHoverEffect(false);
  }

  function handleIconHover(hovering: boolean) {
    setIsHoveringIcon(hovering);
    // Re-enable hover effects when cursor leaves the icon
    if (!hovering) {
      setAllowHoverEffect(true);
    }
  }

  function handleTextClick() {
    route({ workspaceId: workspace.id });
  }

  async function handleRename(newName: string) {
    await renameWorkspace(workspace.id, newName);
  }

  const popoverItems = [
    <LineItem
      key="rename-workspace"
      icon={SvgEdit}
      onClick={noProp(() => setIsEditing(true))}
    >
      Rename Workspace
    </LineItem>,
    null,
    <LineItem
      key="delete-workspace"
      icon={SvgTrash}
      onClick={noProp(() => setDeleteConfirmationModalOpen(true))}
      danger
    >
      Delete Workspace
    </LineItem>,
  ];

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "transition-colors duration-200",
        isOver && "bg-background-tint-03 rounded-08"
      )}
    >
      {/* Confirmation Modal (only for deletion) */}
      {deleteConfirmationModalOpen && (
        <ConfirmationModalLayout
          title="Delete Workspace"
          icon={SvgTrash}
          onClose={() => setDeleteConfirmationModalOpen(false)}
          submit={
            <Button
              danger
              onClick={() => {
                setDeleteConfirmationModalOpen(false);
                deleteWorkspace(workspace.id);
              }}
            >
              Delete
            </Button>
          }
        >
          Are you sure you want to delete this workspace? This action cannot be
          undone.
        </ConfirmationModalLayout>
      )}

      {/* Workspace Folder */}
      <Popover onOpenChange={setPopoverOpen}>
        <Popover.Anchor>
          <SidebarTab
            leftIcon={() => (
              <OpalButton
                onMouseEnter={() => handleIconHover(true)}
                onMouseLeave={() => handleIconHover(false)}
                icon={getFolderIcon()}
                prominence="tertiary"
                size="sm"
                onClick={noProp(handleIconClick)}
              />
            )}
            transient={
              activeSidebar.isWorkspace() &&
              activeSidebar.getId() === String(workspace.id)
            }
            onClick={noProp(handleTextClick)}
            focused={isEditing}
            rightChildren={
              <>
                <Popover.Trigger asChild onClick={noProp()}>
                  <div>
                    <IconButton
                      icon={SvgMoreHorizontal}
                      className={cn(
                        !popoverOpen && "hidden",
                        !isEditing && "group-hover/SidebarTab:flex"
                      )}
                      transient={popoverOpen}
                      internal
                    />
                  </div>
                </Popover.Trigger>

                <Popover.Content side="right" align="end" width="md">
                  <PopoverMenu>{popoverItems}</PopoverMenu>
                </Popover.Content>
              </>
            }
          >
            {isEditing ? (
              <ButtonRenaming
                initialName={workspace.name}
                onRename={handleRename}
                onClose={() => setIsEditing(false)}
              />
            ) : (
              workspace.name
            )}
          </SidebarTab>
        </Popover.Anchor>
      </Popover>

      {/* Workspace Chat-Sessions */}
      {open &&
        workspace.chat_sessions.map((chatSession) => (
          <ChatButton
            key={chatSession.id}
            chatSession={chatSession}
            workspace={workspace}
            draggable
          />
        ))}
    </div>
  );
});
WorkspaceFolderButton.displayName = "WorkspaceFolderButton";

export default WorkspaceFolderButton;
