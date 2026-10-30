"use client";

/**
 * A form generated from a node type's config JSON Schema, so node types
 * without a dedicated UI can still be configured in both workflow editors.
 * Modeled on the connector form (`FieldRendering.tsx`): the schema is parsed
 * into typed field options (`configSchema.ts`) and each kind has a renderer.
 * It is a controlled component (no Formik) so either editor can host it.
 */

import React, { useEffect, useId, useMemo, useState } from "react";
import {
  type ConfigField,
  type NumberField,
  type StringField,
  parseConfigSchema,
} from "@/lib/workflows/configSchema";

type Config = Record<string, unknown>;

export interface SchemaConfigFormProps {
  /** JSON Schema of the config (`NodeTypeVersionInfo.config_schema`). */
  schema: Record<string, unknown>;
  value: Config | null;
  onChange: (next: Config) => void;
  readOnly?: boolean;
  /** Field names to leave out (e.g. ones a specialized UI renders). */
  hiddenFields?: readonly string[];
}

const INPUT_CLASS =
  "w-full px-3 rounded-08 border border-border-02 bg-background-tint-00 text-text-05 text-sm disabled:opacity-60";

export function SchemaConfigForm({
  schema,
  value,
  onChange,
  readOnly = false,
  hiddenFields = [],
}: SchemaConfigFormProps) {
  const parsed = useMemo(() => parseConfigSchema(schema), [schema]);
  const fields = parsed.fields.filter((f) => !hiddenFields.includes(f.name));
  const config = value ?? {};

  const setField = (name: string, next: unknown) => {
    const updated = { ...config };
    if (next === undefined) delete updated[name];
    else updated[name] = next;
    onChange(updated);
  };

  return (
    <div className="flex flex-col gap-3">
      {fields.length === 0 && parsed.unsupported.length === 0 && (
        <p className="text-xs text-text-03">This step has no settings.</p>
      )}
      {fields.map((field) => (
        <FieldRow
          key={field.name}
          field={field}
          value={config[field.name]}
          readOnly={readOnly}
          onChange={(next) => setField(field.name, next)}
        />
      ))}
      {parsed.unsupported.length > 0 && (
        <p className="text-xs text-text-03" role="note">
          Not editable here: {parsed.unsupported.map((f) => f.label).join(", ")}
          . These settings are kept unchanged when you save.
        </p>
      )}
    </div>
  );
}

// ── One labelled field ───────────────────────────────────────────────────

interface FieldRowProps {
  field: ConfigField;
  value: unknown;
  readOnly: boolean;
  onChange: (next: unknown) => void;
}

function FieldRow({ field, value, readOnly, onChange }: FieldRowProps) {
  const id = useId();
  const label = (
    <span className="text-xs font-medium text-text-04">
      {field.label}
      {field.required && !field.nullable && (
        <span className="text-status-error-05"> *</span>
      )}
    </span>
  );

  if (field.kind === "boolean") {
    return (
      <div className="flex flex-col gap-0.5">
        <label htmlFor={id} className="flex items-center gap-2">
          <input
            id={id}
            type="checkbox"
            className="accent-[var(--theme-primary-05)]"
            checked={value === true}
            disabled={readOnly}
            onChange={(e) => onChange(e.target.checked)}
          />
          {label}
        </label>
        <Description text={field.description} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id}>{label}</label>
      <FieldInput
        id={id}
        field={field}
        value={value}
        readOnly={readOnly}
        onChange={onChange}
      />
      <Description text={field.description} />
    </div>
  );
}

function Description({ text }: { text?: string }) {
  return text ? <span className="text-xs text-text-03">{text}</span> : null;
}

// ── Inputs per field kind ────────────────────────────────────────────────

interface FieldInputProps extends FieldRowProps {
  id: string;
}

function FieldInput({ id, field, value, readOnly, onChange }: FieldInputProps) {
  switch (field.kind) {
    case "string":
      return (
        <StringInput
          id={id}
          field={field}
          value={value}
          readOnly={readOnly}
          onChange={onChange}
        />
      );
    case "number":
      return (
        <NumberInput
          id={id}
          field={field}
          value={value}
          readOnly={readOnly}
          onChange={onChange}
        />
      );
    case "enum": {
      const current = value == null ? "" : String(value);
      return (
        <select
          id={id}
          className={`${INPUT_CLASS} h-9`}
          value={current}
          disabled={readOnly}
          onChange={(e) => {
            const picked = field.options.find(
              (o) => String(o) === e.target.value
            );
            onChange(picked ?? (field.nullable ? null : undefined));
          }}
        >
          {(field.nullable || !field.required || current === "") && (
            <option value="">—</option>
          )}
          {field.options.map((option) => (
            <option key={String(option)} value={String(option)}>
              {String(option)}
            </option>
          ))}
        </select>
      );
    }
    case "string_list":
      return (
        <StringListInput
          id={id}
          value={value}
          readOnly={readOnly}
          onChange={onChange}
        />
      );
    case "boolean":
      return null; // rendered by FieldRow
  }
}

function emptyValue(field: ConfigField): null | undefined {
  return field.nullable ? null : undefined;
}

function StringInput({
  id,
  field,
  value,
  readOnly,
  onChange,
}: FieldInputProps & { field: StringField }) {
  const text = typeof value === "string" ? value : "";
  const update = (next: string) =>
    onChange(next === "" && field.nullable ? null : next);

  if (field.multiline) {
    return (
      <textarea
        id={id}
        className={`${INPUT_CLASS} py-2 ${field.monospace ? "font-mono" : ""}`}
        rows={field.monospace ? 8 : 3}
        value={text}
        disabled={readOnly}
        onChange={(e) => update(e.target.value)}
      />
    );
  }
  return (
    <input
      id={id}
      type="text"
      className={`${INPUT_CLASS} h-9`}
      value={text}
      disabled={readOnly}
      onChange={(e) => update(e.target.value)}
    />
  );
}

function NumberInput({
  id,
  field,
  value,
  readOnly,
  onChange,
}: FieldInputProps & { field: NumberField }) {
  return (
    <input
      id={id}
      type="number"
      className={`${INPUT_CLASS} h-9`}
      value={typeof value === "number" ? value : ""}
      min={field.minimum}
      max={field.maximum}
      step={field.integer ? 1 : "any"}
      disabled={readOnly}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw === "") return onChange(emptyValue(field));
        const parsed = Number(raw);
        if (!Number.isNaN(parsed)) onChange(parsed);
      }}
    />
  );
}

/** One entry per line; keeps a local draft so blank lines can be typed. */
function StringListInput({
  id,
  value,
  readOnly,
  onChange,
}: Omit<FieldInputProps, "field">) {
  const list = Array.isArray(value) ? value.map(String) : [];
  const joined = list.join("\n");
  const [draft, setDraft] = useState(joined);

  // Follow outside changes (e.g. an upgrade applied to the node).
  useEffect(() => {
    setDraft((current) =>
      current.split("\n").filter(Boolean).join("\n") === joined
        ? current
        : joined
    );
  }, [joined]);

  return (
    <textarea
      id={id}
      className={`${INPUT_CLASS} py-2`}
      rows={3}
      placeholder="One per line"
      value={draft}
      disabled={readOnly}
      onChange={(e) => {
        setDraft(e.target.value);
        onChange(
          e.target.value
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean)
        );
      }}
    />
  );
}
