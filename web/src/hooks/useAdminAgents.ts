"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { buildApiPath } from "@/lib/urlBuilder";
import { Agent } from "@/app/admin/assistants/interfaces";

interface UseAdminAgentsOptions {
  includeDeleted?: boolean;
  getEditable?: boolean;
  includeDefault?: boolean;
  pageNum?: number;
  pageSize?: number;
  // Server-side search term matched against agent name OR description.
  searchQuery?: string;
}

interface PaginatedAgentsResponse {
  items: Agent[];
  total_items: number;
}

export const useAdminAgents = (options?: UseAdminAgentsOptions) => {
  const {
    includeDeleted = false,
    getEditable = false,
    includeDefault = false,
    pageNum,
    pageSize,
    searchQuery,
  } = options || {};

  // If pageNum and pageSize are provided, use paginated endpoint.
  const usePagination = pageNum !== undefined && pageSize !== undefined;

  const trimmedQuery = searchQuery?.trim();

  const url = usePagination
    ? buildApiPath("/api/admin/agents", {
        include_deleted: includeDeleted,
        get_editable: getEditable,
        include_default: includeDefault,
        page_num: pageNum,
        page_size: pageSize,
        ...(trimmedQuery ? { q: trimmedQuery } : {}),
      })
    : buildApiPath("/api/admin/agent", {
        include_deleted: includeDeleted,
        get_editable: getEditable,
      });

  const { data, error, isLoading, mutate } = useSWR<
    Agent[] | PaginatedAgentsResponse
  >(url, errorHandlingFetcher, { keepPreviousData: true });

  // Handle both paginated and non-paginated responses
  const agents = usePagination
    ? (data as PaginatedAgentsResponse)?.items || []
    : (data as Agent[]) || [];

  const totalItems = usePagination
    ? (data as PaginatedAgentsResponse)?.total_items || 0
    : agents.length;

  return {
    agents,
    totalItems,
    error,
    isLoading,
    refresh: mutate,
  };
};
