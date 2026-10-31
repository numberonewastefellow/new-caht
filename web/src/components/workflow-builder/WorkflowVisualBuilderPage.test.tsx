import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { useWorkflow } from "@/hooks/useWorkflows";
import WorkflowVisualBuilderPage from "@/refresh-pages/WorkflowVisualBuilderPage";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));
jest.mock("@xyflow/react", () => ({
  ReactFlowProvider: ({ children }: { children: unknown }) => children,
}));
jest.mock("@/hooks/useWorkflows", () => ({ useWorkflow: jest.fn() }));
jest.mock("@/hooks/useAgents", () => ({
  useAgents: () => ({ agents: [], isLoading: false, refresh: jest.fn() }),
}));
jest.mock("@/lib/hooks/useLLMProviders", () => ({
  useLLMProviders: () => ({ llmProviders: [] }),
}));
jest.mock("@/hooks/useAvailableTools", () => ({
  useAvailableTools: () => ({ tools: [] }),
}));
jest.mock("@/lib/hooks/useDocumentSets", () => ({
  useDocumentSets: () => ({ documentSets: [] }),
}));
jest.mock("@/lib/workflows/useNodeTypes", () => ({
  useNodeTypes: () => ({ catalog: [], isReady: true, isLoading: false }),
}));
jest.mock("@/lib/workflows/api", () => ({
  describeSaveError: jest.fn(),
  saveWorkflow: jest.fn(),
}));
jest.mock("@/hooks/useToast", () => ({ toast: {} }));
jest.mock("@/components/workflow-builder/useWorkflowGraph", () => ({
  useWorkflowGraph: () => ({
    nodes: [],
    edges: [],
    meta: { name: "Test workflow" },
    modeConflicts: [],
    selectedNode: null,
    loadFromSnapshot: jest.fn(),
    stepOrderToNodeKey: jest.fn(),
  }),
}));
jest.mock("@/components/workflow-builder/graphUtils", () => ({
  graphToSteps: () => [],
}));
jest.mock("@/components/workflow-builder/WorkflowCanvas", () => ({
  WorkflowCanvas: () => "canvas",
}));
jest.mock("@/components/workflow-builder/AgentSidebar", () => ({
  AgentSidebar: () => null,
}));
jest.mock("@/components/workflow-builder/StepConfigPanel", () => ({
  StepConfigPanel: () => null,
}));
jest.mock("@/components/workflow-builder/GlobalConfigToolbar", () => ({
  GlobalConfigToolbar: () => null,
}));
jest.mock("@/components/workflow-builder/AgentTestModal", () => ({
  AgentTestModal: () => null,
}));
jest.mock("@/components/workflow-builder/QuickCreateAgentModal", () => ({
  QuickCreateAgentModal: () => null,
}));
jest.mock("@/components/workflow-builder/JsonViewModal", () => ({
  JsonViewModal: () => null,
}));
jest.mock("@/components/workflow-builder/NodeBadges", () => ({
  UPGRADE_NODE_EVENT: "wfb-upgrade-node",
}));
jest.mock("@/components/workflows/NodeUpgradeDialog", () => ({
  NodeUpgradeDialog: () => null,
}));
jest.mock("@/components/workflows/WorkflowVersionsDialog", () => ({
  WorkflowVersionsDialog: () => null,
}));

describe("WorkflowVisualBuilderPage", () => {
  it("keeps the same hook order when an existing workflow finishes loading", () => {
    const loadWorkflow = useWorkflow as jest.Mock;

    loadWorkflow.mockReturnValue({
      workflow: undefined,
      isLoading: true,
      refresh: jest.fn(),
    });
    const { rerender } = render(<WorkflowVisualBuilderPage workflowId={69} />);
    expect(screen.getByText("Loading workflow...")).toBeInTheDocument();

    loadWorkflow.mockReturnValue({
      workflow: { id: 69, name: "Test workflow", steps: [] },
      isLoading: false,
      refresh: jest.fn(),
    });
    rerender(<WorkflowVisualBuilderPage workflowId={69} />);

    expect(screen.getByText("canvas")).toBeInTheDocument();
    expect(screen.queryByText("Loading workflow...")).not.toBeInTheDocument();
  });
});
