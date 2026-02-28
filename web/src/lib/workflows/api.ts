/**
 * API functions for multi-agent workflow CRUD and execution operations.
 */

import {
  WorkflowCreate,
  WorkflowSnapshot,
  WorkflowUpdate,
  WorkflowExecutionSnapshot,
} from "./interfaces";

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

export async function deleteWorkflow(
  workflowId: number
): Promise<Response> {
  return fetch(`/api/admin/workflow/${workflowId}`, {
    method: "DELETE",
  });
}

export async function backfillWorkflowPersonas(): Promise<Response> {
  return fetch("/api/admin/workflow/backfill-personas", {
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
  const response = await fetch(`/api/workflow/${workflowId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch workflow ${workflowId}: ${response.status}`);
  }
  return response.json();
}

// ========================
// Execution Operations
// ========================

export async function runWorkflow(
  workflowId: number,
  message: string,
  chatSessionId?: number | null
): Promise<Response> {
  return fetch(`/api/workflow/${workflowId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      chat_session_id: chatSessionId ?? null,
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
