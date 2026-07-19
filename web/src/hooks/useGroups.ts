"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { Team } from "@/lib/types";
import { useContext } from "react";
import { SettingsContext } from "@/providers/SettingsProvider";

/**
 * Fetches all teams in the organization.
 *
 * Returns team information including team members, curators, and associated resources.
 * Use this for displaying team lists in sharing dialogs, admin panels, or permission
 * management interfaces.
 *
 * Note: This hook only returns data if enterprise features are enabled. In non-enterprise
 * environments, it returns an empty array.
 *
 * @returns Object containing:
 *   - data: Array of Team objects, or undefined while loading
 *   - isLoading: Boolean indicating if data is being fetched
 *   - error: Any error that occurred during fetch
 *   - refreshTeams: Function to manually revalidate the data
 *
 * @example
 * // Fetch teams for sharing dialogs
 * const { data: teamsData, isLoading } = useTeams();
 * if (isLoading) return <Spinner />;
 * return <TeamList teams={teamsData ?? []} />;
 *
 * @example
 * // Fetch teams with manual refresh
 * const { data: teamsData, refreshTeams } = useTeams();
 * // Later...
 * await createNewTeam(...);
 * refreshTeams(); // Refresh the team list
 */
export default function useTeams() {
  const combinedSettings = useContext(SettingsContext);
  const isPaidEnterpriseFeaturesEnabled =
    combinedSettings && combinedSettings.enterpriseSettings !== null;

  const { data, error, mutate, isLoading } = useSWR<Team[]>(
    isPaidEnterpriseFeaturesEnabled ? "/api/teams" : null,
    errorHandlingFetcher
  );

  // If enterprise features are not enabled, return empty array
  if (!isPaidEnterpriseFeaturesEnabled) {
    return {
      data: [],
      isLoading: false,
      error: undefined,
      refreshTeams: () => {},
    };
  }

  return {
    data,
    isLoading,
    error,
    refreshTeams: mutate,
  };
}
