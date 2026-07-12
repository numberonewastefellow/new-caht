"use client";

import { AdminDateRangeSelector } from "@/components/dateRangeSelectors/AdminDateRangeSelector";
import { OmBotChart } from "@/app/admin/performance/usage/OmBotChart";
import { FeedbackChart } from "@/app/admin/performance/usage/FeedbackChart";
import { QueryPerformanceChart } from "@/app/admin/performance/usage/QueryPerformanceChart";
import { PersonaMessagesChart } from "@/app/admin/performance/usage/PersonaMessagesChart";
import { useTimeRange } from "@/app/admin/performance/lib";
import { AdminPageTitle } from "@/components/admin/Title";
import UsageReports from "@/app/admin/performance/usage/UsageReports";
import Separator from "@/refresh-components/Separator";
import { useAdminPersonas } from "@/hooks/useAdminPersonas";
import { SvgActivity } from "@opal/icons";

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useTimeRange();
  const { personas } = useAdminPersonas();

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
      <PersonaMessagesChart
        availablePersonas={personas}
        timeRange={timeRange}
      />
      <Separator />
      <UsageReports />
    </>
  );
}
