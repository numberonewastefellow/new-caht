import { TeamMemberRole } from "@/lib/types";
import { TeamCreate, TeamSettingsUpdate } from "./types";

export const createTeam = async (team: TeamCreate) => {
  return fetch("/api/teams", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(team),
  });
};

export const deleteTeam = async (teamId: number) => {
  return fetch(`/api/teams/${teamId}`, {
    method: "DELETE",
  });
};

// Add existing users to a team.
// POST /api/teams/{id}/add-users {user_ids, role}
// NOTE: the current backend only reads `user_ids`; `role` is forward-compatible
// with the upgraded endpoint and is ignored until the backend persists it.
export const addUsersToTeam = async (
  teamId: number,
  userIds: string[],
  role: TeamMemberRole
) => {
  return fetch(`/api/teams/${teamId}/add-users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_ids: userIds, role }),
  });
};

// Change a member's role.
// POST /api/teams/{id}/set-role {user_id, role}
// TODO(backend): this endpoint is part of the frozen contract but is not yet
// implemented server-side (only /set-curator exists today). Until it lands this
// call will 404 and surface a toast error.
export const setTeamRole = async (
  teamId: number,
  userId: string,
  role: TeamMemberRole
) => {
  return fetch(`/api/teams/${teamId}/set-role`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, role }),
  });
};

// Persist the remaining membership (used for member removal).
// PATCH /api/teams/{id} {user_ids, cc_pair_ids}
export const patchTeamMembership = async (
  teamId: number,
  userIds: string[],
  ccPairIds: number[]
) => {
  return fetch(`/api/teams/${teamId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_ids: userIds, cc_pair_ids: ccPairIds }),
  });
};

// Persist team-level settings.
// PATCH /api/teams/{id}
// TODO(backend): the PATCH endpoint currently only reads user_ids/cc_pair_ids.
// The settings fields below are sent for forward-compatibility; they are
// silently ignored until the backend is upgraded to persist them.
export const updateTeamSettings = async (
  teamId: number,
  userIds: string[],
  ccPairIds: number[],
  settings: TeamSettingsUpdate
) => {
  return fetch(`/api/teams/${teamId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_ids: userIds,
      cc_pair_ids: ccPairIds,
      ...settings,
    }),
  });
};
