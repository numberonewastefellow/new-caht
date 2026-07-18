"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useRef,
  ReactNode,
  Dispatch,
  SetStateAction,
} from "react";
import type {
  CategorizedFiles,
  Workspace,
  WorkspaceFile,
  KnowledgeFileDeleteResult,
} from "@/app/app/workspaces/workspacesService";
import {
  fetchWorkspaces as svcFetchWorkspaces,
  createWorkspace as svcCreateWorkspace,
  uploadFiles as svcUploadFiles,
  getRecentFiles as svcGetRecentFiles,
  getFilesInWorkspace as svcGetFilesInWorkspace,
  getWorkspace as svcGetWorkspace,
  getWorkspaceInstructions as svcGetWorkspaceInstructions,
  upsertWorkspaceInstructions as svcUpsertWorkspaceInstructions,
  getWorkspaceDetails as svcGetWorkspaceDetails,
  WorkspaceDetails,
  renameWorkspace as svcRenameWorkspace,
  deleteWorkspace as svcDeleteWorkspace,
  deleteKnowledgeFile as svcDeleteKnowledgeFile,
  getKnowledgeFileStatuses as svcGetKnowledgeFileStatuses,
  unlinkFileFromWorkspace as svcUnlinkFileFromWorkspace,
  linkFileToWorkspace as svcLinkFileToWorkspace,
  KnowledgeFileStatus,
} from "@/app/app/workspaces/workspacesService";
import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { useAppRouter } from "@/hooks/appNavigation";
import { ChatFileType } from "@/app/app/interfaces";
import { toast } from "@/hooks/useToast";
import { useWorkspaces } from "@/lib/hooks/useWorkspaces";

export type { Workspace, WorkspaceFile } from "@/app/app/workspaces/workspacesService";

