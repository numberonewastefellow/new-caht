"use client";

import React, { useRef, useState, useEffect, useMemo } from "react";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import { WorkspaceFile } from "@/providers/WorkspacesContext";
import { formatRelativeTime } from "@/app/app/components/workspaces/workspace_utils";
import Text from "@/refresh-components/texts/Text";
import type { IconProps } from "@opal/types";
import { getFileExtension } from "@/lib/utils";
import { KnowledgeFileStatus } from "@/app/app/workspaces/workspacesService";
import Button from "@/refresh-components/buttons/Button";
import SimpleLoader from "@/refresh-components/loaders/SimpleLoader";
import AttachmentButton from "@/refresh-components/buttons/AttachmentButton";
import Modal from "@/refresh-components/Modal";
import { useModal } from "@/refresh-components/contexts/ModalContext";
import TextSeparator from "@/refresh-components/TextSeparator";
import {
  SvgEye,
  SvgFiles,
  SvgTrash,
  SvgUploadCloud,
  SvgXCircle,
} from "@opal/icons";
import { getColorfulFileIcon } from "@/refresh-components/popovers/ActionsPopover/colorfulIcons";
import { Section } from "@/layouts/general-layouts";
import useFilter from "@/hooks/useFilter";
import { Button as OpalButton } from "@opal/components";
import ScrollIndicatorDiv from "@/refresh-components/ScrollIndicatorDiv";

function getIcon(
  file: WorkspaceFile,
  isProcessing: boolean
): React.FunctionComponent<IconProps> {
  if (isProcessing) return SimpleLoader;
  return getColorfulFileIcon(file.name);
}

function getDescription(file: WorkspaceFile): string {
  const s = String(file.status || "");
  const typeLabel = getFileExtension(file.name);
  if (s === KnowledgeFileStatus.PROCESSING) return "Processing...";
  if (s === KnowledgeFileStatus.UPLOADING) return "Uploading...";
  if (s === KnowledgeFileStatus.DELETING) return "Deleting...";
  if (s === KnowledgeFileStatus.COMPLETED) return typeLabel;
  return file.status ?? typeLabel;
}

interface FileAttachmentProps {
  file: WorkspaceFile;
  isSelected: boolean;
  onClick?: () => void;
  onView?: () => void;
  onDelete?: () => void;
}

function FileAttachment({
  file,
  isSelected,
  onClick,
  onView,
  onDelete,
}: FileAttachmentProps) {
  const isProcessing =
    String(file.status) === KnowledgeFileStatus.PROCESSING ||
    String(file.status) === KnowledgeFileStatus.UPLOADING ||
    String(file.status) === KnowledgeFileStatus.DELETING;

  const Icon = getIcon(file, isProcessing);
  const description = getDescription(file);
  const rightText = file.last_accessed_at
    ? formatRelativeTime(file.last_accessed_at)
    : "";

  return (
    <AttachmentButton
      onClick={onClick}
      icon={Icon}
      description={description}
      rightText={rightText}
      selected={isSelected}
      processing={isProcessing}
      onView={onView}
      actionIcon={SvgTrash}
      onAction={onDelete}
    >
      {file.name}
    </AttachmentButton>
  );
}

export interface KnowledgeFilesModalProps {
  // Modal content
  title: string;
  description: string;
  recentFiles: WorkspaceFile[];
  handleUploadChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  selectedFileIds?: string[];

  // FileAttachment related
  onView?: (file: WorkspaceFile) => void;
  onDelete?: (file: WorkspaceFile) => void;
  onPickRecent?: (file: WorkspaceFile) => void;
  onUnpickRecent?: (file: WorkspaceFile) => void;
}

