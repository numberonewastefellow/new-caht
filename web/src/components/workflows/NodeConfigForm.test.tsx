import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { NodeConfigForm } from "./NodeConfigForm";
import { createEditorStep, type EditorStep } from "@/lib/workflows/editorModel";
import { CATALOG } from "@/lib/workflows/testFixtures";

const SCHEMAS: Record<string, Record<string, unknown>> = {
  parallel: {
    type: "object",
    properties: {
      branches: { type: "array", title: "Branches", items: { type: "object" } },
      max_concurrency: { type: "integer", title: "Max concurrency" },
    },
  },
  loop: {
    type: "object",
    properties: {
      mode: { enum: ["for_each", "while"], type: "string", title: "Mode" },
      items: { type: "string", title: "Items" },
      condition_field: { type: "string", title: "Condition field" },
      operator: { enum: ["contains", "is_empty"], type: "string", title: "Operator" },
      match_value: { type: "string", title: "Match value" },
    },
  },
  code: {
    type: "object",
    properties: {
      code: { type: "string", title: "Code" },
      inputs: { type: "object", title: "Inputs" },
      outputs: { type: "array", title: "Outputs", items: { type: "object" } },
    },
  },
};

function setup(step: EditorStep, steps: EditorStep[] = [step]) {
  const onChange = jest.fn();
  render(
    <NodeConfigForm
      step={step}
      steps={steps}
      schema={SCHEMAS[step.step_type]!}
      onChange={onChange}
    />
  );
  return onChange;
}

const parallel = (branches: string[]) =>
  createEditorStep("parallel", CATALOG, {
    node_key: "p",
    step_name: "Fan out",
    output_key: "p",
    config: { branches: branches.map((label) => ({ label })) },
  });

const child = (key: string, branch: number) =>
  createEditorStep("agent", CATALOG, {
    node_key: key,
    agent_id: 1,
    step_name: key,
    output_key: key,
    parent_key: "p",
    branch_index: branch,
  });

const loop = (config: Record<string, unknown>) =>
  createEditorStep("loop", CATALOG, {
    node_key: "l",
    step_name: "Each",
    output_key: "l",
    config,
  });

const code = (config: Record<string, unknown>) =>
  createEditorStep("code", CATALOG, {
    node_key: "c",
    step_name: "Code",
    output_key: "c",
    config,
  });

describe("parallel branches", () => {
  it("renames a branch", () => {
    const onChange = setup(parallel(["A", "B"]));
    fireEvent.change(screen.getByLabelText("Branch 1 name"), {
      target: { value: "Flights" },
    });
    expect(onChange).toHaveBeenCalledWith(
      { branches: [{ label: "Flights" }, { label: "B" }] },
      undefined
    );
  });

  it("adds a branch, up to eight", () => {
    const onChange = setup(parallel(["A", "B"]));
    fireEvent.click(screen.getByText("Add branch"));
    expect(onChange).toHaveBeenCalledWith(
      { branches: [{ label: "A" }, { label: "B" }, { label: "Branch 3" }] },
      undefined
    );
  });

  it("lets a branch name be cleared while typing", () => {
    setup(parallel(["", "B"]));
    expect(screen.getByLabelText("Branch 1 name")).toHaveValue("");
  });

  it("a new branch doesn't repeat an existing name", () => {
    const onChange = setup(parallel(["Branch 3", "B"]));
    fireEvent.click(screen.getByText("Add branch"));
    expect(onChange).toHaveBeenCalledWith(
      { branches: [{ label: "Branch 3" }, { label: "B" }, { label: "Branch 4" }] },
      undefined
    );
  });

  it("disables adding beyond eight branches", () => {
    setup(parallel(["1", "2", "3", "4", "5", "6", "7", "8"]));
    expect(screen.getByText("Add branch")).toBeDisabled();
  });

  it("reports which branch was removed, so step numbers can shift", () => {
    const onChange = setup(parallel(["A", "B", "C"]));
    fireEvent.click(screen.getByLabelText("Remove branch 2"));
    expect(onChange).toHaveBeenCalledWith(
      { branches: [{ label: "A" }, { label: "C" }] },
      1
    );
  });

  it("won't remove a branch holding steps, or go below two", () => {
    const p = parallel(["A", "B", "C"]);
    setup(p, [p, child("x", 0)]);
    expect(screen.getByLabelText("Remove branch 1")).toBeDisabled();
    expect(screen.getByLabelText("Remove branch 2")).toBeEnabled();
  });

  it("won't go below two branches", () => {
    setup(parallel(["A", "B"]));
    expect(screen.getByLabelText("Remove branch 1")).toBeDisabled();
  });

  it("hides the generated field for branches", () => {
    setup(parallel(["A", "B"]));
    expect(screen.queryByText(/Not editable here/)).toBeNull();
  });
});

