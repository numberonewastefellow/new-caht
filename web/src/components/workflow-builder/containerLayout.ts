/**
 * Canvas layout for workflows with containers: a block is a row of steps, left to
 * right, and a container is a box holding one lane per branch, stacked vertically.
 * The workflow is a tree of such rows, so this needs no general graph layout. Pure,
 * and positions never affect execution.
 */

import { depthFirst, type BlockStep } from "@/lib/workflows/stepTree";

export interface Size {
  width: number;
  height: number;
}

export interface LayoutStep extends BlockStep {
  /** The node's own size; a container's size comes from its lanes instead. */
  size: Size;
  /** Lane labels, one per branch; null when the step isn't a container. */
  lanes: string[] | null;
}

export interface LaneBox {
  label: string;
  y: number;
  height: number;
}

export interface Placement {
  /** Relative to the parent box, or to the canvas at the top level. */
  x: number;
  y: number;
  parentId: string | null;
  size: Size;
  lanes: LaneBox[] | null;
}

export interface WorkflowLayout {
  placements: Map<string, Placement>;
  size: Size;
}

const STEP_GAP = 110;
const BOX_PADDING = 24;
const BOX_HEADER = 68;
const LANE_LABEL = 28;
const LANE_GAP = 14;
const LANE_PADDING = 12;
const EMPTY_LANE: Size = { width: 260, height: 70 };

interface Row {
  steps: LayoutStep[];
  size: Size;
}

function rowOf(steps: LayoutStep[], sizeOf: (step: LayoutStep) => Size): Row {
  if (steps.length === 0) return { steps, size: EMPTY_LANE };
  const sizes = steps.map(sizeOf);
  return {
    steps,
    size: {
      width:
        sizes.reduce((total, s) => total + s.width, 0) +
        STEP_GAP * (steps.length - 1),
      height: Math.max(...sizes.map((s) => s.height)),
    },
  };
}

export function layoutWorkflow(steps: readonly LayoutStep[]): WorkflowLayout {
  const ordered = depthFirst(steps);
  const childrenOf = new Map<string, LayoutStep[]>();
  for (const step of ordered) {
    if (!step.parent_key) continue;
    childrenOf.set(step.parent_key, [
      ...(childrenOf.get(step.parent_key) ?? []),
      step,
    ]);
  }

  const lanesOf = (container: LayoutStep): Row[] => {
    const children = childrenOf.get(container.node_key) ?? [];
    return (container.lanes ?? []).map((_, branch) =>
      rowOf(
        children.filter((c) => c.branch_index === branch),
        sizeOf
      )
    );
  };

  const sizes = new Map<string, Size>();
  function sizeOf(step: LayoutStep): Size {
    const known = sizes.get(step.node_key);
    if (known) return known;
    if (!step.lanes) return step.size;
    const rows = lanesOf(step);
    const size = {
      width:
        Math.max(step.size.width, ...rows.map((r) => r.size.width + LANE_PADDING * 2)) +
        BOX_PADDING * 2,
      height:
        BOX_HEADER +
        rows.reduce(
          (total, r) => total + LANE_LABEL + r.size.height + LANE_PADDING + LANE_GAP,
          0
        ) +
        BOX_PADDING -
        LANE_GAP,
    };
    sizes.set(step.node_key, size);
    return size;
  }

  const placements = new Map<string, Placement>();

  /** Places a row with its top-left at (x, y); steps are centered on the row. */
  function placeRow(
    row: Row,
    x: number,
    y: number,
    parentId: string | null
  ): void {
    let cursor = x;
    for (const step of row.steps) {
      const size = sizeOf(step);
      const stepY = y + (row.size.height - size.height) / 2;
      placements.set(step.node_key, {
        x: cursor,
        y: stepY,
        parentId,
        size,
        lanes: step.lanes ? placeLanes(step) : null,
      });
      cursor += size.width + STEP_GAP;
    }
  }

  function placeLanes(container: LayoutStep): LaneBox[] {
    let top = BOX_HEADER;
    return lanesOf(container).map((row, branch) => {
      const height = LANE_LABEL + row.size.height + LANE_PADDING;
      placeRow(row, BOX_PADDING + LANE_PADDING, top + LANE_LABEL, container.node_key);
      const lane = {
        label: container.lanes![branch]!,
        y: top,
        height,
      };
      top += height + LANE_GAP;
      return lane;
    });
  }

  const known = new Set(ordered.map((s) => s.node_key));
  const topLevel = rowOf(
    ordered.filter((s) => !s.parent_key || !known.has(s.parent_key)),
    sizeOf
  );
  placeRow(topLevel, 0, 0, null);
  return { placements, size: topLevel.size };
}
