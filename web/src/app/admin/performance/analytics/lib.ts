import useSWR, { mutate } from "swr";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { buildApiPath } from "@/lib/urlBuilder";
import {
  convertDateToEndOfDay,
  convertDateToStartOfDay,
  getXDaysAgo,
} from "@/components/dateRangeSelectors/dateUtils";
import { DateRange } from "@/components/dateRangeSelectors/AdminDateRangeSelector";

// ---------------------------------------------------------------------------
// WS-H analytics / query-history / reporting / app-settings types.
// Shapes mirror the backend pydantic responses.
// ---------------------------------------------------------------------------

export interface DailyUsagePoint {
  date: string;
  total_queries: number;
  active_users: number;
  likes: number;
  dislikes: number;
  avg_latency_ms: number | null;
}

export interface UsageSummary {
  total_queries: number;
  total_active_users: number;
  total_likes: number;
  total_dislikes: number;
  avg_latency_ms: number | null;
}

export interface AgentUsagePoint {
  agent_name: string;
  total_messages: number;
}

export interface ChatSessionSummary {
  id: string;
  user_email: string | null;
  name: string | null;
  first_user_message: string;
  first_ai_message: string;
  agent_id: number | null;
  agent_name: string | null;
  time_created: string;
  feedback: "like" | "dislike" | "mixed" | null;
  flow_type: string;
  message_count: number;
}

export interface QueryHistoryMessage {
  id: number;
  message_type: string;
  message: string;
  time_created: string;
  feedback: "like" | "dislike" | "mixed" | null;
  feedback_text: string | null;
}

export interface ChatSessionDetail {
  id: string;
  user_email: string | null;
  name: string | null;
  agent_id: number | null;
  agent_name: string | null;
  time_created: string;
  flow_type: string;
  messages: QueryHistoryMessage[];
}

export interface PaginatedSessions {
  items: ChatSessionSummary[];
  total_items: number;
}

export interface UsageReportSchema {
  id: number;
  report_name: string;
  requestor_email: string | null;
  period_from: string | null;
  period_to: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Date range helpers
// ---------------------------------------------------------------------------

export function defaultDateRange(): DateRange {
  return { from: getXDaysAgo(30), to: new Date() };
}

/** Convert a picker range into inclusive ISO start/end query params. */
export function rangeParams(range: DateRange): Record<string, string | undefined> {
  return {
    start: convertDateToStartOfDay(range?.from)?.toISOString(),
    end: convertDateToEndOfDay(range?.to)?.toISOString(),
  };
}

// ---------------------------------------------------------------------------
// SWR hooks (analytics)
// ---------------------------------------------------------------------------

export function useUsage(range: DateRange) {
  const url = buildApiPath("/api/analytics/admin/usage", rangeParams(range));
  const swr = useSWR<DailyUsagePoint[]>(url, errorHandlingFetcher);
  return { ...swr, refresh: () => mutate(url) };
}

export function useSummary(range: DateRange) {
  const url = buildApiPath("/api/analytics/admin/summary", rangeParams(range));
  const swr = useSWR<UsageSummary>(url, errorHandlingFetcher);
  return { ...swr, refresh: () => mutate(url) };
}

export function useTopAgents(range: DateRange, limit = 10) {
  const url = buildApiPath("/api/analytics/admin/top-agents", {
    ...rangeParams(range),
    limit: String(limit),
  });
  const swr = useSWR<AgentUsagePoint[]>(url, errorHandlingFetcher);
  return { ...swr, refresh: () => mutate(url) };
}
