import { useTeams } from "@/lib/hooks";

export const useSpecificTeam = (teamId: string) => {
  const { data, isLoading, error, refreshTeams } = useTeams();
  const team = data?.find((group) => group.id.toString() === teamId);
  return {
    team,
    isLoading,
    error,
    refreshTeam: refreshTeams,
  };
};
