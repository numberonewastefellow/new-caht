"use client";

import useSWR from "swr";
import {
  WorkflowSnapshot,
  WorkflowVersionDetail,
  WorkflowVersionSummary,
} from "@/lib/workflows/interfaces";
import { workflowVersionsUrl } from "@/lib/workflows/api";
import { errorHandlingFetcher } from "@/lib/fetcher";

/**
 * Fetches all workflows accessible to the current user.
 */
export function useWorkflows() {
  const { data, error, mutate } = useSWR<WorkflowSnapshot[]>(
    "/api/workflow",
    errorHandlingFetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  return {
    workflows: data ?? [],
    isLoading: !error && !data,
    error,
    refresh: mutate,
  };
}

/**
 * Fetches a single workflow by ID with full details.
 */
export function useWorkflow(workflowId: number | null) {
  const { data, error, isLoading, mutate } = useSWR<WorkflowSnapshot>(
    workflowId ? `/api/workflow/${workflowId}` : null,
    errorHandlingFetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  return {
    workflow: data ?? null,
    isLoading,
    error,
    refresh: mutate,
  };
}

/**
 * Saved versions of a workflow, newest first.
 */
export function useWorkflowVersions(workflowId: number | null) {
  const { data, error, isLoading, mutate } = useSWR<WorkflowVersionSummary[]>(
    workflowId ? workflowVersionsUrl(workflowId) : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );

  return {
    versions: data ?? [],
    isLoading,
    error,
    refresh: mutate,
  };
}

/**
 * One saved version of a workflow, including its definition.
 */
export function useWorkflowVersion(
  workflowId: number | null,
  version: number | null
) {
  const { data, error, isLoading } = useSWR<WorkflowVersionDetail>(
    workflowId && version
      ? `${workflowVersionsUrl(workflowId)}/${version}`
      : null,
    errorHandlingFetcher,
    // Versions are immutable.
    { revalidateOnFocus: false, revalidateIfStale: false }
  );

  return { detail: data ?? null, isLoading, error };
}
