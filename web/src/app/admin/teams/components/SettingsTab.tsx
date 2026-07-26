"use client";

import { useState } from "react";
import { Team, TeamMemberRole } from "@/lib/types";
import { toast } from "@/hooks/useToast";
import Text from "@/refresh-components/texts/Text";
import Button from "@/refresh-components/buttons/Button";
import Switch from "@/refresh-components/inputs/Switch";
import InputSelect from "@/refresh-components/inputs/InputSelect";
import Separator from "@/refresh-components/Separator";
import { SvgTrash } from "@opal/icons";
import { updateTeamSettings } from "../lib";
import { getTeamMembers } from "./shared";

const ROLE_LABEL: Record<TeamMemberRole, string> = {
  OWNER: "Owner",
  ADMIN: "Admin",
  MEMBER: "Member",
};

interface SettingsTabProps {
  team: Team;
  canManage: boolean;
  onRefresh: () => void;
  onDelete: () => void;
}

export default function SettingsTab({
  team,
  canManage,
  onRefresh,
  onDelete,
}: SettingsTabProps) {
  const [isPublic, setIsPublic] = useState(!!team.is_public);
  const [defaultRole, setDefaultRole] = useState<TeamMemberRole>(
    team.default_member_role ?? "MEMBER"
  );
  const [allowGuest, setAllowGuest] = useState(!!team.allow_guest_access);
  const [saving, setSaving] = useState(false);

  const dirty =
    isPublic !== !!team.is_public ||
    defaultRole !== (team.default_member_role ?? "MEMBER") ||
    allowGuest !== !!team.allow_guest_access;

  async function save() {
    setSaving(true);
    const userIds = getTeamMembers(team).map((m) => m.id);
    const ccPairIds = team.cc_pairs.map((cc) => cc.id);
    try {
      const res = await updateTeamSettings(team.id, userIds, ccPairIds, {
        is_public: isPublic,
        default_member_role: defaultRole,
        allow_guest_access: allowGuest,
      });
      if (res.ok) {
        toast.success("Team settings saved");
      } else {
        const body = await res.json().catch(() => ({}));
        toast.error(
          `Failed to save settings - ${body.detail || body.message || res.status}`
        );
      }
    } catch (e: any) {
      toast.error(`Failed to save settings - ${e?.message ?? "unknown error"}`);
    } finally {
      setSaving(false);
      onRefresh();
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-16 border bg-background-tint-01 p-5 flex flex-col gap-5">
        <Row
          title="Team visibility"
          description="Public teams are discoverable across the org. Private teams are invite-only."
        >
          <Switch
            checked={isPublic}
            onCheckedChange={setIsPublic}
            disabled={!canManage}
          />
        </Row>

        <Separator noPadding />

        <Row
          title="Default new-member role"
          description="Role assigned when someone joins via SSO or is added to the team."
        >
          <div className="w-[150px]">
            <InputSelect
              value={defaultRole}
              onValueChange={(v) => setDefaultRole(v as TeamMemberRole)}
              disabled={!canManage}
            >
              <InputSelect.Trigger />
              <InputSelect.Content>
                <InputSelect.Item value="ADMIN">
                  {ROLE_LABEL.ADMIN}
                </InputSelect.Item>
                <InputSelect.Item value="MEMBER">
                  {ROLE_LABEL.MEMBER}
                </InputSelect.Item>
              </InputSelect.Content>
            </InputSelect>
          </div>
        </Row>

        <Separator noPadding />

        <Row
          title="Allow guest access"
          description="External collaborators can be added with limited access to KBs and chats."
        >
          <Switch
            checked={allowGuest}
            onCheckedChange={setAllowGuest}
            disabled={!canManage}
          />
        </Row>

        {canManage && (
          <>
            <Separator noPadding />
            <div className="flex items-center justify-between gap-4">
              {/* TODO(backend): the PATCH /api/teams/{id} endpoint currently only
                  persists membership (user_ids / cc_pair_ids). These settings are
                  sent for forward-compatibility and are ignored until the backend
                  is upgraded to store them. */}
              <Text secondaryBody text03 className="text-xs max-w-md">
                Some settings are pending backend support and may not persist yet.
              </Text>
              <Button action onClick={save} disabled={!dirty || saving}>
                {saving ? "Saving…" : "Save changes"}
              </Button>
            </div>
          </>
        )}
      </div>

      {canManage && (
        <div
          className="rounded-16 border p-5"
          style={{
            borderColor: "var(--theme-red-02)",
            backgroundColor: "var(--theme-red-01)",
          }}
        >
          <Text mainUiBody style={{ color: "var(--theme-red-05)" }}>
            Danger zone
          </Text>
          <Text as="p" secondaryBody text03 className="mt-1 text-xs max-w-xl">
            Deleting this team removes all members and resource associations. This
            cannot be undone.
          </Text>
          <div className="mt-3">
            <Button danger leftIcon={SvgTrash} onClick={onDelete}>
              Delete team
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-6">
      <div>
        <Text mainUiBody text04 className="text-sm">
          {title}
        </Text>
        <Text as="p" secondaryBody text03 className="mt-0.5 text-xs max-w-md">
          {description}
        </Text>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}
