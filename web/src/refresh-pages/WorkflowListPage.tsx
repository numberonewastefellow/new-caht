"use client";

import React, { useMemo, useState } from "react";
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
import { SvgSparkle, SvgTrash, SvgOnyxOctagon } from "@opal/icons";

// Accent used for one-off coloring — adapts to the active accent theme.
const ACCENT = "var(--virtualai-accent, var(--theme-primary-05))";
const ACCENT_SUBTLE = "var(--virtualai-accent-subtle, var(--theme-purple-01))";

type FilterKey = "all" | "autonomous" | "sequential" | "private";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "autonomous", label: "Autonomous" },
  { key: "sequential", label: "Sequential" },
  { key: "private", label: "Private" },
];

function modeMeta(mode: string): { label: string; bg: string; fg: string } {
  if (mode === "llm_decision")
    return { label: "Autonomous", bg: ACCENT_SUBTLE, fg: ACCENT };
  if (mode === "sequential")
    return {
      label: "Sequential",
      bg: "var(--theme-blue-01)",
      fg: "var(--theme-blue-05)",
    };
  return { label: mode, bg: "var(--background-tint-02)", fg: "var(--text-02)" };
}

const MAX_CHAIN = 4;

function AgentChain({ workflow }: { workflow: WorkflowSnapshot }) {
  const names = workflow.steps.map(
    (s) => s.persona_name || `Agent #${s.persona_id}`
  );
  const shown = names.slice(0, MAX_CHAIN);
  const extra = names.length - shown.length;

  return (
    <div className="flex items-center gap-1.5 flex-wrap mt-2 min-w-0">
      <Text secondaryBody text02 className="text-xs flex-shrink-0">
        {names.length} agent{names.length !== 1 ? "s" : ""}
      </Text>
      {shown.map((name, i) => (
        <React.Fragment key={i}>
          <span className="text-text-03 text-xs">→</span>
          <span
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border max-w-[12rem] truncate"
            style={{
              borderColor: "var(--line-01)",
              color: "var(--text-02)",
              backgroundColor: "var(--background-tint-01)",
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: ACCENT }}
            />
            <span className="truncate">{name}</span>
          </span>
        </React.Fragment>
      ))}
      {extra > 0 && (
        <span className="text-text-03 text-xs">+{extra} more</span>
      )}
    </div>
  );
}

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
  const mode = modeMeta(workflow.orchestration_mode);

  return (
    <Card
      padding={1}
      className="hover:bg-background-tint-01 hover:shadow-[0_4px_24px_var(--virtualai-accent-glow)] transition-all"
    >
      <div className="flex items-center gap-4 w-full">
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{
            backgroundColor: ACCENT_SUBTLE,
            boxShadow: "0 0 0 1px var(--virtualai-accent-glow)",
          }}
        >
          <SvgSparkle className="w-5 h-5" style={{ stroke: ACCENT }} />
        </div>

        <div className="flex-1 min-w-0 overflow-hidden">
          <div className="flex items-center gap-2 flex-wrap">
            <Text mainContentEmphasis className="truncate">
              {workflow.name}
            </Text>
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
              style={{ backgroundColor: mode.bg, color: mode.fg }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: mode.fg }}
              />
              {mode.label}
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
          <AgentChain workflow={workflow} />
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
            title="Delete agentic system"
          >
            <SvgTrash className="w-4 h-4" />
          </button>
        </div>
      </div>
    </Card>
  );
}

function KpiTile({
  value,
  label,
  accent,
}: {
  value: number;
  label: string;
  accent?: boolean;
}) {
  return (
    <Card padding={1}>
      <div className="flex flex-col">
        <div
          className="text-[1.75rem] leading-none font-bold"
          style={{ color: accent ? ACCENT : "var(--text-01)" }}
        >
          {value}
        </div>
        <Text secondaryBody text03 className="text-xs mt-1 uppercase tracking-wide">
          {label}
        </Text>
      </div>
    </Card>
  );
}

