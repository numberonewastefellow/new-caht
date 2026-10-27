"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import type { Route } from "next";
import { AdminPageTitle } from "@/components/admin/Title";
import IconButton from "@/refresh-components/buttons/IconButton";
import Text from "@/refresh-components/texts/Text";
import InputTypeIn from "@/refresh-components/inputs/InputTypeIn";
import Switch from "@/refresh-components/inputs/Switch";
import SimpleTabs from "@/refresh-components/SimpleTabs";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SvgClock, SvgEdit, SvgTrash } from "@opal/icons";
import { useSchedules } from "@/hooks/useSchedules";
import { useUser } from "@/providers/UserProvider";
import type { PulseSchedule } from "@/lib/schedules/interfaces";
import { scheduleHref } from "@/lib/schedules/api";
import { formatAbsolute, formatRelative } from "@/lib/schedules/format";
import { inputModeOption, inputSummary } from "@/lib/schedules/inputModes";
import { needsAttention } from "@/lib/schedules/status";
import ScheduleModal from "@/sections/schedules/ScheduleModal";
import DeleteScheduleModal from "@/sections/schedules/DeleteScheduleModal";
import Th from "@/sections/schedules/Th";
import {
  RunStatusPill,
  ScheduleStateBadge,
} from "@/sections/schedules/StatusPill";
import { setEnabledWithToast } from "@/sections/schedules/scheduleActions";

type Filter = "all" | "active" | "paused" | "attention";

/**
 * Admin → Schedules: every user's Pulse schedules. Admins can edit, pause/resume
 * and delete them. Editing never changes the owner (runs keep executing as the
 * owner, who keeps full access and is notified); `updated_by` records the admin.
 */
