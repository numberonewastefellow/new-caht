import {
  configDefaults,
  missingRequiredFields,
  parseConfigSchema,
} from "@/lib/workflows/configSchema";

/** Shaped like pydantic v2's `model_json_schema()` output. */
const SCHEMA = {
  title: "CodeConfigV1",
  type: "object",
  $defs: {
    Mode: { enum: ["fast", "safe"], title: "Mode", type: "string" },
  },
  properties: {
    source: { title: "Source", type: "string", format: "code" },
    label: { title: "Label", type: "string", default: "" },
    retries: {
      anyOf: [{ type: "integer", minimum: 0 }, { type: "null" }],
      default: null,
      title: "Retries",
      description: "How often to retry",
    },
    verbose: { title: "Verbose", type: "boolean", default: false },
    mode: { $ref: "#/$defs/Mode", default: "safe" },
    packages: { items: { type: "string" }, type: "array", title: "Packages" },
    env: {
      additionalProperties: { type: "string" },
      type: "object",
      title: "Env",
    },
    matrix: { items: { type: "integer" }, type: "array" },
  },
  required: ["source"],
};

describe("parseConfigSchema", () => {
  const parsed = parseConfigSchema(SCHEMA);

  it("maps supported properties to typed fields", () => {
    expect(parsed.fields.map((f) => [f.name, f.kind])).toEqual([
      ["source", "string"],
      ["label", "string"],
      ["retries", "number"],
      ["verbose", "boolean"],
      ["mode", "enum"],
      ["packages", "string_list"],
    ]);
    expect(parsed.fields[0]).toMatchObject({
      required: true,
      multiline: true,
      monospace: true,
    });
    expect(parsed.fields[2]).toMatchObject({
      nullable: true,
      integer: true,
      minimum: 0,
      label: "Retries",
      description: "How often to retry",
    });
    expect(parsed.fields[4]).toMatchObject({
      options: ["fast", "safe"],
      default: "safe",
    });
  });

  it("reports unsupported properties", () => {
    expect(parsed.unsupported).toEqual([
      { name: "env", label: "Env" },
      { name: "matrix", label: "Matrix" },
    ]);
  });

  it("renders x-ui code fields as monospace text areas", () => {
    const code = parseConfigSchema({
      properties: { code: { type: "string", "x-ui": "code" } },
    }).fields[0];
    expect(code).toMatchObject({
      kind: "string",
      multiline: true,
      monospace: true,
    });
  });

  it("uses defaults of fields it can't edit for new nodes", () => {
    const parsed = parseConfigSchema({
      properties: {
        inputs: { type: "object", default: { text: "$user_input" } },
      },
    });
    expect(configDefaults(parsed)).toEqual({ inputs: { text: "$user_input" } });
  });

  it("tolerates missing or empty schemas", () => {
    expect(parseConfigSchema(null)).toEqual({ fields: [], unsupported: [] });
    expect(parseConfigSchema({ type: "object" }).fields).toEqual([]);
  });

  it("builds defaults and finds missing required values", () => {
    expect(configDefaults(parsed)).toEqual({
      label: "",
      retries: null,
      verbose: false,
      mode: "safe",
    });
    expect(
      missingRequiredFields(parsed, { source: "  " }).map((f) => f.name)
    ).toEqual(["source"]);
    expect(missingRequiredFields(parsed, { source: "x" })).toEqual([]);
  });
});
