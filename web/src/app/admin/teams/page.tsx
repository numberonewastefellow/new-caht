"use client";

import { TeamsTable } from "./TeamsTable";
import TeamCreationForm from "./TeamCreationForm";
import { useState } from "react";
import { ThreeDotsLoader } from "@/components/Loading";
import { useConnectorStatus, useTeams } from "@/lib/hooks";
import { AdminPageTitle } from "@/components/admin/Title";
import useUsers from "@/hooks/useUsers";
import { useUser } from "@/providers/UserProvider";
import CreateButton from "@/refresh-components/buttons/CreateButton";
import { Card } from "@/refresh-components/cards";
import Text from "@/refresh-components/texts/Text";
import { ErrorCallout } from "@/components/ErrorCallout";
import { SvgUsers } from "@opal/icons";

const Main = () => {
  const [showForm, setShowForm] = useState(false);

  const { data, isLoading, error, refreshTeams } = useTeams();

  const {
    data: ccPairs,
    isLoading: isCCPairsLoading,
    error: ccPairsError,
  } = useConnectorStatus();

  const {
    data: users,
    isLoading: userIsLoading,
    error: usersError,
  } = useUsers({ includeApiKeys: true });

  const { isAdmin } = useUser();

  if (isLoading || isCCPairsLoading || userIsLoading) {
    return <ThreeDotsLoader />;
  }

  if (error || !data) {
    return <ErrorCallout errorTitle="Failed to load teams" />;
  }

  if (ccPairsError || !ccPairs) {
    return <ErrorCallout errorTitle="Failed to load connectors" />;
  }

  if (usersError || !users) {
    return <ErrorCallout errorTitle="Failed to load users" />;
  }

  const activeTeams = data.filter((team) => !team.is_up_for_deletion);

  return (
    <>
      {activeTeams.length > 0 ? (
        <>
          <div className="flex items-center justify-between gap-4 mb-4">
            <Text secondaryBody text03>
              {activeTeams.length} team{activeTeams.length !== 1 ? "s" : ""}
            </Text>
            {isAdmin && (
              <CreateButton onClick={() => setShowForm(true)}>
                Create Team
              </CreateButton>
            )}
          </div>
          <Card padding={0}>
            <TeamsTable teams={data} refresh={refreshTeams} />
          </Card>
        </>
      ) : (
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
              <CreateButton onClick={() => setShowForm(true)}>
                Create Team
              </CreateButton>
            )}
          </div>
        </Card>
      )}

      {showForm && (
        <TeamCreationForm
          onClose={() => {
            refreshTeams();
            setShowForm(false);
          }}
          users={users.accepted}
          ccPairs={ccPairs}
        />
      )}
    </>
  );
};

const Page = () => {
  return (
    <>
      <AdminPageTitle
        title="Teams"
        icon={SvgUsers}
        description="Organize members into teams and control the resources each team can access."
      />

      <Main />
    </>
  );
};

export default Page;
