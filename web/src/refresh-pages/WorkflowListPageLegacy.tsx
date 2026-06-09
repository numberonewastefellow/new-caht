"use client";

// TODO(agentic-ui-cleanup): TEMPORARY legacy page for backward-compat during the Agentic AI rollout.
// DELETE once the new UI is verified in production. Removal steps:
//   1) delete this *Legacy.tsx file
//   2) in web/src/app/admin/workflows/page.tsx, render <WorkflowListPage/> directly (drop <VersionedPage> wrapper)
//   3) remove the "Classic view" switch button from WorkflowListPage.tsx
//   4) if NO other page still uses versioning: delete usePageVersion.ts, VersionedPage.tsx,
//      UiConfigProvider.tsx, the layout.tsx wiring + the DEFAULT_UI_VERSION env var
// Tracking: AGENTIC_AI_REBRAND_PLAN.md -> "Legacy cleanup checklist"
//
// This file is a VERBATIM copy of the pre-redesign WorkflowListPage, with one
// addition: a "Try the new Agentic AI view" switch in the header.

import React from "react";
import { useRouter } from "next/navigation";
import * as SettingsLayouts from "@/layouts/settings-layouts";
import * as GeneralLayouts from "@/layouts/general-layouts";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { Card } from "@/refresh-components/cards";
import { useWorkflows } from "@/hooks/useWorkflows";
import { deleteWorkflow } from "@/lib/workflows/api";
import { WorkflowSnapshot } from "@/lib/workflows/interfaces";
import { toast } from "@/hooks/useToast";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import { useVersionSwitch } from "@/refresh-components/VersionedPage";
import {
  SvgSliders,
  SvgSparkle,
  SvgTrash,
  SvgOnyxOctagon,
} from "@opal/icons";

function WorkflowCard({
  workflow,
  onEdit,
  onVisualEdit,
  onDelete,
}: {
  workflow: WorkflowSnapshot;
  onEdit: () => void;
  onVisualEdit: () => void;
  onDelete: () => void;
}) {
  const stepCount = workflow.steps.length;
  const modeLabel =
    workflow.orchestration_mode === "llm_decision"
      ? "LLM Decision"
      : workflow.orchestration_mode === "sequential"
        ? "Sequential"
        : workflow.orchestration_mode;

  return (
    <Card padding={1} className="hover:bg-background-tint-01 transition-colors">
      <div className="flex items-center gap-4 w-full">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: "var(--theme-purple-01)" }}
        >
          <SvgSliders className="w-5 h-5" style={{ stroke: "var(--theme-purple-05)" }} />
        </div>

        <div className="flex-1 min-w-0 overflow-hidden">
          <div className="flex items-center gap-2">
            <Text mainContentEmphasis className="truncate">
              {workflow.name}
            </Text>
            <span
              className="px-2 py-0.5 rounded-full text-xs"
              style={{
                backgroundColor: "var(--theme-blue-01)",
                color: "var(--theme-blue-05)",
              }}
            >
              {modeLabel}
            </span>
            {!workflow.is_public && (
              <span
                className="px-2 py-0.5 rounded-full text-xs"
                style={{
                  backgroundColor: "var(--theme-orange-01)",
                  color: "var(--theme-orange-05)",
                }}
              >
                Private
              </span>
            )}
          </div>
          <Text secondaryBody text03 className="truncate">
            {workflow.description || "No description"}
          </Text>
          <div className="flex items-center gap-3 mt-1 min-w-0">
            <Text secondaryBody text02 className="text-xs flex-shrink-0">
              {stepCount} step{stepCount !== 1 ? "s" : ""}
            </Text>
            <Text secondaryBody text02 className="text-xs truncate">
              {workflow.steps
                .map((s) => s.persona_name || `Agent #${s.persona_id}`)
                .join(" → ")}
            </Text>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <Button secondary onClick={onVisualEdit}>
            Visual
          </Button>
          <Button secondary onClick={onEdit}>
            Edit
          </Button>
          <button
            className="p-2 rounded-8 hover:bg-theme-red-01 text-text-02 hover:text-theme-red-05 transition-colors"
            onClick={onDelete}
            title="Delete workflow"
          >
            <SvgTrash className="w-4 h-4" />
          </button>
        </div>
      </div>
    </Card>
  );
}

