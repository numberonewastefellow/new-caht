"use client";

import useSWR from "swr";
import { WorkflowSnapshot } from "@/lib/workflows/interfaces";
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
