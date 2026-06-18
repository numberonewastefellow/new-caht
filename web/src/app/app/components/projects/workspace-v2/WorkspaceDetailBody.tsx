"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { useProjectsContext } from "@/providers/ProjectsContext";
import { type ProjectFile } from "@/app/app/projects/projectsService";
import { MinimalOnyxDocument } from "@/lib/search/interfaces";
import type { IconProps } from "@opal/types";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { cn, hasNonImageFiles } from "@/lib/utils";
import { formatRelativeTime } from "../project_utils";
import { type WorkspaceTab } from "./workspaceTheme";
import { FileCard, FileCardSkeleton } from "@/sections/cards/FileCard";
import UserFilesModal from "@/components/modals/UserFilesModal";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import InputTextArea from "@/refresh-components/inputs/InputTextArea";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import ProjectChatSessionList from "../ProjectChatSessionList";
import { UNNAMED_CHAT } from "@/lib/constants";
import {
  SvgBookOpen,
  SvgFileText,
  SvgBubbleText,
  SvgUploadCloud,
  SvgChevronRight,
  SvgSparkle,
  SvgPlus,
  SvgSearch,
  SvgUserPlus,
} from "@opal/icons";

export interface WorkspaceDetailBodyProps {
  tab: WorkspaceTab;
  setTab: (tab: WorkspaceTab) => void;
  setPresentingDocument?: (document: MinimalOnyxDocument) => void;
  projectTokenCount?: number;
  availableContextTokens?: number;
  onNewChat?: () => void;
}

/* ── Small section-header chip icon (single accent, theme-aware) ── */
function SectionIcon({
  icon: Icon,
}: {
  icon: React.FunctionComponent<IconProps>;
}) {
  return (
    <span
      className="flex h-7 w-7 items-center justify-center rounded-lg"
      style={{ backgroundColor: "var(--virtualai-accent-subtle)" }}
    >
      <Icon
        className="h-4 w-4 stroke-current"
        style={{ color: "var(--virtualai-accent)" }}
      />
    </span>
  );
}

