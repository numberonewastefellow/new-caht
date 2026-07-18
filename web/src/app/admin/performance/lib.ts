import { errorHandlingFetcher } from "@/lib/fetcher";
import useSWR, { mutate } from "swr";
import { OmBotAnalytics, QueryAnalytics, UserAnalytics } from "./usage/types";
import { useState } from "react";
import { buildApiPath } from "@/lib/urlBuilder";

import {
  convertDateToEndOfDay,
  convertDateToStartOfDay,
  getXDaysAgo,
} from "../../../components/dateRangeSelectors/dateUtils";
import { THIRTY_DAYS } from "../../../components/dateRangeSelectors/AdminDateRangeSelector";
import { DateRangePickerValue } from "@/components/dateRangeSelectors/AdminDateRangeSelector";

export const useTimeRange = () => {
  return useState<DateRangePickerValue>({
    to: new Date(),
    from: getXDaysAgo(30),
    selectValue: THIRTY_DAYS,
  });
};

export const useQueryAnalytics = (timeRange: DateRangePickerValue) => {
  const url = buildApiPath("/api/analytics/admin/query", {
    start: convertDateToStartOfDay(timeRange.from)?.toISOString(),
    end: convertDateToEndOfDay(timeRange.to)?.toISOString(),
  });
  const swrResponse = useSWR<QueryAnalytics[]>(url, errorHandlingFetcher);

  return {
    ...swrResponse,
    refreshQueryAnalytics: () => mutate(url),
  };
};

export const useUserAnalytics = (timeRange: DateRangePickerValue) => {
  const url = buildApiPath("/api/analytics/admin/user", {
    start: convertDateToStartOfDay(timeRange.from)?.toISOString(),
    end: convertDateToEndOfDay(timeRange.to)?.toISOString(),
  });
  const swrResponse = useSWR<UserAnalytics[]>(url, errorHandlingFetcher);

  return {
    ...swrResponse,
    refreshUserAnalytics: () => mutate(url),
  };
};

export const useOnyxBotAnalytics = (timeRange: DateRangePickerValue) => {
  const url = buildApiPath("/api/analytics/admin/onyxbot", {
    start: convertDateToStartOfDay(timeRange.from)?.toISOString(),
    end: convertDateToEndOfDay(timeRange.to)?.toISOString(),
  });
  const swrResponse = useSWR<OmBotAnalytics[]>(url, errorHandlingFetcher); // TODO

  return {
    ...swrResponse,
    refreshOnyxBotAnalytics: () => mutate(url),
  };
};

export function getDatesList(startDate: Date): string[] {
  const datesList: string[] = [];
  const endDate = new Date(); // current date

  for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().split("T")[0]; // convert date object to 'YYYY-MM-DD' format
    if (dateStr !== undefined) {
      datesList.push(dateStr);
    }
  }

  return datesList;
}

export interface AgentMessageAnalytics {
  total_messages: number;
  date: string;
  agent_id: number;
}

export interface AgentSnapshot {
  id: number;
  name: string;
  description: string;
  is_visible: boolean;
  is_public: boolean;
}

export const useAgentMessages = (
  agentId: number | undefined,
  timeRange: DateRangePickerValue
) => {
  const url = buildApiPath(`/api/analytics/admin/agent/messages`, {
    agent_id: agentId?.toString(),
    start: convertDateToStartOfDay(timeRange.from)?.toISOString(),
    end: convertDateToEndOfDay(timeRange.to)?.toISOString(),
  });

  const { data, error, isLoading } = useSWR<AgentMessageAnalytics[]>(
    agentId !== undefined ? url : null,
    errorHandlingFetcher
  );

  return {
    data,
    error,
    isLoading,
    refreshAgentMessages: () => mutate(url),
  };
};

export interface AgentUniqueUserAnalytics {
  unique_users: number;
  date: string;
  agent_id: number;
}

export const useAgentUniqueUsers = (
  agentId: number | undefined,
  timeRange: DateRangePickerValue
) => {
  const url = buildApiPath(`/api/analytics/admin/agent/unique-users`, {
    agent_id: agentId?.toString(),
    start: convertDateToStartOfDay(timeRange.from)?.toISOString(),
    end: convertDateToEndOfDay(timeRange.to)?.toISOString(),
  });

  const { data, error, isLoading } = useSWR<AgentUniqueUserAnalytics[]>(
    agentId !== undefined ? url : null,
    errorHandlingFetcher
  );

  return {
    data,
    error,
    isLoading,
    refreshAgentUniqueUsers: () => mutate(url),
  };
};
