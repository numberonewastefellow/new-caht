"use client";

import useSWR from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import { cn } from "@/lib/utils";

export default function SystemHealthDot() {
  const { error } = useSWR("/api/health", errorHandlingFetcher, {
    revalidateOnFocus: false,
    dedupingInterval: 30000,
  });

  const isHealthy = !error;
  const label = isHealthy
    ? "All systems operational"
    : "Backend unavailable";

  return (
    <SimpleTooltip tooltip={label}>
      <span
        className={cn(
          "inline-block w-2 h-2 rounded-full flex-shrink-0",
          isHealthy
            ? "bg-status-success-strong"
            : "bg-status-error-strong"
        )}
        aria-label={label}
      />
    </SimpleTooltip>
  );
}
