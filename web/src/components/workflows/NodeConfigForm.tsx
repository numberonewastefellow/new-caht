"use client";

/**
 * The settings of a schema-driven step in either workflow editor: the form
 * generated from its config schema, plus editors for the settings a generated form
 * can't handle. A node type adds an entry to NODE_FORMS for anything special.
 */

import React, { type ComponentType } from "react";
import { SchemaConfigForm } from "@/components/workflows/SchemaConfigForm";
import type { EditorStep } from "@/lib/workflows/editorModel";
import { branchLabels } from "@/lib/workflows/nodeConfigRules";
import { availableReferences } from "@/lib/workflows/references";
import { VALUELESS_OPERATORS } from "@/lib/workflows/routerConfig";

type Config = Record<string, unknown>;

const MIN_BRANCHES = 2;
const MAX_BRANCHES = 8;
const OUTPUT_TYPES = [
  "string",
  "number",
  "integer",
  "boolean",
  "object",
  "array",
] as const;
const LOOP_CONDITION_FIELDS = [
  "condition_field",
  "operator",
  "match_value",
  "case_sensitive",
];

const INPUT_CLASS =
  "min-w-0 flex-1 h-8 px-2 rounded-08 border border-border-02 bg-background-tint-00 text-text-05 text-sm";
const ROW_BUTTON_CLASS =
  "h-8 px-2 rounded-08 border border-border-02 text-xs text-text-03 disabled:opacity-50 disabled:cursor-not-allowed";
const ADD_BUTTON_CLASS =
  "self-start h-8 px-2 rounded-08 border border-border-02 text-xs text-text-04 disabled:opacity-50 disabled:cursor-not-allowed";

/** The first `prefix N` not in `taken`, counting from the next row number. */
function freeName(prefix: string, taken: readonly string[]): string {
  let n = taken.length + 1;
  while (taken.includes(`${prefix}${n}`)) n++;
  return `${prefix}${n}`;
}

interface SectionProps {
  step: EditorStep;
  steps: readonly EditorStep[];
  config: Config;
  references: string[];
  onChange: (config: Config, removedBranch?: number) => void;
}

function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-text-04">{title}</span>
      {children}
      {hint && <span className="text-xs text-text-03">{hint}</span>}
    </div>
  );
}

// ── Parallel: branch names ──────────────────────────────────────────────────

