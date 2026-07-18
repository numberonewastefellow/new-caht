"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { cn, noProp } from "@/lib/utils";
import KnowledgeFilesModal from "@/components/modals/KnowledgeFilesModal";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import {
  WorkspaceFile,
  KnowledgeFileStatus,
} from "@/app/app/workspaces/workspacesService";
import IconButton from "@/refresh-components/buttons/IconButton";
import { toast } from "@/hooks/useToast";
import { useWorkspacesContext } from "@/providers/WorkspacesContext";
import Text from "@/refresh-components/texts/Text";
import Modal from "@/refresh-components/Modal";
import {
  SvgExternalLink,
  SvgFiles,
  SvgLoader,
  SvgPaperclip,
  SvgUploadCloud,
} from "@opal/icons";
import { getColorfulFileIcon } from "@/refresh-components/popovers/ActionsPopover/colorfulIcons";
import { Section } from "@/layouts/general-layouts";
import Truncated from "@/refresh-components/texts/Truncated";
import Button from "@/refresh-components/buttons/Button";

/** Max recent files to show in the quick-attach dialog */
const QUICK_ATTACH_MAX = 6;

const getFileExtension = (fileName: string): string => {
  const idx = fileName.lastIndexOf(".");
  if (idx === -1) return "";
  const ext = fileName.slice(idx + 1).toLowerCase();
  if (ext === "txt") return "PLAINTEXT";
  return ext.toUpperCase();
};

/* ─── File Row ─── */

interface FileRowProps {
  workspaceFile: WorkspaceFile;
  onPick: (file: WorkspaceFile) => void;
  onView: (file: WorkspaceFile) => void;
}

function FileRow({ workspaceFile, onPick, onView }: FileRowProps) {
  const isProcessing = useMemo(
    () =>
      String(workspaceFile.status) === KnowledgeFileStatus.PROCESSING ||
      String(workspaceFile.status) === KnowledgeFileStatus.UPLOADING ||
      String(workspaceFile.status) === KnowledgeFileStatus.DELETING,
    [workspaceFile.status]
  );

  const ColorfulIcon = getColorfulFileIcon(workspaceFile.name);
  const ext = getFileExtension(workspaceFile.name);

  return (
    <button
      type="button"
      className="flex items-center gap-3 w-full px-3 py-2.5 rounded-08 transition-colors group virtualai-card-hover"
      onClick={() => onPick(workspaceFile)}
    >
      {/* File icon */}
      <div className="flex-shrink-0 w-8 h-8 rounded-08 virtualai-accent-icon-badge flex items-center justify-center">
        {isProcessing ? (
          <SvgLoader className="w-4 h-4 animate-spin stroke-text-02" />
        ) : (
          <ColorfulIcon className="w-4 h-4" />
        )}
      </div>

      {/* File name */}
      <div className="flex-1 min-w-0 text-left">
        <Truncated mainUiMuted text04 nowrap>
          {workspaceFile.name}
        </Truncated>
      </div>

      {/* File type pill */}
      {ext && (
        <span className="flex-shrink-0 text-[10px] font-semibold uppercase tracking-wider text-text-02 bg-background-tint-02 px-2 py-0.5 rounded-full group-hover:hidden">
          {ext}
        </span>
      )}

      {/* View button — appears on hover */}
      <IconButton
        icon={SvgExternalLink}
        onClick={noProp(() => onView(workspaceFile))}
        tooltip="Open file"
        disabled={isProcessing}
        internal
        className="hidden group-hover:flex flex-shrink-0"
      />
    </button>
  );
}

/* ─── Main Component ─── */

export interface FilePickerPopoverProps {
  onPickRecent?: (file: WorkspaceFile) => void;
  onUnpickRecent?: (file: WorkspaceFile) => void;
  onFileClick?: (file: WorkspaceFile) => void;
  handleUploadChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  trigger?: React.ReactNode | ((open: boolean) => React.ReactNode);
  selectedFileIds?: string[];
}

