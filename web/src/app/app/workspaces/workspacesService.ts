import { ChatFileType, ChatSession } from "../interfaces";

// Generic error handler that avoids exposing server error details
const handleRequestError = (action: string, response: Response) => {
  throw new Error(`${action} failed (Status: ${response.status})`);
};

export interface Workspace {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  user_id: string;
  instructions: string | null;
  chat_sessions: ChatSession[];
}

export interface CategorizedFiles {
  knowledge_files: WorkspaceFile[];
  rejected_files: RejectedFile[];
}

export interface WorkspaceFile {
  id: string;
  name: string;
  workspace_id: number | null;
  user_id: string | null;
  file_id: string;
  created_at: string;
  status: KnowledgeFileStatus;
  file_type: string;
  last_accessed_at: string;
  chat_file_type: ChatFileType;
  token_count: number | null;
  chunk_count: number | null;
  temp_id?: string | null;
}

export interface RejectedFile {
  file_name: string;
  reason: string;
}

export interface KnowledgeFileDeleteResult {
  has_associations: boolean;
  workspace_names: string[];
  assistant_names: string[];
}

export enum KnowledgeFileStatus {
  UPLOADING = "UPLOADING", //UI only
  PROCESSING = "PROCESSING",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
  CANCELED = "CANCELED",
  DELETING = "DELETING",
}

export type WorkspaceDetails = {
  workspace: Workspace;
  files?: WorkspaceFile[];
  persona_id_to_is_default?: Record<number, boolean>;
};

export async function fetchWorkspaces(): Promise<Workspace[]> {
  const response = await fetch("/api/workspaces");
  if (!response.ok) {
    handleRequestError("Fetch workspaces", response);
  }
  return response.json();
}

export async function createWorkspace(name: string): Promise<Workspace> {
  const response = await fetch(
    `/api/workspaces/create?name=${encodeURIComponent(name)}`,
    { method: "POST" }
  );
  if (!response.ok) {
    handleRequestError("Create workspace", response);
  }
  return response.json();
}

export async function uploadFiles(
  files: File[],
  workspaceId?: number | null,
  tempIdMap?: Map<string, string>
): Promise<CategorizedFiles> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  if (workspaceId !== undefined && workspaceId !== null) {
    formData.append("workspace_id", String(workspaceId));
  }
  if (tempIdMap !== undefined && tempIdMap !== null) {
    formData.append(
      "temp_id_map",
      JSON.stringify(Object.fromEntries(tempIdMap))
    );
  }

  const response = await fetch("/api/workspaces/file/upload", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    handleRequestError("Upload files", response);
  }

  return response.json();
}

export async function getRecentFiles(): Promise<WorkspaceFile[]> {
  const response = await fetch(`/api/user/files/recent`);
  if (!response.ok) {
    handleRequestError("Fetch recent files", response);
  }
  return response.json();
}

export async function getFilesInWorkspace(
  workspaceId: number
): Promise<WorkspaceFile[]> {
  const response = await fetch(`/api/workspaces/files/${workspaceId}`);
  if (!response.ok) {
    handleRequestError("Fetch workspace files", response);
  }
  return response.json();
}

export async function getWorkspace(workspaceId: number): Promise<Workspace> {
  const response = await fetch(`/api/workspaces/${workspaceId}`);
  if (!response.ok) {
    handleRequestError("Fetch workspace", response);
  }
  return response.json();
}

