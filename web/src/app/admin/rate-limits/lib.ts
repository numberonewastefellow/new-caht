import { RateLimitPolicyArgs, RateLimitScope } from "./types";

const API = "/api/admin/rate-limits";

export const POLICIES_URL = `${API}/policies`;
export const BUDGET_URL = `${API}/budget`;

export const createPolicy = (args: RateLimitPolicyArgs) =>
  fetch(`${API}/policies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });

export const updatePolicy = (id: number, args: RateLimitPolicyArgs) =>
  fetch(`${API}/policies/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });

export const deletePolicy = (id: number) =>
  fetch(`${API}/policies/${id}`, { method: "DELETE" });

export const historyUrl = (
  scope: RateLimitScope,
  opts: { hours?: number; userId?: string; teamId?: number } = {}
) => {
  const params = new URLSearchParams({ scope });
  if (opts.hours) params.set("hours", String(opts.hours));
  if (opts.userId) params.set("user_id", opts.userId);
  if (opts.teamId !== undefined) params.set("team_id", String(opts.teamId));
  return `${API}/history?${params.toString()}`;
};

// Team options for the TEAM-scope picker.
// Integrator note (Contract 1): the Team admin API base is `/teams`; this base branch still exposes
// the group endpoint. Retarget to `/api/teams` when WS-B is merged.
export const TEAMS_URL = "/api/nexus/admin/user-group";
