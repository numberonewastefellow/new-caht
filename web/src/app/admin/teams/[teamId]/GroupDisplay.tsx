"use client";

import { toast } from "@/hooks/useToast";
import { useState } from "react";
import { ConnectorTitle } from "@/components/admin/connectors/ConnectorTitle";
import AddMemberForm from "./AddMemberForm";
import { updateTeam, updateCuratorStatus } from "./lib";
import { Card } from "@/refresh-components/cards";
import {
  User,
  Team,
  UserRole,
  USER_ROLE_LABELS,
  ConnectorStatus,
} from "@/lib/types";
import AddConnectorForm from "./AddConnectorForm";
import Separator from "@/refresh-components/Separator";
import InputSelect from "@/refresh-components/inputs/InputSelect";
import Text from "@/components/ui/text";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import Button from "@/refresh-components/buttons/Button";
import { DeleteButton } from "@/components/DeleteButton";
import { Bubble } from "@/components/Bubble";
import { BookmarkIcon, RobotIcon } from "@/components/icons/icons";
import { useUser } from "@/providers/UserProvider";
import GenericConfirmModal from "@/components/modals/GenericConfirmModal";

interface GroupDisplayProps {
  users: User[];
  ccPairs: ConnectorStatus<any, any>[];
  team: Team;
  refreshTeam: () => void;
}

const UserRoleDropdown = ({
  user,
  group,
  onSuccess,
  onError,
  isAdmin,
}: {
  user: User;
  group: Team;
  onSuccess: () => void;
  onError: (message: string) => void;
  isAdmin: boolean;
}) => {
  const [localRole, setLocalRole] = useState(() => {
    if (user.role === UserRole.CURATOR) {
      return group.curator_ids.includes(user.id)
        ? UserRole.CURATOR
        : UserRole.BASIC;
    }
    return user.role;
  });
  const [isSettingRole, setIsSettingRole] = useState(false);
  const [showDemoteConfirm, setShowDemoteConfirm] = useState(false);
  const [pendingRoleChange, setPendingRoleChange] = useState<string | null>(
    null
  );
  const { user: currentUser } = useUser();

  const applyRoleChange = async (value: string) => {
    if (value === localRole) return;
    if (value === UserRole.BASIC || value === UserRole.CURATOR) {
      setIsSettingRole(true);
      setLocalRole(value);
      try {
        const response = await updateCuratorStatus(group.id, {
          user_id: user.id,
          is_curator: value === UserRole.CURATOR,
        });
        if (response.ok) {
          onSuccess();
          user.role = value;
        } else {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to update user role");
        }
      } catch (error: any) {
        onError(error.message);
        setLocalRole(user.role);
      } finally {
        setIsSettingRole(false);
      }
    }
  };

  const handleChange = (value: string) => {
    if (value === UserRole.BASIC && user.id === currentUser?.id) {
      setPendingRoleChange(value);
      setShowDemoteConfirm(true);
    } else {
      applyRoleChange(value);
    }
  };

  const isEditable =
    user.role === UserRole.BASIC || user.role === UserRole.CURATOR;

  return (
    <>
      {/* Confirmation modal - only shown when users try to demote themselves */}
      {showDemoteConfirm && pendingRoleChange && (
        <GenericConfirmModal
          title="Remove Yourself as a Curator for this Team?"
          message="Are you sure you want to change your role to Basic? This will remove your ability to curate this team."
          confirmText="Yes, set me to Basic"
          onClose={() => {
            // Cancel the role change if user dismisses modal
            setShowDemoteConfirm(false);
            setPendingRoleChange(null);
          }}
          onConfirm={() => {
            // Apply the role change if user confirms
            setShowDemoteConfirm(false);
            applyRoleChange(pendingRoleChange);
            setPendingRoleChange(null);
          }}
        />
      )}

      {isEditable ? (
        <InputSelect
          value={localRole}
          onValueChange={handleChange}
          disabled={isSettingRole}
        >
          <InputSelect.Trigger placeholder="Select role" />

          <InputSelect.Content>
            <InputSelect.Item value={UserRole.BASIC}>Basic</InputSelect.Item>
            <InputSelect.Item value={UserRole.CURATOR}>
              Curator
            </InputSelect.Item>
          </InputSelect.Content>
        </InputSelect>
      ) : (
        <div>{USER_ROLE_LABELS[localRole]}</div>
      )}
    </>
  );
};

