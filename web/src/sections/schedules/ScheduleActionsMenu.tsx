"use client";

import { useState } from "react";
import Popover, { PopoverMenu } from "@/refresh-components/Popover";
import IconButton from "@/refresh-components/buttons/IconButton";
import LineItem from "@/refresh-components/buttons/LineItem";
import { noProp } from "@/lib/utils";
import {
  SvgCopy,
  SvgEdit,
  SvgHistory,
  SvgMoreHorizontal,
  SvgPlayCircle,
  SvgSparkle,
  SvgTrash,
} from "@opal/icons";

export interface ScheduleActionsMenuProps {
  onRunNow?: () => void;
  onEdit?: () => void;
  onDuplicate?: () => void;
  onViewRuns?: () => void;
  onOpenWorkflow?: () => void;
  onDelete: () => void;
  /** Visual style of the trigger */
  bordered?: boolean;
}

/** ⋯ menu for a schedule (Run now / Edit / Duplicate / View runs / Delete). */
export default function ScheduleActionsMenu({
  onRunNow,
  onEdit,
  onDuplicate,
  onViewRuns,
  onOpenWorkflow,
  onDelete,
  bordered,
}: ScheduleActionsMenuProps) {
  const [open, setOpen] = useState(false);

  const act = (fn?: () => void) =>
    noProp(() => {
      setOpen(false);
      fn?.();
    });

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <div className="inline-flex">
          <IconButton
            icon={SvgMoreHorizontal}
            tooltip="More actions"
            aria-label="More actions"
            secondary={bordered}
            tertiary={!bordered}
            transient={open}
          />
        </div>
      </Popover.Trigger>
      <Popover.Content side="bottom" align="end" width="lg">
        <PopoverMenu>
          {[
            onRunNow && (
              <LineItem key="run" icon={SvgPlayCircle} onClick={act(onRunNow)}>
                Run now
              </LineItem>
            ),
            onEdit && (
              <LineItem key="edit" icon={SvgEdit} onClick={act(onEdit)}>
                Edit
              </LineItem>
            ),
            onDuplicate && (
              <LineItem key="dup" icon={SvgCopy} onClick={act(onDuplicate)}>
                Duplicate
              </LineItem>
            ),
            onViewRuns && (
              <LineItem key="runs" icon={SvgHistory} onClick={act(onViewRuns)}>
                View runs
              </LineItem>
            ),
            onOpenWorkflow && (
              <LineItem
                key="wf"
                icon={SvgSparkle}
                onClick={act(onOpenWorkflow)}
              >
                Open workflow
              </LineItem>
            ),
            null,
            <LineItem key="del" icon={SvgTrash} danger onClick={act(onDelete)}>
              Delete
            </LineItem>,
          ]}
        </PopoverMenu>
      </Popover.Content>
    </Popover>
  );
}
