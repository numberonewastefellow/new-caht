"use client";

import useSWR, { mutate } from "swr";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import Text from "@/components/ui/text";
import Checkbox from "@/refresh-components/inputs/Checkbox";
import { DeleteButton } from "@/components/DeleteButton";
import { ThreeDotsLoader } from "@/components/Loading";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { toast } from "@/hooks/useToast";
import { deletePolicy, POLICIES_URL, updatePolicy } from "./lib";
import { RateLimitPolicy, RateLimitScope, SCOPE_LABELS } from "./types";

function subjectLabel(policy: RateLimitPolicy): string {
  switch (policy.scope) {
    case RateLimitScope.GLOBAL:
    case RateLimitScope.TENANT:
      return "Whole tenant";
    case RateLimitScope.USER:
      return policy.user_id ? `User ${policy.user_id.slice(0, 8)}…` : "Every user";
    case RateLimitScope.TEAM:
      return policy.team_id ? `Team #${policy.team_id}` : "—";
    default:
      return "—";
  }
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

export default function PolicyTable() {
  const { data, isLoading, error } = useSWR<RateLimitPolicy[]>(
    POLICIES_URL,
    errorHandlingFetcher
  );

  const handleToggle = (policy: RateLimitPolicy) => {
    updatePolicy(policy.id, {
      scope: policy.scope,
      token_budget: policy.token_budget,
      period_hours: policy.period_hours,
      enabled: !policy.enabled,
    }).then(() => mutate(POLICIES_URL));
  };

  const handleDelete = (id: number) =>
    deletePolicy(id).then((res) => {
      if (res.ok) {
        toast.success("Policy deleted");
        mutate(POLICIES_URL);
      } else {
        toast.error("Failed to delete policy");
      }
    });

  if (isLoading) return <ThreeDotsLoader />;
  if (error) return <Text>Failed to load rate limit policies.</Text>;

  const policies = data ?? [];
  if (policies.length === 0) {
    return (
      <Text className="my-4 text-text-muted">
        No rate limit policies configured yet. Create one to start enforcing token
        budgets.
      </Text>
    );
  }

  return (
    <Table className="my-4">
      <TableHeader>
        <TableRow>
          <TableHead>Enabled</TableHead>
          <TableHead>Scope</TableHead>
          <TableHead>Subject</TableHead>
          <TableHead>Window</TableHead>
          <TableHead>Token Budget</TableHead>
          <TableHead>Delete</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {policies.map((policy) => (
          <TableRow key={policy.id}>
            <TableCell>
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={policy.enabled}
                  onCheckedChange={() => handleToggle(policy)}
                />
                <span>{policy.enabled ? "Enabled" : "Disabled"}</span>
              </div>
            </TableCell>
            <TableCell className="font-medium text-text-darker">
              {SCOPE_LABELS[policy.scope] ?? policy.scope}
            </TableCell>
            <TableCell>{subjectLabel(policy)}</TableCell>
            <TableCell>
              {policy.period_hours} hour{policy.period_hours > 1 ? "s" : ""}
            </TableCell>
            <TableCell>{formatTokens(policy.token_budget)} tokens</TableCell>
            <TableCell>
              <DeleteButton onClick={() => handleDelete(policy.id)} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
