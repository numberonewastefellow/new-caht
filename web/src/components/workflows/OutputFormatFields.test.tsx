import React, { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { OutputFormatFields } from "./OutputFormatFields";

const CLASSES = {
  section: "",
  label: "",
  select: "",
  textarea: "",
  hint: "",
  error: "",
};

function setup(
  initial: Record<string, unknown> | null = null,
  canRequestInput = false
) {
  const onChange = jest.fn();
  function Harness() {
    const [config, setConfig] = useState(initial);
    return (
      <OutputFormatFields
        step={{ config, can_request_input: canRequestInput }}
        classes={CLASSES}
        onChange={(next) => {
          setConfig(next);
          onChange(next);
        }}
      />
    );
  }
  render(<Harness />);
  return onChange;
}

const format = () => screen.getByLabelText("Output format") as HTMLSelectElement;
const schemaBox = () => screen.queryByLabelText("JSON schema") as HTMLTextAreaElement | null;
const SCHEMA = { type: "object", properties: { days: { type: "array" } } };

describe("OutputFormatFields", () => {
  it("starts as text, with no schema box", () => {
    setup();
    expect(format().value).toBe("text");
    expect(schemaBox()).toBeNull();
  });

  it("shows a saved schema", () => {
    setup({ output_schema: SCHEMA });
    expect(format().value).toBe("json");
    expect(JSON.parse(schemaBox()!.value)).toEqual(SCHEMA);
  });

  it("switching to JSON offers a starting schema", () => {
    const onChange = setup();
    fireEvent.change(format(), { target: { value: "json" } });
    expect(onChange.mock.calls[0][0].output_schema.type).toBe("object");
    expect(schemaBox()).not.toBeNull();
  });

  it("switching back to text clears the schema", () => {
    const onChange = setup({ output_schema: SCHEMA });
    fireEvent.change(format(), { target: { value: "text" } });
    expect(onChange).toHaveBeenLastCalledWith({ output_schema: null });
    expect(schemaBox()).toBeNull();
  });

  it("keeps the last valid schema while the text isn't JSON", () => {
    const onChange = setup({ output_schema: SCHEMA });
    fireEvent.change(schemaBox()!, { target: { value: "{ not json" } });
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(schemaBox()!.value).toBe("{ not json");

    const next = { type: "object", properties: { a: { type: "string" } } };
    fireEvent.change(schemaBox()!, { target: { value: JSON.stringify(next) } });
    expect(onChange).toHaveBeenLastCalledWith({ output_schema: next });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("keeps the step's other settings", () => {
    const onChange = setup({ other: 1 });
    fireEvent.change(format(), { target: { value: "json" } });
    expect(onChange.mock.calls[0][0].other).toBe(1);
  });

  it("isn't offered on a step that can ask questions", () => {
    setup(null, true);
    expect(format()).toBeDisabled();
  });
});