export default function FilePickerPopover({
  onPickRecent,
  onUnpickRecent,
  onFileClick,
  handleUploadChange,
  trigger,
  selectedFileIds,
}: FilePickerPopoverProps) {
  const { allRecentFiles } = useWorkspacesContext();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const recentFilesModal = useCreateModal();
  const [open, setOpen] = useState(false);
  const [recentFilesSnapshot, setRecentFilesSnapshot] = useState<WorkspaceFile[]>(
    []
  );
  const { deleteKnowledgeFile, setCurrentMessageFiles } = useWorkspacesContext();
  const [deletedFileIds, setDeletedFileIds] = useState<string[]>([]);

  const triggerUploadPicker = () => fileInputRef.current?.click();

  useEffect(() => {
    setRecentFilesSnapshot(
      allRecentFiles.slice().filter((f) => !deletedFileIds.includes(f.id))
    );
  }, [allRecentFiles]);

  const handleDeleteFile = (file: WorkspaceFile) => {
    const lastStatus = file.status;
    setRecentFilesSnapshot((prev) =>
      prev.map((f) =>
        f.id === file.id ? { ...f, status: KnowledgeFileStatus.DELETING } : f
      )
    );
    deleteKnowledgeFile(file.id)
      .then((result) => {
        if (!result.has_associations) {
          toast.success("File deleted successfully");
          setCurrentMessageFiles((prev) =>
            prev.filter((f) => f.id !== file.id)
          );
          setDeletedFileIds((prev) => [...prev, file.id]);
          setRecentFilesSnapshot((prev) => prev.filter((f) => f.id != file.id));
        } else {
          setRecentFilesSnapshot((prev) =>
            prev.map((f) =>
              f.id === file.id ? { ...f, status: lastStatus } : f
            )
          );
          let workspaces = result.workspace_names.join(", ");
          let assistants = result.assistant_names.join(", ");
          let message = "Cannot delete file. It is associated with";
          if (workspaces) {
            message += ` workspaces: ${workspaces}`;
          }
          if (workspaces && assistants) {
            message += " and ";
          }
          if (assistants) {
            message += `assistants: ${assistants}`;
          }

          toast.error(message);
        }
      })
      .catch((error) => {
        setRecentFilesSnapshot((prev) =>
          prev.map((f) => (f.id === file.id ? { ...f, status: lastStatus } : f))
        );
        toast.error("Failed to delete file. Please try again.");
        console.error("Failed to delete file", error);
      });
  };

  const quickFiles = recentFilesSnapshot.slice(0, QUICK_ATTACH_MAX);
  const hasMoreFiles = recentFilesSnapshot.length > QUICK_ATTACH_MAX;
  const totalCount = recentFilesSnapshot.length;

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        multiple
        onChange={handleUploadChange}
        accept={"*/*"}
      />

      {/* Full Recent Files Modal (secondary) */}
      <recentFilesModal.Provider>
        <KnowledgeFilesModal
          title="Recent Files"
          description="Upload files or pick from your recent files."
          recentFiles={recentFilesSnapshot}
          onPickRecent={(file) => {
            onPickRecent && onPickRecent(file);
          }}
          onUnpickRecent={(file) => {
            onUnpickRecent && onUnpickRecent(file);
          }}
          handleUploadChange={handleUploadChange}
          onView={onFileClick}
          selectedFileIds={selectedFileIds}
          onDelete={handleDeleteFile}
        />
      </recentFilesModal.Provider>

      {/* Trigger button */}
      <span
        onClick={() => setOpen(true)}
        style={{ display: "contents" }}
      >
        {typeof trigger === "function" ? trigger(open) : trigger}
      </span>

      {/* Quick Attach Dialog */}
      <Modal open={open} onOpenChange={setOpen}>
        <Modal.Content
          width="sm"
          height="fit"
          preventAccidentalClose={false}
        >
          <Modal.Header
            icon={SvgPaperclip}
            title="Attach Files"
            description="Select a recent file or upload from your device"
          />

          <Modal.Body twoTone padding={0.75} gap={0.5}>
            {/* Upload zone */}
            <button
              type="button"
              onClick={() => {
                triggerUploadPicker();
                setOpen(false);
              }}
              className={cn(
                "w-full flex items-center gap-3 p-3 rounded-12",
                "border border-dashed border-border-02",
                "transition-colors cursor-pointer",
                "hover:border-[var(--virtualai-accent,var(--theme-primary-05))]",
                "hover:bg-[color-mix(in_srgb,var(--virtualai-accent,var(--theme-primary-05))_4%,var(--background-tint-01)_96%)]"
              )}
            >
              <div className="w-9 h-9 rounded-08 flex items-center justify-center flex-shrink-0 virtualai-accent-icon-badge">
                <span style={{ color: "var(--virtualai-accent, var(--theme-primary-05))" }}>
                  <SvgUploadCloud className="w-5 h-5 stroke-current" />
                </span>
              </div>
              <div className="text-left">
                <Text as="p" mainUiMuted text04>
                  Upload from Device
                </Text>
                <Text as="p" secondaryBody text02>
                  Browse and attach files from your computer
                </Text>
              </div>
            </button>

            {/* Recent Files Section */}
            {quickFiles.length > 0 && (
              <Section gap={0.25} alignItems="start" padding={0}>
                <Text
                  as="p"
                  secondaryBody
                  text02
                  className="px-1 pt-2 pb-1 uppercase tracking-wider text-[10px] font-semibold"
                >
                  Recent Files
                </Text>

                <div className="w-full flex flex-col">
                  {quickFiles.map((file) => (
                    <FileRow
                      key={file.id}
                      workspaceFile={file}
                      onPick={(f) => {
                        onPickRecent && onPickRecent(f);
                        setOpen(false);
                      }}
                      onView={(f) => {
                        onFileClick && onFileClick(f);
                        setOpen(false);
                      }}
                    />
                  ))}
                </div>
              </Section>
            )}

            {/* Empty state */}
            {quickFiles.length === 0 && (
              <div className="flex flex-col items-center py-6 gap-2">
                <SvgFiles className="w-10 h-10 stroke-text-01" />
                <Text as="p" text02 secondaryBody>
                  No recent files
                </Text>
              </div>
            )}
          </Modal.Body>

          {/* Footer */}
          <Modal.Footer justifyContent="between">
            {totalCount > 0 && (
              <Text as="p" text02 secondaryBody>
                {totalCount} {totalCount === 1 ? "file" : "files"} available
              </Text>
            )}
            {hasMoreFiles ? (
              <Button
                secondary
                onClick={() => {
                  setOpen(false);
                  recentFilesModal.toggle(true);
                }}
              >
                <SvgFiles className="w-4 h-4 mr-1.5" />
                Browse All Files
              </Button>
            ) : totalCount > 0 ? (
              <Button
                secondary
                onClick={() => {
                  setOpen(false);
                  recentFilesModal.toggle(true);
                }}
              >
                <SvgFiles className="w-4 h-4 mr-1.5" />
                Manage Files
              </Button>
            ) : null}
          </Modal.Footer>
        </Modal.Content>
      </Modal>
    </>
  );
}
