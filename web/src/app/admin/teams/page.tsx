"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { useConnectorStatus, useTeams } from "@/lib/hooks";
import useUsers from "@/hooks/useUsers";
import { useUser } from "@/providers/UserProvider";
import { toast } from "@/hooks/useToast";
import { ThreeDotsLoader } from "@/components/Loading";
import { ErrorCallout } from "@/components/ErrorCallout";
import { AdminPageTitle } from "@/components/admin/Title";
import { Card } from "@/refresh-components/cards";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import Tabs from "@/refresh-components/Tabs";
import GenericConfirmModal from "@/components/modals/GenericConfirmModal";
import { SvgSettings, SvgSparkle, SvgUsers } from "@opal/icons";

import { deleteTeam } from "./lib";
import TeamListSidebar from "./components/TeamListSidebar";
import TeamDetailHeader from "./components/TeamDetailHeader";
import MembersTab from "./components/MembersTab";
import ResourcesTab from "./components/ResourcesTab";
import SettingsTab from "./components/SettingsTab";
import NewTeamDialog from "./components/NewTeamDialog";
import AddMembersDialog from "./components/AddMembersDialog";
import { getMemberCount } from "./components/shared";

function TeamsAdmin() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAdmin } = useUser();

  const { data: teams, isLoading, error, refreshTeams } = useTeams();
  const {
    data: users,
    isLoading: usersLoading,
    error: usersError,
  } = useUsers({ includeApiKeys: true });
  const {
    data: ccPairs,
    isLoading: ccPairsLoading,
    error: ccPairsError,
  } = useConnectorStatus();

  const [newTeamOpen, setNewTeamOpen] = useState(false);
  const [addMembersOpen, setAddMembersOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const activeTeams = useMemo(
    () => (teams ?? []).filter((t) => !t.is_up_for_deletion),
    [teams]
  );

  const paramTeam = searchParams.get("team");
  const selectedId = useMemo(() => {
    const parsed = paramTeam ? Number(paramTeam) : NaN;
    if (!Number.isNaN(parsed) && activeTeams.some((t) => t.id === parsed)) {
      return parsed;
    }
    return activeTeams[0]?.id ?? null;
  }, [paramTeam, activeTeams]);

  // Keep the URL in sync with the resolved selection (deep-linking).
  useEffect(() => {
    if (selectedId != null && String(selectedId) !== paramTeam) {
      router.replace(`/admin/teams?team=${selectedId}` as Route);
    }
  }, [selectedId, paramTeam, router]);

  function selectTeam(id: number) {
    router.replace(`/admin/teams?team=${id}` as Route);
  }

  const selected = useMemo(
    () => activeTeams.find((t) => t.id === selectedId) ?? null,
    [activeTeams, selectedId]
  );

  if (isLoading || usersLoading || ccPairsLoading) {
    return <ThreeDotsLoader />;
  }
  if (error || !teams) {
    return <ErrorCallout errorTitle="Failed to load teams" />;
  }
  if (usersError || !users) {
    return <ErrorCallout errorTitle="Failed to load users" />;
  }
  if (ccPairsError || !ccPairs) {
    return <ErrorCallout errorTitle="Failed to load connectors" />;
  }

  async function confirmDelete() {
    if (!selected) return;
    const res = await deleteTeam(selected.id);
    if (res.ok) {
      toast.success(`Team "${selected.name}" deleted`);
    } else {
      const body = await res.json().catch(() => ({}));
      toast.error(`Failed to delete team - ${body.detail || body.message}`);
    }
    setDeleteOpen(false);
    refreshTeams();
    // Move selection to the first remaining team.
    const remaining = activeTeams.filter((t) => t.id !== selected.id);
    if (remaining[0]) selectTeam(remaining[0].id);
  }

  // Empty state — no teams yet.
  if (activeTeams.length === 0) {
    return (
      <>
        <Card variant="tertiary" padding={2}>
          <div className="flex flex-col items-center gap-3 py-10 w-full">
            <div
              className="w-14 h-14 rounded-full flex items-center justify-center"
              style={{
                backgroundColor:
                  "var(--virtualai-accent-subtle, var(--theme-purple-01))",
              }}
            >
              <SvgUsers
                className="w-7 h-7"
                style={{
                  color: "var(--virtualai-accent, var(--theme-primary-05))",
                }}
              />
            </div>
            <Text mainContentEmphasis>No teams yet</Text>
            <Text secondaryBody text03 className="text-center max-w-md">
              Teams group members together and control which connectors and
              resources they can access. Create your first team to get started.
            </Text>
            {isAdmin && (
              <Button action onClick={() => setNewTeamOpen(true)}>
                Create team
              </Button>
            )}
          </div>
        </Card>

        <NewTeamDialog
          open={newTeamOpen}
          onClose={() => setNewTeamOpen(false)}
          allUsers={users.accepted}
          onCreated={(id) => {
            refreshTeams();
            if (id) selectTeam(id);
          }}
        />
      </>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-4 min-h-[calc(100vh-14rem)]">
        <TeamListSidebar
          teams={activeTeams}
          selectedId={selectedId}
          onSelect={selectTeam}
          onNewTeam={() => setNewTeamOpen(true)}
          canCreate={isAdmin}
        />

        <main className="min-w-0 flex flex-col gap-4">
          {selected ? (
            <>
              <TeamDetailHeader
                team={selected}
                canManage={isAdmin}
                onAddMembers={() => setAddMembersOpen(true)}
                onRename={() =>
                  // TODO: rename flow (backend PATCH does not accept name yet).
                  toast.info("Rename is not available yet.")
                }
                onDelete={() => setDeleteOpen(true)}
              />

              <Tabs defaultValue="members">
                <Tabs.List>
                  <Tabs.Trigger value="members" icon={SvgUsers}>
                    {`Members (${getMemberCount(selected)})`}
                  </Tabs.Trigger>
                  <Tabs.Trigger value="resources" icon={SvgSparkle}>
                    Resources
                  </Tabs.Trigger>
                  <Tabs.Trigger value="settings" icon={SvgSettings}>
                    Settings
                  </Tabs.Trigger>
                </Tabs.List>

                <Tabs.Content value="members">
                  <MembersTab
                    team={selected}
                    canManage={isAdmin}
                    onAddMembers={() => setAddMembersOpen(true)}
                    onRefresh={refreshTeams}
                  />
                </Tabs.Content>

                <Tabs.Content value="resources">
                  <ResourcesTab
                    team={selected}
                    users={users.accepted}
                    ccPairs={ccPairs}
                    onRefresh={refreshTeams}
                  />
                </Tabs.Content>

                <Tabs.Content value="settings">
                  <SettingsTab
                    team={selected}
                    canManage={isAdmin}
                    onRefresh={refreshTeams}
                    onDelete={() => setDeleteOpen(true)}
                  />
                </Tabs.Content>
              </Tabs>
            </>
          ) : (
            <Card variant="tertiary" padding={2}>
              <Text secondaryBody text03 className="text-center py-10">
                Select a team to view its details.
              </Text>
            </Card>
          )}
        </main>
      </div>

      <NewTeamDialog
        open={newTeamOpen}
        onClose={() => setNewTeamOpen(false)}
        allUsers={users.accepted}
        onCreated={(id) => {
          refreshTeams();
          if (id) selectTeam(id);
        }}
      />

      {selected && (
        <AddMembersDialog
          open={addMembersOpen}
          onClose={() => setAddMembersOpen(false)}
          team={selected}
          allUsers={users.accepted}
          onAdded={refreshTeams}
        />
      )}

      {selected && deleteOpen && (
        <GenericConfirmModal
          title={`Delete "${selected.name}"?`}
          message="Deleting this team removes all members and resource associations. This cannot be undone."
          confirmText="Delete team"
          onClose={() => setDeleteOpen(false)}
          onConfirm={confirmDelete}
        />
      )}
    </>
  );
}

const Page = () => {
  return (
    <>
      <AdminPageTitle
        title="Teams & Members"
        icon={SvgUsers}
        description="Create teams, manage members and roles, and control the resources each team can access."
      />
      <Suspense fallback={<ThreeDotsLoader />}>
        <TeamsAdmin />
      </Suspense>
    </>
  );
};

export default Page;
