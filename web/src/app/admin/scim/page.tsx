"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import { ThreeDotsLoader } from "@/components/Loading";
import { AdminPageTitle } from "@/components/admin/Title";
import { ErrorCallout } from "@/components/ErrorCallout";
import { errorHandlingFetcher } from "@/lib/fetcher";
import Separator from "@/refresh-components/Separator";
import Text from "@/refresh-components/texts/Text";
import Title from "@/components/ui/title";
import Modal from "@/refresh-components/Modal";
import CreateButton from "@/refresh-components/buttons/CreateButton";
import CopyIconButton from "@/refresh-components/buttons/CopyIconButton";
import { DeleteButton } from "@/components/DeleteButton";
import { toast } from "@/hooks/useToast";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SvgArrowExchange, SvgUser, SvgUsers, SvgKey } from "@opal/icons";
import CreateScimTokenModal from "./CreateScimTokenModal";
import { revokeScimToken } from "./lib";
import { ScimStatus, ScimTokenCreatedResponse, ScimTokenInfo } from "./types";

const STATUS_URL = "/api/admin/scim/status";
const TOKENS_URL = "/api/admin/scim/tokens";

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
}) {
  return (
    <div className="flex-1 rounded-16 border border-border-01 bg-background-neutral-02 p-4">
      <div className="flex items-center gap-2">
        <span
          className="flex h-8 w-8 items-center justify-center rounded-08"
          style={{
            backgroundColor: "var(--virtualai-accent-subtle, transparent)",
            color: "var(--virtualai-accent, var(--theme-primary-05))",
          }}
        >
          <Icon className="h-4 w-4" />
        </span>
        <Text secondaryBody text03>
          {label}
        </Text>
      </div>
      <Text className="mt-2 text-2xl font-semibold">{value}</Text>
    </div>
  );
}

function formatDate(value: string | null): string {
  if (!value) return "Never";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

function Main() {
  const { data: status, error: statusError } = useSWR<ScimStatus>(
    STATUS_URL,
    errorHandlingFetcher
  );
  const {
    data: tokens,
    isLoading,
    error: tokensError,
  } = useSWR<ScimTokenInfo[]>(TOKENS_URL, errorHandlingFetcher);

  const [showCreate, setShowCreate] = useState(false);
  const [newRawToken, setNewRawToken] = useState<string | null>(null);

  const refresh = () => {
    mutate(TOKENS_URL);
    mutate(STATUS_URL);
  };

  if (isLoading || (!tokens && !tokensError)) {
    return <ThreeDotsLoader />;
  }

  if (tokensError || !tokens) {
    return (
      <ErrorCallout
        errorTitle="Failed to fetch SCIM tokens"
        errorMsg={tokensError?.info?.detail || tokensError?.toString()}
      />
    );
  }

  return (
    <>
      {/* Raw token — shown exactly once */}
      <Modal
        open={!!newRawToken}
        onOpenChange={(open) => {
          if (!open) setNewRawToken(null);
        }}
      >
        <Modal.Content width="sm" height="sm">
          <Modal.Header
            title="New SCIM Token"
            icon={SvgArrowExchange}
            onClose={() => setNewRawToken(null)}
            description="Copy this token into your identity provider now. You won’t be able to see it again."
          />
          <Modal.Body>
            <Text as="p" className="flex-1 break-all">
              {newRawToken}
            </Text>
            <CopyIconButton getCopyText={() => newRawToken!} />
          </Modal.Body>
        </Modal.Content>
      </Modal>

      <div className="flex flex-col items-start gap-4">
        <Text as="p" text03>
          SCIM 2.0 lets your identity provider (Okta, Microsoft Entra ID, …)
          automatically provision and deprovision users and sync groups to
          Teams. Point your IdP at the base URL below and authenticate with a
          bearer token generated here.
        </Text>

        {/* Base URL for IdP setup */}
        {status && (
          <div className="w-full rounded-16 border border-border-01 bg-background-neutral-02 p-4">
            <Text secondaryBody text03>
              SCIM Base URL
            </Text>
            <div className="mt-1 flex items-center gap-2">
              <Text as="span" className="break-all font-mono">
                {status.base_url}
              </Text>
              <CopyIconButton getCopyText={() => status.base_url} />
            </div>
            <Text as="p" text03 className="mt-2">
              Discovery endpoints (<code>/ServiceProviderConfig</code>,{" "}
              <code>/ResourceTypes</code>, <code>/Schemas</code>) are public;
              all provisioning endpoints require the bearer token.
            </Text>
          </div>
        )}

        {/* Status cards */}
        {status && (
          <div className="flex w-full flex-col gap-3 sm:flex-row">
            <StatCard
              icon={SvgKey}
              label="Active Tokens"
              value={status.active_token_count}
            />
            <StatCard
              icon={SvgUser}
              label="Provisioned Users"
              value={status.user_mapping_count}
            />
            <StatCard
              icon={SvgUsers}
              label="Synced Teams"
              value={status.team_mapping_count}
            />
          </div>
        )}
        {statusError && (
          <Text as="p" text03>
            Could not load provisioning status.
          </Text>
        )}

        <CreateButton onClick={() => setShowCreate(true)}>
          Generate SCIM Token
        </CreateButton>
      </div>

      <Separator />

      <Title className="mt-6">SCIM Tokens</Title>
      {tokens.length === 0 ? (
        <Text as="p" text03 className="mt-2">
          No SCIM tokens yet. Generate one to connect your identity provider.
        </Text>
      ) : (
        <Table className="overflow-visible">
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Token</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Last Used</TableHead>
              <TableHead>Revoke</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tokens.map((token) => (
              <TableRow key={token.id}>
                <TableCell>{token.name}</TableCell>
                <TableCell className="font-mono">
                  {token.token_display}
                </TableCell>
                <TableCell>{token.is_active ? "Active" : "Revoked"}</TableCell>
                <TableCell>{formatDate(token.created_at)}</TableCell>
                <TableCell>{formatDate(token.last_used_at)}</TableCell>
                <TableCell>
                  {token.is_active ? (
                    <DeleteButton
                      onClick={async () => {
                        const response = await revokeScimToken(token.id);
                        if (!response.ok) {
                          const errorMsg = await response.text();
                          toast.error(`Failed to revoke token: ${errorMsg}`);
                          return;
                        }
                        toast.success("SCIM token revoked");
                        refresh();
                      }}
                    />
                  ) : (
                    <Text as="span" text03>
                      —
                    </Text>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <CreateScimTokenModal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={(created: ScimTokenCreatedResponse) => {
          setShowCreate(false);
          setNewRawToken(created.raw_token);
          refresh();
        }}
      />
    </>
  );
}

export default function Page() {
  return (
    <>
      <AdminPageTitle title="SCIM Provisioning" icon={SvgArrowExchange} />
      <Main />
    </>
  );
}
