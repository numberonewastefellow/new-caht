"use client";

import React, { useState } from "react";
import {
  OUTPUT_SCHEMA_FIELD,
  stepOutputSchema,
} from "@/lib/workflows/nodeConfigRules";
import type { EditorStep } from "@/lib/workflows/editorModel";

const TEXT_VALUE = "text";
const JSON_VALUE = "json";
const STARTER_SCHEMA = {
  type: "object",
  properties: { result: { type: "string" } },
  required: ["result"],
};

const format = (schema: unknown) => JSON.stringify(schema, null, 2);

export interface OutputFormatClasses {
  section: string;
  label: string;
  select: string;
  textarea: string;
  hint: string;
  error: string;
}

/**
 * What an agent step must return: free text, or JSON of a declared shape, for when a
 * later step reads its fields. Used by both workflow editors.
 */
export function OutputFormatFields({
  step,
  classes,
  onChange,
}: {
  step: Pick<EditorStep, "config" | "can_request_input">;
  classes: OutputFormatClasses;
  onChange: (config: Record<string, unknown>) => void;
}) {
  const schema = stepOutputSchema(step);
  const [text, setText] = useState(schema ? format(schema) : "");
  const [invalid, setInvalid] = useState(false);

  const write = (next: unknown) =>
    onChange({ ...(step.config ?? {}), [OUTPUT_SCHEMA_FIELD]: next });

  const onModeChange = (value: string) => {
    setInvalid(false);
    if (value === TEXT_VALUE) {
      setText("");
      write(null);
      return;
    }
    setText(format(STARTER_SCHEMA));
    write(STARTER_SCHEMA);
  };

  const onSchemaChange = (value: string) => {
    setText(value);
    try {
      write(JSON.parse(value));
      setInvalid(false);
    } catch {
      setInvalid(true);
    }
  };

  return (
    <div className={classes.section}>
      <label className={classes.label}>
        Output format
        <select
          className={classes.select}
          value={schema ? JSON_VALUE : TEXT_VALUE}
          disabled={step.can_request_input && !schema}
          onChange={(e) => onModeChange(e.target.value)}
        >
          <option value={TEXT_VALUE}>Text</option>
          <option value={JSON_VALUE}>JSON</option>
        </select>
      </label>
      {step.can_request_input && !schema && (
        <p className={classes.hint}>
          A step that can ask the user questions returns text.
        </p>
      )}
      {schema !== null && (
        <>
          <label className={classes.label}>
            JSON schema
            <textarea
              className={classes.textarea}
              rows={8}
              spellCheck={false}
              value={text}
              onChange={(e) => onSchemaChange(e.target.value)}
            />
          </label>
          {invalid ? (
            <p className={classes.error} role="alert">
              This isn&apos;t valid JSON yet, so the last valid schema is kept.
            </p>
          ) : (
            <p className={classes.hint}>
              The agent must return this shape. Later steps read its fields, like
              $step.output.field. Its reply is checked, and retried once if it
              doesn&apos;t match.
            </p>
          )}
        </>
      )}
    </div>
  );
}