export async function renameWorkspace(
  workspaceId: number,
  name: string
): Promise<Workspace> {
  const response = await fetch(`/api/workspaces/${workspaceId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    handleRequestError("Rename workspace", response);
  }
  return response.json();
}

export async function deleteWorkspace(workspaceId: number): Promise<void> {
  const response = await fetch(`/api/workspaces/${workspaceId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    handleRequestError("Delete workspace", response);
  }
}

export async function getWorkspaceInstructions(
  workspaceId: number
): Promise<string | null> {
  const response = await fetch(`/api/workspaces/${workspaceId}/instructions`);
  if (!response.ok) {
    handleRequestError("Fetch workspace instructions", response);
  }
  const data = (await response.json()) as { instructions: string | null };
  return data.instructions ?? null;
}

export async function upsertWorkspaceInstructions(
  workspaceId: number,
  instructions: string
): Promise<string | null> {
  const response = await fetch(`/api/workspaces/${workspaceId}/instructions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instructions }),
  });
  if (!response.ok) {
    handleRequestError("Update workspace instructions", response);
  }
  const data = (await response.json()) as { instructions: string | null };
  return data.instructions ?? null;
}

export async function getWorkspaceDetails(
  workspaceId: number
): Promise<WorkspaceDetails> {
  const response = await fetch(`/api/workspaces/${workspaceId}/details`);
  if (!response.ok) {
    handleRequestError("Fetch workspace details", response);
  }
  return response.json();
}

export async function unlinkFileFromWorkspace(
  workspaceId: number,
  fileId: string
): Promise<Response> {
  const response = await fetch(
    `/api/workspaces/${encodeURIComponent(
      workspaceId
    )}/files/${encodeURIComponent(fileId)}`,
    { method: "DELETE" }
  );
  if (!response.ok) {
    handleRequestError("Unlink file from workspace", response);
  }
  return response;
}

export async function linkFileToWorkspace(
  workspaceId: number,
  fileId: string
): Promise<Response> {
  const response = await fetch(
    `/api/workspaces/${encodeURIComponent(
      workspaceId
    )}/files/${encodeURIComponent(fileId)}`,
    { method: "POST" }
  );
  if (!response.ok) {
    handleRequestError("Link file to workspace", response);
  }
  return response;
}

export async function deleteKnowledgeFile(
  fileId: string
): Promise<KnowledgeFileDeleteResult> {
  const response = await fetch(
    `/api/workspaces/file/${encodeURIComponent(fileId)}`,
    {
      method: "DELETE",
    }
  );
  if (!response.ok) {
    handleRequestError("Delete file", response);
  }
  return (await response.json()) as KnowledgeFileDeleteResult;
}

export async function getKnowledgeFile(fileId: string): Promise<WorkspaceFile> {
  const response = await fetch(
    `/api/workspaces/file/${encodeURIComponent(fileId)}`
  );
  if (!response.ok) {
    handleRequestError("Fetch file", response);
  }
  return response.json();
}

export async function getKnowledgeFileStatuses(
  fileIds: string[]
): Promise<WorkspaceFile[]> {
  const response = await fetch(`/api/workspaces/file/statuses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids: fileIds }),
  });
  if (!response.ok) {
    handleRequestError("Fetch file statuses", response);
  }
  return response.json();
}

export async function getSessionWorkspaceTokenCount(
  chatSessionId: string
): Promise<number> {
  const response = await fetch(
    `/api/workspaces/session/${encodeURIComponent(
      chatSessionId
    )}/token-count`
  );
  if (!response.ok) {
    return 0;
  }
  const data = (await response.json()) as { total_tokens: number };
  return data.total_tokens ?? 0;
}

export async function getWorkspaceFilesForSession(
  chatSessionId: string
): Promise<WorkspaceFile[]> {
  const response = await fetch(
    `/api/workspaces/session/${encodeURIComponent(chatSessionId)}/files`
  );
  if (!response.ok) {
    return [];
  }
  return response.json();
}

export async function getWorkspaceTokenCount(workspaceId: number): Promise<number> {
  const response = await fetch(
    `/api/workspaces/${encodeURIComponent(workspaceId)}/token-count`
  );
  if (!response.ok) {
    return 0;
  }
  const data = (await response.json()) as { total_tokens: number };
  return data.total_tokens ?? 0;
}

export async function getMaxSelectedDocumentTokens(
  personaId: number
): Promise<number> {
  const response = await fetch(
    `/api/converse/max-selected-document-tokens?persona_id=${personaId}`
  );
  if (!response.ok) {
    return 128_000;
  }
  const json = await response.json();
  return (json?.max_tokens as number) ?? 128_000;
}

export async function moveChatSession(
  workspaceId: number,
  chatSessionId: string
): Promise<boolean> {
  const response = await fetch(
    `/api/workspaces/${workspaceId}/move_chat_session`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_session_id: chatSessionId }),
    }
  );
  if (!response.ok) {
    handleRequestError("Move chat session", response);
  }
  return response.ok;
}

export async function removeChatSessionFromWorkspace(
  chatSessionId: string
): Promise<boolean> {
  const response = await fetch(`/api/workspaces/remove_chat_session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_session_id: chatSessionId }),
  });
  if (!response.ok) {
    handleRequestError("Remove chat session from workspace", response);
  }
  return response.ok;
}
