"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useProjectsContext } from "@/providers/ProjectsContext";
import FilePickerPopover from "@/refresh-components/popovers/FilePickerPopover";
import type { ProjectFile } from "../../projects/projectsService";
import { MinimalOnyxDocument } from "@/lib/search/interfaces";
import Button from "@/refresh-components/buttons/Button";

import UserFilesModal from "@/components/modals/UserFilesModal";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import Text from "@/refresh-components/texts/Text";
import CreateButton from "@/refresh-components/buttons/CreateButton";
import { FileCard, FileCardSkeleton } from "@/sections/cards/FileCard";
import { cn, hasNonImageFiles } from "@/lib/utils";
import IconButton from "@/refresh-components/buttons/IconButton";
import ButtonRenaming from "@/refresh-components/buttons/ButtonRenaming";
import { UserFileStatus } from "../../projects/projectsService";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";
import { SvgEdit, SvgFiles, SvgFolderOpen } from "@opal/icons";

/* ── Chevron helper ── */
function Chevron({ expanded }: { expanded: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 12 12"
      className={cn(
        "transition-transform duration-150 flex-shrink-0",
        expanded ? "rotate-90" : ""
      )}
      style={{
        stroke: "var(--text-03)",
        fill: "none",
        strokeWidth: 1.5,
        strokeLinecap: "round",
        strokeLinejoin: "round",
      }}
    >
      <polyline points="4,2 8,6 4,10" />
    </svg>
  );
}

export interface ProjectContextPanelProps {
  projectTokenCount?: number;
  availableContextTokens?: number;
  setPresentingDocument?: (document: MinimalOnyxDocument) => void;
}

