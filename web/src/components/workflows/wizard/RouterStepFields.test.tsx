import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import { RouterStepFields, toggleBranchTarget } from "./RouterStepFields";
import { defaultRouterConfig } from "@/lib/workflows/routerConfig";

describe("toggleBranchTarget", () => {
  it("keeps a step in at most one branch", () => {
    let config = toggleBranchTarget(defaultRouterConfig(), "true", "a", true);
    config = toggleBranchTarget(config, "false", "a", true);
    expect(config).toMatchObject({
      true_node_keys: [],
      false_node_keys: ["a"],
    });
    config = toggleBranchTarget(config, "false", "a", false);
    expect(config).toMatchObject({ true_node_keys: [], false_node_keys: [] });
  });
});

describe("RouterStepFields", () => {
  it("picks branch targets by step name and stores node keys", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(
      <RouterStepFields
        config={{ ...defaultRouterConfig(), condition_field: "$a.output" }}
        laterSteps={[
          { node_key: "s3", label: "3. Write" },
          { node_key: "n_1", label: "4. Escalate" },
        ]}
        onChange={onChange}
      />
    );

    const trueBranch = screen.getByRole("group", { name: "Run only if TRUE" });
    await user.click(
      Array.from(trueBranch.querySelectorAll("label")).find(
        (l) => l.textContent?.includes("Escalate")
      )!
    );
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        condition_field: "$a.output",
        true_node_keys: ["n_1"],
        false_node_keys: [],
      })
    );
  });

  it("explains when there is nothing to branch to", () => {
    render(
      <RouterStepFields config={null} laterSteps={[]} onChange={jest.fn()} />
    );
    expect(
      screen.getAllByText("Add steps after this condition to branch to them.")
    ).toHaveLength(2);
  });
});