// Helper to generate unique temp IDs
const generateTempId = () => {
  try {
    return `temp_${crypto.randomUUID()}`;
  } catch {
    // Extremely unlikely fallback
    return `temp_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
  }
};

// Create optimistic file from File object
const createOptimisticFile = (
  file: File,
  workspaceId: number | null = null
): WorkspaceFile => {
  const tempId = generateTempId();
  return {
    id: tempId, // Use temp ID as the actual ID initially
    file_id: tempId,
    name: file.name,
    workspace_id: workspaceId,
    user_id: null,
    created_at: new Date().toISOString(),
    status: KnowledgeFileStatus.UPLOADING,
    file_type: file.type,
    last_accessed_at: new Date().toISOString(),
    chat_file_type: ChatFileType.DOCUMENT,
    token_count: null,
    chunk_count: null,
    temp_id: tempId, // Store temp_id for mapping later
  };
};

function buildFileKey(file: File): string {
  const namePrefix = (file.name ?? "").slice(0, 50);
  return `${file.size}|${namePrefix}`;
}

interface WorkspacesContextType {
  workspaces: Workspace[];
  recentFiles: WorkspaceFile[];
  currentWorkspaceDetails: WorkspaceDetails | null;
  currentWorkspaceId: number | null;
  currentMessageFiles: WorkspaceFile[];
  beginUpload: (
    files: File[],
    workspaceId?: number | null,
    onSuccess?: (uploaded: CategorizedFiles) => void,
    onFailure?: (failedTempIds: string[]) => void
  ) => Promise<WorkspaceFile[]>;
  allRecentFiles: WorkspaceFile[];
  allCurrentWorkspaceFiles: WorkspaceFile[];
  isLoadingWorkspaceDetails: boolean;
  setCurrentMessageFiles: Dispatch<SetStateAction<WorkspaceFile[]>>;
  upsertInstructions: (instructions: string) => Promise<void>;
  fetchWorkspaces: () => Promise<Workspace[]>;
  createWorkspace: (name: string) => Promise<Workspace>;
  renameWorkspace: (workspaceId: number, name: string) => Promise<Workspace>;
  deleteWorkspace: (workspaceId: number) => Promise<void>;
  uploadFiles: (
    files: File[],
    workspaceId?: number | null
  ) => Promise<CategorizedFiles>;
  getRecentFiles: () => Promise<WorkspaceFile[]>;
  getFilesInWorkspace: (workspaceId: number) => Promise<WorkspaceFile[]>;
  refreshCurrentWorkspaceDetails: () => Promise<void>;
  refreshRecentFiles: () => Promise<void>;
  deleteKnowledgeFile: (fileId: string) => Promise<KnowledgeFileDeleteResult>;
  unlinkFileFromWorkspace: (workspaceId: number, fileId: string) => Promise<void>;
  linkFileToWorkspace?: (workspaceId: number, file: WorkspaceFile) => void;
  lastFailedFiles: WorkspaceFile[];
  clearLastFailedFiles: () => void;
}

const WorkspacesContext = createContext<WorkspacesContextType | undefined>(
  undefined
);

interface WorkspacesProviderProps {
  children: ReactNode;
}

export function WorkspacesProvider({ children }: WorkspacesProviderProps) {
  // Use SWR hook for workspaces list - no more SSR initial data
  const { workspaces, refreshWorkspaces } = useWorkspaces();
  const [recentFiles, setRecentFiles] = useState<WorkspaceFile[]>([]);
  const [currentWorkspaceDetails, setCurrentWorkspaceDetails] =
    useState<WorkspaceDetails | null>(null);
  const searchParams = useSearchParams();
  const currentWorkspaceIdRaw = searchParams.get(SEARCH_PARAM_NAMES.PROJECT_ID);
  const currentWorkspaceId = currentWorkspaceIdRaw
    ? Number.parseInt(currentWorkspaceIdRaw)
    : null;
  const [currentMessageFiles, setCurrentMessageFiles] = useState<WorkspaceFile[]>(
    []
  );
  const pollIntervalRef = useRef<number | null>(null);
  const isPollingRef = useRef<boolean>(false);
  const [lastFailedFiles, setLastFailedFiles] = useState<WorkspaceFile[]>([]);
  const [trackedUploadIds, setTrackedUploadIds] = useState<Set<string>>(
    new Set()
  );
  const [allRecentFiles, setAllRecentFiles] = useState<WorkspaceFile[]>([]);
  const [allCurrentWorkspaceFiles, setAllCurrentWorkspaceFiles] = useState<
    WorkspaceFile[]
  >([]);
  const [isLoadingWorkspaceDetails, setIsLoadingWorkspaceDetails] = useState(false);
  const workspaceToUploadFilesMapRef = useRef<Map<number, WorkspaceFile[]>>(
    new Map()
  );
  const route = useAppRouter();
  const router = useRouter();

  // Use SWR's mutate to refresh workspaces - returns the new data
  const fetchWorkspaces = useCallback(async (): Promise<Workspace[]> => {
    try {
      const result = await refreshWorkspaces();
      return result ?? [];
    } catch (err) {
      return [];
    }
  }, [refreshWorkspaces]);

  // Load full details for current workspace
  const refreshCurrentWorkspaceDetails = useCallback(async () => {
    if (currentWorkspaceId) {
      setIsLoadingWorkspaceDetails(true);
      try {
        const details = await svcGetWorkspaceDetails(currentWorkspaceId);
        await fetchWorkspaces();
        setCurrentWorkspaceDetails(details);
        setAllCurrentWorkspaceFiles(details.files || []);
        if (workspaceToUploadFilesMapRef.current.has(currentWorkspaceId)) {
          setAllCurrentWorkspaceFiles((prev) => [
            ...prev,
            ...(workspaceToUploadFilesMapRef.current.get(currentWorkspaceId) || []),
          ]);
        }
      } catch (err) {
        // A soft-deleted or otherwise inaccessible workspace returns 404 from the
        // details endpoint. Don't render it — tell the user and send them back to
        // the workspaces dashboard.
        const notFound =
          err instanceof Error && err.message.includes("(Status: 404)");
        if (notFound) {
          setCurrentWorkspaceDetails(null);
          setAllCurrentWorkspaceFiles([]);
          toast.warning("This workspace is no longer available");
          router.push("/app/workspaces" as Route);
        }
      } finally {
        setIsLoadingWorkspaceDetails(false);
      }
    }
  }, [
    fetchWorkspaces,
    currentWorkspaceId,
    setCurrentWorkspaceDetails,
    workspaceToUploadFilesMapRef,
    router,
  ]);

  const upsertInstructions = useCallback(
    async (instructions: string) => {
      if (!currentWorkspaceId) {
        throw new Error("No workspace selected");
      }
      await svcUpsertWorkspaceInstructions(currentWorkspaceId, instructions);
      await refreshCurrentWorkspaceDetails();
    },
    [currentWorkspaceId, refreshCurrentWorkspaceDetails]
  );

  const createWorkspace = useCallback(
    async (name: string): Promise<Workspace> => {
      try {
        const workspace: Workspace = await svcCreateWorkspace(name);
        // Navigate to the newly created workspace's page
        route({ workspaceId: workspace.id });
        // Refresh list to keep order consistent with backend
        await fetchWorkspaces();
        return workspace;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to create workspace";
        throw err;
      }
    },
    [fetchWorkspaces, route]
  );

  const renameWorkspace = useCallback(
    async (workspaceId: number, name: string): Promise<Workspace> => {
      // Optimistically update workspace details UI if this is the current workspace
      if (currentWorkspaceId === workspaceId) {
        setCurrentWorkspaceDetails((prev) =>
          prev ? { ...prev, workspace: { ...prev.workspace, name } } : prev
        );
      }

      try {
        const updated = await svcRenameWorkspace(workspaceId, name);
        // Refresh to get canonical state from server (SWR handles workspaces list)
        await fetchWorkspaces();
        if (currentWorkspaceId === workspaceId) {
          await refreshCurrentWorkspaceDetails();
        }
        return updated;
      } catch (err) {
        // Refresh to restore on failure
        await fetchWorkspaces();
        if (currentWorkspaceId === workspaceId) {
          await refreshCurrentWorkspaceDetails();
        }
        const message =
          err instanceof Error ? err.message : "Failed to rename workspace";
        throw err;
      }
    },
    [fetchWorkspaces, currentWorkspaceId, refreshCurrentWorkspaceDetails]
  );

  const deleteWorkspace = useCallback(
    async (workspaceId: number): Promise<void> => {
      try {
        await svcDeleteWorkspace(workspaceId);
        await fetchWorkspaces();
        if (currentWorkspaceId === workspaceId) {
          setCurrentWorkspaceDetails(null);
          setAllCurrentWorkspaceFiles([]);
          workspaceToUploadFilesMapRef.current.delete(workspaceId);
          router.push("/app/workspaces" as Route);
        }
      } catch (err) {
        throw err;
      }
    },
    [fetchWorkspaces, currentWorkspaceId, workspaceToUploadFilesMapRef, router]
  );

  const getRecentFiles = useCallback(async (): Promise<WorkspaceFile[]> => {
    try {
      const data: WorkspaceFile[] = await svcGetRecentFiles();
      return data;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to fetch recent files";
      return [];
    }
  }, []);

  const refreshRecentFiles = useCallback(async () => {
    const files = await getRecentFiles();
    setRecentFiles(files);
  }, [getRecentFiles]);

  const getTempIdMap = (files: File[], optimisticFiles: WorkspaceFile[]) => {
    const tempIdMap = new Map<string, string>();
    for (const f of files) {
      const tempId = optimisticFiles.find((o) => o.name === f.name)?.temp_id;
      if (tempId) {
        tempIdMap.set(buildFileKey(f), tempId);
      }
    }
    return tempIdMap;
  };

  const removeOptimisticFilesByTempIds = useCallback(
    (optimisticTempIds: Set<string>, workspaceId?: number | null) => {
      // Remove from recent optimistic list
      setAllRecentFiles((prev) =>
        prev.filter((f) => !f.temp_id || !optimisticTempIds.has(f.temp_id))
      );

      // Remove from current message files if present
      setCurrentMessageFiles((prev) =>
        prev.filter((f) => !f.temp_id || !optimisticTempIds.has(f.temp_id))
      );

      // Remove from workspace optimistic list
      if (workspaceId) {
        setAllCurrentWorkspaceFiles((prev) =>
          prev.filter((f) => !f.temp_id || !optimisticTempIds.has(f.temp_id))
        );

        // Clear the tracked optimistic files for this workspace
        let workspaceIdToFiles: WorkspaceFile[] =
          workspaceToUploadFilesMapRef.current.get(workspaceId) || [];
        workspaceIdToFiles = workspaceIdToFiles.filter(
          (f: WorkspaceFile) => !f.temp_id || !optimisticTempIds.has(f.temp_id)
        );
        workspaceToUploadFilesMapRef.current.set(workspaceId, workspaceIdToFiles);
      }
    },
    [workspaceToUploadFilesMapRef]
  );

  const beginUpload = useCallback(
    async (
      files: File[],
      workspaceId?: number | null,
      onSuccess?: (uploaded: CategorizedFiles) => void,
      onFailure?: (failedTempIds: string[]) => void
    ): Promise<WorkspaceFile[]> => {
      const optimisticFiles = files.map((f) =>
        createOptimisticFile(f, workspaceId)
      );
      const tempIdMap = getTempIdMap(files, optimisticFiles);
      setAllRecentFiles((prev) => [...optimisticFiles, ...prev]);
      if (workspaceId) {
        setAllCurrentWorkspaceFiles((prev) => [...optimisticFiles, ...prev]);
        workspaceToUploadFilesMapRef.current.set(workspaceId, optimisticFiles);
      }
      svcUploadFiles(files, workspaceId, tempIdMap)
        .then((uploaded) => {
          const uploadedFiles = uploaded.knowledge_files || [];
          const tempIdToUploadedFileMap = new Map(
            uploadedFiles.map((f) => [f.temp_id, f])
          );

          setAllRecentFiles((prev) =>
            prev.map((f) => {
              if (f.temp_id) {
                const u = tempIdToUploadedFileMap.get(f.temp_id);
                return u ? { ...f, ...u } : f;
              }
              return f;
            })
          );
          setCurrentMessageFiles((prev) =>
            prev.map((f) => {
              if (f.temp_id) {
                const u = tempIdToUploadedFileMap.get(f.temp_id);
                return u ? { ...f, ...u } : f;
              }
              return f;
            })
          );
          if (workspaceId) {
            setAllCurrentWorkspaceFiles((prev) =>
              prev.map((f) => {
                if (f.temp_id) {
                  const u = tempIdToUploadedFileMap.get(f.temp_id);
                  return u ? { ...f, ...u } : f;
                }
                return f;
              })
            );
            workspaceToUploadFilesMapRef.current.set(workspaceId, []);
          }
          const rejected_files = uploaded.rejected_files || [];

          if (rejected_files.length > 0) {
            const uniqueReasons = new Set(
              rejected_files.map((rejected_file) => rejected_file.reason)
            );
            const detailsParts = Array.from(uniqueReasons);

            toast.warning(
              `Some files were not uploaded. ${detailsParts.join(" | ")}`
            );

            const failedNameSet = new Set<string>(
              rejected_files.map((file) => file.file_name)
            );
            const failedTempIds = Array.from(
              new Set(
                optimisticFiles
                  .filter((f) => f.temp_id && failedNameSet.has(f.name))
                  .map((f) => f.temp_id as string)
              )
            );
            removeOptimisticFilesByTempIds(new Set(failedTempIds), workspaceId);
            if (failedTempIds.length > 0) {
              onFailure?.(failedTempIds);
            }
          }
          if (uploadedFiles.length > 0) {
            setTrackedUploadIds((prev) => {
              const next = new Set(prev);
              for (const f of uploadedFiles) next.add(f.id);
              return next;
            });
          }
          onSuccess?.(uploaded);
        })
        .catch((err) => {
          // Roll back optimistic inserts on failure
          const optimisticTempIds = new Set(
            optimisticFiles
              .map((f) => f.temp_id)
              .filter((id): id is string => Boolean(id))
          );

          removeOptimisticFilesByTempIds(optimisticTempIds, workspaceId);

          toast.error("Failed to upload files");

          onFailure?.(Array.from(optimisticTempIds));
        })
        .finally(() => {
          if (workspaceId && currentWorkspaceId === workspaceId) {
            refreshCurrentWorkspaceDetails();
          }
          refreshRecentFiles();
        });
      return optimisticFiles;
    },
    [
      currentWorkspaceId,
      refreshCurrentWorkspaceDetails,
      refreshRecentFiles,
      removeOptimisticFilesByTempIds,
    ]
  );

  const uploadFiles = useCallback(
    async (
      files: File[],
      workspaceId?: number | null
    ): Promise<CategorizedFiles> => {
      try {
        const uploaded: CategorizedFiles = await svcUploadFiles(
          files,
          workspaceId
        );
        const uploadedFiles = uploaded.knowledge_files || [];
        // Track these uploaded file IDs for targeted polling
        if (uploadedFiles.length > 0) {
          setTrackedUploadIds((prev) => {
            const next = new Set(prev);
            for (const f of uploadedFiles) next.add(f.id);
            return next;
          });
        }

        // Refresh canonical sources instead of manual merges
        if (workspaceId && currentWorkspaceId === workspaceId) {
          await refreshCurrentWorkspaceDetails();
        }
        await refreshRecentFiles();
        return uploaded;
      } catch (err) {
        throw err;
      }
    },
    [currentWorkspaceId, refreshCurrentWorkspaceDetails, refreshRecentFiles]
  );

  const getFilesInWorkspace = useCallback(
    async (workspaceId: number): Promise<WorkspaceFile[]> => {
      try {
        const data: WorkspaceFile[] = await svcGetFilesInWorkspace(workspaceId);
        return data;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to fetch workspace files";
        return [];
      }
    },
    []
  );

  useEffect(() => {
    // Initial load - only fetch recent files since workspaces come from props
    getRecentFiles().then((recent) => {
      setRecentFiles(recent);
      setAllRecentFiles(recent);
    });
  }, [getRecentFiles]);

  useEffect(() => {
    setAllRecentFiles((prev) =>
      prev.map((f) => {
        const newFile = recentFiles.find((f2) => f2.id === f.id);
        return newFile ? { ...f, ...newFile } : f;
      })
    );
  }, [recentFiles]);

  // Clear workspace details when switching workspaces to show skeleton
  useEffect(() => {
    setCurrentWorkspaceDetails(null);
    setAllCurrentWorkspaceFiles([]);
  }, [currentWorkspaceId]);

  useEffect(() => {
    if (currentWorkspaceId) {
      refreshCurrentWorkspaceDetails();
    }
  }, [currentWorkspaceId, refreshCurrentWorkspaceDetails]);

  // Targeted polling for tracked uploaded files only
  useEffect(() => {
    const ids = Array.from(trackedUploadIds);
    const shouldPoll = ids.length > 0;

    const poll = async () => {
      if (isPollingRef.current) return;
      isPollingRef.current = true;
      try {
        const statuses = await svcGetKnowledgeFileStatuses(ids);
        if (!statuses || statuses.length === 0) return;

        // Build maps for quick lookup
        const statusById = new Map(statuses.map((f) => [f.id, f]));

        // Update currentMessageFiles inline based on polled statuses
        setCurrentMessageFiles((prev) => {
          let changed = false;
          const next: WorkspaceFile[] = [];
          const newlyFailedLocal: WorkspaceFile[] = [];
          for (const f of prev) {
            const latest = statusById.get(f.id);
            if (latest) {
              const latestStatus = String(latest.status).toLowerCase();
              if (latestStatus === "failed") {
                if (String(f.status).toLowerCase() !== "failed") {
                  newlyFailedLocal.push(latest);
                }
                changed = true;
                continue;
              }
              if (
                latest.status !== f.status ||
                latest.name !== f.name ||
                latest.file_type !== f.file_type
              ) {
                next.push({ ...f, ...latest } as WorkspaceFile);
                changed = true;
                continue;
              }
            }
            next.push(f);
          }
          if (newlyFailedLocal.length > 0) {
            setLastFailedFiles(newlyFailedLocal);
          }
          return changed || next.length !== prev.length ? next : prev;
        });

        // Update currentWorkspaceDetails.files with latest statuses
        setCurrentWorkspaceDetails((prev) => {
          if (!prev || !prev.files || prev.files.length === 0) return prev;
          let changed = false;
          const nextFiles = prev.files.map((f) => {
            const latest = statusById.get(f.id);
            if (latest) {
              if (
                latest.status !== f.status ||
                latest.name !== f.name ||
                latest.file_type !== f.file_type
              ) {
                changed = true;
                return { ...f, ...latest } as WorkspaceFile;
              }
            }
            return f;
          });
          return changed
            ? ({ ...prev, files: nextFiles } as WorkspaceDetails)
            : prev;
        });

        // Update recent files list inline as well
        setRecentFiles((prev) => {
          if (prev.length === 0) return prev;
          let changed = false;
          const map = new Map(prev.map((f) => [f.id, f]));
          for (const latest of statuses) {
            const id = latest.id;
            if (map.has(id)) {
              const prevVal = map.get(id)!;
              if (
                latest.status !== prevVal.status ||
                latest.name !== prevVal.name ||
                latest.file_type !== prevVal.file_type
              ) {
                map.set(id, latest);
                changed = true;
              }
            }
          }
          return changed ? Array.from(map.values()) : prev;
        });

        // Remove completed/failed from tracking
        const remaining = new Set(trackedUploadIds);
        const newlyFailed: WorkspaceFile[] = [];
        for (const f of statuses) {
          const s = String(f.status).toLowerCase();
          if (s === "completed") {
            remaining.delete(f.id);
          } else if (s === "failed") {
            remaining.delete(f.id);
            newlyFailed.push(f);
          }
        }
        if (newlyFailed.length > 0) {
          setLastFailedFiles(newlyFailed);
        }
        const trackingChanged = remaining.size !== trackedUploadIds.size;
        if (trackingChanged) {
          setTrackedUploadIds(remaining);
        }

        // If all tracked uploads finished (completed or failed), do a single refresh
        if (remaining.size === 0) {
          if (currentWorkspaceId) {
            await refreshCurrentWorkspaceDetails();
          }
          await refreshRecentFiles();
        }
      } finally {
        isPollingRef.current = false;
      }
    };

    if (shouldPoll && pollIntervalRef.current === null) {
      // Kick once immediately, then start interval
      poll();
      pollIntervalRef.current = window.setInterval(poll, 3000);
    }

    if (!shouldPoll && pollIntervalRef.current !== null) {
      window.clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    return () => {
      if (pollIntervalRef.current !== null) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [
    trackedUploadIds,
    currentWorkspaceId,
    refreshCurrentWorkspaceDetails,
    refreshRecentFiles,
  ]);

  const value: WorkspacesContextType = useMemo(
    () => ({
      workspaces,
      recentFiles,
      currentWorkspaceDetails,
      currentWorkspaceId,
      currentMessageFiles,
      allRecentFiles,
      allCurrentWorkspaceFiles,
      isLoadingWorkspaceDetails,
      beginUpload,
      setCurrentMessageFiles,
      upsertInstructions,
      fetchWorkspaces,
      createWorkspace,
      renameWorkspace,
      deleteWorkspace,
      uploadFiles,
      getRecentFiles,
      getFilesInWorkspace,
      refreshCurrentWorkspaceDetails,
      refreshRecentFiles,
      lastFailedFiles,
      clearLastFailedFiles: () => setLastFailedFiles([]),
      deleteKnowledgeFile: async (fileId: string) => {
        const result = await svcDeleteKnowledgeFile(fileId);
        // If no associations, backend enqueues deletion and status moves to DELETING; refresh lists
        if (!result.has_associations) {
          if (currentWorkspaceId) {
            await refreshCurrentWorkspaceDetails();
          }
          await refreshRecentFiles();
        }
        return result;
      },
      unlinkFileFromWorkspace: async (workspaceId: number, fileId: string) => {
        const file = allCurrentWorkspaceFiles.find((f) => f.id === fileId);
        if (!file) return;
        setAllCurrentWorkspaceFiles((prev) =>
          prev.filter((f) => f.id !== file.id)
        );
        svcUnlinkFileFromWorkspace(workspaceId, file.id).then(async (result) => {
          if (result.ok) {
            if (currentWorkspaceId === workspaceId) {
              await refreshCurrentWorkspaceDetails();
            }
            await refreshRecentFiles();
          } else {
            if (currentWorkspaceId === workspaceId) {
              setAllCurrentWorkspaceFiles((prev) => [file, ...prev]);
            }
          }
        });
      },
      linkFileToWorkspace: async (workspaceId: number, file: WorkspaceFile) => {
        const existing = allCurrentWorkspaceFiles.find((f) => f.id === file.id);
        if (existing) return;
        setAllCurrentWorkspaceFiles((prev) => [file, ...prev]);
        svcLinkFileToWorkspace(workspaceId, file.id).then(async (result) => {
          if (result.ok) {
            if (currentWorkspaceId === workspaceId) {
              await refreshCurrentWorkspaceDetails();
            }
            await refreshRecentFiles();
          } else {
            if (currentWorkspaceId === workspaceId) {
              setAllCurrentWorkspaceFiles((prev) =>
                prev.filter((f) => f.id !== file.id)
              );
            }
          }
        });
      },
    }),
    [
      workspaces,
      recentFiles,
      currentWorkspaceDetails,
      currentWorkspaceId,
      currentMessageFiles,
      allRecentFiles,
      allCurrentWorkspaceFiles,
      isLoadingWorkspaceDetails,
      beginUpload,
      setCurrentMessageFiles,
      upsertInstructions,
      fetchWorkspaces,
      createWorkspace,
      renameWorkspace,
      deleteWorkspace,
      uploadFiles,
      getRecentFiles,
      getFilesInWorkspace,
      refreshCurrentWorkspaceDetails,
      refreshRecentFiles,
      lastFailedFiles,
    ]
  );

  return (
    <WorkspacesContext.Provider value={value}>
      {children}
    </WorkspacesContext.Provider>
  );
}

export function useWorkspacesContext(): WorkspacesContextType {
  const ctx = useContext(WorkspacesContext);
  if (!ctx) {
    throw new Error(
      "useWorkspacesContext must be used within a WorkspacesProvider"
    );
  }
  return ctx;
}
