import { TeamUpdate, SetCuratorRequest } from "../types";

export const updateTeam = async (teamId: number, team: TeamUpdate) => {
  const url = `/api/teams/${teamId}`;
  return await fetch(url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(team),
  });
};

export const updateCuratorStatus = async (
  groupId: number,
  curatorRequest: SetCuratorRequest
) => {
  const url = `/api/teams/${groupId}/set-curator`;
  return await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(curatorRequest),
  });
};