export default function KnowledgeFilesModal({
  title,
  description,
  recentFiles,
  handleUploadChange,
  selectedFileIds,

  onView,
  onDelete,
  onPickRecent,
  onUnpickRecent,
}: KnowledgeFilesModalProps) {
  const { isOpen, toggle } = useModal();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(selectedFileIds || [])
  );
  const [showOnlySelected, setShowOnlySelected] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const triggerUploadPicker = () => fileInputRef.current?.click();

  useEffect(() => {
    if (selectedFileIds) setSelectedIds(new Set(selectedFileIds));
    else setSelectedIds(new Set());
  }, [selectedFileIds]);

  const selectedCount = selectedIds.size;

  function handleDeselectAll() {
    selectedIds.forEach((id) => {
      const file = recentFiles.find((f) => f.id === id);
      if (file) {
        onUnpickRecent?.(file);
      }
    });
    setSelectedIds(new Set());
  }

  const files = useMemo(
    () =>
      showOnlySelected
        ? recentFiles.filter((workspaceFile) => selectedIds.has(workspaceFile.id))
        : recentFiles,
    [showOnlySelected, recentFiles, selectedIds]
  );

  const { query, setQuery, filtered } = useFilter(files, (file) => file.name);

  return (
    <>
      {/* Hidden file input */}
      {handleUploadChange && (
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleUploadChange}
        />
      )}

      <Modal open={isOpen} onOpenChange={toggle}>
        <Modal.Content
          width="sm"
          height="lg"
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            searchInputRef.current?.focus();
          }}
          preventAccidentalClose={false}
        >
          <Modal.Header icon={SvgFiles} title={title} description={description}>
            {/* Search bar section */}
            <Section flexDirection="row" gap={0.5}>
              <InputTypeIn
                ref={searchInputRef}
                placeholder="Search files..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                leftSearchIcon
                autoComplete="off"
                tabIndex={0}
                onFocus={(e) => {
                  e.target.select();
                }}
              />
              {handleUploadChange && (
                <Button
                  secondary
                  onClick={triggerUploadPicker}
                >
                  <SvgUploadCloud className="w-4 h-4 mr-1.5" />
                  Upload
                </Button>
              )}
            </Section>
          </Modal.Header>

          <Modal.Body
            padding={filtered.length === 0 ? 0.5 : 0}
            gap={0.5}
            alignItems="center"
          >
            {/* File display section */}
            {filtered.length === 0 ? (
              <div className="flex flex-col items-center py-8 gap-2">
                <SvgFiles className="w-10 h-10 stroke-text-01" />
                <Text as="p" text02 secondaryBody>
                  {query.trim() ? "No matching files" : "No files uploaded yet"}
                </Text>
              </div>
            ) : (
              <ScrollIndicatorDiv className="p-2 gap-2 max-h-[70vh]">
                {filtered.map((workspaceFle) => {
                  const isSelected = selectedIds.has(workspaceFle.id);
                  return (
                    <FileAttachment
                      key={workspaceFle.id}
                      file={workspaceFle}
                      isSelected={isSelected}
                      onClick={
                        onPickRecent
                          ? () => {
                              if (isSelected) {
                                onUnpickRecent?.(workspaceFle);
                                setSelectedIds((prev) => {
                                  const next = new Set(prev);
                                  next.delete(workspaceFle.id);
                                  return next;
                                });
                              } else {
                                onPickRecent(workspaceFle);
                                setSelectedIds((prev) => {
                                  const next = new Set(prev);
                                  next.add(workspaceFle.id);
                                  return next;
                                });
                              }
                            }
                          : undefined
                      }
                      onView={onView ? () => onView(workspaceFle) : undefined}
                      onDelete={
                        onDelete ? () => onDelete(workspaceFle) : undefined
                      }
                    />
                  );
                })}

                {/* File count divider - only show when not searching or filtering */}
                {!query.trim() && !showOnlySelected && (
                  <TextSeparator
                    count={recentFiles.length}
                    text={recentFiles.length === 1 ? "File" : "Files"}
                  />
                )}
              </ScrollIndicatorDiv>
            )}
          </Modal.Body>

          <Modal.Footer>
            {/* Left side: file count and controls */}
            {onPickRecent && (
              <Section flexDirection="row" justifyContent="start" gap={0.5}>
                <span
                  className="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full"
                  style={
                    selectedCount > 0
                      ? {
                          backgroundColor:
                            "color-mix(in srgb, var(--virtualai-accent, var(--theme-primary-05)) 10%, var(--background-neutral-01) 90%)",
                          color:
                            "var(--virtualai-accent, var(--theme-primary-05))",
                        }
                      : {
                          backgroundColor: "var(--background-tint-02)",
                          color: "var(--text-02)",
                        }
                  }
                >
                  {selectedCount} {selectedCount === 1 ? "file" : "files"}{" "}
                  selected
                </span>
                <OpalButton
                  icon={SvgEye}
                  prominence="tertiary"
                  size="sm"
                  onClick={() => setShowOnlySelected(!showOnlySelected)}
                  transient={showOnlySelected}
                  tooltip={showOnlySelected ? "Show all" : "Show selected only"}
                />
                <OpalButton
                  icon={SvgXCircle}
                  prominence="tertiary"
                  size="sm"
                  onClick={handleDeselectAll}
                  disabled={selectedCount === 0}
                  tooltip="Deselect all"
                />
              </Section>
            )}

            {/* Right side: Done button */}
            <Button secondary onClick={() => toggle(false)}>
              Done
            </Button>
          </Modal.Footer>
        </Modal.Content>
      </Modal>
    </>
  );
}
