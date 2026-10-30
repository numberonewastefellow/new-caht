/**
 * Turn a node type's config JSON Schema (generated from its pydantic model)
 * into a flat list of form fields. Supported: string, number/integer,
 * boolean, enum and string arrays, each optionally nullable. Anything else is
 * reported in `unsupported` so the form can say it can't be edited here.
 */

export interface ConfigFieldBase {
  name: string;
  label: string;
  description?: string;
  required: boolean;
  /** `null` is an accepted value (e.g. `int | None`). */
  nullable: boolean;
}

export interface StringField extends ConfigFieldBase {
  kind: "string";
  default?: string;
  /** Render as a multi-line text area (`format: "textarea"` or `"code"`). */
  multiline: boolean;
  monospace: boolean;
}

export interface NumberField extends ConfigFieldBase {
  kind: "number";
  integer: boolean;
  minimum?: number;
  maximum?: number;
  default?: number;
}

export interface BooleanField extends ConfigFieldBase {
  kind: "boolean";
  default?: boolean;
}

export interface EnumField extends ConfigFieldBase {
  kind: "enum";
  options: (string | number)[];
  default?: string | number;
}

export interface StringListField extends ConfigFieldBase {
  kind: "string_list";
  default?: string[];
}

export type ConfigField =
  | StringField
  | NumberField
  | BooleanField
  | EnumField
  | StringListField;

export interface UnsupportedField {
  name: string;
  label: string;
  /** The schema default, used for new nodes (the value isn't editable here). */
  default?: unknown;
}

export interface ParsedConfigSchema {
  fields: ConfigField[];
  unsupported: UnsupportedField[];
}

type JsonSchema = Record<string, unknown>;

function asSchema(value: unknown): JsonSchema | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonSchema)
    : null;
}

/** "max_retries" -> "Max retries" (pydantic titles are used when present). */
function humanize(name: string): string {
  const words = name.replace(/_/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Follow a local `#/$defs/Name` reference (one level, as pydantic emits). */
function resolveRef(schema: JsonSchema, root: JsonSchema): JsonSchema {
  const ref = schema.$ref;
  if (typeof ref !== "string" || !ref.startsWith("#/$defs/")) return schema;
  const defs = asSchema(root.$defs);
  const target = asSchema(defs?.[ref.slice("#/$defs/".length)]);
  return target ? { ...target, ...schema, $ref: undefined } : schema;
}

/** Split `anyOf: [X, {type: "null"}]` into X plus a nullable flag. */
function unwrapNullable(
  schema: JsonSchema,
  root: JsonSchema
): { schema: JsonSchema; nullable: boolean } {
  const variants = Array.isArray(schema.anyOf)
    ? schema.anyOf.map(asSchema).filter((s): s is JsonSchema => !!s)
    : null;
  if (!variants) return { schema: resolveRef(schema, root), nullable: false };

  const nonNull = variants.filter((v) => v.type !== "null");
  const nullable = nonNull.length < variants.length;
  if (nonNull.length !== 1) return { schema, nullable };
  // Keep the outer title/description/default, which pydantic puts there.
  const { anyOf: _anyOf, ...outer } = schema;
  return { schema: { ...resolveRef(nonNull[0]!, root), ...outer }, nullable };
}

/** Code fields: `x-ui: "code"` (or `format: "code"`) in the schema. */
function isCode(schema: JsonSchema): boolean {
  return schema["x-ui"] === "code" || schema.format === "code";
}

function parseField(
  name: string,
  rawSchema: JsonSchema,
  root: JsonSchema,
  required: boolean
): ConfigField | null {
  const { schema, nullable } = unwrapNullable(rawSchema, root);
  const base: ConfigFieldBase = {
    name,
    label: typeof schema.title === "string" ? schema.title : humanize(name),
    description:
      typeof schema.description === "string" ? schema.description : undefined,
    required,
    nullable,
  };
  const dflt = schema.default;

  if (Array.isArray(schema.enum)) {
    const options = schema.enum.filter(
      (o): o is string | number =>
        typeof o === "string" || typeof o === "number"
    );
    return {
      ...base,
      kind: "enum",
      options,
      default:
        typeof dflt === "string" || typeof dflt === "number" ? dflt : undefined,
    };
  }

  switch (schema.type) {
    case "string":
      return {
        ...base,
        kind: "string",
        default: typeof dflt === "string" ? dflt : undefined,
        multiline:
          isCode(schema) ||
          schema.format === "textarea" ||
          schema["x-ui"] === "textarea",
        monospace: isCode(schema),
      };
    case "integer":
    case "number":
      return {
        ...base,
        kind: "number",
        integer: schema.type === "integer",
        minimum:
          typeof schema.minimum === "number" ? schema.minimum : undefined,
        maximum:
          typeof schema.maximum === "number" ? schema.maximum : undefined,
        default: typeof dflt === "number" ? dflt : undefined,
      };
    case "boolean":
      return {
        ...base,
        kind: "boolean",
        default: typeof dflt === "boolean" ? dflt : undefined,
      };
    case "array": {
      const items = asSchema(schema.items);
      if (items?.type !== "string") return null;
      return {
        ...base,
        kind: "string_list",
        default: Array.isArray(dflt)
          ? dflt.filter((v): v is string => typeof v === "string")
          : undefined,
      };
    }
    default:
      return null;
  }
}

export function parseConfigSchema(
  schema: Record<string, unknown> | null | undefined
): ParsedConfigSchema {
  const root = asSchema(schema) ?? {};
  const properties = asSchema(root.properties) ?? {};
  const required = new Set(
    Array.isArray(root.required) ? root.required.map(String) : []
  );

  const parsed: ParsedConfigSchema = { fields: [], unsupported: [] };
  for (const [name, value] of Object.entries(properties)) {
    const propSchema = asSchema(value);
    const field = propSchema
      ? parseField(name, propSchema, root, required.has(name))
      : null;
    if (field) {
      parsed.fields.push(field);
    } else {
      const title = propSchema?.title;
      parsed.unsupported.push({
        name,
        label: typeof title === "string" ? title : humanize(name),
        ...(propSchema && "default" in propSchema
          ? { default: propSchema.default }
          : {}),
      });
    }
  }
  return parsed;
}

/** The initial config for a new node: every field's schema default. */
export function configDefaults(
  parsed: ParsedConfigSchema
): Record<string, unknown> {
  const config: Record<string, unknown> = {};
  for (const field of parsed.unsupported) {
    if (field.default !== undefined) config[field.name] = field.default;
  }
  for (const field of parsed.fields) {
    if (field.default !== undefined) config[field.name] = field.default;
    else if (field.nullable) config[field.name] = null;
  }
  return config;
}

function isBlank(value: unknown): boolean {
  return (
    value === undefined ||
    value === null ||
    (typeof value === "string" && value.trim() === "")
  );
}

/** Required fields that have no value in `config`. */
export function missingRequiredFields(
  parsed: ParsedConfigSchema,
  config: Record<string, unknown> | null | undefined
): ConfigField[] {
  return parsed.fields.filter(
    (f) => f.required && !f.nullable && isBlank(config?.[f.name])
  );
}
