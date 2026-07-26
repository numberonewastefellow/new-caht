import { TeamCreate } from "./types";

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
