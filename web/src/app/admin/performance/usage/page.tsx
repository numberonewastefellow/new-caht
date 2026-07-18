"use client";

import { AdminDateRangeSelector } from "@/components/dateRangeSelectors/AdminDateRangeSelector";
import { OmBotChart } from "@/app/admin/performance/usage/OmBotChart";
import { FeedbackChart } from "@/app/admin/performance/usage/FeedbackChart";
import { QueryPerformanceChart } from "@/app/admin/performance/usage/QueryPerformanceChart";
import { AgentMessagesChart } from "@/app/admin/performance/usage/AgentMessagesChart";
import { useTimeRange } from "@/app/admin/performance/lib";
import { AdminPageTitle } from "@/components/admin/Title";
import UsageReports from "@/app/admin/performance/usage/UsageReports";
import Separator from "@/refresh-components/Separator";
import { useAdminAgents } from "@/hooks/useAdminAgents";
import { SvgActivity } from "@opal/icons";

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useTimeRange();
  const { agents } = useAdminAgents();

  return (
    <>
      <AdminPageTitle title="Usage Statistics" icon={SvgActivity} />
      <AdminDateRangeSelector
        value={timeRange}
        onValueChange={(value) => setTimeRange(value as any)}
      />
      <QueryPerformanceChart timeRange={timeRange} />
      <FeedbackChart timeRange={timeRange} />
      <OmBotChart timeRange={timeRange} />
      <AgentMessagesChart
        availableAgents={agents}
        timeRange={timeRange}
      />
      <Separator />
      <UsageReports />
    </>
  );
}