export default function ProjectContextPanel({
  projectTokenCount = 0,
  availableContextTokens = 128_000,
  setPresentingDocument,
}: ProjectContextPanelProps) {
  const projectFilesModal = useCreateModal();

  // Edit project name
  const [isEditingName, setIsEditingName] = useState(false);

  // Collapsible sections
  const [guidelinesExpanded, setGuidelinesExpanded] = useState(false);
  const [filesExpanded, setFilesExpanded] = useState(true);

  // Inline guidelines editing
  const [guidelinesText, setGuidelinesText] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const {
    currentProjectDetails,
    currentProjectId,
    unlinkFileFromProject,
    linkFileToProject,
    allCurrentProjectFiles,
    isLoadingProjectDetails,
    beginUpload,
    projects,
    renameProject,
    upsertInstructions,
  } = useProjectsContext();

  const currentInstructions =
    currentProjectDetails?.project?.instructions ?? "";

  // Pre-fill guidelines text when expanding
  useEffect(() => {
    if (guidelinesExpanded) {
      setGuidelinesText(currentInstructions);
    }
  }, [guidelinesExpanded, currentInstructions]);

  // Convert ProjectFile to MinimalOnyxDocument format for viewing
  const handleOnView = useCallback(
    (file: ProjectFile) => {
      if (!setPresentingDocument) return;
      const documentForViewer: MinimalOnyxDocument = {
        document_id: `project_file__${file.file_id}`,
        semantic_identifier: file.name,
      };
      setPresentingDocument(documentForViewer);
    },
    [setPresentingDocument]
  );

  const handleUploadFiles = useCallback(
    async (files: File[]) => {
      if (!files || files.length === 0) return;
      beginUpload(Array.from(files), currentProjectId);
    },
    [currentProjectId, beginUpload]
  );

  const totalFiles = allCurrentProjectFiles.length;
  const displayFileCount = totalFiles > 100 ? "100+" : String(totalFiles);

  const handleUploadChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;
      await handleUploadFiles(Array.from(files));
      e.target.value = "";
    },
    [handleUploadFiles]
  );

  // Dropzone for drag-and-drop
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    noClick: true,
    noKeyboard: true,
    multiple: true,
    noDragEventsBubbling: true,
    onDrop: (acceptedFiles) => {
      void handleUploadFiles(acceptedFiles);
    },
  });

  // Project name
  const currentProject = projects.find((p) => p.id === currentProjectId);
  const projectName = currentProject?.name || "Loading project...";

  // Save guidelines inline
  async function handleSaveGuidelines() {
    setIsSaving(true);
    try {
      await upsertInstructions(guidelinesText.trim());
    } catch (e) {
      console.error("Failed to save guidelines", e);
    }
    setIsSaving(false);
    setGuidelinesExpanded(false);
  }

  if (!currentProjectId) return null;

  const displayedFiles = allCurrentProjectFiles.slice(0, 4);
  const shouldCompactImages = hasNonImageFiles(displayedFiles);

  return (
    <>
      <projectFilesModal.Provider>
        <UserFilesModal
          title="Project Files"
          description="Sessions in this project can access the files here."
          recentFiles={[...allCurrentProjectFiles]}
          onView={handleOnView}
          handleUploadChange={handleUploadChange}
          onDelete={async (file: ProjectFile) => {
            if (!currentProjectId) return;
            await unlinkFileFromProject(currentProjectId, file.id);
          }}
        />
      </projectFilesModal.Provider>

      <div className="flex flex-col w-full max-w-[var(--app-page-main-content-width)] mx-auto p-4 pt-14 pb-6">
        {/* ── Project Card ── */}
        <div className="bg-background-tint-01 rounded-xl border border-border-01 p-5 flex flex-col gap-0">
          {/* Row 1: Project identity */}
          <div className="group flex items-center gap-2.5">
            <SvgFolderOpen className="h-6 w-6 text-text-03 flex-shrink-0" />
            {isEditingName ? (
              <ButtonRenaming
                initialName={projectName}
                onRename={async (newName) => {
                  if (currentProjectId) {
                    await renameProject(currentProjectId, newName);
                  }
                }}
                onClose={() => setIsEditingName(false)}
                className="font-heading-h3 text-text-04"
              />
            ) : (
              <>
                <Text as="p" headingH3 text04 className="truncate">
                  {projectName}
                </Text>
                <IconButton
                  icon={SvgEdit}
                  internal
                  onClick={() => setIsEditingName(true)}
                  className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity"
                  tooltip="Rename project"
                />
              </>
            )}
          </div>

          {/* Row 2: Project Guidelines (collapsible) */}
          <div className="mt-4">
            <button
              type="button"
              onClick={() => setGuidelinesExpanded((v) => !v)}
              className="flex items-center gap-1.5 w-full text-left group/guidelines"
            >
              <Chevron expanded={guidelinesExpanded} />
              <Text as="span" secondaryAction text03>
                Project Guidelines
              </Text>
            </button>

            {/* Collapsed: show preview */}
            {!guidelinesExpanded && (
              <div className="ml-5 mt-1">
                {isLoadingProjectDetails && !currentProjectDetails ? (
                  <div className="h-4 w-3/4 rounded bg-background-tint-02 animate-pulse" />
                ) : currentInstructions ? (
                  <Text as="p" text02 secondaryBody className="truncate">
                    {currentInstructions}
                  </Text>
                ) : (
                  <Text as="p" text02 secondaryBody className="italic">
                    No guidelines set. Click to add.
                  </Text>
                )}
              </div>
            )}

            {/* Expanded: inline textarea editor */}
            {guidelinesExpanded && (
              <div className="ml-5 mt-2">
                <InputTextArea
                  value={guidelinesText}
                  onChange={(e) => setGuidelinesText(e.target.value)}
                  placeholder="Specify behaviors, tone, or context for chats in this project..."
                />
                <div className="flex gap-2 mt-2 justify-end">
                  <Button
                    secondary
                    onClick={() => setGuidelinesExpanded(false)}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleSaveGuidelines} disabled={isSaving}>
                    {isSaving ? "Saving..." : "Save"}
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Row 3: Files (collapsible) */}
          <div
            className="mt-3"
            {...getRootProps({ onClick: (e) => e.stopPropagation() })}
          >
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setFilesExpanded((v) => !v)}
                className="flex items-center gap-1.5 text-left"
              >
                <Chevron expanded={filesExpanded} />
                <Text as="span" secondaryAction text03>
                  Files{totalFiles > 0 ? ` (${displayFileCount})` : ""}
                </Text>
              </button>

              <FilePickerPopover
                trigger={(open) => (
                  <CreateButton
                    secondary={undefined}
                    tertiary
                    transient={open}
                  >
                    Add Files
                  </CreateButton>
                )}
                onFileClick={handleOnView}
                onPickRecent={async (file) => {
                  if (file.status === UserFileStatus.UPLOADING) return;
                  if (file.status === UserFileStatus.DELETING) return;
                  if (!currentProjectId) return;
                  if (!linkFileToProject) return;
                  linkFileToProject(currentProjectId, file);
                }}
                onUnpickRecent={async (file) => {
                  if (!currentProjectId) return;
                  await unlinkFileFromProject(currentProjectId, file.id);
                }}
                handleUploadChange={handleUploadChange}
                selectedFileIds={(allCurrentProjectFiles || []).map(
                  (f) => f.id
                )}
              />
            </div>

            {/* Hidden dropzone input */}
            <input {...getInputProps()} />

            {/* Files content (shown when expanded) */}
            {filesExpanded && (
              <div className="ml-5 mt-2">
                {isLoadingProjectDetails && !currentProjectDetails ? (
                  <>
                    <div className="sm:hidden">
                      <div className="w-full h-[68px] rounded-xl bg-background-tint-02 animate-pulse" />
                    </div>
                    <div className="hidden sm:flex gap-1">
                      <FileCardSkeleton />
                      <FileCardSkeleton />
                      <FileCardSkeleton />
                      <FileCardSkeleton />
                    </div>
                  </>
                ) : allCurrentProjectFiles.length > 0 ? (
                  <>
                    {/* Mobile */}
                    <div className="sm:hidden">
                      <button
                        className="w-full rounded-xl px-3 py-3 text-left bg-transparent hover:bg-accent-background-hovered hover:dark:bg-neutral-800/75 transition-colors"
                        onClick={() => projectFilesModal.toggle(true)}
                      >
                        <div className="flex flex-col overflow-hidden">
                          <div className="flex items-center justify-between gap-2 w-full">
                            <Text as="p" text04 secondaryAction>
                              View files
                            </Text>
                            <SvgFiles className="h-5 w-5 stroke-text-02" />
                          </div>
                          <Text as="p" text03 secondaryBody>
                            {displayFileCount} files
                          </Text>
                        </div>
                      </button>
                    </div>

                    {/* Desktop */}
                    <div className="hidden sm:flex gap-1 relative items-center">
                      {allCurrentProjectFiles.slice(0, 4).map((f) => (
                        <div key={f.id}>
                          <FileCard
                            file={f}
                            removeFile={async (fileId: string) => {
                              if (!currentProjectId) return;
                              await unlinkFileFromProject(
                                currentProjectId,
                                fileId
                              );
                            }}
                            onFileClick={handleOnView}
                            compactImages={shouldCompactImages}
                          />
                        </div>
                      ))}
                      {totalFiles > 4 && (
                        <button
                          className="rounded-xl px-3 py-1 text-left transition-colors hover:bg-background-tint-02"
                          onClick={() => projectFilesModal.toggle(true)}
                        >
                          <div className="flex flex-col overflow-hidden h-12 p-1">
                            <div className="flex items-center justify-between gap-2 w-full">
                              <Text as="p" text04 secondaryAction>
                                View All
                              </Text>
                              <SvgFiles className="h-5 w-5 stroke-text-02" />
                            </div>
                            <Text as="p" text03 secondaryBody>
                              {displayFileCount} files
                            </Text>
                          </div>
                        </button>
                      )}
                      {isDragActive && (
                        <div className="pointer-events-none absolute inset-0 rounded-lg border-2 border-dashed border-action-link-05" />
                      )}
                    </div>
                    {projectTokenCount > availableContextTokens && (
                      <Text as="p" text02 secondaryBody className="mt-2">
                        This project exceeds the model&apos;s context limits.
                        Sessions will automatically search for relevant files
                        first before generating response.
                      </Text>
                    )}
                  </>
                ) : (
                  <div
                    className={`h-12 rounded-lg border border-dashed ${
                      isDragActive
                        ? "bg-action-link-01 border-action-link-05"
                        : "border-border-01"
                    } flex items-center pl-2`}
                  >
                    <p
                      className={`font-secondary-body ${
                        isDragActive ? "text-action-link-05" : "text-text-02"
                      }`}
                    >
                      {isDragActive
                        ? "Drop files here to add to this project"
                        : "Add documents, texts, or images. Drag & drop supported."}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