function BranchLabelsEditor({ step, steps, config, onChange }: SectionProps) {
  const labels = branchLabels(config);
  const inUse = new Set(
    steps
      .filter((s) => s.parent_key === step.node_key)
      .map((s) => s.branch_index)
  );
  const write = (next: string[], removedBranch?: number) =>
    onChange(
      { ...config, branches: next.map((label) => ({ label })) },
      removedBranch
    );

  return (
    <Section
      title="Branches"
      hint="All branches run at the same time. A branch holding steps can't be removed until they're moved."
    >
      {labels.map((label, branch) => (
        <div key={branch} className="flex items-center gap-2">
          <input
            aria-label={`Branch ${branch + 1} name`}
            className={INPUT_CLASS}
            value={label}
            onChange={(e) =>
              write(labels.map((l, i) => (i === branch ? e.target.value : l)))
            }
          />
          <button
            type="button"
            aria-label={`Remove branch ${branch + 1}`}
            className={ROW_BUTTON_CLASS}
            disabled={inUse.has(branch) || labels.length <= MIN_BRANCHES}
            onClick={() =>
              write(
                labels.filter((_, i) => i !== branch),
                branch
              )
            }
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        className={ADD_BUTTON_CLASS}
        disabled={labels.length >= MAX_BRANCHES}
        onClick={() => write([...labels, freeName("Branch ", labels)])}
      >
        Add branch
      </button>
    </Section>
  );
}

// ── Code: inputs and outputs ────────────────────────────────────────────────

function CodeInputsEditor({ step, config, references, onChange }: SectionProps) {
  const inputs = Object.entries(
    (config.inputs as Record<string, string> | undefined) ?? {}
  );
  const listId = `code-references-${step.node_key}`;
  const write = (next: [string, string][]) =>
    onChange({ ...config, inputs: Object.fromEntries(next) });
  // Applied when the field is left: while typing, a name can match another input's.
  const rename = (index: number, field: HTMLInputElement) => {
    const name = field.value.trim();
    const taken = inputs.some(([other], i) => i !== index && other === name);
    if (!name || taken) {
      field.value = inputs[index]![0];
      return;
    }
    write(inputs.map((row, i) => (i === index ? [name, row[1]] : row)));
  };

  return (
    <Section
      title="Inputs"
      hint="Read in main(inputs) as inputs['name']. The value is text or a $reference."
    >
      <datalist id={listId}>
        {references.map((r) => (
          <option key={r} value={r} />
        ))}
      </datalist>
      {inputs.map(([name, value], index) => (
        <div key={index} className="flex items-center gap-2">
          <input
            aria-label={`Input ${index + 1} name`}
            key={name}
            className={INPUT_CLASS}
            placeholder="name"
            defaultValue={name}
            onBlur={(e) => rename(index, e.target)}
          />
          <input
            aria-label={`Input ${index + 1} value`}
            className={INPUT_CLASS}
            list={listId}
            placeholder="$user_input"
            value={value}
            onChange={(e) =>
              write(
                inputs.map((row, i) =>
                  i === index ? [row[0], e.target.value] : row
                )
              )
            }
          />
          <button
            type="button"
            aria-label={`Remove input ${index + 1}`}
            className={ROW_BUTTON_CLASS}
            onClick={() => write(inputs.filter((_, i) => i !== index))}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        className={ADD_BUTTON_CLASS}
        onClick={() =>
          write([
            ...inputs,
            [freeName("input_", inputs.map(([name]) => name)), ""],
          ])
        }
      >
        Add input
      </button>
    </Section>
  );
}

function CodeOutputsEditor({ config, onChange }: SectionProps) {
  const outputs =
    (config.outputs as { name: string; type?: string }[] | undefined) ?? [];
  const write = (next: { name: string; type?: string }[]) =>
    onChange({ ...config, outputs: next });

  return (
    <Section
      title="Outputs"
      hint="The keys main() must return. Later steps read them as $key.output.name."
    >
      {outputs.map((output, index) => (
        <div key={index} className="flex items-center gap-2">
          <input
            aria-label={`Output ${index + 1} name`}
            className={INPUT_CLASS}
            placeholder="name"
            value={output.name}
            onChange={(e) =>
              write(
                outputs.map((o, i) =>
                  i === index ? { ...o, name: e.target.value } : o
                )
              )
            }
          />
          <select
            aria-label={`Output ${index + 1} type`}
            className={INPUT_CLASS}
            value={output.type ?? "string"}
            onChange={(e) =>
              write(
                outputs.map((o, i) =>
                  i === index ? { ...o, type: e.target.value } : o
                )
              )
            }
          >
            {OUTPUT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
          <button
            type="button"
            aria-label={`Remove output ${index + 1}`}
            className={ROW_BUTTON_CLASS}
            disabled={outputs.length <= 1}
            onClick={() => write(outputs.filter((_, i) => i !== index))}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        className={ADD_BUTTON_CLASS}
        onClick={() =>
          write([
            ...outputs,
            { name: freeName("output_", outputs.map((o) => o.name)), type: "string" },
          ])
        }
      >
        Add output
      </button>
    </Section>
  );
}

function CodeIoEditor(props: SectionProps) {
  return (
    <>
      <CodeInputsEditor {...props} />
      <CodeOutputsEditor {...props} />
    </>
  );
}

// ── Which editors each node type gets ───────────────────────────────────────

interface NodeForm {
  /** Fields the generated form leaves out. */
  hiddenFields: (config: Config) => string[];
  Editor?: ComponentType<SectionProps>;
}

const NODE_FORMS: Readonly<Record<string, NodeForm>> = {
  parallel: {
    hiddenFields: () => ["branches"],
    Editor: BranchLabelsEditor,
  },
  code: {
    hiddenFields: () => ["inputs", "outputs"],
    Editor: CodeIoEditor,
  },
  // A loop shows the settings of its mode only.
  loop: {
    hiddenFields: (config) => {
      if (config.mode !== "while") return LOOP_CONDITION_FIELDS;
      return VALUELESS_OPERATORS.has(String(config.operator))
        ? ["items", "match_value"]
        : ["items"];
    },
  },
};

export function NodeConfigForm({
  step,
  steps,
  schema,
  onChange,
}: {
  step: EditorStep;
  steps: readonly EditorStep[];
  schema: Record<string, unknown>;
  /** `removedBranch`: branch numbers above it have to shift down by one. */
  onChange: (config: Config, removedBranch?: number) => void;
}) {
  const config = step.config ?? {};
  const form = NODE_FORMS[step.step_type];
  const references = availableReferences(step, steps);

  return (
    <div className="flex flex-col gap-3">
      {form?.Editor && (
        <form.Editor
          step={step}
          steps={steps}
          config={config}
          references={references}
          onChange={onChange}
        />
      )}
      <SchemaConfigForm
        schema={schema}
        value={step.config}
        onChange={(next) => onChange(next)}
        hiddenFields={form?.hiddenFields(config) ?? []}
      />
      <p className="text-xs text-text-03" role="note">
        This step can read: {references.join(", ")}
      </p>
    </div>
  );
}
