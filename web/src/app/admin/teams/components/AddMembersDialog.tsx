"use client";

import { useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { Team, TeamMemberRole, User } from "@/lib/types";
import { toast } from "@/hooks/useToast";
import Modal from "@/refresh-components/Modal";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import Checkbox from "@/refresh-components/inputs/Checkbox";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import InputSelect from "@/refresh-components/inputs/InputSelect";
import { SvgUserPlus, SvgX } from "@opal/icons";
import { addUsersToTeam } from "../lib";
import { UserAvatar, getTeamMembers } from "./shared";

const ROLE_LABEL: Record<TeamMemberRole, string> = {
  OWNER: "Owner",
  ADMIN: "Admin",
  MEMBER: "Member",
};

interface AddMembersDialogProps {
  open: boolean;
  onClose: () => void;
  team: Team;
  allUsers: User[];
  onAdded: () => void;
}

export default function AddMembersDialog({
  open,
  onClose,
  team,
  allUsers,
  onAdded,
}: AddMembersDialogProps) {
  const [selected, setSelected] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<TeamMemberRole>("MEMBER");
  const [submitting, setSubmitting] = useState(false);

  const excludeIds = useMemo(
    () => new Set(getTeamMembers(team).map((m) => m.id)),
    [team]
  );

  const candidates = useMemo(() => {
    const q = query.trim().toLowerCase();
    return allUsers.filter(
      (u) =>
        !excludeIds.has(u.id) &&
        (!q || u.email.toLowerCase().includes(q))
    );
  }, [allUsers, excludeIds, query]);

  function reset() {
    setSelected([]);
    setQuery("");
    setRole("MEMBER");
    setSubmitting(false);
  }

  function close() {
    onClose();
    reset();
  }

  async function submit() {
    if (selected.length === 0) return;
    setSubmitting(true);
    try {
      const res = await addUsersToTeam(team.id, selected, role);
      if (res.ok) {
        toast.success(
          selected.length === 1
            ? "Member added to team"
            : `${selected.length} members added to team`
        );
        onAdded();
        close();
      } else {
        const body = await res.json().catch(() => ({}));
        toast.error(
          `Failed to add members - ${body.detail || body.message || res.status}`
        );
        setSubmitting(false);
      }
    } catch (e: any) {
      toast.error(`Failed to add members - ${e?.message ?? "unknown error"}`);
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={(o) => !o && close()}>
      <Modal.Content width="sm" height="lg">
        <Modal.Header
          icon={SvgUserPlus}
          title="Add members"
          description="Search existing users by email and choose the role to add them as."
          onClose={close}
        />

        <Modal.Body>
          <div className="flex flex-col gap-3 w-full">
            {selected.length > 0 && (
              <div className="flex flex-wrap gap-1.5 rounded-12 border bg-background-tint-02 p-2">
                {selected.map((id) => {
                  const u = allUsers.find((x) => x.id === id);
                  if (!u) return null;
                  return (
                    <span
                      key={id}
                      className="inline-flex items-center gap-1.5 pl-1 pr-1.5 py-1 rounded-full bg-background-neutral-00 border"
                    >
                      <UserAvatar id={u.id} email={u.email} size={18} />
                      <Text secondaryBody text04 className="text-xs">
                        {u.email}
                      </Text>
                      <button
                        type="button"
                        onClick={() =>
                          setSelected((prev) => prev.filter((x) => x !== id))
                        }
                        className="hover:text-text-05"
                      >
                        <SvgX className="w-3 h-3" />
                      </button>
                    </span>
                  );
                })}
              </div>
            )}

            <InputTypeIn
              autoFocus
              leftSearchIcon
              placeholder="Search by email"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />

            <div className="max-h-[260px] overflow-y-auto rounded-12 border divide-y divide-border-01">
              {candidates.map((u) => {
                const isSel = selected.includes(u.id);
                return (
                  <label
                    key={u.id}
                    className={cn(
                      "flex cursor-pointer items-center gap-3 px-3 py-2.5 transition-colors hover:bg-background-tint-02",
                      isSel && "bg-background-tint-02"
                    )}
                  >
                    <Checkbox
                      checked={isSel}
                      onCheckedChange={() =>
                        setSelected((prev) =>
                          prev.includes(u.id)
                            ? prev.filter((x) => x !== u.id)
                            : [...prev, u.id]
                        )
                      }
                    />
                    <UserAvatar id={u.id} email={u.email} size={30} />
                    <Text mainUiBody text04 className="truncate flex-1 text-sm">
                      {u.email}
                    </Text>
                  </label>
                );
              })}
              {candidates.length === 0 && (
                <div className="px-3 py-8 text-center">
                  <Text secondaryBody text03 className="text-sm">
                    No matching users to add.
                  </Text>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1.5 w-[180px]">
              <Text secondaryBody text03 className="text-xs">
                Add as
              </Text>
              <InputSelect
                value={role}
                onValueChange={(v) => setRole(v as TeamMemberRole)}
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
          </div>
        </Modal.Body>

        <Modal.Footer>
          <Button main tertiary onClick={close}>
            Cancel
          </Button>
          <Button
            action
            leftIcon={SvgUserPlus}
            disabled={selected.length === 0 || submitting}
            onClick={submit}
          >
            {submitting
              ? "Adding…"
              : `Add members${selected.length ? ` (${selected.length})` : ""}`}
          </Button>
        </Modal.Footer>
      </Modal.Content>
    </Modal>
  );
}
