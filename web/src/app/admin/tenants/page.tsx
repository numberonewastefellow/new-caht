"use client";

import { useMemo, useState } from "react";
import useSWR, { mutate } from "swr";
import { AdminPageTitle } from "@/components/admin/Title";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { ThreeDotsLoader } from "@/components/Loading";
import { ErrorCallout } from "@/components/ErrorCallout";
import Separator from "@/refresh-components/Separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import Title from "@/components/ui/title";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import CreateButton from "@/refresh-components/buttons/CreateButton";
import { DeleteButton } from "@/components/DeleteButton";
import { toast } from "@/hooks/useToast";
import { SvgServer, SvgUser, SvgUsers, SvgSlash } from "@opal/icons";
import type { IconProps } from "@opal/types";
import { TenantListResponse, TENANTS_ADMIN_URL } from "./types";
import { deactivateTenant, deleteTenant } from "./lib";
import CreateTenantModal from "./CreateTenantModal";
import AssignUserModal from "./AssignUserModal";

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.FunctionComponent<IconProps>;
  label: string;
  value: number | string;
}) {
  return (
    <div className="flex-1 min-w-[10rem] rounded-16 border border-border-01 bg-background-tint-01 p-4 flex items-center gap-3">
      <div
        className="flex items-center justify-center h-10 w-10 rounded-12"
        style={{
          background: "var(--virtualai-accent-subtle, var(--theme-primary-01))",
          color: "var(--virtualai-accent, var(--theme-primary-05))",
        }}
      >
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex flex-col">
        <Text figureSmallValue>{value}</Text>
        <Text secondaryBody text03>
          {label}
        </Text>
      </div>
    </div>
  );
}

function Main() {
  const { data, isLoading, error } = useSWR<TenantListResponse>(
    TENANTS_ADMIN_URL,
    errorHandlingFetcher
  );

  const [showCreate, setShowCreate] = useState(false);
  const [assignTenantId, setAssignTenantId] = useState<string | null>(null);

  const totals = useMemo(() => {
    const tenants = data?.tenants ?? [];
    return {
      tenantCount: tenants.length,
      activeUsers: tenants.reduce((sum, t) => sum + t.active_user_count, 0),
      totalUsers: tenants.reduce((sum, t) => sum + t.total_user_count, 0),
    };
  }, [data]);

  if (isLoading) {
    return <ThreeDotsLoader />;
  }

  if (!data || error) {
    return (
      <ErrorCallout
        errorTitle="Failed to load tenants"
        errorMsg={error?.info?.detail || error?.toString()}
      />
    );
  }

  const refresh = () => mutate(TENANTS_ADMIN_URL);

  const introSection = (
    <div className="flex flex-col items-start gap-4">
      <Text as="p">
        Each tenant is an isolated Postgres schema — data written in one tenant
        is never visible in another. Provision tenants on demand and route users
        to them. No billing or external control plane is involved.
      </Text>
      <CreateButton onClick={() => setShowCreate(true)}>
        Provision Tenant
      </CreateButton>
    </div>
  );

  return (
    <>
      {introSection}

      <div className="flex flex-wrap gap-4 mt-6">
        <StatCard icon={SvgServer} label="Tenants" value={totals.tenantCount} />
        <StatCard
          icon={SvgUser}
          label="Active users"
          value={totals.activeUsers}
        />
        <StatCard
          icon={SvgUsers}
          label="Total mappings"
          value={totals.totalUsers}
        />
      </div>

      <Separator />

      <Title className="mt-6">Tenants</Title>

      {data.tenants.length === 0 ? (
        <Text as="p" text03 className="mt-4">
          No tenants yet. Provision one to get started.
        </Text>
      ) : (
        <Table className="overflow-visible mt-2">
          <TableHeader>
            <TableRow>
              <TableHead>Tenant ID</TableHead>
              <TableHead>Active users</TableHead>
              <TableHead>Total mappings</TableHead>
              <TableHead>Assign</TableHead>
              <TableHead>Deactivate</TableHead>
              <TableHead>Delete</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.tenants.map((tenant) => (
              <TableRow key={tenant.tenant_id}>
                <TableCell className="font-mono max-w-80 break-all">
                  {tenant.tenant_id}
                </TableCell>
                <TableCell>{tenant.active_user_count}</TableCell>
                <TableCell>{tenant.total_user_count}</TableCell>
                <TableCell>
                  <Button
                    internal
                    leftIcon={SvgUser}
                    onClick={() => setAssignTenantId(tenant.tenant_id)}
                  >
                    Assign
                  </Button>
                </TableCell>
                <TableCell>
                  <Button
                    internal
                    leftIcon={SvgSlash}
                    onClick={async () => {
                      try {
                        const result = await deactivateTenant(
                          tenant.tenant_id
                        );
                        toast.success(result.detail || "Tenant deactivated");
                        refresh();
                      } catch (e) {
                        toast.error(
                          `Failed to deactivate: ${
                            e instanceof Error ? e.message : String(e)
                          }`
                        );
                      }
                    }}
                  >
                    Deactivate
                  </Button>
                </TableCell>
                <TableCell>
                  <DeleteButton
                    onClick={async () => {
                      try {
                        const result = await deleteTenant(tenant.tenant_id);
                        toast.success(result.detail || "Tenant deleted");
                        refresh();
                      } catch (e) {
                        toast.error(
                          `Failed to delete: ${
                            e instanceof Error ? e.message : String(e)
                          }`
                        );
                      }
                    }}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <CreateTenantModal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={refresh}
      />
      <AssignUserModal
        tenantId={assignTenantId}
        onClose={() => setAssignTenantId(null)}
        onAssigned={refresh}
      />
    </>
  );
}

export default function Page() {
  return (
    <>
      <AdminPageTitle title="Tenants" icon={SvgServer} />
      <Main />
    </>
  );
}
