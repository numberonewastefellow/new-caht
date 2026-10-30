/**
 * Visual Builder UI registration: which canvas node and config panel each
 * editor kind uses (see `editorKindFor` in @/lib/workflows/nodeRegistry).
 *
 * A node type the backend adds with no frontend change is a `schema` node:
 * GenericNode on the canvas and a form generated from its config schema.
 * To give a type its own UI, add an editor kind for it in nodeRegistry.ts
 * and register its components here (and its Wizard rendering).
 */

import type { ComponentType } from "react";
import type { NodeProps, NodeTypes } from "@xyflow/react";
import type { NodeEditorKind } from "@/lib/workflows/nodeRegistry";
import { AgentNode } from "./AgentNode";
import { ConditionalRouterNode } from "./ConditionalRouterNode";
import { FinishNode } from "./FinishNode";
import { GenericNode } from "./GenericNode";
import { OrchestratorNode } from "./OrchestratorNode";
import { AgentConfigPanel } from "./NodeConfigPanel";
import { RouterConfigPanel } from "./RouterConfigPanel";
import {
  GenericConfigPanel,
  UnsupportedConfigPanel,
} from "./GenericConfigPanel";
import { GenericNodeIcon, RouterIcon } from "./nodeIcons";
import type { StepConfigPanel } from "./types";

export interface NodeKindUi {
  /** Canvas component (React Flow custom node). */
  CanvasNode: ComponentType<NodeProps & { data: never }>;
  /** Right-hand config panel for a selected node. */
  ConfigPanel: StepConfigPanel;
  /** Icon on the node's card in the Utils palette. */
  PaletteIcon: ComponentType<{ size?: number }>;
  /** CSS modifier of the palette card (`wfb-sidebar-card--<variant>`). */
  paletteVariant: "condition" | "generic";
  /** Agents are dragged from the Agents tab, not the Utils palette. */
  inUtilsPalette: boolean;
}

export const NODE_KIND_UI: Record<NodeEditorKind, NodeKindUi> = {
  agent: {
    CanvasNode: AgentNode,
    ConfigPanel: AgentConfigPanel,
    PaletteIcon: GenericNodeIcon,
    paletteVariant: "generic",
    inUtilsPalette: false,
  },
  router: {
    CanvasNode: ConditionalRouterNode,
    ConfigPanel: RouterConfigPanel,
    PaletteIcon: RouterIcon,
    paletteVariant: "condition",
    inUtilsPalette: true,
  },
  schema: {
    CanvasNode: GenericNode,
    ConfigPanel: GenericConfigPanel,
    PaletteIcon: GenericNodeIcon,
    paletteVariant: "generic",
    inUtilsPalette: true,
  },
  unsupported: {
    CanvasNode: GenericNode,
    ConfigPanel: UnsupportedConfigPanel,
    PaletteIcon: GenericNodeIcon,
    paletteVariant: "generic",
    inUtilsPalette: false,
  },
};

/** React Flow node types: every editor kind plus the start/end nodes. */
export const FLOW_NODE_TYPES: NodeTypes = {
  orchestrator: OrchestratorNode as NodeTypes[string],
  finish: FinishNode,
  ...Object.fromEntries(
    Object.entries(NODE_KIND_UI).map(([kind, ui]) => [
      kind,
      ui.CanvasNode as NodeTypes[string],
    ])
  ),
};

export function nodeKindUi(kind: string | undefined): NodeKindUi {
  return NODE_KIND_UI[kind as NodeEditorKind] ?? NODE_KIND_UI.unsupported;
}

export function configPanelFor(kind: string | undefined): StepConfigPanel {
  return nodeKindUi(kind).ConfigPanel;
}
