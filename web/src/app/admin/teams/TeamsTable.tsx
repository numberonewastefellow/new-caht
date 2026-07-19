"use client";

import {
  Table,
  TableHead,
  TableRow,
  TableBody,
  TableCell,
  TableHeader,
} from "@/components/ui/table";
import { toast } from "@/hooks/useToast";
import { ConnectorTitle } from "@/components/admin/connectors/ConnectorTitle";
import { deleteUserGroup } from "./lib";
import { User, Team } from "@/lib/types";
import { DeleteButton } from "@/components/DeleteButton";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { SvgEdit } from "@opal/icons";

const MAX_AVATARS = 5;
const MAX_CONNECTORS = 3;

function initials(email: string): string {
  const local = (email.split("@")[0] || email).trim();
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length >= 2) {
    const chars = `${parts[0]?.[0] ?? ""}${parts[1]?.[0] ?? ""}`;
    return chars.toUpperCase() || "?";
  }
  return (local.slice(0, 2) || "?").toUpperCase();
}

function MemberAvatars({ users }: { users: User[] }) {
  if (users.length === 0) {
    return (
      <Text secondaryBody text03 className="text-sm">
        —
      </Text>
    );
  }
  const shown = users.slice(0, MAX_AVATARS);
  const extra = users.length - shown.length;
  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center -space-x-2">
        {shown.map((user) => (
          <div
            key={user.id}
            title={user.email}
            className="w-7 h-7 rounded-full flex items-center justify-center text-[0.65rem] font-main-ui-body border-2"
            style={{
              backgroundColor:
                "var(--virtualai-accent-subtle, var(--theme-purple-01))",
              color: "var(--virtualai-accent, var(--theme-primary-05))",
              borderColor: "var(--background-tint-00)",
            }}
          >
            {initials(user.email)}
          </div>
        ))}
      </div>
      <Text secondaryBody text03 className="text-sm">
        {users.length} member{users.length !== 1 ? "s" : ""}
        {extra > 0 ? ` · +${extra}` : ""}
      </Text>
    </div>
  );
}

function StatusBadge({ upToDate }: { upToDate: boolean }) {
  const color = upToDate ? "green" : "amber";
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs whitespace-nowrap"
      style={{
        backgroundColor: `var(--theme-${color}-01)`,
        color: `var(--theme-${color}-05)`,
      }}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${upToDate ? "" : "animate-pulse"}`}
        style={{ backgroundColor: `var(--theme-${color}-05)` }}
      />
      {upToDate ? "Up to date" : "Syncing"}
    </span>
  );
}

interface TeamsTableProps {
  teams: Team[];
  refresh: () => void;
}

export const TeamsTable = ({ teams, refresh }: TeamsTableProps) => {
  // sort by name for consistent ordering (copy so we don't mutate props)
  const sortedTeams = [...teams]
    .filter((team) => !team.is_up_for_deletion)
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <Table>
      <TableHeader>
        <TableRow noHover className="bg-background-tint-01">
          <TableHead>Team</TableHead>
          <TableHead>Members</TableHead>
          <TableHead>Data Sources</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">
            <div className="w-full text-right">Actions</div>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sortedTeams.map((team) => (
          <TableRow key={team.id}>
            <TableCell>
              <Button
                internal
                leftIcon={SvgEdit}
                href={`/admin/teams/${team.id}`}
                className="truncate"
              >
                {team.name}
              </Button>
            </TableCell>
            <TableCell>
              <MemberAvatars users={team.users} />
            </TableCell>
            <TableCell>
              {team.cc_pairs.length > 0 ? (
                <div className="flex flex-col gap-2">
                  {team.cc_pairs.slice(0, MAX_CONNECTORS).map((ccPair) => (
                    <ConnectorTitle
                      key={ccPair.id}
                      connector={ccPair.connector}
                      ccPairId={ccPair.id}
                      ccPairName={ccPair.name}
                      showMetadata={false}
                    />
                  ))}
                  {team.cc_pairs.length > MAX_CONNECTORS && (
                    <Text secondaryBody text03 className="text-xs">
                      + {team.cc_pairs.length - MAX_CONNECTORS} more
                    </Text>
                  )}
                </div>
              ) : (
                <Text secondaryBody text03 className="text-sm">
                  —
                </Text>
              )}
            </TableCell>
            <TableCell>
              <StatusBadge upToDate={team.is_up_to_date} />
            </TableCell>
            <TableCell>
              <div className="flex justify-end">
                <DeleteButton
                  onClick={async (event) => {
                    event.stopPropagation();
                    const response = await deleteUserGroup(team.id);
                    if (response.ok) {
                      toast.success(`Team "${team.name}" deleted`);
                    } else {
                      const errorMsg = (await response.json()).detail;
                      toast.error(`Failed to delete Team - ${errorMsg}`);
                    }
                    refresh();
                  }}
                />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
