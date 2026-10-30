/**
 * The Wizard (refresh-pages/WorkflowEditorPage) saves through the shared
 * serializer, so a save keeps fields it doesn't display (bug 2: it used to
 * drop input_mapping, every *_override and icon_name).
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom";
import WorkflowEditorPage from "@/refresh-pages/WorkflowEditorPage";
import { CATALOG, makeStep, makeWorkflow } from "@/lib/workflows/testFixtures";

const push = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push, back: jest.fn(), refresh: jest.fn() }),
  usePathname: () => "/admin/workflows/edit/1",
  useSearchParams: () => new URLSearchParams(),
}));
jest.mock("@/hooks/useAgents", () => ({
  useAgents: () => ({
    agents: [
      { id: 11, name: "Researcher", description: "" },
      { id: 13, name: "Writer", description: "" },
    ],
  }),
}));
jest.mock("@/hooks/useWorkflows", () => ({
  useWorkflows: () => ({ refresh: jest.fn() }),
  useWorkflowVersions: () => ({ versions: [], isLoading: false }),
  useWorkflowVersion: () => ({ detail: null, isLoading: false }),
}));
jest.mock("@/lib/hooks/useLLMProviders", () => ({
  useLLMProviders: () => ({ llmProviders: [] }),
}));
jest.mock("@/lib/workflows/useNodeTypes", () => ({
  useNodeTypes: () => ({ catalog: CATALOG, isReady: true, isLoading: false }),
}));
const mockSave = jest.fn();
jest.mock("@/lib/workflows/api", () => ({
  ...jest.requireActual("@/lib/workflows/api"),
  saveWorkflow: (...args: unknown[]) => mockSave(...args),
}));

const workflow = makeWorkflow([
  makeStep({
    id: 1,
    step_order: 0,
    input_mapping: { topic: "$user_input" },
    llm_model_override: "gpt-4.1",
    system_prompt_override: "Be brief.",
    tool_ids_override: [3],
  }),
  makeStep({
    id: 2,
    step_order: 1,
    step_type: "conditional_router",
    type_version: 2,
    latest_type_version: 2,
    agent_id: null,
    agent_name: null,
    output_key: "route",
    config: {
      condition_field: "$out_1.output",
      operator: "contains",
      match_value: "x",
      case_sensitive: false,
      true_node_keys: ["s3"],
      false_node_keys: [],
    },
  }),
  makeStep({ id: 3, step_order: 2, agent_id: 13 }),
]);

describe("Wizard save", () => {
  it("keeps node keys, overrides, input mappings and icon_name", async () => {
    const user = userEvent.setup();
    mockSave.mockResolvedValue({ ...workflow, version: 8 });
    render(<WorkflowEditorPage workflow={workflow} />);

    // Make the form dirty, then walk to the last wizard step and save.
    await user.click(screen.getByPlaceholderText(/Travel Planner/));
    await user.paste(" v2");
    await user.click(screen.getByRole("button", { name: /Next/ }));
    await user.click(screen.getByRole("button", { name: /Next/ }));
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(mockSave).toHaveBeenCalled());
    const [workflowId, payload] = mockSave.mock.calls[0]!;
    expect(workflowId).toBe(1);
    expect(payload).toMatchObject({
      name: "Fixture workflow v2",
      icon_name: "rocket",
      expected_version: 7,
    });
    expect(payload.steps).toEqual([
      expect.objectContaining({
        node_key: "s1",
        input_mapping: { topic: "$user_input" },
        llm_model_override: "gpt-4.1",
        system_prompt_override: "Be brief.",
        tool_ids_override: [3],
      }),
      expect.objectContaining({
        node_key: "s2",
        step_type: "conditional_router",
        type_version: 2,
        config: expect.objectContaining({ true_node_keys: ["s3"] }),
      }),
      expect.objectContaining({ node_key: "s3", agent_id: 13 }),
    ]);
  });
});
