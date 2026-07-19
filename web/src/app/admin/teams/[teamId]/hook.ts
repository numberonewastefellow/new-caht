import { useTeams } from "@/lib/hooks";

export const useSpecificUserGroup = (groupId: string) => {
  const { data, isLoading, error, refreshTeams } = useTeams();
  const userGroup = data?.find((group) => group.id.toString() === groupId);
  return {
    userGroup,
    isLoading,
    error,
    refreshUserGroup: refreshTeams,
  };
};
