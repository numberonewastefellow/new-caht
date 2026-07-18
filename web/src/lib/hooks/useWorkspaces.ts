import useSWR from "swr";
import { Workspace } from "@/app/app/workspaces/workspacesService";
import { errorHandlingFetcher } from "@/lib/fetcher";

export function useWorkspaces() {
  const { data, error, mutate } = useSWR<Workspace[]>(
    "/api/workspaces",
    errorHandlingFetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
    }
  );

  return {
    workspaces: data ?? [],
    isLoading: !error && !data,
    error,
    refreshWorkspaces: mutate,
  };
}
