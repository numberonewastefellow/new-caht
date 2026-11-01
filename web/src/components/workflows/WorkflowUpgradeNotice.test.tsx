import React from "react";
import { fireEvent, render, screen, waitFor } from "@tests/setup/test-utils";
import "@testing-library/jest-dom";
import WorkflowUpgradeNotice from "./WorkflowUpgradeNotice";
import { saveWorkflow } from "@/lib/workflows/api";
import type { WorkflowSnapshot } from "@/lib/workflows/interfaces";

jest.mock("@/lib/workflows/api", () => ({
  describeSaveError: (e: Error) => e.message,
  saveWorkflow: jest.fn(),
}));

const workflow = (schema_version: number) =>
  ({ id: 7, version: 3, schema_version }) as WorkflowSnapshot;

describe("WorkflowUpgradeNotice", () => {
  beforeEach(() => jest.clearAllMocks());

  it("only shows on the older format", () => {
    const { rerender } = render(
      <WorkflowUpgradeNotice workflow={workflow(2)} onUpgraded={jest.fn()} />
    );
    expect(screen.queryByTestId("workflow-upgrade-notice")).not.toBeInTheDocument();
    rerender(<WorkflowUpgradeNotice workflow={null} onUpgraded={jest.fn()} />);
    expect(screen.queryByTestId("workflow-upgrade-notice")).not.toBeInTheDocument();
    rerender(<WorkflowUpgradeNotice workflow={workflow(1)} onUpgraded={jest.fn()} />);
    expect(screen.getByTestId("workflow-upgrade-notice")).toBeInTheDocument();
  });

  it("upgrades this version of the workflow and reports back", async () => {
    const upgraded = workflow(2);
    (saveWorkflow as jest.Mock).mockResolvedValue(upgraded);
    const onUpgraded = jest.fn();
    render(<WorkflowUpgradeNotice workflow={workflow(1)} onUpgraded={onUpgraded} />);

    fireEvent.click(screen.getByRole("button", { name: "Upgrade references" }));

    await waitFor(() => expect(onUpgraded).toHaveBeenCalledWith(upgraded));
    expect(saveWorkflow).toHaveBeenCalledWith(7, { schema_version: 2, expected_version: 3 });
  });

  it("doesn't report an upgrade the server refused", async () => {
    (saveWorkflow as jest.Mock).mockRejectedValue(new Error('"Step" reads $missing'));
    const onUpgraded = jest.fn();
    render(<WorkflowUpgradeNotice workflow={workflow(1)} onUpgraded={onUpgraded} />);

    fireEvent.click(screen.getByRole("button", { name: "Upgrade references" }));

    await waitFor(() => expect(saveWorkflow).toHaveBeenCalled());
    expect(onUpgraded).not.toHaveBeenCalled();
  });
});
