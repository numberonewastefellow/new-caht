"use client";

import useSWR from "swr";
import { useContext } from "react";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { SettingsContext } from "@/providers/SettingsProvider";

export interface MinimalTeamSnapshot {
  id: number;
  name: string;
}

// TODO (@raunakab):
// Refactor this hook to live inside of a special `ee` directory.

export default function useShareableTeams() {
  const combinedSettings = useContext(SettingsContext);
  const isPaidEnterpriseFeaturesEnabled =
    combinedSettings && combinedSettings.enterpriseSettings !== null;

  const { data, error, mutate, isLoading } = useSWR<MinimalTeamSnapshot[]>(
    isPaidEnterpriseFeaturesEnabled ? "/api/teams/minimal" : null,
    errorHandlingFetcher
  );

  if (!isPaidEnterpriseFeaturesEnabled) {
    return {
      data: [],
      isLoading: false,
      error: undefined,
      refreshShareableTeams: () => {},
    };
  }

  return {
    data,
    isLoading,
    error,
    refreshShareableTeams: mutate,
  };
}
