"use client";

import React, { useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import * as SettingsLayouts from "@/layouts/settings-layouts";
import * as GeneralLayouts from "@/layouts/general-layouts";
import * as InputLayouts from "@/layouts/input-layouts";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { Card } from "@/refresh-components/cards";
import Separator from "@/refresh-components/Separator";
import InputTypeInField from "@/refresh-components/form/InputTypeInField";
import InputTextAreaField from "@/refresh-components/form/InputTextAreaField";
import SwitchField from "@/refresh-components/form/SwitchField";
import SimpleTooltip from "@/refresh-components/SimpleTooltip";
import { Formik, Form, FieldArray, useFormikContext } from "formik";
import * as Yup from "yup";
import { useAgents } from "@/hooks/useAgents";
import { selectableStepAgents } from "@/lib/workflows/stepAgents";
import { StepPlacementFields } from "@/components/workflows/StepPlacementFields";
import { ancestorsOf } from "@/lib/workflows/containerRules";
import {
  canReorder,
  descendantKeys,
  moveStep,
  removeStep,
  reorderInBlock,
} from "@/lib/workflows/stepTree";
import {
  MAX_CALLS_PER_AGENT,
  MAX_ORCHESTRATOR_STEPS,
  MAX_TIMEOUT_SECONDS,
  MIN_TIMEOUT_SECONDS,
} from "@/lib/workflows/workflowLimits";
import { useWorkflows } from "@/hooks/useWorkflows";
import { useLLMProviders } from "@/lib/hooks/useLLMProviders";
import { parseLlmDescriptor, structureValue } from "@/lib/llm/utils";
import LLMSelector from "@/components/llm/LLMSelector";
import {
  deleteWorkflow,
  describeSaveError,
  saveWorkflow,
} from "@/lib/workflows/api";
import type {
  NodeUpgradeResult,
  WorkflowSnapshot,
} from "@/lib/workflows/interfaces";
import {
  type EditorStep,
  type WorkflowMeta,
  DEFAULT_WORKFLOW_META,
  createEditorStep,
  newNodeKey,
  nextOutputKey,
} from "@/lib/workflows/editorModel";
import {
  type NodeCatalog,
  AGENT_NODE_TYPE,
  ROUTER_NODE_TYPE,
  editorKindFor,
  isAllowedInMode,
  labelFor,
  paletteTypes,
  resolveVersion,
} from "@/lib/workflows/nodeRegistry";
import {
  buildWorkflowCreate,
  buildWorkflowUpdate,
  snapshotToEditorSteps,
  snapshotToMeta,
  stepOrderToNodeKey,
} from "@/lib/workflows/serializer";
import {
  stepDisplayName,
  stepsNotAllowedInMode,
  validateSteps,
} from "@/lib/workflows/validation";
import { useNodeTypes } from "@/lib/workflows/useNodeTypes";
import { SchemaConfigForm } from "@/components/workflows/SchemaConfigForm";
import {
  NodeUpgradeDialog,
  type NodeUpgradeTarget,
} from "@/components/workflows/NodeUpgradeDialog";
import { WorkflowVersionsDialog } from "@/components/workflows/WorkflowVersionsDialog";
import { RouterStepFields } from "@/components/workflows/wizard/RouterStepFields";
import { toast } from "@/hooks/useToast";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import {
  SvgArrowLeft,
  SvgArrowRight,
  SvgArrowUpCircle,
  SvgHistory,
  SvgInfoSmall,
  SvgSettings,
  SvgSliders,
  SvgSparkle,
  SvgTrash,
  SvgOmOctagon,
} from "@opal/icons";
import { cn } from "@/lib/utils";

// ─── Info Tooltip ────────────────────────────────────────────────────────

function InfoTip({ children }: { children: string }) {
  return (
    <SimpleTooltip
      tooltip={
        <div className="max-w-xs text-xs leading-relaxed">
          {children}
        </div>
      }
      side="top"
      delayDuration={200}
    >
      <span className="inline-flex items-center cursor-help ml-1">
        <SvgInfoSmall className="w-3.5 h-3.5 stroke-text-03 hover:stroke-text-05 transition-colors" />
      </span>
    </SimpleTooltip>
  );
}

// ─── Step Indicator ─────────────────────────────────────────────────────

const TOTAL_STEPS = 3;

const STEP_CONFIG = [
  { label: "Identity", subtitle: "Name & details", color: "blue" },
  { label: "Agent Steps", subtitle: "Add agents", color: "purple" },
  { label: "Configure", subtitle: "Orchestration settings", color: "green" },
] as const;

const DEFAULT_STEP_COLOR = { bg01: "var(--theme-blue-01)", bg05: "var(--theme-blue-05)", text04: "var(--theme-blue-04)" };

const STEP_COLORS: Record<string, { bg01: string; bg05: string; text04: string }> = {
  blue: DEFAULT_STEP_COLOR,
  purple: { bg01: "var(--theme-purple-01)", bg05: "var(--theme-purple-05)", text04: "var(--theme-purple-04)" },
  green: { bg01: "var(--theme-green-01)", bg05: "var(--theme-green-05)", text04: "var(--theme-green-04)" },
};

function StepIndicator({ currentStep, onStepClick }: { currentStep: number; onStepClick?: (step: number) => void }) {
  return (
    <div className="flex items-center gap-2 px-4 py-5">
      {STEP_CONFIG.map((step, i) => {
        const isCurrent = i === currentStep;
        const isCompleted = i < currentStep;
        const colors = STEP_COLORS[step.color] ?? DEFAULT_STEP_COLOR;

        return (
          <React.Fragment key={i}>
            <div
              className={cn("flex items-center gap-2.5 min-w-0", isCompleted && onStepClick && "cursor-pointer")}
              onClick={() => isCompleted && onStepClick?.(i)}
            >
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300"
                style={{ backgroundColor: isCurrent ? colors.bg05 : isCompleted ? colors.bg01 : "var(--background-tint-03)" }}
              >
                <Text as="span" style={{ color: isCurrent ? "var(--background-tint-00)" : "var(--text-02)" }}>
                  {i + 1}
                </Text>
              </div>
              <div className="flex flex-col min-w-0">
                <Text as="span" mainUiAction className="truncate" style={{ color: isCurrent ? colors.bg05 : "var(--text-02)" }}>
                  {step.label}
                </Text>
                <Text as="span" secondaryBody className="truncate" style={{ color: isCurrent ? colors.text04 : "var(--text-02)" }}>
                  {step.subtitle}
                </Text>
              </div>
            </div>
            {i < STEP_CONFIG.length - 1 && (
              <div
                className="flex-1 h-0.5 rounded-full transition-colors duration-300"
                style={{ backgroundColor: isCompleted ? colors.bg05 : "var(--background-tint-03)" }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Workflow Step Row ───────────────────────────────────────────────────

/** Formik values of the Wizard: workflow settings plus editor steps. */
type WizardValues = WorkflowMeta & { steps: EditorStep[] };

/** Step types offered for a step: the palette for the mode, plus its own type. */
function stepTypeOptions(
  catalog: NodeCatalog,
  mode: WizardValues["orchestration_mode"],
  currentType: string
): { value: string; label: string }[] {
  const options = paletteTypes(catalog, mode).map((t) => ({
    value: t.type,
    label: labelFor(catalog, t.type),
  }));
  if (!options.some((o) => o.value === currentType)) {
    options.push({ value: currentType, label: labelFor(catalog, currentType) });
  }
  return options;
}

const CONTAINER_INDENT_PX = 28;

const PLACEMENT_CLASSES = {
  section: "min-w-[12rem]",
  label: "flex flex-col gap-1 text-xs text-text-03",
  select: "h-9 px-2 rounded-8 border border-border bg-background text-sm text-text-05",
};

interface WorkflowStepRowProps {
  index: number;
  agents: { id: number; name: string; description: string }[];
  catalog: NodeCatalog;
  onRemove: () => void;
  canRemove: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onUpgrade: () => void;
}

function WorkflowStepRow({
  index,
  agents,
  catalog,
  onRemove,
  canRemove,
  canMoveUp,
  canMoveDown,
  onMoveUp,
  onMoveDown,
  onUpgrade,
}: WorkflowStepRowProps) {
  const { values, setFieldValue, errors, touched } =
    useFormikContext<WizardValues>();
  const step = values.steps[index]!;
  const kind = editorKindFor(catalog, step.step_type);
  const isConditionalRouter = kind === "router";
  const typeInfo = resolveVersion(catalog, step.step_type, step.type_version);
  // Only node types that can pause may ask the user for input.
  const canPause = typeInfo?.can_pause ?? kind === "agent";
  const modeConflict = !isAllowedInMode(
    catalog,
    step.step_type,
    step.type_version,
    values.orchestration_mode
  );
  const stepErrors = (errors.steps as any)?.[index];
  const stepTouched = (touched.steps as any)?.[index];

  const changeType = (type: string) =>
    setFieldValue(
      `steps.${index}`,
      createEditorStep(type, catalog, {
        node_key: step.node_key,
        step_name: step.step_name,
        step_description: step.step_description,
        output_key: step.output_key,
        parent_key: step.parent_key,
        branch_index: step.branch_index,
        is_terminal: step.is_terminal,
        promote_output: step.promote_output,
      })
    );
  const depth = ancestorsOf(
    step,
    new Map(values.steps.map((s) => [s.node_key, s]))
  ).length;

  return (
    <div style={{ marginLeft: depth * CONTAINER_INDENT_PX }}>
    <Card padding={1}>
      <div className="flex items-start gap-3">
        {/* Step number */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1"
          style={{
            backgroundColor: isConditionalRouter
              ? "var(--theme-green-01)"
              : "var(--theme-purple-01)",
          }}
        >
          <Text
            as="span"
            style={{
              color: isConditionalRouter
                ? "var(--theme-green-05)"
                : "var(--theme-purple-05)",
            }}
          >
            {index + 1}
          </Text>
        </div>

        <div className="flex-1 space-y-4">
          {/* Row 0: Step name + type */}
          <div className="grid grid-cols-2 gap-4">
            <InputLayouts.Vertical
              name={`steps.${index}.step_name`}
              title="Step Name"
              description="A short label for this step shown during execution."
            >
              <InputTypeInField
                name={`steps.${index}.step_name`}
                placeholder={
                  isConditionalRouter
                    ? "e.g. Check Error, Route by Status..."
                    : "e.g. Research, Summarize, Find Flights..."
                }
              />
            </InputLayouts.Vertical>

            <div className="flex flex-col gap-0.5">
              <div className="flex items-center gap-1">
                <Text mainContentEmphasis text04>Step Type</Text>
                <InfoTip>
                  Agent steps run an AI agent. Condition steps evaluate a condition and skip the steps of the losing branch. Other types come from the node type catalog.
                </InfoTip>
              </div>
              <select
                value={step.step_type}
                disabled={kind === "unsupported"}
                className="w-full h-10 px-3 rounded-8 border border-border bg-background-tint-00 text-text-05 text-sm"
                onChange={(e) => changeType(e.target.value)}
              >
                {stepTypeOptions(catalog, values.orchestration_mode, step.step_type).map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              {step.upgrade_available && (
                <button
                  type="button"
                  onClick={onUpgrade}
                  className="self-start mt-1 inline-flex items-center gap-1 text-xs"
                  style={{ color: "var(--virtualai-accent, var(--theme-primary-05))" }}
                >
                  <SvgArrowUpCircle className="w-3.5 h-3.5" style={{ stroke: "currentColor" }} />
                  Upgrade available
                </button>
              )}
            </div>
          </div>

          {values.orchestration_mode === "sequential" && (
            <div className="flex flex-wrap gap-3">
              <StepPlacementFields
                step={step}
                steps={values.steps}
                catalog={catalog}
                classes={PLACEMENT_CLASSES}
                onMove={(place) =>
                  setFieldValue(
                    "steps",
                    moveStep(values.steps, step.node_key, place)
                  )
                }
              />
            </div>
          )}

          {modeConflict && (
            <Text secondaryBody className="text-xs text-status-warning-05">
              This step type can&apos;t be used in{" "}
              {values.orchestration_mode === "llm_decision" ? "LLM Decision" : "Sequential"} mode.
              Remove it or change the orchestration mode in step 3.
            </Text>
          )}

          {/* Agent-specific: agent selector */}
          {kind === "agent" && (
            <div className="flex flex-col gap-0.5">
              <div className="flex items-center gap-1">
                <Text mainContentEmphasis text04>Agent</Text>
                <Text text03 mainContentMuted className="text-status-error-05">*</Text>
                <InfoTip>
                  Select which agent (agent) handles this step. The agent&apos;s own LLM, tools, and system prompt will be used. Create agents first in the Agents page.
                </InfoTip>
              </div>
              <select
                name={`steps.${index}.agent_id`}
                value={step.agent_id ?? ""}
                className={cn(
                  "w-full h-10 px-3 rounded-8 border bg-background-tint-00 text-text-05 text-sm",
                  stepTouched?.agent_id && stepErrors?.agent_id
                    ? "border-status-error-05"
                    : "border-border"
                )}
                onChange={(e) => {
                  setFieldValue(
                    `steps.${index}.agent_id`,
                    e.target.value === "" ? null : Number(e.target.value)
                  );
                }}
              >
                <option value="">-- Select Agent --</option>
                {selectableStepAgents(agents).map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
              {stepTouched?.agent_id && stepErrors?.agent_id && (
                <Text secondaryBody className="text-status-error-05 text-xs mt-0.5">
                  {stepErrors.agent_id}
                </Text>
              )}
            </div>
          )}

          {/* Conditional Router config (branches as node keys) */}
          {isConditionalRouter && (
            <RouterStepFields
              config={step.config}
              laterSteps={values.steps.slice(index + 1).map((s, i) => ({
                node_key: s.node_key,
                label: `${index + i + 2}. ${stepDisplayName(s, index + i + 1)}`,
              }))}
              onChange={(config) => setFieldValue(`steps.${index}.config`, { ...config })}
            />
          )}

          {/* Other catalog node types: form from their config schema */}
          {(kind === "schema" || kind === "container") && typeInfo && (
            <div className="space-y-2 p-3 rounded-8 border border-border bg-background-tint-01">
              <Text secondaryBody text04 className="text-xs font-medium">
                {typeInfo.label} Settings
              </Text>
              <SchemaConfigForm
                schema={typeInfo.config_schema}
                value={step.config}
                onChange={(config) => setFieldValue(`steps.${index}.config`, config)}
              />
            </div>
          )}

          {kind === "unsupported" && (
            <div className="space-y-2 p-3 rounded-8 border border-border bg-background-tint-01">
              <Text secondaryBody text03 className="text-xs">
                This editor doesn&apos;t know the node type &quot;{step.step_type}&quot;. It is kept unchanged when you save.
              </Text>
              <pre className="text-xs text-text-04 whitespace-pre-wrap break-words">
                {JSON.stringify(step.config ?? {}, null, 2)}
              </pre>
            </div>
          )}

          {/* Row 2: Step Description — full width */}
          <InputLayouts.Vertical
            name={`steps.${index}.step_description`}
            title="Step Description"
            optional
            description={
              isConditionalRouter
                ? "Describe the routing logic for documentation purposes."
                : "What this step should accomplish. Helps the orchestrator decide when to use it."
            }
          >
            <InputTextAreaField
              name={`steps.${index}.step_description`}
              placeholder={
                isConditionalRouter
                  ? "e.g. Route to error handling if the research step found errors."
                  : "e.g. Collect travel details like destination, dates, budget, and number of travelers from the user's message."
              }
            />
          </InputLayouts.Vertical>

          {/* Row 3: Output Key — own row */}
          <div className="max-w-xs">
            <div className="flex flex-col gap-0.5">
              <div className="flex items-center">
                <Text mainContentEmphasis text04>Output Key</Text>
                <InfoTip>
                  {isConditionalRouter
                    ? 'Stores "true" or "false" as the result of the condition evaluation.'
                    : 'A unique variable name to store this step\u0027s output (e.g. "travel_details", "flights", "summary"). Other steps can reference this output. Use lowercase with underscores, no spaces.'}
                </InfoTip>
              </div>
              <InputTypeInField
                name={`steps.${index}.output_key`}
                placeholder={isConditionalRouter ? "e.g. route_result" : "e.g. research_results"}
              />
            </div>
          </div>

          {/* Row 4: Toggle switches — a step inside a container has none */}
          {!step.parent_key && (
          <div className="flex items-center gap-6 pt-1 border-t border-border-01">
            <div className="flex items-center gap-2">
              <SwitchField name={`steps.${index}.is_terminal`} />
              <div className="flex items-center">
                <Text secondaryBody text04>Terminal Step</Text>
                <InfoTip>
                  When enabled, the workflow stops after this step completes and returns its output as the final answer.
                </InfoTip>
              </div>
            </div>
            {canPause && (
              <div className="flex items-center gap-2">
                <SwitchField name={`steps.${index}.can_request_input`} />
                <div className="flex items-center">
                  <Text secondaryBody text04>Can Request Input</Text>
                  <InfoTip>
                    When enabled, this agent can pause the workflow and ask the user for more information.
                  </InfoTip>
                </div>
              </div>
            )}
            <div className="flex items-center gap-2">
              <SwitchField name={`steps.${index}.promote_output`} />
              <div className="flex items-center">
                <Text secondaryBody text04>Show as Message</Text>
                <InfoTip>
                  When enabled, this step&apos;s output is displayed as main message content (outside the thinking panel).
                </InfoTip>
              </div>
            </div>
          </div>
          )}
        </div>

        {/* Reorder + Remove buttons */}
        <div className="flex flex-col gap-1 mt-1">
          <SimpleTooltip tooltip="Move step up" side="left">
            <button
              type="button"
              className="p-1 rounded hover:bg-background-tint-03 disabled:opacity-30"
              disabled={!canMoveUp}
              onClick={onMoveUp}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 15l-6-6-6 6" />
              </svg>
            </button>
          </SimpleTooltip>
          <SimpleTooltip tooltip="Move step down" side="left">
            <button
              type="button"
              className="p-1 rounded hover:bg-background-tint-03 disabled:opacity-30"
              disabled={!canMoveDown}
              onClick={onMoveDown}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
          </SimpleTooltip>
          {canRemove && (
            <SimpleTooltip tooltip="Remove this step" side="left">
              <button
                type="button"
                className="p-1 rounded hover:bg-theme-red-01 text-text-02 hover:text-theme-red-05"
                onClick={onRemove}
              >
                <SvgTrash className="w-4 h-4" />
              </button>
            </SimpleTooltip>
          )}
        </div>
      </div>
    </Card>
    </div>
  );
}

// ─── Main Editor ─────────────────────────────────────────────────────────

export interface WorkflowEditorPageProps {
  workflow?: WorkflowSnapshot;
  refreshWorkflow?: () => void;
}

export default function WorkflowEditorPage({
  workflow: existingWorkflow,
  refreshWorkflow,
}: WorkflowEditorPageProps) {
  const router = useRouter();
  const { refresh: refreshWorkflows } = useWorkflows();
  const { agents } = useAgents();
  const { llmProviders } = useLLMProviders();
  const { catalog, isReady: catalogReady } = useNodeTypes();
  const deleteModal = useCreateModal();

  const [currentStep, setCurrentStep] = useState(0);
  const [showVersions, setShowVersions] = useState(false);
  const [upgradeTarget, setUpgradeTarget] = useState<
    (NodeUpgradeTarget & { index: number }) | null
  >(null);

  const agentOptions = agents.map((a) => ({
    id: a.id,
    name: a.name,
    description: a.description,
  }));

  const getCurrentLlm = useCallback(
    (values: any) => {
      if (values.orchestrator_llm_model && values.orchestrator_llm_provider) {
        const provider = llmProviders?.find(
          (p: any) => p.name === values.orchestrator_llm_provider
        );
        return structureValue(
          values.orchestrator_llm_provider,
          provider?.provider || "",
          values.orchestrator_llm_model
        );
      }
      return null;
    },
    [llmProviders]
  );

  const onLlmSelect = useCallback(
    (selected: string | null, setFieldValue: any) => {
      if (selected === null) {
        setFieldValue("orchestrator_llm_model", null);
        setFieldValue("orchestrator_llm_provider", null);
      } else {
        const { modelName, name } = parseLlmDescriptor(selected);
        if (modelName && name) {
          setFieldValue("orchestrator_llm_model", modelName);
          setFieldValue("orchestrator_llm_provider", name);
        }
      }
    },
    []
  );

  // The shared serializer carries every step field (node keys, versions,
  // configs, input mappings, overrides) and icon_name through a save.
  const initialValues: WizardValues = useMemo(
    () =>
      existingWorkflow
        ? {
            ...snapshotToMeta(existingWorkflow),
            steps: snapshotToEditorSteps(existingWorkflow),
          }
        : {
            ...DEFAULT_WORKFLOW_META,
            steps: [
              createEditorStep(AGENT_NODE_TYPE, catalog, {
                node_key: newNodeKey(),
                output_key: "step_0",
              }),
            ],
          },
    [existingWorkflow, catalog]
  );

  /** A new step of `type`, with a fresh node key and output key. */
  const newStep = (type: string, steps: EditorStep[]): EditorStep =>
    createEditorStep(type, catalog, {
      node_key: newNodeKey(steps.map((s) => s.node_key)),
      output_key: nextOutputKey(type === ROUTER_NODE_TYPE ? "route" : "step", steps),
    });

  const validationSchema = Yup.object().shape({
    name: Yup.string().required("Workflow name is required"),
    description: Yup.string().optional(),
    orchestration_mode: Yup.string().oneOf(["sequential", "llm_decision"]).required(),
    orchestrator_prompt: Yup.string().optional(),
    max_steps: Yup.number().min(1, "Must be at least 1").max(MAX_ORCHESTRATOR_STEPS, `Maximum ${MAX_ORCHESTRATOR_STEPS} steps`).required("Required"),
    max_calls_per_agent: Yup.number().min(1, "Must be at least 1").max(MAX_CALLS_PER_AGENT, `Maximum ${MAX_CALLS_PER_AGENT}`).required("Required"),
    timeout_seconds: Yup.number().min(MIN_TIMEOUT_SECONDS, `Minimum ${MIN_TIMEOUT_SECONDS} seconds`).max(MAX_TIMEOUT_SECONDS, "Maximum 2 hours").required("Required"),
    steps: Yup.array()
      .of(
        Yup.object().shape({
          step_type: Yup.string().required(),
          agent_id: Yup.number().nullable().when("step_type", {
            is: AGENT_NODE_TYPE,
            then: (schema) => schema.required("Agent is required").min(1, "Please select an agent"),
          }),
          step_name: Yup.string().required("Step name is required"),
          step_description: Yup.string().optional(),
          output_key: Yup.string()
            .matches(/^[a-z][a-z0-9_]*$/, "Use lowercase letters, numbers, and underscores only (e.g. research_output)")
            .required("Output key is required"),
          is_terminal: Yup.boolean(),
          can_request_input: Yup.boolean(),
          promote_output: Yup.boolean(),
        })
      )
      .min(1, "Add at least one step"),
  });

  // Validate current step before allowing navigation forward
  function validateCurrentStep(values: WizardValues, step: number): string | null {
    if (step === 0) {
      if (!values.name.trim()) return "Please enter a workflow name before proceeding.";
    }
    if (step === 1) {
      // Mode checks wait for submit: the mode is chosen in the next step.
      const errors = validateSteps(values.steps, values.orchestration_mode, catalog, {
        checkModes: false,
      });
      if (errors[0]) return errors[0].message;
    }
    return null;
  }

  async function handleSubmit(values: WizardValues) {
    const errors = validateSteps(values.steps, values.orchestration_mode, catalog);
    if (errors[0]) {
      toast.error(errors[0].message);
      return;
    }

    const { steps, ...meta } = values;
    const payload = existingWorkflow
      ? buildWorkflowUpdate(meta, steps, existingWorkflow.version)
      : buildWorkflowCreate(meta, steps);

    try {
      await saveWorkflow(existingWorkflow?.id ?? null, payload);
    } catch (error) {
      toast.error(
        `Failed to ${existingWorkflow ? "update" : "create"} workflow: ${describeSaveError(error)}`
      );
      return;
    }

    toast.success(
      `Workflow "${values.name}" ${existingWorkflow ? "updated" : "created"} successfully`
    );

    await refreshWorkflows();
    if (refreshWorkflow) refreshWorkflow();
    router.push("/admin/workflows");
  }

  function handleRestored(restored: WorkflowSnapshot) {
    setShowVersions(false);
    toast.success(`Restored; saved as version ${restored.version}.`);
    // The editor re-mounts with the restored definition (Formik is keyed by version).
    if (refreshWorkflow) refreshWorkflow();
  }

  async function handleDelete() {
    if (!existingWorkflow) return;

    const response = await deleteWorkflow(existingWorkflow.id);
    if (!response.ok) {
      toast.error("Failed to delete workflow");
      return;
    }

    toast.success("Workflow deleted");
    deleteModal.toggle(false);
    await refreshWorkflows();
    router.push("/admin/workflows");
  }

  return (
    <>
      <div className="h-full w-full">
        {!catalogReady ? (
          <div className="flex items-center justify-center h-full">
            <Text secondaryBody text03>Loading...</Text>
          </div>
        ) : (
        <Formik
          key={existingWorkflow?.version ?? "new"}
          initialValues={initialValues}
          validationSchema={validationSchema}
          onSubmit={handleSubmit}
          validateOnChange
          validateOnBlur
        >
          {({ isSubmitting, isValid, dirty, values, setFieldValue, errors, setTouched, touched }) => (
            <>
              {upgradeTarget && (
                <NodeUpgradeDialog
                  target={upgradeTarget}
                  onApply={(result: NodeUpgradeResult) => {
                    const i = upgradeTarget.index;
                    const latest = values.steps[i]?.latest_type_version ?? result.to_version;
                    setFieldValue(`steps.${i}.type_version`, result.to_version);
                    setFieldValue(`steps.${i}.config`, result.config);
                    setFieldValue(`steps.${i}.upgrade_available`, result.to_version < latest);
                    setUpgradeTarget(null);
                    toast.success("Upgrade applied. Save the workflow to keep it.");
                  }}
                  onClose={() => setUpgradeTarget(null)}
                />
              )}

              <deleteModal.Provider>
                {deleteModal.isOpen && (
                  <ConfirmationModalLayout
                    icon={SvgTrash}
                    title="Delete Workflow"
                    submit={
                      <Button danger onClick={handleDelete}>
                        Delete Workflow
                      </Button>
                    }
                    onClose={() => deleteModal.toggle(false)}
                  >
                    <GeneralLayouts.Section alignItems="start" gap={0.5}>
                      <Text>This will permanently delete the workflow and all its configuration.</Text>
                      <Text>Are you sure?</Text>
                    </GeneralLayouts.Section>
                  </ConfirmationModalLayout>
                )}
              </deleteModal.Provider>

              <Form className="h-full w-full">
                <SettingsLayouts.Root>
                  <SettingsLayouts.Header
                    icon={SvgSliders}
                    title={existingWorkflow ? "Edit Workflow" : "Create Workflow"}
                    rightChildren={
                      <div className="flex gap-2">
                        <Button type="button" secondary onClick={() => router.push("/admin/workflows")}>
                          Cancel
                        </Button>
                        {existingWorkflow && (
                          <Button type="button" secondary leftIcon={SvgHistory} onClick={() => setShowVersions(true)}>
                            Versions
                          </Button>
                        )}
                        {currentStep > 0 && (
                          <Button type="button" secondary leftIcon={SvgArrowLeft} onClick={() => setCurrentStep(currentStep - 1)}>
                            Back
                          </Button>
                        )}
                        {currentStep < TOTAL_STEPS - 1 ? (
                          <Button
                            type="button"
                            rightIcon={SvgArrowRight}
                            onClick={() => {
                              const error = validateCurrentStep(values, currentStep);
                              if (error) {
                                toast.error(error);
                                return;
                              }
                              setCurrentStep(currentStep + 1);
                            }}
                          >
                            Next
                          </Button>
                        ) : (
                          <Button
                            type="submit"
                            leftIcon={existingWorkflow ? undefined : SvgSparkle}
                            disabled={isSubmitting || !isValid || !dirty}
                          >
                            {existingWorkflow ? "Save" : "Create"}
                          </Button>
                        )}
                      </div>
                    }
                    backButton
                    separator
                  >
                    <StepIndicator currentStep={currentStep} onStepClick={(step) => setCurrentStep(step)} />
                  </SettingsLayouts.Header>

                  <SettingsLayouts.Body>
                    {/* ═══ STEP 1: Identity — Name & Details ═══ */}
                    {currentStep === 0 && (
                      <>
                        <GeneralLayouts.Section gap={1}>
                          <InputLayouts.Vertical
                            name="name"
                            title="Workflow Name"
                            description="A clear, descriptive name that users will see when selecting this workflow."
                          >
                            <InputTypeInField name="name" placeholder="e.g. Travel Planner, Research & Summarize, Content Pipeline" />
                          </InputLayouts.Vertical>

                          <InputLayouts.Vertical
                            name="description"
                            title="Description"
                            optional
                            description="Explain what this workflow does for end users. This is displayed in the workflow list and helps users understand when to use it."
                          >
                            <InputTextAreaField
                              name="description"
                              placeholder="e.g. Plans a complete trip by coordinating specialist agents for flights, hotels, activities, and itinerary building. Just tell it where you want to go!"
                            />
                          </InputLayouts.Vertical>
                        </GeneralLayouts.Section>

                        <Separator noPadding />

                        <GeneralLayouts.Section gap={0.5}>
                          <Card>
                            <InputLayouts.Horizontal
                              name="is_public"
                              title="Public"
                              description="When enabled, all users can see and use this workflow. When disabled, only you (the creator) can access it."
                            >
                              <SwitchField name="is_public" />
                            </InputLayouts.Horizontal>
                          </Card>
                        </GeneralLayouts.Section>
                      </>
                    )}

                    {/* ═══ STEP 2: Agent Steps — Add & Reorder Agents ═══ */}
                    {currentStep === 1 && (
                      <>
                        <div className="flex items-start gap-3 mb-1">
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                            style={{ backgroundColor: "var(--theme-purple-01)" }}
                          >
                            <SvgOmOctagon className="w-4 h-4" style={{ stroke: "var(--theme-purple-05)" }} />
                          </div>
                          <div className="flex flex-col">
                            <Text as="p" mainContentEmphasis>Agent Steps</Text>
                            <Text as="p" secondaryBody text03>
                              Define the agents that participate in this workflow and their execution order. Each step runs a specific agent
                              (agent) with its own LLM and tools. In LLM Decision mode, the orchestrator dynamically chooses which agent
                              to call next. In Sequential mode, agents run top-to-bottom in order.
                            </Text>
                          </div>
                        </div>

                        {/* Quick help card */}
                        <Card variant="secondary">
                          <div className="flex items-start gap-2">
                            <SvgInfoSmall className="w-4 h-4 stroke-text-03 flex-shrink-0 mt-0.5" />
                            <div className="flex flex-col gap-1">
                              <Text secondaryBody text03 className="text-xs font-medium">How agent steps work</Text>
                              <Text secondaryBody text03 className="text-xs">
                                Each step maps to an agent you&apos;ve created in the Agents page. The agent&apos;s system prompt, tools, and LLM
                                configuration are used when the step runs. For example, a Travel Planner workflow might have: Details Collector
                                (step 1) &rarr; Flight Finder (step 2) &rarr; Hotel Finder (step 3) &rarr; Itinerary Builder (step 4).
                              </Text>
                            </div>
                          </div>
                        </Card>

                        <FieldArray name="steps">
                          {(arrayHelpers) => (
                            <GeneralLayouts.Section gap={0.5}>
                              {values.steps.map((step, index) => (
                                <WorkflowStepRow
                                  key={step.node_key}
                                  index={index}
                                  agents={agentOptions}
                                  catalog={catalog}
                                  onUpgrade={() =>
                                    setUpgradeTarget({
                                      index,
                                      stepName: stepDisplayName(step, index),
                                      stepType: step.step_type,
                                      fromVersion: step.type_version ?? 1,
                                      config: step.config,
                                      stepOrderToNodeKey: stepOrderToNodeKey(values.steps),
                                    })
                                  }
                                  onRemove={() => {
                                    const inside = descendantKeys(values.steps, step.node_key).size;
                                    if (
                                      inside === 0 ||
                                      window.confirm(
                                        `Remove "${stepDisplayName(step, index)}" and the ${inside} step(s) inside it?`
                                      )
                                    ) {
                                      setFieldValue("steps", removeStep(values.steps, step.node_key));
                                    }
                                  }}
                                  canRemove={values.steps.length > 1}
                                  canMoveUp={canReorder(values.steps, step.node_key, -1)}
                                  canMoveDown={canReorder(values.steps, step.node_key, 1)}
                                  onMoveUp={() =>
                                    setFieldValue("steps", reorderInBlock(values.steps, step.node_key, -1))
                                  }
                                  onMoveDown={() =>
                                    setFieldValue("steps", reorderInBlock(values.steps, step.node_key, 1))
                                  }
                                />
                              ))}

                              <div className="flex flex-wrap gap-2">
                                <Button
                                  type="button"
                                  secondary
                                  leftIcon={SvgSparkle}
                                  onClick={() => arrayHelpers.push(newStep(AGENT_NODE_TYPE, values.steps))}
                                >
                                  Add Agent Step
                                </Button>
                                {paletteTypes(catalog, values.orchestration_mode)
                                  .filter((t) => t.type !== AGENT_NODE_TYPE)
                                  .map((t) => (
                                    <Button
                                      key={t.type}
                                      type="button"
                                      secondary
                                      onClick={() => arrayHelpers.push(newStep(t.type, values.steps))}
                                    >
                                      {`Add ${labelFor(catalog, t.type)}`}
                                    </Button>
                                  ))}
                              </div>
                              {values.orchestration_mode === "llm_decision" && (
                                <Text secondaryBody text03 className="text-xs">
                                  Conditions and other step types that only run in order are available when the
                                  orchestration mode (step 3) is Sequential.
                                </Text>
                              )}
                            </GeneralLayouts.Section>
                          )}
                        </FieldArray>
                      </>
                    )}

                    {/* ═══ STEP 3: Configure — Orchestration Settings ═══ */}
                    {currentStep === 2 && (
                      <>
                        <div className="flex items-start gap-3 mb-1">
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                            style={{ backgroundColor: "var(--theme-blue-01)" }}
                          >
                            <SvgSettings className="w-4 h-4" style={{ stroke: "var(--theme-blue-05)" }} />
                          </div>
                          <div className="flex flex-col">
                            <Text as="p" mainContentEmphasis>Orchestration Mode</Text>
                            <Text as="p" secondaryBody text03>
                              Controls how agents are coordinated during execution. This is the most important architectural decision for your workflow.
                            </Text>
                          </div>
                        </div>

                        <GeneralLayouts.Section gap={0.5}>
                          <Card
                            className={cn("cursor-pointer", values.orchestration_mode === "llm_decision" && "ring-2 ring-[var(--theme-primary-05)]")}
                            onClick={() => setFieldValue("orchestration_mode", "llm_decision")}
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="radio"
                                checked={values.orchestration_mode === "llm_decision"}
                                onChange={() => setFieldValue("orchestration_mode", "llm_decision")}
                                className="accent-[var(--theme-primary-05)]"
                              />
                              <div>
                                <Text mainContentEmphasis>LLM Decision (Recommended)</Text>
                                <Text secondaryBody text03>
                                  An orchestrator LLM dynamically decides which agent to call next based on the conversation context.
                                  Best for workflows where the order may vary or agents need to loop back for missing information.
                                  Uses an additional LLM call between each step for routing decisions.
                                </Text>
                              </div>
                            </div>
                          </Card>

                          <Card
                            className={cn("cursor-pointer", values.orchestration_mode === "sequential" && "ring-2 ring-[var(--theme-primary-05)]")}
                            onClick={() => setFieldValue("orchestration_mode", "sequential")}
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="radio"
                                checked={values.orchestration_mode === "sequential"}
                                onChange={() => setFieldValue("orchestration_mode", "sequential")}
                                className="accent-[var(--theme-primary-05)]"
                              />
                              <div>
                                <Text mainContentEmphasis>Sequential</Text>
                                <Text secondaryBody text03>
                                  Agents run in the fixed order defined in Step 2. Each agent&apos;s output feeds into the next.
                                  Faster and cheaper since no orchestrator LLM is needed. Best for pipelines with a known, fixed order
                                  (e.g. Research &rarr; Summarize &rarr; Translate).
                                </Text>
                              </div>
                            </div>
                          </Card>
                          {stepsNotAllowedInMode(values.steps, values.orchestration_mode, catalog).length > 0 && (
                            <Text secondaryBody className="text-xs text-status-warning-05">
                              Some steps can&apos;t run in this mode:{" "}
                              {stepsNotAllowedInMode(values.steps, values.orchestration_mode, catalog)
                                .map((s) => `"${s.step_name || s.step_type}"`)
                                .join(", ")}
                              . Remove them in step 2 or pick another mode.
                            </Text>
                          )}
                        </GeneralLayouts.Section>

                        {values.orchestration_mode === "llm_decision" && (
                          <>
                            <Separator noPadding />

                            <GeneralLayouts.Section gap={1}>
                              <InputLayouts.Vertical
                                name="orchestrator_prompt"
                                title="Orchestrator Instructions"
                                optional
                                description="System prompt for the orchestrator LLM that decides agent routing. Tell it the preferred order, rules, and when to stop."
                              >
                                <InputTextAreaField
                                  name="orchestrator_prompt"
                                  placeholder={"e.g. You are a travel planning orchestrator. Follow this order:\n1. Call Details Collector first to gather travel info\n2. Then call Flight Finder and Hotel Finder\n3. Finally call Itinerary Builder to create the plan\n4. After all agents respond, write a short final summary"}
                                />
                                <Text secondaryBody text03 className="text-xs mt-1">
                                  This is an LLM system prompt, not a user-facing description. Write it as instructions for the AI orchestrator.
                                  Include the expected agent order, any rules (e.g. &quot;call each agent exactly once&quot;), and when to finish.
                                </Text>
                              </InputLayouts.Vertical>

                              <Card>
                                <InputLayouts.Horizontal
                                  name="orchestrator_llm"
                                  title="Orchestrator Model"
                                  description="The LLM that handles routing decisions between agents. Use a fast, cheap model here (e.g. GPT-4.1) since it only makes routing decisions, not content. Leave empty to use the system default."
                                >
                                  <LLMSelector
                                    name="orchestrator_llm"
                                    llmProviders={llmProviders ?? []}
                                    currentLlm={getCurrentLlm(values)}
                                    onSelect={(selected) => onLlmSelect(selected, setFieldValue)}
                                  />
                                </InputLayouts.Horizontal>
                              </Card>
                            </GeneralLayouts.Section>
                          </>
                        )}

                        <Separator noPadding />

                        <div className="flex items-start gap-3 mb-1">
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                            style={{ backgroundColor: "var(--theme-blue-01)" }}
                          >
                            <SvgSliders className="w-4 h-4" style={{ stroke: "var(--theme-blue-05)" }} />
                          </div>
                          <div className="flex flex-col">
                            <Text as="p" mainContentEmphasis>Safety Limits</Text>
                            <Text as="p" secondaryBody text03>
                              Guard rails to prevent runaway workflows. These limits stop execution if something goes wrong (e.g. an agent loops indefinitely).
                            </Text>
                          </div>
                        </div>

                        <GeneralLayouts.Section gap={0.5}>
                          <Card>
                            {values.orchestration_mode === "llm_decision" && (
                              <>
                            <InputLayouts.Horizontal
                              name="max_steps"
                              title="Max Total Steps"
                              description="The maximum number of total agent calls in one workflow run. If the orchestrator tries to make more calls than this, the workflow stops. For a 6-agent workflow, set this to at least 8-10 to allow some buffer."
                            >
                              <input
                                type="number"
                                value={values.max_steps}
                                onChange={(e) => setFieldValue("max_steps", parseInt(e.target.value) || 10)}
                                min={1}
                                max={MAX_ORCHESTRATOR_STEPS}
                                className="w-20 h-10 px-3 rounded-8 border border-border bg-background-tint-00 text-text-05 text-sm text-center"
                              />
                            </InputLayouts.Horizontal>
                            <InputLayouts.Horizontal
                              name="max_calls_per_agent"
                              title="Max Calls per Agent"
                              description="How many times the orchestrator can call the same agent. Set to 1 if each agent should run exactly once (e.g. Travel Planner). Set to 2-3 if agents may need to loop back for additional information from the user."
                            >
                              <input
                                type="number"
                                value={values.max_calls_per_agent}
                                onChange={(e) => setFieldValue("max_calls_per_agent", parseInt(e.target.value) || 2)}
                                min={1}
                                max={MAX_CALLS_PER_AGENT}
                                className="w-20 h-10 px-3 rounded-8 border border-border bg-background-tint-00 text-text-05 text-sm text-center"
                              />
                            </InputLayouts.Horizontal>
                              </>
                            )}
                            <InputLayouts.Horizontal
                              name="timeout_seconds"
                              title="Timeout"
                              description="Maximum wall-clock time (in seconds) before the workflow is forcefully stopped. Default: 1800s (30 min). For simple 2-3 agent workflows, 300-600s is usually enough."
                            >
                              <input
                                type="number"
                                value={values.timeout_seconds}
                                onChange={(e) => setFieldValue("timeout_seconds", parseInt(e.target.value) || 1800)}
                                min={30}
                                max={7200}
                                className="w-24 h-10 px-3 rounded-8 border border-border bg-background-tint-00 text-text-05 text-sm text-center"
                              />
                            </InputLayouts.Horizontal>
                          </Card>
                        </GeneralLayouts.Section>

                        {existingWorkflow && (
                          <>
                            <Separator noPadding />
                            <Card>
                              <InputLayouts.Horizontal
                                title="Delete This Workflow"
                                description="Permanently removes this workflow and all its configuration. This action cannot be undone."
                                center
                              >
                                <Button secondary danger onClick={() => deleteModal.toggle(true)}>
                                  Delete Workflow
                                </Button>
                              </InputLayouts.Horizontal>
                            </Card>
                          </>
                        )}
                      </>
                    )}
                  </SettingsLayouts.Body>
                </SettingsLayouts.Root>
              </Form>
            </>
          )}
        </Formik>
        )}
      </div>

      {showVersions && existingWorkflow && (
        <WorkflowVersionsDialog
          workflowId={existingWorkflow.id}
          currentVersion={existingWorkflow.version}
          catalog={catalog}
          onRestored={handleRestored}
          onClose={() => setShowVersions(false)}
        />
      )}
    </>
  );
}
