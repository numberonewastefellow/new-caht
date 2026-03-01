"use client";

import React, { useState, useCallback } from "react";
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
import { useWorkflows } from "@/hooks/useWorkflows";
import { useLLMProviders } from "@/lib/hooks/useLLMProviders";
import { parseLlmDescriptor, structureValue } from "@/lib/llm/utils";
import LLMSelector from "@/components/llm/LLMSelector";
import { createWorkflow, updateWorkflow, deleteWorkflow } from "@/lib/workflows/api";
import {
  WorkflowSnapshot,
  WorkflowStepCreate,
} from "@/lib/workflows/interfaces";
import { toast } from "@/hooks/useToast";
import { useCreateModal } from "@/refresh-components/contexts/ModalContext";
import ConfirmationModalLayout from "@/refresh-components/layouts/ConfirmationModalLayout";
import {
  SvgArrowLeft,
  SvgArrowRight,
  SvgInfoSmall,
  SvgSettings,
  SvgSliders,
  SvgSparkle,
  SvgTrash,
  SvgOnyxOctagon,
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

interface WorkflowStepRowProps {
  index: number;
  agents: { id: number; name: string; description: string }[];
  onRemove: () => void;
  canRemove: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

function WorkflowStepRow({
  index,
  agents,
  onRemove,
  canRemove,
  canMoveUp,
  canMoveDown,
  onMoveUp,
  onMoveDown,
}: WorkflowStepRowProps) {
  const { values, setFieldValue, errors, touched } = useFormikContext<any>();
  const currentPersonaId = values.steps?.[index]?.persona_id ?? 0;
  const stepErrors = (errors.steps as any)?.[index];
  const stepTouched = (touched.steps as any)?.[index];

  return (
    <Card padding={1}>
      <div className="flex items-start gap-3">
        {/* Step number */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1"
          style={{ backgroundColor: "var(--theme-purple-01)" }}
        >
          <Text as="span" style={{ color: "var(--theme-purple-05)" }}>
            {index + 1}
          </Text>
        </div>

        <div className="flex-1 space-y-3">
          <div className="flex gap-3">
            <div className="flex-1">
              <InputLayouts.Vertical
                name={`steps.${index}.step_name`}
                title="Step Name"
                description="A short label for this step shown during execution."
              >
                <InputTypeInField
                  name={`steps.${index}.step_name`}
                  placeholder="e.g. Research, Summarize, Find Flights..."
                />
              </InputLayouts.Vertical>
            </div>
            <div className="flex-1">
              <div className="flex flex-col gap-0.5">
                <div className="flex items-center gap-1">
                  <Text mainContentEmphasis text04>Agent</Text>
                  <Text text03 mainContentMuted className="text-status-error-05">*</Text>
                  <InfoTip>
                    Select which agent (persona) handles this step. The agent&apos;s own LLM, tools, and system prompt will be used. Create agents first in the Agents page.
                  </InfoTip>
                </div>
                <select
                  name={`steps.${index}.persona_id`}
                  value={currentPersonaId}
                  className={cn(
                    "w-full h-10 px-3 rounded-8 border bg-background-tint-00 text-text-05 text-sm",
                    stepTouched?.persona_id && stepErrors?.persona_id
                      ? "border-status-error-05"
                      : "border-border"
                  )}
                  onChange={(e) => {
                    setFieldValue(
                      `steps.${index}.persona_id`,
                      parseInt(e.target.value) || 0
                    );
                  }}
                  onBlur={() => {
                    // Trigger touched state for validation display
                    const touchedArr = Array.isArray(touched.steps) ? touched.steps : [];
                    const touchedSteps = [...touchedArr];
                    touchedSteps[index] = { ...touchedSteps[index], persona_id: true };
                  }}
                >
                  <option value={0}>-- Select Agent --</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
                {stepTouched?.persona_id && stepErrors?.persona_id && (
                  <Text secondaryBody className="text-status-error-05 text-xs mt-0.5">
                    {stepErrors.persona_id}
                  </Text>
                )}
              </div>
            </div>
          </div>

          <InputLayouts.Vertical
            name={`steps.${index}.step_description`}
            title="Step Description"
            optional
            description="What this step should accomplish. Helps the orchestrator decide when to use it."
          >
            <InputTextAreaField
              name={`steps.${index}.step_description`}
              placeholder="e.g. Collect travel details like destination, dates, budget, and number of travelers from the user's message."
            />
          </InputLayouts.Vertical>

          <div className="flex gap-3 items-start">
            <div className="flex-1">
              <div className="flex flex-col gap-0.5">
                <div className="flex items-center">
                  <Text mainContentEmphasis text04>Output Key</Text>
                  <InfoTip>
                    A unique variable name to store this step&apos;s output (e.g. &quot;travel_details&quot;, &quot;flights&quot;, &quot;summary&quot;). Other steps can reference this output. Use lowercase with underscores, no spaces.
                  </InfoTip>
                </div>
                <InputTypeInField
                  name={`steps.${index}.output_key`}
                  placeholder="e.g. research_results"
                />
              </div>
            </div>
            <div className="flex items-end gap-1 pb-0.5">
              <div className="flex flex-col gap-0.5">
                <div className="flex items-center">
                  <Text mainContentEmphasis text04>Terminal Step</Text>
                  <InfoTip>
                    When enabled, the workflow stops after this step completes and returns its output as the final answer. When disabled (default), the workflow continues to the next step. Use this for the last step in a sequence, or for early-exit conditions.
                  </InfoTip>
                </div>
                <SwitchField name={`steps.${index}.is_terminal`} />
              </div>
            </div>
            <div className="flex items-end gap-1 pb-0.5">
              <div className="flex flex-col gap-0.5">
                <div className="flex items-center">
                  <Text mainContentEmphasis text04>Can Request Input</Text>
                  <InfoTip>
                    When enabled, this agent can pause the workflow and ask the user for more information. The workflow saves its state and resumes when the user responds. Use this for agents that need to clarify details before proceeding.
                  </InfoTip>
                </div>
                <SwitchField name={`steps.${index}.can_request_input`} />
              </div>
            </div>
          </div>
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
  const deleteModal = useCreateModal();

  const [currentStep, setCurrentStep] = useState(0);

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

  const initialValues = {
    name: existingWorkflow?.name ?? "",
    description: existingWorkflow?.description ?? "",
    orchestration_mode: existingWorkflow?.orchestration_mode ?? "llm_decision",
    orchestrator_prompt: existingWorkflow?.orchestrator_prompt ?? "",
    orchestrator_llm_provider: existingWorkflow?.orchestrator_llm_provider ?? null,
    orchestrator_llm_model: existingWorkflow?.orchestrator_llm_model ?? null,
    max_steps: existingWorkflow?.max_steps ?? 10,
    max_calls_per_agent: existingWorkflow?.max_calls_per_agent ?? 2,
    timeout_seconds: existingWorkflow?.timeout_seconds ?? 1800,
    is_public: existingWorkflow?.is_public ?? true,
    steps: existingWorkflow?.steps?.map((s) => ({
      persona_id: s.persona_id,
      step_order: s.step_order,
      step_name: s.step_name,
      step_description: s.step_description ?? "",
      output_key: s.output_key ?? "output",
      is_terminal: s.is_terminal,
      can_request_input: s.can_request_input ?? false,
    })) ?? [
      {
        persona_id: 0,
        step_order: 0,
        step_name: "",
        step_description: "",
        output_key: "output",
        is_terminal: false,
        can_request_input: false,
      },
    ],
  };

  const validationSchema = Yup.object().shape({
    name: Yup.string().required("Workflow name is required"),
    description: Yup.string().optional(),
    orchestration_mode: Yup.string().oneOf(["sequential", "llm_decision"]).required(),
    orchestrator_prompt: Yup.string().optional(),
    max_steps: Yup.number().min(1, "Must be at least 1").max(50, "Maximum 50 steps").required("Required"),
    max_calls_per_agent: Yup.number().min(1, "Must be at least 1").max(20, "Maximum 20").required("Required"),
    timeout_seconds: Yup.number().min(30, "Minimum 30 seconds").max(7200, "Maximum 2 hours").required("Required"),
    steps: Yup.array()
      .of(
        Yup.object().shape({
          persona_id: Yup.number().min(1, "Please select an agent").required("Agent is required"),
          step_name: Yup.string().required("Step name is required"),
          step_description: Yup.string().optional(),
          output_key: Yup.string()
            .matches(/^[a-z][a-z0-9_]*$/, "Use lowercase letters, numbers, and underscores only (e.g. research_output)")
            .required("Output key is required"),
          is_terminal: Yup.boolean(),
          can_request_input: Yup.boolean(),
        })
      )
      .min(1, "Add at least one step"),
  });

  // Validate current step before allowing navigation forward
  function validateCurrentStep(values: typeof initialValues, step: number): string | null {
    if (step === 0) {
      if (!values.name.trim()) return "Please enter a workflow name before proceeding.";
    }
    if (step === 1) {
      for (let i = 0; i < values.steps.length; i++) {
        const s = values.steps[i];
        if (!s) continue;
        if (!s.step_name?.trim()) return `Step ${i + 1}: Please enter a step name.`;
        if (!s.persona_id || s.persona_id === 0) return `Step ${i + 1}: Please select an agent.`;
      }
    }
    return null;
  }

  async function handleSubmit(values: typeof initialValues) {
    try {
      const steps: WorkflowStepCreate[] = values.steps.map((s, i) => ({
        persona_id: s.persona_id,
        step_order: i,
        step_name: s.step_name,
        step_description: s.step_description || null,
        output_key: s.output_key || "output",
        is_terminal: s.is_terminal,
        can_request_input: s.can_request_input ?? false,
      }));

      const payload = {
        name: values.name,
        description: values.description || null,
        orchestration_mode: values.orchestration_mode,
        orchestrator_prompt: values.orchestrator_prompt || null,
        orchestrator_llm_provider: values.orchestrator_llm_provider || null,
        orchestrator_llm_model: values.orchestrator_llm_model || null,
        max_steps: values.max_steps,
        max_calls_per_agent: values.max_calls_per_agent,
        timeout_seconds: values.timeout_seconds,
        is_public: values.is_public,
        steps,
      };

      let response;
      if (existingWorkflow) {
        response = await updateWorkflow(existingWorkflow.id, payload);
      } else {
        response = await createWorkflow(payload);
      }

      if (!response.ok) {
        const error = await response.text();
        toast.error(`Failed to ${existingWorkflow ? "update" : "create"} workflow: ${error}`);
        return;
      }

      toast.success(
        `Workflow "${values.name}" ${existingWorkflow ? "updated" : "created"} successfully`
      );

      await refreshWorkflows();
      if (refreshWorkflow) refreshWorkflow();
      router.push("/admin/workflows");
    } catch (error) {
      console.error("Submit error:", error);
      toast.error(`An error occurred: ${error}`);
    }
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
        <Formik
          initialValues={initialValues}
          validationSchema={validationSchema}
          onSubmit={handleSubmit}
          validateOnChange
          validateOnBlur
        >
          {({ isSubmitting, isValid, dirty, values, setFieldValue, errors, setTouched, touched }) => (
            <>
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
                            <SvgOnyxOctagon className="w-4 h-4" style={{ stroke: "var(--theme-purple-05)" }} />
                          </div>
                          <div className="flex flex-col">
                            <Text as="p" mainContentEmphasis>Agent Steps</Text>
                            <Text as="p" secondaryBody text03>
                              Define the agents that participate in this workflow and their execution order. Each step runs a specific agent
                              (persona) with its own LLM and tools. In LLM Decision mode, the orchestrator dynamically chooses which agent
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
                              {values.steps.map((_step, index) => (
                                <WorkflowStepRow
                                  key={index}
                                  index={index}
                                  agents={agentOptions}
                                  onRemove={() => arrayHelpers.remove(index)}
                                  canRemove={values.steps.length > 1}
                                  canMoveUp={index > 0}
                                  canMoveDown={index < values.steps.length - 1}
                                  onMoveUp={() => arrayHelpers.swap(index, index - 1)}
                                  onMoveDown={() => arrayHelpers.swap(index, index + 1)}
                                />
                              ))}

                              <Button
                                type="button"
                                secondary
                                leftIcon={SvgSparkle}
                                onClick={() =>
                                  arrayHelpers.push({
                                    persona_id: 0,
                                    step_order: values.steps.length,
                                    step_name: "",
                                    step_description: "",
                                    output_key: "output",
                                    is_terminal: false,
                                    can_request_input: false,
                                  })
                                }
                              >
                                Add Step
                              </Button>
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
                                max={50}
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
                                max={20}
                                className="w-20 h-10 px-3 rounded-8 border border-border bg-background-tint-00 text-text-05 text-sm text-center"
                              />
                            </InputLayouts.Horizontal>
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
      </div>
    </>
  );
}
