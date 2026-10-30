/**
 * API functions for multi-agent workflow CRUD and execution operations.
 */

import {
  NodeTypeInfo,
  NodeUpgradeRequest,
  NodeUpgradeResult,
  WorkflowCreate,
  WorkflowSnapshot,
  WorkflowUpdate,
  WorkflowExecutionSnapshot,
  WorkflowVersionDetail,
  WorkflowVersionSummary,
} from "./interfaces";

// ========================
// URLs (also used as SWR keys)
// ========================

export const NODE_TYPES_URL = "/api/workflow/node-types";
export const workflowUrl = (workflowId: number) =>
  `/api/workflow/${workflowId}`;
export const workflowVersionsUrl = (workflowId: number) =>
  `/api/workflow/${workflowId}/versions`;

// ========================
// Errors
// ========================

/** A failed workflow API call, carrying the server's `detail` message. */
export class WorkflowApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    // Keep `instanceof` working when compiled to ES5.
    Object.setPrototypeOf(this, new.target.prototype);
    this.name = "WorkflowApiError";
    this.status = status;
  }

  /** Someone else saved the workflow since it was loaded. */
  get isVersionConflict(): boolean {
    return this.status === 409;
  }
}

/** Extract a human-readable message from an error response body. */
async function errorDetail(res: Response): Promise<string> {
  const fallback = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      return String(body.detail[0].msg);
    }
    if (typeof body?.message === "string") return body.message;
  } catch {
    // not JSON; keep the generic message
  }
  return fallback;
}

/** Parse a JSON response, throwing a WorkflowApiError when it failed. */
async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) throw new WorkflowApiError(await errorDetail(res), res.status);
  return (await res.json()) as T;
}

function jsonInit(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

/** The message to show a user when saving a workflow failed. */
export function describeSaveError(error: unknown): string {
  if (error instanceof WorkflowApiError && error.isVersionConflict) {
    return (
      "This workflow was changed by someone else since you opened it. " +
      "Reload the page to get the latest version, then re-apply your edits."
    );
  }
  if (error instanceof Error && error.message) return error.message;
  return "Save failed";
}

// ========================
// CRUD Operations (Admin)
// ========================

export async function createWorkflow(
  data: WorkflowCreate
): Promise<Response> {
  return fetch("/api/admin/workflow", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateWorkflow(
  workflowId: number,
  data: WorkflowUpdate
): Promise<Response> {
  return fetch(`/api/admin/workflow/${workflowId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

/**
 * Create (no id) or update a workflow and return the saved workflow.
 * Throws WorkflowApiError with the server's detail on 400/409 etc.
 */
export async function saveWorkflow(
  workflowId: number | null,
  data: WorkflowCreate | WorkflowUpdate
): Promise<WorkflowSnapshot> {
  const res = workflowId
    ? await updateWorkflow(workflowId, data as WorkflowUpdate)
    : await createWorkflow(data as WorkflowCreate);
  return parseJson<WorkflowSnapshot>(res);
}

export async function deleteWorkflow(
  workflowId: number
): Promise<Response> {
  return fetch(`/api/admin/workflow/${workflowId}`, {
    method: "DELETE",
  });
}

export async function backfillWorkflowAgents(): Promise<Response> {
  return fetch("/api/admin/workflow/backfill-agents", {
    method: "POST",
  });
}

// ========================
// Read Operations (User)
// ========================

export async function fetchWorkflows(): Promise<WorkflowSnapshot[]> {
  const response = await fetch("/api/workflow");
  if (!response.ok) {
    throw new Error(`Failed to fetch workflows: ${response.status}`);
  }
  return response.json();
}

export async function fetchWorkflow(
  workflowId: number
): Promise<WorkflowSnapshot> {
  const response = await fetch(workflowUrl(workflowId));
  if (!response.ok) {
    throw new Error(`Failed to fetch workflow ${workflowId}: ${response.status}`);
  }
  return response.json();
}

// ========================
// Node Types
// ========================

/** The node type catalog: every type, version, config schema and capability. */
export async function fetchNodeTypes(): Promise<NodeTypeInfo[]> {
  return parseJson<NodeTypeInfo[]>(await fetch(NODE_TYPES_URL));
}

/**
 * Convert a node's config to the latest version of its type. Nothing is
 * saved; the caller applies the result and it persists on the next save.
 * Throws WorkflowApiError: 409 = breaking change, 404 = unknown type.
 */
export async function upgradeNodeConfig(
  nodeType: string,
  request: NodeUpgradeRequest
): Promise<NodeUpgradeResult> {
  const res = await fetch(
    `${NODE_TYPES_URL}/${encodeURIComponent(nodeType)}/upgrade`,
    jsonInit("POST", request)
  );
  return parseJson<NodeUpgradeResult>(res);
}

// ========================
// Versions
// ========================

/** Saved versions of a workflow, newest first. */
export async function listWorkflowVersions(
  workflowId: number
): Promise<WorkflowVersionSummary[]> {
  return parseJson<WorkflowVersionSummary[]>(
    await fetch(workflowVersionsUrl(workflowId))
  );
}

/** One saved version including its full definition. */
export async function getWorkflowVersion(
  workflowId: number,
  version: number
): Promise<WorkflowVersionDetail> {
  return parseJson<WorkflowVersionDetail>(
    await fetch(`${workflowVersionsUrl(workflowId)}/${version}`)
  );
}

/** Make an earlier version current again (recorded as a new version). */
export async function restoreWorkflowVersion(
  workflowId: number,
  version: number
): Promise<WorkflowSnapshot> {
  const res = await fetch(
    `/api/admin/workflow/${workflowId}/versions/${version}/restore`,
    { method: "POST" }
  );
  return parseJson<WorkflowSnapshot>(res);
}

// ========================
// Execution Operations
// ========================

export async function runWorkflow(
  workflowId: number,
  message: string,
  chatSessionId?: string | null,
  fileDescriptors?: { id: string; type: string; name?: string | null }[]
): Promise<Response> {
  return fetch(`/api/workflow/${workflowId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      chat_session_id: chatSessionId ?? null,
      file_descriptors: fileDescriptors ?? [],
    }),
  });
}

export async function fetchWorkflowExecutions(
  workflowId: number,
  limit: number = 20
): Promise<WorkflowExecutionSnapshot[]> {
  const response = await fetch(
    `/api/workflow/${workflowId}/executions?limit=${limit}`
  );
  if (!response.ok) {
    throw new Error(
      `Failed to fetch executions for workflow ${workflowId}: ${response.status}`
    );
  }
  return response.json();
}
