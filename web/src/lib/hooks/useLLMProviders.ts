import useSWR from "swr";
import { LLMProviderDescriptor } from "@/app/admin/configuration/llm/interfaces";
import { errorHandlingFetcher } from "@/lib/fetcher";

export function useLLMProviders(agentId?: number) {
  // agentId can be:
  // - undefined: public providers only (/api/llm/provider)
  // - number (agentId): agent-specific providers with RBAC enforcement

  const url =
    typeof agentId === "number"
      ? `/api/llm/agent/${agentId}/providers`
      : "/api/llm/provider";

  const { data, error, mutate } = useSWR<LLMProviderDescriptor[] | undefined>(
    url,
    errorHandlingFetcher,
    {
      revalidateOnFocus: false, // Cache aggressively for performance
      dedupingInterval: 60000, // Dedupe requests within 1 minute
    }
  );

  return {
    llmProviders: data,
    isLoading: !error && !data,
    error,
    refetch: mutate,
  };
}
