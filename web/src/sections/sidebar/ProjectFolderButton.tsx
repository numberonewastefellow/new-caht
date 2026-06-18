"use client";

import React, { useState, memo } from "react";
import { Project, useProjectsContext } from "@/providers/ProjectsContext";
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

/* ── Colorful project icon — colored rounded square with grid inside ── */
const ColorfulProjectIcon: React.FunctionComponent<IconProps> = () => (
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

const ColorfulProjectIconOpen: React.FunctionComponent<IconProps> = () => (
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

export interface ProjectFolderButtonProps {
  project: Project;
}

const ProjectFolderButton = memo(({ project }: ProjectFolderButtonProps) => {
  const route = useAppRouter();
  const [open, setOpen] = useState(false);
  const [deleteConfirmationModalOpen, setDeleteConfirmationModalOpen] =
    useState(false);
  const { renameProject, deleteProject } = useProjectsContext();
  const [isEditing, setIsEditing] = useState(false);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [isHoveringIcon, setIsHoveringIcon] = useState(false);
  const [allowHoverEffect, setAllowHoverEffect] = useState(true);
  const activeSidebar = useAppFocus();

  // Make project droppable
  const dropId = `project-${project.id}`;
  const { setNodeRef, isOver } = useDroppable({
    id: dropId,
    data: {
      type: DRAG_TYPES.PROJECT,
      project,
    },
  });

  function getFolderIcon(): React.FunctionComponent<IconProps> {
    if (open) {
      return ColorfulProjectIconOpen;
    } else {
      return isHoveringIcon && allowHoverEffect
        ? ColorfulProjectIconOpen
        : ColorfulProjectIcon;
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
    route({ projectId: project.id });
  }

  async function handleRename(newName: string) {
    await renameProject(project.id, newName);
  }

  const popoverItems = [
    <LineItem
      key="rename-project"
      icon={SvgEdit}
      onClick={noProp(() => setIsEditing(true))}
    >
      Rename Workspace
    </LineItem>,
    null,
    <LineItem
      key="delete-project"
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
                deleteProject(project.id);
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

      {/* Project Folder */}
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
              activeSidebar.isProject() &&
              activeSidebar.getId() === String(project.id)
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
                initialName={project.name}
                onRename={handleRename}
                onClose={() => setIsEditing(false)}
              />
            ) : (
              project.name
            )}
          </SidebarTab>
        </Popover.Anchor>
      </Popover>

      {/* Project Chat-Sessions */}
      {open &&
        project.chat_sessions.map((chatSession) => (
          <ChatButton
            key={chatSession.id}
            chatSession={chatSession}
            project={project}
            draggable
          />
        ))}
    </div>
  );
});
ProjectFolderButton.displayName = "ProjectFolderButton";

export default ProjectFolderButton;