export default function WorkflowListPageLegacy() {
  const router = useRouter();
  const { workflows, isLoading, refresh } = useWorkflows();
  const deleteModal = useCreateModal();
  const [workflowToDelete, setWorkflowToDelete] = React.useState<WorkflowSnapshot | null>(null);
  const [searchQuery, setSearchQuery] = React.useState("");
  const { setVersion } = useVersionSwitch();

  const filteredWorkflows = React.useMemo(() => {
    if (!searchQuery.trim()) return workflows;
    const q = searchQuery.toLowerCase();
    return workflows.filter(
      (w) =>
        w.name.toLowerCase().includes(q) ||
        (w.description && w.description.toLowerCase().includes(q))
    );
  }, [workflows, searchQuery]);

  async function handleDelete() {
    if (!workflowToDelete) return;

    const response = await deleteWorkflow(workflowToDelete.id);
    if (!response.ok) {
      toast.error("Failed to delete workflow");
      return;
    }

    toast.success(`Workflow "${workflowToDelete.name}" deleted`);
    setWorkflowToDelete(null);
    deleteModal.toggle(false);
    await refresh();
  }

  return (
    <>
      <deleteModal.Provider>
        {deleteModal.isOpen && workflowToDelete && (
          <ConfirmationModalLayout
            icon={SvgTrash}
            title="Delete Workflow"
            submit={
              <Button danger onClick={handleDelete}>
                Delete Workflow
              </Button>
            }
            onClose={() => {
              setWorkflowToDelete(null);
              deleteModal.toggle(false);
            }}
          >
            <GeneralLayouts.Section alignItems="start" gap={0.5}>
              <Text>
                Delete &quot;{workflowToDelete.name}&quot;? This action cannot be undone.
              </Text>
            </GeneralLayouts.Section>
          </ConfirmationModalLayout>
        )}
      </deleteModal.Provider>

      <SettingsLayouts.Root width="lg">
        <SettingsLayouts.Header
          icon={SvgSliders}
          title="Workflows"
          description="Create and manage multi-agent workflows"
          rightChildren={
            <div className="flex items-center gap-2">
              <Button tertiary onClick={() => setVersion("new")}>
                Try the new Agentic AI view
              </Button>
              <Button secondary onClick={() => router.push("/admin/workflows/visual")}>
                Visual Builder
              </Button>
              <Button leftIcon={SvgSparkle} onClick={() => router.push("/admin/workflows/create")}>
                New Workflow
              </Button>
            </div>
          }
        >
          <input
            type="text"
            placeholder="Search workflows by name or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 rounded-lg text-sm
              bg-background-tint-02 text-text-01 placeholder-text-03
              border border-line-01 focus:outline-none focus:ring-1
              focus:ring-[var(--virtualai-accent,#6366f1)]
              focus:border-[var(--virtualai-accent,#6366f1)]
              transition-colors"
          />
        </SettingsLayouts.Header>

        <SettingsLayouts.Body>
          {isLoading ? (
            <GeneralLayouts.Section gap={0.5}>
              {[1, 2, 3].map((i) => (
                <Card key={i} padding={1}>
                  <div className="h-16 animate-pulse bg-background-tint-02 rounded-8" />
                </Card>
              ))}
            </GeneralLayouts.Section>
          ) : workflows.length === 0 ? (
            <Card padding={2}>
              <div className="flex flex-col items-center gap-3 py-8">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center"
                  style={{ backgroundColor: "var(--theme-purple-01)" }}
                >
                  <SvgOnyxOctagon className="w-8 h-8" style={{ stroke: "var(--theme-purple-05)" }} />
                </div>
                <Text mainContentEmphasis>No workflows yet</Text>
                <Text secondaryBody text03 className="text-center max-w-sm">
                  Create a workflow to coordinate multiple agents working together on complex tasks.
                </Text>
                <Button leftIcon={SvgSparkle} onClick={() => router.push("/admin/workflows/create")}>
                  Create Your First Workflow
                </Button>
              </div>
            </Card>
          ) : filteredWorkflows.length === 0 ? (
            <Card padding={1}>
              <div className="flex flex-col items-center gap-2 py-6">
                <Text secondaryBody text03>
                  No workflows match &quot;{searchQuery}&quot;
                </Text>
              </div>
            </Card>
          ) : (
            <GeneralLayouts.Section gap={0.5}>
              {filteredWorkflows.map((workflow) => (
                <WorkflowCard
                  key={workflow.id}
                  workflow={workflow}
                  onEdit={() => router.push(`/admin/workflows/edit/${workflow.id}`)}
                  onVisualEdit={() => router.push(`/admin/workflows/visual/${workflow.id}`)}
                  onDelete={() => {
                    setWorkflowToDelete(workflow);
                    deleteModal.toggle(true);
                  }}
                />
              ))}
            </GeneralLayouts.Section>
          )}
        </SettingsLayouts.Body>
      </SettingsLayouts.Root>
    </>
  );
}
