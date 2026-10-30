import React, { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { SchemaConfigForm } from "./SchemaConfigForm";

const SCHEMA = {
  type: "object",
  properties: {
    source: { title: "Source", type: "string" },
    retries: {
      anyOf: [{ type: "integer" }, { type: "null" }],
      default: null,
      title: "Retries",
    },
    verbose: { title: "Verbose", type: "boolean", default: false },
    mode: { title: "Mode", enum: ["fast", "safe"], type: "string" },
    packages: { title: "Packages", type: "array", items: { type: "string" } },
    env: { title: "Env", type: "object" },
  },
  required: ["source"],
};

/** Hosts the controlled form and records every change. */
function Harness({
  initial,
  onChange,
  readOnly,
}: {
  initial: Record<string, unknown>;
  onChange: (v: Record<string, unknown>) => void;
  readOnly?: boolean;
}) {
  const [value, setValue] = useState(initial);
  return (
    <SchemaConfigForm
      schema={SCHEMA}
      value={value}
      readOnly={readOnly}
      onChange={(next) => {
        setValue(next);
        onChange(next);
      }}
    />
  );
}

describe("SchemaConfigForm", () => {
  it("renders a field per supported property and notes the rest", () => {
    render(<Harness initial={{ env: { A: "1" } }} onChange={jest.fn()} />);
    for (const label of ["Source", "Retries", "Verbose", "Mode", "Packages"]) {
      expect(screen.getByLabelText(new RegExp(label))).toBeInTheDocument();
    }
    expect(screen.getByRole("note")).toHaveTextContent(
      "Not editable here: Env"
    );
  });

  it("edits each kind of field and keeps unsupported values", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<Harness initial={{ env: { A: "1" } }} onChange={onChange} />);

    await user.click(screen.getByLabelText(/Source/));
    await user.paste("print(1)");
    await user.click(screen.getByLabelText(/Retries/));
    await user.paste("3");
    await user.click(screen.getByLabelText(/Verbose/));
    await user.selectOptions(screen.getByLabelText(/Mode/), "safe");
    await user.click(screen.getByLabelText(/Packages/));
    await user.paste("numpy\n\npandas");

    expect(onChange).toHaveBeenLastCalledWith({
      env: { A: "1" },
      source: "print(1)",
      retries: 3,
      verbose: true,
      mode: "safe",
      packages: ["numpy", "pandas"],
    });
  });

  it("clears a nullable number back to null", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<Harness initial={{ retries: 4 }} onChange={onChange} />);
    await user.clear(screen.getByLabelText(/Retries/));
    expect(onChange).toHaveBeenLastCalledWith({ retries: null });
  });

  it("disables inputs when read-only", () => {
    render(<Harness initial={{}} onChange={jest.fn()} readOnly />);
    expect(screen.getByLabelText(/Source/)).toBeDisabled();
    expect(screen.getByLabelText(/Verbose/)).toBeDisabled();
  });
});
