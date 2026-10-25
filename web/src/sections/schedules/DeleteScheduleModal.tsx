"use client";

import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import * as GeneralLayouts from "@/layouts/general-layouts";
import { SvgTrash } from "@opal/icons";
import type { PulseSchedule } from "@/lib/schedules/interfaces";
import { deleteWithToast } from "@/sections/schedules/scheduleActions";

export interface DeleteScheduleModalProps {
  schedule: Pick<PulseSchedule, "id" | "name">;
  onClose: () => void;
  onDeleted?: () => void;
}

/** Render inside a `useCreateModal()` Provider. */
export default function DeleteScheduleModal({
  schedule,
  onClose,
  onDeleted,
}: DeleteScheduleModalProps) {
  async function handleDelete() {
    const ok = await deleteWithToast(schedule);
    if (!ok) return;
    onClose();
    onDeleted?.();
  }

  return (
    <ConfirmationModalLayout
      icon={SvgTrash}
      title="Delete schedule"
      submit={
        <Button danger onClick={handleDelete}>
          Delete
        </Button>
      }
      onClose={onClose}
    >
      <GeneralLayouts.Section alignItems="start" gap={0.5}>
        <Text>
          Delete &quot;{schedule.name}&quot;? It stops running and its run
          history is removed. Chats created by earlier runs stay in your chat
          history.
        </Text>
      </GeneralLayouts.Section>
    </ConfirmationModalLayout>
  );
}