/* ── Instructions ── */
function InstructionsSection() {
  const {
    currentProjectId,
    currentProjectDetails,
    upsertInstructions,
    isLoadingProjectDetails,
  } = useProjectsContext();
  const currentInstructions =
    currentProjectDetails?.project?.instructions ?? "";
  const [open, setOpen] = useState(true);
  const [text, setText] = useState(currentInstructions);
  const [isSaving, setIsSaving] = useState(false);

  // Keep the editor in sync when the project/instructions load or change.
  useEffect(() => {
    setText(currentInstructions);
  }, [currentInstructions, currentProjectId]);

  async function handleSave() {
    setIsSaving(true);
    try {
      await upsertInstructions(text.trim());
    } catch (e) {
      console.error("Failed to save workspace instructions", e);
    }
    setIsSaving(false);
  }

  return (
    <section className="rounded-2xl border border-border-01 bg-background-tint-01">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3"
      >
        <div className="flex items-center gap-2">
          <SectionIcon icon={SvgBookOpen} />
          <div className="text-left">
            <div className="text-sm font-semibold text-text-05">
              Workspace instructions
            </div>
            <div className="text-[11px] text-text-03">
              System prompt applied to every chat in this workspace.
            </div>
          </div>
        </div>
        <SvgChevronRight
          className={cn(
            "h-4 w-4 stroke-text-02 transition-transform",
            open && "rotate-90"
          )}
        />
      </button>
      {open && (
        <div className="border-t border-border-01 px-4 py-3">
          {isLoadingProjectDetails && !currentProjectDetails ? (
            <div className="h-24 w-full rounded-08 bg-background-tint-02 animate-pulse" />
          ) : (
            <>
              <InputTextArea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={4}
                placeholder="e.g. You are an insurance claims investigator. Always cite the file you reference…"
              />
              <div className="mt-2 flex items-center justify-between">
                <span className="text-[11px] text-text-03">
                  Markdown supported
                </span>
                <Button onClick={handleSave} disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save"}
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}

/* ── Files ── */
function FilesSection({
  variant,
  setPresentingDocument,
}: {
  variant: "preview" | "full";
  setPresentingDocument?: (document: MinimalOnyxDocument) => void;
}) {
  const {
    currentProjectId,
    currentProjectDetails,
    allCurrentProjectFiles,
    isLoadingProjectDetails,
    beginUpload,
    unlinkFileFromProject,
  } = useProjectsContext();
  const filesModal = useCreateModal();

  const handleOnView = useCallback(
    (file: ProjectFile) => {
      if (!setPresentingDocument) return;
      setPresentingDocument({
        document_id: `project_file__${file.file_id}`,
        semantic_identifier: file.name,
      });
    },
    [setPresentingDocument]
  );

  const handleUploadFiles = useCallback(
    (files: File[]) => {
      if (!files || files.length === 0) return;
      beginUpload(Array.from(files), currentProjectId);
    },
    [currentProjectId, beginUpload]
  );

  const handleUploadChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;
      handleUploadFiles(Array.from(files));
      e.target.value = "";
    },
    [handleUploadFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    noClick: true,
    noKeyboard: true,
    multiple: true,
    noDragEventsBubbling: true,
    onDrop: (accepted) => handleUploadFiles(accepted),
  });

  const totalFiles = allCurrentProjectFiles.length;
  const displayFiles =
    variant === "preview"
      ? allCurrentProjectFiles.slice(0, 6)
      : allCurrentProjectFiles;
  const compactImages = hasNonImageFiles(displayFiles);
  const isLoading = isLoadingProjectDetails && !currentProjectDetails;

  return (
    <section
      className="rounded-2xl border border-border-01 bg-background-tint-01"
      {...getRootProps({ onClick: (e) => e.stopPropagation() })}
    >
      <div className="flex items-center justify-between border-b border-border-01 px-4 py-3">
        <div className="flex items-center gap-2">
          <SectionIcon icon={SvgFileText} />
          <div>
            <div className="text-sm font-semibold text-text-05">Files</div>
            <div className="text-[11px] text-text-03">
              {totalFiles} {totalFiles === 1 ? "item" : "items"} · grounding
              context for every chat
            </div>
          </div>
        </div>
        <label className="flex cursor-pointer items-center gap-1.5 rounded-full border border-border-02 px-3 py-1.5 text-xs font-medium text-text-03 transition-colors hover:bg-background-tint-02 hover:text-text-05">
          <SvgUploadCloud className="h-3.5 w-3.5 stroke-current" />
          Upload
          <input
            type="file"
            multiple
            className="hidden"
            onChange={handleUploadChange}
          />
        </label>
      </div>

      <div className="p-3">
        {/* Dropzone hint */}
        <div
          className={cn(
            "mb-3 rounded-xl border-2 border-dashed px-4 py-5 text-center text-xs transition-all",
            isDragActive
              ? "border-action-link-05 bg-action-link-01 text-action-link-05"
              : "border-border-02 bg-background-tint-02/30 text-text-03"
          )}
        >
          {isDragActive
            ? "Drop files here to add to this workspace"
            : "Drag & drop files here, or click upload. PDF, DOCX, images, CSV up to 25 MB."}
        </div>
        <input {...getInputProps()} />

        {isLoading ? (
          <div className="flex flex-wrap gap-2">
            <FileCardSkeleton />
            <FileCardSkeleton />
            <FileCardSkeleton />
          </div>
        ) : totalFiles === 0 ? (
          <Text as="p" text03 secondaryBody className="px-1 py-2">
            No files yet. Upload documents to ground this workspace&apos;s chats.
          </Text>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              {displayFiles.map((f) => (
                <FileCard
                  key={f.id}
                  file={f}
                  removeFile={async (fileId: string) => {
                    if (!currentProjectId) return;
                    await unlinkFileFromProject(currentProjectId, fileId);
                  }}
                  onFileClick={handleOnView}
                  compactImages={compactImages}
                />
              ))}
            </div>
            {variant === "preview" && totalFiles > displayFiles.length && (
              <button
                onClick={() => filesModal.toggle(true)}
                className="mt-2 text-xs font-medium text-text-03 hover:text-text-05 transition-colors"
              >
                View all {totalFiles} files
              </button>
            )}
          </>
        )}
      </div>

      <filesModal.Provider>
        <UserFilesModal
          title="Workspace Files"
          description="Sessions in this workspace can access the files here."
          recentFiles={[...allCurrentProjectFiles]}
          onView={handleOnView}
          handleUploadChange={handleUploadChange}
          onDelete={async (file: ProjectFile) => {
            if (!currentProjectId) return;
            await unlinkFileFromProject(currentProjectId, file.id);
          }}
        />
      </filesModal.Provider>
    </section>
  );
}

/* ── Chat history rail ── */
function ChatHistoryRail({ setTab }: { setTab: (tab: WorkspaceTab) => void }) {
  const { currentProjectDetails } = useProjectsContext();
  const chats = useMemo(() => {
    const sessions = currentProjectDetails?.project?.chat_sessions ?? [];
    return [...sessions]
      .sort(
        (a, b) =>
          new Date(b.time_updated).getTime() -
          new Date(a.time_updated).getTime()
      )
      .slice(0, 5);
  }, [currentProjectDetails?.project?.chat_sessions]);

  return (
    <section className="rounded-2xl border border-border-01 bg-background-tint-01">
      <div className="flex items-center justify-between border-b border-border-01 px-4 py-3">
        <div className="flex items-center gap-2">
          <SectionIcon icon={SvgBubbleText} />
          <div className="text-sm font-semibold text-text-05">Chat history</div>
        </div>
        <button
          onClick={() => setTab("chats")}
          className="text-[11px] text-text-03 hover:text-text-05 transition-colors"
        >
          View all
        </button>
      </div>
      {chats.length === 0 ? (
        <Text as="p" text03 secondaryBody className="px-4 py-3">
          No chats yet.
        </Text>
      ) : (
        <ul className="divide-y divide-border-01">
          {chats.map((chat) => (
            <li key={chat.id} className="group">
              <Link
                href={{ pathname: "/app", query: { chatId: chat.id } }}
                className="block px-4 py-3 hover:bg-background-tint-02 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="truncate text-sm font-medium text-text-04">
                    {chat.name || UNNAMED_CHAT}
                  </div>
                  <SvgChevronRight className="h-3.5 w-3.5 stroke-text-02 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <div className="mt-1 text-[10px] uppercase tracking-wider text-text-03">
                  {formatRelativeTime(chat.time_updated)}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ── Quick actions ── */
function QuickActions({ onNewChat }: { onNewChat?: () => void }) {
  const { currentProjectId } = useProjectsContext();
  const router = useRouter();

  const goWithPrompt = useCallback(
    (prompt?: string) => {
      if (currentProjectId == null) return;
      const params = new URLSearchParams();
      params.set(SEARCH_PARAM_NAMES.PROJECT_ID, String(currentProjectId));
      if (prompt) params.set(SEARCH_PARAM_NAMES.USER_PROMPT, prompt);
      router.push(`/app?${params.toString()}`);
    },
    [currentProjectId, router]
  );

  return (
    <section
      className="rounded-2xl border border-border-01 p-4"
      style={{ backgroundColor: "var(--virtualai-accent-subtle)" }}
    >
      <div className="flex items-center gap-2 text-sm font-semibold text-text-05">
        <SvgSparkle
          className="h-4 w-4 stroke-current"
          style={{ color: "var(--virtualai-accent)" } as React.CSSProperties}
        />
        Quick actions
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <QuickBtn
          icon={SvgPlus}
          label="New chat"
          onClick={onNewChat ?? (() => goWithPrompt())}
        />
        <QuickBtn
          icon={SvgFileText}
          label="Summarize files"
          onClick={() => goWithPrompt("Summarize the files in this workspace.")}
        />
        <QuickBtn
          icon={SvgSearch}
          label="Ask the docs"
          onClick={() =>
            goWithPrompt("Using the files in this workspace, answer: ")
          }
        />
        <QuickBtn
          icon={SvgUserPlus}
          label="Invite member"
          disabled
          tooltip="Member sharing isn't available yet"
        />
      </div>
    </section>
  );
}

function QuickBtn({
  icon: Icon,
  label,
  onClick,
  disabled,
  tooltip,
}: {
  icon: React.FunctionComponent<{ className?: string; style?: React.CSSProperties }>;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  tooltip?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={tooltip}
      className={cn(
        "flex items-center gap-1.5 rounded-lg border border-border-01 bg-background-tint-01 px-2.5 py-2 text-xs text-text-04 transition-colors",
        disabled
          ? "opacity-50 cursor-not-allowed"
          : "hover:bg-background-tint-02 hover:text-text-05"
      )}
    >
      <Icon
        className="h-3.5 w-3.5 stroke-current"
        style={{ color: "var(--virtualai-accent)" }}
      />
      {label}
    </button>
  );
}

export default function WorkspaceDetailBody({
  tab,
  setTab,
  setPresentingDocument,
  projectTokenCount = 0,
  availableContextTokens = 128_000,
  onNewChat,
}: WorkspaceDetailBodyProps) {
  const { currentProjectId } = useProjectsContext();
  if (!currentProjectId) return null;

  const exceedsContextLimit = projectTokenCount > availableContextTokens;

  return (
    <div className="mx-auto w-full max-w-[72rem] px-4 pt-6 pb-10">
      {exceedsContextLimit && (
        <div className="mb-4 rounded-xl border border-border-02 bg-background-tint-02/40 px-4 py-3">
          <Text as="p" text02 secondaryBody>
            This workspace exceeds the model&apos;s context limits. Sessions will
            automatically search for relevant files first before generating
            response.
          </Text>
        </div>
      )}
      {tab === "overview" && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <InstructionsSection />
            <FilesSection
              variant="preview"
              setPresentingDocument={setPresentingDocument}
            />
          </div>
          <aside className="space-y-4">
            <ChatHistoryRail setTab={setTab} />
            <QuickActions onNewChat={onNewChat} />
          </aside>
        </div>
      )}

      {tab === "files" && (
        <FilesSection variant="full" setPresentingDocument={setPresentingDocument} />
      )}

      {tab === "chats" && (
        <div className="rounded-2xl border border-border-01 bg-background-tint-01 p-2">
          <ProjectChatSessionList />
        </div>
      )}
    </div>
  );
}
