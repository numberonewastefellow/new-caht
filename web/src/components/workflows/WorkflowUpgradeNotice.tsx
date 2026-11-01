"use client";

import { useState } from "react";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { toast } from "@/hooks/useToast";
import { describeSaveError, saveWorkflow } from "@/lib/workflows/api";
import type { WorkflowSnapshot } from "@/lib/workflows/interfaces";

const OLD_REFERENCE_FORMAT = 1;
const CURRENT_REFERENCE_FORMAT = 2;

/**
 * An older workflow can't read one field of a step's result ($step.output.status). Upgrading
 * is the owner's choice, because it makes every reference in the workflow stricter: one that
 * can't resolve then stops the save with its name, rather than reading as empty at run time.
 */
export default function WorkflowUpgradeNotice({
  workflow,
  onUpgraded,
}: {
  workflow: WorkflowSnapshot | null | undefined;
  onUpgraded: (upgraded: WorkflowSnapshot) => void;
}) {
  const [busy, setBusy] = useState(false);
  if (workflow?.schema_version !== OLD_REFERENCE_FORMAT) return null;
  const { id, version } = workflow;

  async function handleUpgrade() {
    setBusy(true);
    try {
      const upgraded = await saveWorkflow(id, {
        schema_version: CURRENT_REFERENCE_FORMAT,
        expected_version: version,
      });
      toast.success("References upgraded.");
      onUpgraded(upgraded);
    } catch (e) {
      toast.error(describeSaveError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="flex items-center justify-between gap-3 flex-wrap rounded-08 border border-border-01 bg-background-tint-01 px-3 py-2"
      data-testid="workflow-upgrade-notice"
    >
      <Text as="p" secondaryBody text04>
        This workflow uses the older reference format, so steps can&apos;t read one field of a
        result, like $step.output.status. Save any changes before you upgrade.
      </Text>
      <Button type="button" secondary disabled={busy} onClick={handleUpgrade}>
        Upgrade references
      </Button>
    </div>
  );
}
