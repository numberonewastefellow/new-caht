"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { NODE_TYPES_URL } from "./api";
import type { NodeTypeInfo } from "./interfaces";
import type { NodeCatalog } from "./nodeRegistry";

const EMPTY_CATALOG: NodeCatalog = [];

/**
 * The backend node type catalog (`GET /workflow/node-types`).
 *
 * `catalog` is empty until loaded (or when loading failed); the helpers in
 * `nodeRegistry.ts` treat an empty catalog leniently. `isReady` turns true once
 * the request settled either way, so editors can wait for it before building
 * their node views.
 */
export function useNodeTypes() {
  const { data, error, isLoading } = useSWR<NodeTypeInfo[]>(
    NODE_TYPES_URL,
    errorHandlingFetcher,
    {
      revalidateOnFocus: false,
      // The catalog only changes when the backend is redeployed.
      dedupingInterval: 10 * 60 * 1000,
    }
  );

  return {
    catalog: data ?? EMPTY_CATALOG,
    isLoading,
    isReady: !isLoading,
    error,
  };
}
