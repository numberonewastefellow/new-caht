"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import Text from "@/components/ui/text";
import { ThreeDotsLoader } from "@/components/Loading";
import { errorHandlingFetcher } from "@/lib/fetcher";
import SimpleTabs from "@/refresh-components/SimpleTabs";
import { SvgGlobe, SvgShield } from "@opal/icons";
import { historyUrl } from "./lib";
import { RateLimitScope, UsageHistoryResponse } from "./types";

const RANGE_HOURS = 48;

function ChartFor({ scope }: { scope: RateLimitScope }) {
  const { data, isLoading, error } = useSWR<UsageHistoryResponse>(
    historyUrl(scope, { hours: RANGE_HOURS }),
    errorHandlingFetcher,
    { refreshInterval: 30000 }
  );

  if (isLoading) return <ThreeDotsLoader />;
  if (error) return <Text>Failed to load usage history.</Text>;

  const points = (data?.points ?? []).map((p) => ({
    ...p,
    label: new Date(p.bucket_start).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
    }),
  }));

  if (points.length === 0) {
    return (
      <Text className="text-text-muted py-8">
        No usage recorded in the last {RANGE_HOURS} hours for this scope.
      </Text>
    );
  }

  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={points}
          margin={{ top: 10, right: 16, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            fontSize={11}
            minTickGap={24}
          />
          <YAxis
            yAxisId="tokens"
            tickLine={false}
            axisLine={false}
            fontSize={11}
            width={56}
            tickFormatter={(v: number) =>
              v >= 1000 ? `${Math.round(v / 1000)}k` : String(v)
            }
          />
          <YAxis
            yAxisId="throttled"
            orientation="right"
            tickLine={false}
            axisLine={false}
            fontSize={11}
            width={32}
            allowDecimals={false}
          />
          <Tooltip />
          <Legend />
          <Area
            yAxisId="tokens"
            type="monotone"
            name="Tokens used"
            dataKey="tokens_used"
            stroke="var(--virtualai-accent, #6366f1)"
            fill="var(--virtualai-accent, #6366f1)"
            fillOpacity={0.25}
          />
          <Bar
            yAxisId="throttled"
            name="Throttled (429s)"
            dataKey="throttled_count"
            fill="#ef4444"
            radius={[2, 2, 0, 0]}
            barSize={10}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function ThrottleHistoryChart() {
  const [tab, setTab] = useState("0");
  return (
    <Card>
      <CardHeader>
        <CardTitle>Usage & Throttle History</CardTitle>
        <CardDescription>
          Tokens consumed and requests throttled (429) per hour over the last{" "}
          {RANGE_HOURS} hours, org-wide.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <SimpleTabs
          value={tab}
          onValueChange={setTab}
          tabs={{
            "0": {
              name: "Tenant",
              icon: SvgShield,
              content: <ChartFor scope={RateLimitScope.TENANT} />,
            },
            "1": {
              name: "Global",
              icon: SvgGlobe,
              content: <ChartFor scope={RateLimitScope.GLOBAL} />,
            },
          }}
        />
      </CardContent>
    </Card>
  );
}
