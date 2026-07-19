"use client";

import { useEffect, useState, useMemo } from "react";

import { ThreeDotsLoader } from "@/components/Loading";
import { getDatesList } from "@/app/admin/performance/lib";
import {
  AdminDateRangeSelector,
  DateRange,
} from "@/components/dateRangeSelectors/AdminDateRangeSelector";
import { useAgents } from "@/hooks/useAgents";
import AgentAvatar from "@/refresh-components/avatars/AgentAvatar";
import CardSection from "@/components/admin/CardSection";
import Text from "@/refresh-components/texts/Text";
import { TimeSeriesChart } from "@/app/admin/performance/analytics/charts";

type AssistantDailyUsageEntry = {
  date: string;
  total_messages: number;
  total_unique_users: number;
};

type AssistantStatsResponse = {
  daily_stats: AssistantDailyUsageEntry[];
  total_messages: number;
  total_unique_users: number;
};

const CHART_SERIES = [
  { key: "Messages", label: "Messages" },
  { key: "Unique Users", label: "Unique Users" },
];

/** A single KPI tile — accent-tinted number over a muted label. */
function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <CardSection className="flex flex-col gap-1">
      <Text mainUiMuted text04>
        {label}
      </Text>
      <span
        className="text-3xl font-semibold tabular-nums"
        style={{ color: "var(--virtualai-accent, var(--theme-primary-05))" }}
      >
        {value.toLocaleString()}
      </span>
    </CardSection>
  );
}

export function AssistantStats({ assistantId }: { assistantId: number }) {
  const [assistantStats, setAssistantStats] =
    useState<AssistantStatsResponse | null>(null);
  const { agents: assistants } = useAgents();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>({
    from: new Date(new Date().setDate(new Date().getDate() - 30)),
    to: new Date(),
  });

  const assistant = useMemo(
    () => assistants.find((a) => a.id === assistantId),
    [assistants, assistantId]
  );

  useEffect(() => {
    async function fetchStats() {
      try {
        setIsLoading(true);
        setError(null);

        const res = await fetch(
          `/api/analytics/assistant/${assistantId}/stats?start=${
            dateRange?.from?.toISOString() || ""
          }&end=${dateRange?.to?.toISOString() || ""}`
        );

        if (!res.ok) {
          if (res.status === 403) {
            throw new Error("You don't have permission to view these stats.");
          }
          throw new Error("Failed to fetch assistant stats");
        }

        const data = (await res.json()) as AssistantStatsResponse;
        setAssistantStats(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "An unknown error occurred"
        );
      } finally {
        setIsLoading(false);
      }
    }

    fetchStats();
  }, [assistantId, dateRange]);

  const chartData = useMemo(() => {
    if (!assistantStats?.daily_stats?.length || !dateRange) {
      return null;
    }

    const initialDate =
      dateRange.from ||
      new Date(
        Math.min(
          ...assistantStats.daily_stats.map((entry) =>
            new Date(entry.date).getTime()
          )
        )
      );
    const endDate = dateRange.to || new Date();
    const statsMap = new Map(
      assistantStats.daily_stats.map((entry) => [entry.date, entry])
    );

    return getDatesList(initialDate)
      .filter((date) => new Date(date) <= endDate)
      .map((dateStr) => {
        const dayData = statsMap.get(dateStr);
        return {
          Day: dateStr,
          Messages: dayData?.total_messages || 0,
          "Unique Users": dayData?.total_unique_users || 0,
        };
      });
  }, [assistantStats, dateRange]);

  const totalMessages = assistantStats?.total_messages ?? 0;
  const totalUniqueUsers = assistantStats?.total_unique_users ?? 0;

  let chart;
  if (isLoading || !assistant) {
    chart = (
      <div className="h-80 flex items-center justify-center">
        <ThreeDotsLoader />
      </div>
    );
  } else if (error) {
    chart = (
      <div className="h-80 flex items-center justify-center">
        <Text mainUiMuted className="text-error-05">
          {error}
        </Text>
      </div>
    );
  } else if (!chartData?.length) {
    chart = (
      <div className="h-80 flex items-center justify-center">
        <Text mainUiMuted text03>
          No activity for this assistant in the selected date range.
        </Text>
      </div>
    );
  } else {
    chart = (
      <TimeSeriesChart
        data={chartData}
        index="Day"
        series={CHART_SERIES}
        height={320}
      />
    );
  }

  return (
    <div className="flex flex-col gap-5 w-full max-w-5xl mx-auto">
      {/* Header: identity + date range */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          {assistant && <AgentAvatar agent={assistant} />}
          <div className="flex flex-col">
            <Text headingH2 text05>
              {assistant?.name ?? "Assistant"}
            </Text>
            {assistant?.description && (
              <Text mainUiMuted text04>
                {assistant.description}
              </Text>
            )}
          </div>
        </div>
        <AdminDateRangeSelector value={dateRange} onValueChange={setDateRange} />
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <StatTile label="Total Messages" value={totalMessages} />
        <StatTile label="Total Unique Users" value={totalUniqueUsers} />
      </div>

      {/* Trend chart */}
      <CardSection className="flex flex-col gap-3">
        <Text headingH3 text05>
          Daily Activity
        </Text>
        {chart}
      </CardSection>
    </div>
  );
}