export default function WorkflowListPage() {
  const router = useRouter();
  const { workflows, isLoading, refresh } = useWorkflows();
  const deleteModal = useCreateModal();
  const [workflowToDelete, setWorkflowToDelete] =
    useState<WorkflowSnapshot | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterKey>("all");
  const { setVersion } = useVersionSwitch();

  const stats = useMemo(
    () => ({
      total: workflows.length,
      autonomous: workflows.filter(
        (w) => w.orchestration_mode === "llm_decision"
      ).length,
      sequential: workflows.filter(
        (w) => w.orchestration_mode === "sequential"
      ).length,
      agents: workflows.reduce((sum, w) => sum + w.steps.length, 0),
    }),
    [workflows]
  );

  const filteredWorkflows = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return workflows.filter((w) => {
      const matchesFilter =
        activeFilter === "all"
          ? true
          : activeFilter === "private"
            ? !w.is_public
            : activeFilter === "autonomous"
              ? w.orchestration_mode === "llm_decision"
              : activeFilter === "sequential"
                ? w.orchestration_mode === "sequential"
                : true;
      const matchesSearch =
        !q ||
        w.name.toLowerCase().includes(q) ||
        (w.description ? w.description.toLowerCase().includes(q) : false);
      return matchesFilter && matchesSearch;
    });
  }, [workflows, searchQuery, activeFilter]);

  async function handleDelete() {
    if (!workflowToDelete) return;

    const response = await deleteWorkflow(workflowToDelete.id);
    if (!response.ok) {
      toast.error("Failed to delete agentic system");
      return;
    }

    toast.success(`"${workflowToDelete.name}" deleted`);
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
            title="Delete Agentic System"
            submit={
              <Button danger onClick={handleDelete}>
                Delete
              </Button>
            }
            onClose={() => {
              setWorkflowToDelete(null);
              deleteModal.toggle(false);
            }}
          >
            <GeneralLayouts.Section alignItems="start" gap={0.5}>
              <Text>
                Delete &quot;{workflowToDelete.name}&quot;? This action cannot be
                undone.
              </Text>
            </GeneralLayouts.Section>
          </ConfirmationModalLayout>
        )}
      </deleteModal.Provider>

      <SettingsLayouts.Root width="lg">
        {/* ── Hero ─────────────────────────────────────────────── */}
        <div className="w-full bg-background-tint-01 px-4 pt-10">
          <div className="flex flex-col gap-6">
            <div className="flex flex-row justify-between items-start gap-4">
              <div className="flex items-start gap-3 min-w-0">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{
                    backgroundColor: ACCENT_SUBTLE,
                    boxShadow:
                      "0 0 0 1px var(--virtualai-accent-glow), 0 8px 24px var(--virtualai-accent-glow)",
                  }}
                >
                  <SvgSparkle className="w-6 h-6" style={{ stroke: ACCENT }} />
                </div>
                <div className="flex flex-col min-w-0">
                  <Text as="p" headingH1 className="virtualai-gradient-text">
                    Agentic AI
                  </Text>
                  <Text as="p" secondaryBody text03>
                    Build, orchestrate &amp; manage autonomous multi-agent
                    systems
                  </Text>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Button tertiary onClick={() => setVersion("legacy")}>
                  Classic view
                </Button>
                <Button
                  secondary
                  onClick={() => router.push("/admin/workflows/visual")}
                >
                  Visual Builder
                </Button>
                <Button
                  leftIcon={SvgSparkle}
                  onClick={() => router.push("/admin/workflows/create")}
                >
                  New Agent
                </Button>
              </div>
            </div>

            {/* KPI strip */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <KpiTile value={stats.total} label="Systems" />
              <KpiTile value={stats.autonomous} label="Autonomous" accent />
              <KpiTile value={stats.sequential} label="Sequential" />
              <KpiTile value={stats.agents} label="Agents" />
            </div>

            {/* Filters + search */}
            <div className="flex items-center gap-2 flex-wrap">
              {FILTERS.map((f) => {
                const active = activeFilter === f.key;
                return (
                  <button
                    key={f.key}
                    onClick={() => setActiveFilter(f.key)}
                    className="px-3 py-1.5 rounded-full text-xs font-medium border transition-colors"
                    style={
                      active
                        ? {
                            backgroundColor: ACCENT,
                            color: "#fff",
                            borderColor: ACCENT,
                          }
                        : {
                            backgroundColor: "var(--background-tint-02)",
                            color: "var(--text-02)",
                            borderColor: "var(--line-01)",
                          }
                    }
                  >
                    {f.label}
                  </button>
                );
              })}
              <input
                type="text"
                placeholder="Search agents by name or description..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="ml-auto min-w-[16rem] max-w-[22rem] flex-1 px-3 py-2 rounded-lg text-sm
                  bg-background-tint-02 text-text-01 placeholder-text-03
                  border border-line-01 focus:outline-none focus:ring-1
                  focus:ring-[var(--virtualai-accent,#6366f1)]
                  focus:border-[var(--virtualai-accent,#6366f1)]
                  transition-colors"
              />
            </div>
          </div>
        </div>

        {/* ── Body / list ──────────────────────────────────────── */}
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
                  style={{ backgroundColor: ACCENT_SUBTLE }}
                >
                  <SvgOnyxOctagon
                    className="w-8 h-8"
                    style={{ stroke: ACCENT }}
                  />
                </div>
                <Text mainContentEmphasis>No agentic systems yet</Text>
                <Text secondaryBody text03 className="text-center max-w-sm">
                  Create an agentic system to coordinate multiple AI agents
                  working together on complex tasks.
                </Text>
                <Button
                  leftIcon={SvgSparkle}
                  onClick={() => router.push("/admin/workflows/create")}
                >
                  Create Your First Agent
                </Button>
              </div>
            </Card>
          ) : filteredWorkflows.length === 0 ? (
            <Card padding={1}>
              <div className="flex flex-col items-center gap-2 py-6">
                <Text secondaryBody text03>
                  No agentic systems match your filters
                </Text>
              </div>
            </Card>
          ) : (
            <GeneralLayouts.Section gap={0.5}>
              {filteredWorkflows.map((workflow) => (
                <WorkflowCard
                  key={workflow.id}
                  workflow={workflow}
                  onEdit={() =>
                    router.push(`/admin/workflows/edit/${workflow.id}`)
                  }
                  onVisualEdit={() =>
                    router.push(`/admin/workflows/visual/${workflow.id}`)
                  }
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
