"use client";

import { ConnectorStatus, Team, User } from "@/lib/types";
import { GroupDisplay } from "../[teamId]/GroupDisplay";

interface ResourcesTabProps {
  team: Team;
  users: User[];
  ccPairs: ConnectorStatus<any, any>[];
  onRefresh: () => void;
}

/**
 * Resources tab — reuses the existing GroupDisplay component (connectors,
 * document sets, assistants, and per-member curator management) so no
 * functionality from the legacy /admin/teams/[teamId] page is lost.
 */
export default function ResourcesTab({
  team,
  users,
  ccPairs,
  onRefresh,
}: ResourcesTabProps) {
  return (
    <GroupDisplay
      users={users}
      ccPairs={ccPairs}
      team={team}
      refreshTeam={onRefresh}
    />
  );
}
