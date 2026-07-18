"use client";

import { SEARCH_PARAM_NAMES } from "@/app/app/services/searchParams";
import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { useCallback } from "react";

interface UseAppRouterProps {
  chatSessionId?: string;
  agentId?: number;
  workspaceId?: number;
  assistantId?: number;
}

export function useAppRouter() {
  const router = useRouter();
  return useCallback(
    ({
      chatSessionId,
      agentId,
      workspaceId,
      assistantId,
    }: UseAppRouterProps = {}) => {
      const finalParams = [];

      if (chatSessionId)
        finalParams.push(`${SEARCH_PARAM_NAMES.CHAT_ID}=${chatSessionId}`);
      else if (agentId)
        finalParams.push(`${SEARCH_PARAM_NAMES.AGENT_ID}=${agentId}`);
      else if (workspaceId)
        finalParams.push(`${SEARCH_PARAM_NAMES.PROJECT_ID}=${workspaceId}`);
      else if (assistantId)
        finalParams.push(`${SEARCH_PARAM_NAMES.AGENT_ID}=${assistantId}`);

      const finalString = finalParams.join("&");
      const finalUrl = `/app?${finalString}`;

      router.push(finalUrl as Route);
    },
    [router]
  );
}

export function useAppParams() {
  const searchParams = useSearchParams();
  return useCallback((name: string) => searchParams.get(name), [searchParams]);
}
