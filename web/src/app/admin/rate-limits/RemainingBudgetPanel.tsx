"use client";

import useSWR from "swr";
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
import { BUDGET_URL } from "./lib";
import { RemainingBudgetItem, RemainingBudgetResponse, SCOPE_LABELS } from "./types";

// Healthy fill uses the theme accent (adapts to the user's accent theme + color mode); the warning
// and critical states use semantic status colors so an at-risk budget is obvious in either theme.
function fillColor(pct: number): string {
  if (pct >= 100) return "#ef4444"; // critical / exhausted
  if (pct >= 75) return "#f59e0b"; // warning
  return "var(--virtualai-accent, var(--theme-primary-05))";
}

function formatReset(seconds: number): string {
  if (seconds >= 3600) return `${Math.round(seconds / 3600)}h`;
  if (seconds >= 60) return `${Math.round(seconds / 60)}m`;
  return `${seconds}s`;
}

function BudgetBar({ item }: { item: RemainingBudgetItem }) {
  const pct =
    item.budget > 0 ? Math.min(100, (item.used / item.budget) * 100) : 0;
  return (
    <div className="flex flex-col gap-1 py-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-text-darker">
          {SCOPE_LABELS[item.scope] ?? item.scope}
          <span className="text-text-muted font-normal">
            {" "}
            · {item.subject} · {item.period_hours}h
          </span>
        </span>
        <span className="text-text-muted tabular-nums">
          {item.used.toLocaleString()} / {item.budget.toLocaleString()} · resets ~
          {formatReset(item.reset_seconds)}
        </span>
      </div>
      <div
        className="h-2 w-full rounded-full overflow-hidden"
        style={{ backgroundColor: "var(--virtualai-accent-subtle, rgba(120,120,120,0.15))" }}
        role="progressbar"
        aria-valuenow={Math.round(pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: fillColor(pct) }}
        />
      </div>
    </div>
  );
}

export default function RemainingBudgetPanel() {
  // Auto-refresh so the gauge reflects live usage as chat requests consume tokens.
  const { data, isLoading, error } = useSWR<RemainingBudgetResponse>(
    BUDGET_URL,
    errorHandlingFetcher,
    { refreshInterval: 5000 }
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live Remaining Budget</CardTitle>
        <CardDescription>
          Real-time token budget remaining for every enabled policy. Refreshes
          automatically.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <ThreeDotsLoader />
        ) : error ? (
          <Text>Failed to load remaining budget.</Text>
        ) : !data || data.items.length === 0 ? (
          <Text className="text-text-muted">
            No enabled policies to display.
          </Text>
        ) : (
          <div className="flex flex-col divide-y divide-border-01">
            {data.items.map((item) => (
              <BudgetBar key={item.policy_id} item={item} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
