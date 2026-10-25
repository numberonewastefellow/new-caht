/**
 * Schedule mutations with user feedback (toasts) + cache refresh. Shared by the
 * Schedules table, the detail page and the sidebar.
 */

import { toast } from "@/hooks/useToast";
import type { PulseRun, PulseSchedule } from "@/lib/schedules/interfaces";
import {
  deleteSchedule,
  duplicateSchedule,
  refreshPulse,
  runScheduleNow,
  updateSchedule,
} from "@/lib/schedules/api";

function errMessage(e: unknown, fallback: string) {
  return e instanceof Error && e.message ? e.message : fallback;
}

export async function runNowWithToast(
  schedule: Pick<PulseSchedule, "id" | "name">
): Promise<PulseRun | null> {
  try {
    const run = await runScheduleNow(schedule.id);
    toast.success(`Run started for “${schedule.name}”`);
    return run;
  } catch (e) {
    toast.error(errMessage(e, "Couldn't start the run"));
    return null;
  } finally {
    void refreshPulse();
  }
}

export async function setEnabledWithToast(
  schedule: Pick<PulseSchedule, "id" | "name" | "disabled_reason">,
  enabled: boolean
): Promise<PulseSchedule | null> {
  try {
    const updated = await updateSchedule(schedule.id, { enabled });
    if (enabled && schedule.disabled_reason === "auto_paused_failures")
      toast.success(`Resumed “${schedule.name}”. The failure count was reset.`);
    else toast.success(`${enabled ? "Enabled" : "Paused"} “${schedule.name}”`);
    return updated;
  } catch (e) {
    toast.error(errMessage(e, "Couldn't update the schedule"));
    return null;
  } finally {
    void refreshPulse();
  }
}

export async function duplicateWithToast(
  schedule: Pick<PulseSchedule, "id">
): Promise<PulseSchedule | null> {
  try {
    const copy = await duplicateSchedule(schedule.id);
    toast.success(`Duplicated as “${copy.name}” — paused until you enable it`);
    return copy;
  } catch (e) {
    toast.error(errMessage(e, "Couldn't duplicate the schedule"));
    return null;
  } finally {
    void refreshPulse();
  }
}

export async function deleteWithToast(
  schedule: Pick<PulseSchedule, "id" | "name">
): Promise<boolean> {
  try {
    await deleteSchedule(schedule.id);
    toast.success(`Deleted “${schedule.name}”. Its run chats were kept.`);
    return true;
  } catch (e) {
    toast.error(errMessage(e, "Couldn't delete the schedule"));
    return false;
  } finally {
    void refreshPulse();
  }
}
