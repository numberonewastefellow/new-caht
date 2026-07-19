"use client";

import React, { useMemo, useState } from "react";
import { SvgBarChart } from "@opal/icons";

import { AdminPageTitle } from "@/components/admin/Title";
import CardSection from "@/components/admin/CardSection";
import Text from "@/refresh-components/texts/Text";
import { ThreeDotsLoader } from "@/components/Loading";
import {
  AdminDateRangeSelector,
  DateRange,
} from "@/components/dateRangeSelectors/AdminDateRangeSelector";

import { CategoryBarChart, TimeSeriesChart } from "./charts";
import { defaultDateRange, useSummary, useTopAgents, useUsage } from "./lib";

function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString();
}

// ISO "YYYY-MM-DD" -> "MM-DD" for compact axis ticks.
function shortDate(value: string): string {
  return value.length >= 10 ? value.slice(5) : value;
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <CardSection className="flex-1 min-w-[10rem]">
      <Text secondaryBody text03>
        {label}
      </Text>
      <div className="mt-1">
        <Text headingH2>{value}</Text>
      </div>
    </CardSection>
  );
}

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <CardSection>
      <div className="mb-4">
        <Text mainUiBody>{title}</Text>
      </div>
      {children}
    </CardSection>
  );
}

export default function AnalyticsPage() {
  const [range, setRange] = useState<DateRange>(defaultDateRange());

  const { data: usage, isLoading } = useUsage(range);
  const { data: summary } = useSummary(range);
  const { data: topAgents } = useTopAgents(range);

  const usageData = useMemo(
    () =>
      (usage ?? []).map((p) => ({
        date: p.date,
        Queries: p.total_queries,
        "Active users": p.active_users,
      })),
    [usage]
  );

  const feedbackData = useMemo(
    () =>
      (usage ?? []).map((p) => ({
        date: p.date,
        Likes: p.likes,
        Dislikes: p.dislikes,
      })),
    [usage]
  );

  const latencyData = useMemo(
    () =>
      (usage ?? [])
        .filter((p) => p.avg_latency_ms !== null)
        .map((p) => ({ date: p.date, "Avg latency (ms)": p.avg_latency_ms })),
    [usage]
  );

  const agentData = useMemo(
    () =>
      (topAgents ?? []).map((a) => ({
        agent: a.agent_name,
        Messages: a.total_messages,
      })),
    [topAgents]
  );

  return (
    <div>
      <AdminPageTitle
        icon={SvgBarChart}
        title="Analytics"
        description="Usage, engagement and latency across your workspace."
        farRightElement={
          <AdminDateRangeSelector value={range} onValueChange={setRange} />
        }
      />

      <div className="flex flex-wrap gap-4 mt-4">
        <StatTile label="Total queries" value={formatCount(summary?.total_queries)} />
        <StatTile
          label="Active users"
          value={formatCount(summary?.total_active_users)}
        />
        <StatTile label="Likes" value={formatCount(summary?.total_likes)} />
        <StatTile label="Dislikes" value={formatCount(summary?.total_dislikes)} />
        <StatTile
          label="Avg latency"
          value={
            summary && summary.avg_latency_ms != null
              ? `${summary.avg_latency_ms} ms`
              : "—"
          }
        />
      </div>

      {isLoading ? (
        <div className="mt-10">
          <ThreeDotsLoader />
        </div>
      ) : (
        <div className="flex flex-col gap-6 mt-6">
          <ChartCard title="Queries & active users over time">
            <TimeSeriesChart
              data={usageData}
              index="date"
              series={[
                { key: "Queries", label: "Queries" },
                { key: "Active users", label: "Active users" },
              ]}
              xAxisFormatter={shortDate}
            />
          </ChartCard>

          <ChartCard title="Feedback over time">
            <CategoryBarChart
              data={feedbackData}
              index="date"
              series={[
                { key: "Likes", label: "Likes" },
                { key: "Dislikes", label: "Dislikes" },
              ]}
              xAxisFormatter={shortDate}
            />
          </ChartCard>

          <ChartCard title="Average response latency">
            <TimeSeriesChart
              data={latencyData}
              index="date"
              series={[{ key: "Avg latency (ms)", label: "Avg latency (ms)" }]}
              xAxisFormatter={shortDate}
              allowDecimals
            />
          </ChartCard>

          <ChartCard title="Top agents by messages">
            <CategoryBarChart
              data={agentData}
              index="agent"
              series={[{ key: "Messages", label: "Messages" }]}
            />
          </ChartCard>
        </div>
      )}
    </div>
  );
}
