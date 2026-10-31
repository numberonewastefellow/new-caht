/**
 * A workflow as a tree: the top level and each container branch are "blocks", each
 * running its steps in order. Steps are stored flat (`parent_key` + `branch_index`);
 * this module is the one place that reads that structure. Used by both editors.
 */

export interface BlockStep {
  node_key: string;
  parent_key: string | null;
  branch_index: number | null;
}

const TOP_LEVEL = "top";

/** Identifies the block a step runs in. */
export function blockKey(step: BlockStep): string {
  return step.parent_key ? `${step.parent_key}#${step.branch_index}` : TOP_LEVEL;
}

export function isTopLevel(step: BlockStep): boolean {
  return blockKey(step) === TOP_LEVEL;
}

/** Steps grouped by block, keeping their relative order. */
export function groupByBlock<T extends BlockStep>(
  steps: readonly T[]
): Map<string, T[]> {
  const blocks = new Map<string, T[]>();
  for (const step of steps) {
    const key = blockKey(step);
    const block = blocks.get(key);
    if (block) block.push(step);
    else blocks.set(key, [step]);
  }
  return blocks;
}

/**
 * Execution order: each container is followed by its branches, lowest branch first,
 * keeping the order within each block. Steps whose container is missing go last, so
 * validation can report them.
 */
export function depthFirst<T extends BlockStep>(steps: readonly T[]): T[] {
  const keys = new Set(steps.map((s) => s.node_key));
  const childrenOf = new Map<string, T[]>();
  const roots: T[] = [];
  const orphans: T[] = [];
  for (const step of steps) {
    if (!step.parent_key) {
      roots.push(step);
    } else if (keys.has(step.parent_key)) {
      const children = childrenOf.get(step.parent_key);
      if (children) children.push(step);
      else childrenOf.set(step.parent_key, [step]);
    } else {
      orphans.push(step);
    }
  }

  const ordered: T[] = [];
  const seen = new Set<string>();
  const visit = (step: T) => {
    if (seen.has(step.node_key)) return;
    seen.add(step.node_key);
    ordered.push(step);
    const children = childrenOf.get(step.node_key) ?? [];
    const byBranch = children
      .map((child, position) => ({ child, position }))
      .sort(
        (a, b) =>
          (a.child.branch_index ?? 0) - (b.child.branch_index ?? 0) ||
          a.position - b.position
      );
    byBranch.forEach(({ child }) => visit(child));
  };
  roots.forEach(visit);
  // A cycle of parents has no root; keep those steps so validation can report them.
  steps.forEach((step) => {
    if (!seen.has(step.node_key) && !orphans.includes(step)) visit(step);
  });
  orphans.forEach(visit);
  return ordered;
}

/** The steps inside `key`, at any depth. */
export function descendantKeys(
  steps: readonly BlockStep[],
  key: string
): Set<string> {
  const found = new Set<string>();
  let added = true;
  while (added) {
    added = false;
    for (const step of steps) {
      const inside =
        step.parent_key === key ||
        (step.parent_key != null && found.has(step.parent_key));
      if (inside && !found.has(step.node_key)) {
        found.add(step.node_key);
        added = true;
      }
    }
  }
  return found;
}

export interface BlockPlace {
  parent_key: string | null;
  branch_index: number | null;
}

/**
 * Move a step, with anything inside it, into a block: at `position` among that
 * block's steps, or last. Moving a step into itself changes nothing.
 */
export function moveStep<T extends BlockStep>(
  steps: readonly T[],
  key: string,
  to: BlockPlace,
  position?: number
): T[] {
  const moving = steps.find((s) => s.node_key === key);
  if (!moving) return [...steps];
  if (to.parent_key === key || (to.parent_key && descendantKeys(steps, key).has(to.parent_key))) {
    return [...steps];
  }
  const moved: T = { ...moving, ...to };
  const rest = steps.filter((s) => s.node_key !== key);
  const block = rest.filter((s) => blockKey(s) === blockKey(moved));
  const before = position === undefined ? undefined : block[position];
  const at = before
    ? rest.indexOf(before)
    : block.length > 0
      ? rest.indexOf(block[block.length - 1]!) + 1
      : rest.length;
  return depthFirst([...rest.slice(0, at), moved, ...rest.slice(at)]);
}

/**
 * Remove a step. A container takes its steps with it, unless `keepChildren` moves
 * them into its place in the block around it.
 */
export function removeStep<T extends BlockStep>(
  steps: readonly T[],
  key: string,
  { keepChildren = false }: { keepChildren?: boolean } = {}
): T[] {
  const removed = steps.find((s) => s.node_key === key);
  if (!removed) return [...steps];
  if (!keepChildren) {
    const inside = descendantKeys(steps, key);
    return steps.filter((s) => s.node_key !== key && !inside.has(s.node_key));
  }
  return depthFirst(
    steps
      .filter((s) => s.node_key !== key)
      .map((s) =>
        s.parent_key === key
          ? { ...s, parent_key: removed.parent_key, branch_index: removed.branch_index }
          : s
      )
  );
}

/** Swap a step with its neighbour in the same block; containers keep their steps. */
export function reorderInBlock<T extends BlockStep>(
  steps: readonly T[],
  key: string,
  direction: -1 | 1
): T[] {
  const step = steps.find((s) => s.node_key === key);
  if (!step) return [...steps];
  const block = steps.filter((s) => blockKey(s) === blockKey(step));
  const index = block.indexOf(step);
  const neighbour = block[index + direction];
  if (!neighbour) return [...steps];
  const swapped = steps.map((s) =>
    s === step ? neighbour : s === neighbour ? step : s
  );
  return depthFirst(swapped);
}

export function canReorder(
  steps: readonly BlockStep[],
  key: string,
  direction: -1 | 1
): boolean {
  const step = steps.find((s) => s.node_key === key);
  if (!step) return false;
  const block = steps.filter((s) => blockKey(s) === blockKey(step));
  return block[block.indexOf(step) + direction] !== undefined;
}