export const GroupDisplay = ({
  users,
  ccPairs,
  team,
  refreshTeam,
}: GroupDisplayProps) => {
  const [addMemberFormVisible, setAddMemberFormVisible] = useState(false);
  const [addConnectorFormVisible, setAddConnectorFormVisible] = useState(false);

  const { isAdmin } = useUser();

  const onRoleChangeSuccess = () =>
    toast.success("User role updated successfully!");
  const onRoleChangeError = (errorMsg: string) =>
    toast.error(`Unable to update user role - ${errorMsg}`);

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-text-03">Status</span>
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs whitespace-nowrap"
          style={{
            backgroundColor: team.is_up_to_date
              ? "var(--theme-green-01)"
              : "var(--theme-amber-01)",
            color: team.is_up_to_date
              ? "var(--theme-green-05)"
              : "var(--theme-amber-05)",
          }}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              team.is_up_to_date ? "" : "animate-pulse"
            }`}
            style={{
              backgroundColor: team.is_up_to_date
                ? "var(--theme-green-05)"
                : "var(--theme-amber-05)",
            }}
          />
          {team.is_up_to_date ? "Up to date" : "Syncing"}
        </span>
      </div>

      <Separator />

      <h2 className="font-heading-h3 text-text-05 mb-3">Users</h2>

      <div className="mt-2">
        {team.users.length > 0 ? (
          <Card padding={0}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="flex w-full">
                    <div className="ml-auto">Remove User</div>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {team.users.map((groupMember) => {
                  return (
                    <TableRow key={groupMember.id}>
                      <TableCell className="whitespace-normal break-all">
                        {groupMember.email}
                      </TableCell>
                      <TableCell>
                        <UserRoleDropdown
                          user={groupMember}
                          group={team}
                          onSuccess={onRoleChangeSuccess}
                          onError={onRoleChangeError}
                          isAdmin={isAdmin}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex w-full">
                          <div className="ml-auto m-2">
                            {(isAdmin ||
                              !team.curator_ids.includes(
                                groupMember.id
                              )) && (
                              <DeleteButton
                                onClick={async () => {
                                  const response = await updateTeam(
                                    team.id,
                                    {
                                      user_ids: team.users
                                        .filter(
                                          (teamUser) =>
                                            teamUser.id !== groupMember.id
                                        )
                                        .map(
                                          (teamUser) => teamUser.id
                                        ),
                                      cc_pair_ids: team.cc_pairs.map(
                                        (ccPair) => ccPair.id
                                      ),
                                    }
                                  );
                                  if (response.ok) {
                                    toast.success(
                                      "Successfully removed user from team"
                                    );
                                  } else {
                                    const responseJson = await response.json();
                                    const errorMsg =
                                      responseJson.detail ||
                                      responseJson.message;
                                    toast.error(
                                      `Error removing user from team - ${errorMsg}`
                                    );
                                  }
                                  refreshTeam();
                                }}
                              />
                            )}
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Card>
        ) : (
          <div className="text-sm text-text-03">
            No members in this team yet.
          </div>
        )}
      </div>

      <SimpleTooltip
        tooltip="Cannot update team while sync is occurring"
        disabled={team.is_up_to_date}
      >
        <Button
          disabled={!team.is_up_to_date}
          onClick={() => {
            if (team.is_up_to_date) {
              setAddMemberFormVisible(true);
            }
          }}
        >
          Add Users
        </Button>
      </SimpleTooltip>
      {addMemberFormVisible && (
        <AddMemberForm
          users={users}
          team={team}
          onClose={() => {
            setAddMemberFormVisible(false);
            refreshTeam();
          }}
        />
      )}

      <Separator />

      <h2 className="font-heading-h3 text-text-05 mt-10 mb-3">Connectors</h2>
      <div className="mt-2">
        {team.cc_pairs.length > 0 ? (
          <Card padding={0}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Connector</TableHead>
                  <TableHead className="flex w-full">
                    <div className="ml-auto">Remove Connector</div>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {team.cc_pairs.map((ccPair) => {
                  return (
                    <TableRow key={ccPair.id}>
                      <TableCell className="whitespace-normal break-all">
                        <ConnectorTitle
                          connector={ccPair.connector}
                          ccPairId={ccPair.id}
                          ccPairName={ccPair.name}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex w-full">
                          <div className="ml-auto m-2">
                            <DeleteButton
                              onClick={async () => {
                                const response = await updateTeam(
                                  team.id,
                                  {
                                    user_ids: team.users.map(
                                      (teamUser) => teamUser.id
                                    ),
                                    cc_pair_ids: team.cc_pairs
                                      .filter(
                                        (teamCCPair) =>
                                          teamCCPair.id != ccPair.id
                                      )
                                      .map((ccPair) => ccPair.id),
                                  }
                                );
                                if (response.ok) {
                                  toast.success(
                                    "Successfully removed connector from team"
                                  );
                                } else {
                                  const responseJson = await response.json();
                                  const errorMsg =
                                    responseJson.detail || responseJson.message;
                                  toast.error(
                                    `Error removing connector from team - ${errorMsg}`
                                  );
                                }
                                refreshTeam();
                              }}
                            />
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Card>
        ) : (
          <div className="text-sm text-text-03">
            No data sources connected yet.
          </div>
        )}
      </div>

      <SimpleTooltip
        tooltip="Cannot update team while sync is occurring"
        disabled={team.is_up_to_date}
      >
        <Button
          disabled={!team.is_up_to_date}
          onClick={() => {
            if (team.is_up_to_date) {
              setAddConnectorFormVisible(true);
            }
          }}
        >
          Add Connectors
        </Button>
      </SimpleTooltip>

      {addConnectorFormVisible && (
        <AddConnectorForm
          ccPairs={ccPairs}
          team={team}
          onClose={() => {
            setAddConnectorFormVisible(false);
            refreshTeam();
          }}
        />
      )}

      <Separator />

      <h2 className="font-heading-h3 text-text-05 mt-10 mb-3">Document Sets</h2>

      <div>
        {team.document_sets.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {team.document_sets.map((documentSet) => {
              return (
                <Bubble isSelected key={documentSet.id}>
                  <div className="flex">
                    <BookmarkIcon />
                    <Text className="ml-1">{documentSet.name}</Text>
                  </div>
                </Bubble>
              );
            })}
          </div>
        ) : (
          <>
            <Text>No document sets in this team...</Text>
          </>
        )}
      </div>

      <Separator />

      <h2 className="font-heading-h3 text-text-05 mt-10 mb-3">Assistants</h2>

      <div>
        {team.document_sets.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {team.agents.map((agent) => {
              return (
                <Bubble isSelected key={agent.id}>
                  <div className="flex">
                    <RobotIcon />
                    <Text className="ml-1">{agent.name}</Text>
                  </div>
                </Bubble>
              );
            })}
          </div>
        ) : (
          <>
            <Text>No Assistants in this team...</Text>
          </>
        )}
      </div>
    </div>
  );
};