describe("loop", () => {
  it("shows items for a for-each loop, not the condition", () => {
    setup(loop({ mode: "for_each" }));
    expect(screen.getByLabelText("Items")).toBeInTheDocument();
    expect(screen.queryByLabelText("Condition field")).toBeNull();
    expect(screen.queryByLabelText("Operator")).toBeNull();
  });

  it("shows the condition for a while loop, not items", () => {
    setup(loop({ mode: "while", operator: "contains" }));
    expect(screen.queryByLabelText("Items")).toBeNull();
    expect(screen.getByLabelText("Condition field")).toBeInTheDocument();
    expect(screen.getByLabelText("Match value")).toBeInTheDocument();
  });

  it("offers the operator as a choice", () => {
    setup(loop({ mode: "while", operator: "contains" }));
    expect(screen.getByLabelText("Operator").tagName).toBe("SELECT");
  });

  it("hides the match value for operators that compare against nothing", () => {
    setup(loop({ mode: "while", operator: "is_empty" }));
    expect(screen.queryByLabelText("Match value")).toBeNull();
  });
});

describe("code inputs and outputs", () => {
  it("edits an input's name and value", () => {
    const onChange = setup(code({ inputs: { text: "$user_input" } }));
    const name = screen.getByLabelText("Input 1 name");
    fireEvent.change(name, { target: { value: "request" } });
    fireEvent.blur(name);
    expect(onChange).toHaveBeenLastCalledWith({
      inputs: { request: "$user_input" },
    });
    fireEvent.change(screen.getByLabelText("Input 1 value"), {
      target: { value: "hello" },
    });
    expect(onChange).toHaveBeenLastCalledWith({ inputs: { text: "hello" } });
  });

  it("won't merge two inputs by giving them the same name", () => {
    const onChange = setup(code({ inputs: { a: "1", b: "2" } }));
    const name = screen.getByLabelText("Input 2 name") as HTMLInputElement;
    fireEvent.change(name, { target: { value: "a" } });
    fireEvent.blur(name);
    expect(onChange).not.toHaveBeenCalled();
    expect(name.value).toBe("b");
  });

  it("adding an input never overwrites one with the suggested name", () => {
    const onChange = setup(code({ inputs: { input_2: "keep", other: "x" } }));
    fireEvent.click(screen.getByText("Add input"));
    expect(onChange).toHaveBeenLastCalledWith({
      inputs: { input_2: "keep", other: "x", input_3: "" },
    });
  });

  it("adds and removes an input", () => {
    const onChange = setup(code({ inputs: { text: "x" } }));
    fireEvent.click(screen.getByText("Add input"));
    expect(onChange).toHaveBeenLastCalledWith({
      inputs: { text: "x", input_2: "" },
    });
    fireEvent.click(screen.getByLabelText("Remove input 1"));
    expect(onChange).toHaveBeenLastCalledWith({ inputs: {} });
  });

  it("edits an output's name and type", () => {
    const onChange = setup(code({ outputs: [{ name: "result", type: "string" }] }));
    fireEvent.change(screen.getByLabelText("Output 1 type"), {
      target: { value: "array" },
    });
    expect(onChange).toHaveBeenLastCalledWith({
      outputs: [{ name: "result", type: "array" }],
    });
  });

  it("keeps at least one output", () => {
    setup(code({ outputs: [{ name: "result" }] }));
    expect(screen.getByLabelText("Remove output 1")).toBeDisabled();
  });
});

describe("what a step can read", () => {
  it("lists references from earlier steps", () => {
    const first = createEditorStep("agent", CATALOG, {
      node_key: "a",
      agent_id: 1,
      step_name: "a",
      output_key: "research",
    });
    const c = code({});
    setup(c, [first, c]);
    expect(screen.getByRole("note")).toHaveTextContent(
      "This step can read: $user_input, $research.output"
    );
  });
});
