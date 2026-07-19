// Types mirror backend om/server/rate_limits/api_models.py + constants.py.

export enum RateLimitScope {
  GLOBAL = "global",
  TENANT = "tenant",
  TEAM = "team",
  USER = "user",
}

export enum RateLimitAlgorithm {
  SLIDING_WINDOW = "sliding_window",
}

export interface RateLimitPolicyArgs {
  scope: RateLimitScope;
  token_budget: number;
  period_hours: number;
  enabled: boolean;
  algorithm?: RateLimitAlgorithm;
  user_id?: string | null;
  team_id?: number | null;
}

export interface RateLimitPolicy {
  id: number;
  scope: RateLimitScope;
  token_budget: number;
  period_hours: number;
  enabled: boolean;
  algorithm: RateLimitAlgorithm;
  user_id: string | null;
  team_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface RemainingBudgetItem {
  policy_id: number;
  scope: RateLimitScope;
  subject: string;
  period_hours: number;
  budget: number;
  used: number;
  remaining: number;
  reset_seconds: number;
}

export interface RemainingBudgetResponse {
  items: RemainingBudgetItem[];
}

export interface UsageHistoryPoint {
  bucket_start: string;
  tokens_used: number;
  allowed_count: number;
  throttled_count: number;
}

export interface UsageHistoryResponse {
  scope: RateLimitScope;
  subject: string;
  points: UsageHistoryPoint[];
}

export const SCOPE_LABELS: Record<RateLimitScope, string> = {
  [RateLimitScope.GLOBAL]: "Global",
  [RateLimitScope.TENANT]: "Tenant",
  [RateLimitScope.TEAM]: "Team",
  [RateLimitScope.USER]: "Per-User",
};