export default function AdminSchedulesPage() {
  const { user } = useUser();
  const { schedules, isLoading, error } = useSchedules({ allUsers: true });
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<PulseSchedule | null>(null);
  const [toDelete, setToDelete] = useState<PulseSchedule | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const deleteModal = useCreateModal();

  const counts = useMemo(
    () => ({
      all: schedules.length,
      active: schedules.filter((s) => s.enabled).length,
      paused: schedules.filter((s) => !s.enabled).length,
      attention: schedules.filter((s) => needsAttention(s)).length,
      owners: new Set(schedules.map((s) => s.user_id)).size,
    }),
    [schedules]
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return schedules.filter((s) => {
      if (filter === "active" && !s.enabled) return false;
      if (filter === "paused" && s.enabled) return false;
      if (filter === "attention" && !needsAttention(s)) return false;
      if (!q) return true;
      return `${s.name} ${s.workflow_name ?? ""} ${s.owner_email ?? ""}`
        .toLowerCase()
        .includes(q);
    });
  }, [schedules, filter, query]);

  async function toggle(s: PulseSchedule, enabled: boolean) {
    setBusyId(s.id);
    await setEnabledWithToast(s, enabled);
    setBusyId(null);
  }

  const isOwn = (s: PulseSchedule) => !!user && s.user_id === user.id;

  return (
    <>
      <AdminPageTitle
        title="Schedules"
        icon={SvgClock}
        description="All users' scheduled workflows (Pulse). You can edit, pause, resume and delete any schedule. It stays its creator's: runs keep executing as them, they keep access, and they are notified of your changes."
      />

      <deleteModal.Provider>
        {toDelete && (
          <DeleteScheduleModal
            schedule={toDelete}
            onClose={() => {
              setToDelete(null);
              deleteModal.toggle(false);
            }}
          />
        )}
      </deleteModal.Provider>

      {editing && (
        <ScheduleModal
          schedule={editing}
          onClose={() => setEditing(null)}
          allowRunNow={isOwn(editing)}
          ownerNote={
            isOwn(editing)
              ? null
              : `You are editing ${
                  editing.owner_email ?? "another user"
                }'s schedule as an admin. It stays theirs and keeps running as them; they will be notified.`
          }
        />
      )}

      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3 flex-wrap">
          <SimpleTabs
            value={filter}
            onValueChange={(v) => setFilter(v as Filter)}
            tabs={{
              all: { name: `All (${counts.all})`, content: null },
              active: { name: `Active (${counts.active})`, content: null },
              paused: { name: `Paused (${counts.paused})`, content: null },
              attention: {
                name: `Needs attention (${counts.attention})`,
                content: null,
              },
            }}
          />
          <Text as="span" secondaryBody text03>
            {`${counts.owners} user${counts.owners === 1 ? "" : "s"}`}
          </Text>
          <div className="ml-auto w-[18rem]">
            <InputTypeIn
              value={query}
              placeholder="Search name, workflow or owner"
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>

        {error ? (
          <Text
            as="p"
            mainUiBody
            style={{ color: "var(--status-text-error-05)" }}
          >
            Couldn&apos;t load schedules.
          </Text>
        ) : isLoading ? (
          <Text as="p" secondaryBody text03>
            Loading schedules…
          </Text>
        ) : visible.length === 0 ? (
          <Text as="p" secondaryBody text03>
            {schedules.length === 0
              ? "No user has created a schedule yet."
              : "No schedules match."}
          </Text>
        ) : (
          <div className="rounded-12 border border-border-01 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <Th>Schedule</Th>
                  <Th>Owner</Th>
                  <Th>Frequency</Th>
                  <Th>Each run receives</Th>
                  <Th>Next run</Th>
                  <Th>Last run</Th>
                  <Th>Last updated</Th>
                  <Th>On</Th>
                  <Th>
                    <span className="sr-only">Actions</span>
                  </Th>
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((s) => (
                  <TableRow key={s.id} data-schedule-id={s.id}>
                    <TableCell className="py-3 min-w-[11rem]">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <Link
                          href={scheduleHref(s.id) as Route}
                          className="text-text-05 font-medium hover:underline"
                        >
                          {s.name}
                        </Link>
                        <ScheduleStateBadge schedule={s} />
                      </div>
                      <Text as="span" secondaryBody text03>
                        {s.workflow_name ?? `Workflow #${s.workflow_id}`}
                      </Text>
                    </TableCell>
                    <TableCell className="py-3 max-w-[10rem]">
                      <Text
                        as="span"
                        secondaryBody
                        text04
                        className="block truncate"
                        title={s.owner_email ?? undefined}
                      >
                        {isOwn(s) ? "You" : s.owner_email ?? "—"}
                      </Text>
                    </TableCell>
                    <TableCell className="py-3 max-w-[9rem]">
                      <Text as="span" secondaryBody text04>
                        {s.description}
                      </Text>
                    </TableCell>
                    <TableCell className="py-3 max-w-[11rem]">
                      <div title={inputSummary(s)}>
                        <Text as="span" secondaryBody text03>
                          {inputModeOption(s.input_mode).badge}
                        </Text>
                        <Text
                          as="span"
                          secondaryBody
                          text04
                          className="block truncate"
                        >
                          {inputSummary(s)}
                        </Text>
                      </div>
                    </TableCell>
                    <TableCell className="py-3">
                      {s.enabled && s.next_run_at ? (
                        <SimpleTooltip
                          tooltip={formatAbsolute(s.next_run_at, s.timezone)}
                          side="top"
                        >
                          <span className="text-[13px] text-text-04 whitespace-nowrap">
                            {formatRelative(s.next_run_at)}
                          </span>
                        </SimpleTooltip>
                      ) : (
                        <Text as="span" secondaryBody text02>
                          —
                        </Text>
                      )}
                    </TableCell>
                    <TableCell className="py-3">
                      {s.last_run ? (
                        <RunStatusPill status={s.last_run.status} />
                      ) : (
                        <Text as="span" secondaryBody text02>
                          Never
                        </Text>
                      )}
                    </TableCell>
                    <TableCell className="py-3">
                      <Text
                        as="span"
                        secondaryBody
                        text04
                        className="block truncate max-w-[9rem]"
                        title={s.updated_by_email ?? undefined}
                      >
                        {s.updated_by_id && user && s.updated_by_id === user.id
                          ? "You"
                          : s.updated_by_email ?? "—"}
                      </Text>
                      <Text as="span" secondaryBody text02>
                        {formatRelative(s.updated_at)}
                      </Text>
                    </TableCell>
                    <TableCell className="py-3">
                      <Switch
                        checked={s.enabled}
                        disabled={
                          busyId === s.id ||
                          s.disabled_reason === "workflow_deleted"
                        }
                        aria-label={`Enable ${s.name}`}
                        onCheckedChange={(v) => toggle(s, v)}
                      />
                    </TableCell>
                    <TableCell className="py-3">
                      <div className="flex items-center gap-1 justify-end">
                        <IconButton
                          icon={SvgEdit}
                          tooltip="Edit"
                          internal
                          tertiary
                          onClick={() => setEditing(s)}
                          aria-label={`Edit ${s.name}`}
                        />
                        <IconButton
                          icon={SvgTrash}
                          tooltip="Delete"
                          internal
                          tertiary
                          danger
                          onClick={() => {
                            setToDelete(s);
                            deleteModal.toggle(true);
                          }}
                          aria-label={`Delete ${s.name}`}
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </>
  );
}
