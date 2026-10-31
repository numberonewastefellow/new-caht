# Container UI: how platforms draw parallel branches and loops

**Date:** 2026-10-31. **Purpose:** the basis for TODO items 3b–3f. The earlier research covered engines, sandboxes and webhooks only; no canvas code was checked out in the local clones.

**Evidence limits:** read through a web summarizer from the raw GitHub files and official docs below, not line by line, and no screenshots were viewed. Claims marked *(inference)* aren't stated by the source. Dify main and n8n are clean-room: ideas only, no code copied.

## Summary

| Platform | Parallel on canvas | Loop on canvas | Stored as | Does the engine run that structure? |
|---|---|---|---|---|
| **Sim Studio** (Apache-2.0) | Container box | Container box | Parent link on each node, plus `loops`/`parallels` maps | No, compiled to a DAG |
| **Dify** (ideas only) | Fan-out edges *(inference)* | Container box on the same canvas | Flat nodes with container tags | Largely yes (graphon, container-scoped config) |
| **Flowise AgentFlow v2** (Apache-2.0) | Fan-out edges | Iteration box; Loop is a jump to a node ID | `parentNode`, `extent:'parent'` | Yes for Iteration |
| **n8n** (ideas only) | Fan-out edges | Back-edge to an earlier node | `connections` per node and output | Apparently direct; canvas position sets branch order |
| **Langflow** (MIT) | Not checked | Back-edge | Groups nested at `data.node.flow` | Groups are flattened; loops are detected cycles |
| **Power Automate / Logic Apps** (docs only) | Branches joined by `runAfter` | Nested Foreach and Scope | Nested `actions` | Yes, the definition is what runs |

## Decisions for our editors

| # | Decision | Why | Source |
|---|---|---|---|
| U1 | **Parallel is a box with one lane per branch** (user's decision, 2026-10-31). Loop is a box with one lane. | It matches how we store and run containers, shows the join clearly, and allows dragging between lanes. | [Sim subflow view](https://raw.githubusercontent.com/simstudioai/sim/main/packages/workflow-renderer/src/subflow/node-view.tsx), [Sim parallel docs](https://docs.sim.ai/blocks/parallel) |
| U2 | **Keep the flat step list with `parent_key` and `branch_index`.** The canvas is a view of it. | Dify and Sim both use flat nodes with membership. Our API and engine already use this, so the engine doesn't change. | [Dify types](https://raw.githubusercontent.com/langgenius/dify/main/web/app/components/workflow/types.ts), [Sim fixtures](https://patch-diff.githubusercontent.com/raw/simstudioai/sim/pull/3723.diff) |
| U3 | **Membership has one source of truth.** A step's container comes only from `parent_key`, never from edges. | Sim also holds `loops`/`parallels` with `nodes[]`, which looks like duplicated membership *(how it's derived wasn't found)*. | [Sim workflow types](https://raw.githubusercontent.com/simstudioai/sim/main/packages/workflow-types/src/workflow.ts) |
| U4 | **Order inside a block comes from walking the container tree**, depth-first, parents before children. Edges only order steps within their own block. | React Flow needs parents before children. Today's BFS save mixes blocks and can reorder router branches. | [React Flow sub-flows](https://reactflow.dev/learn/layouting/sub-flows), [Sim node order](https://raw.githubusercontent.com/simstudioai/sim/main/packages/workflow-renderer/src/node-order.ts) |
| U5 | **Edges stay within a block.** A connection across containers or lanes is refused. | Dify applies the same scoping. It keeps the drawing honest: a line always means "runs next, here". | [Dify connect handler](https://raw.githubusercontent.com/langgenius/dify/main/web/app/components/workflow/hooks/use-nodes-interactions.ts) |
| U6 | **Layout with ELK, not dagre.** | React Flow's docs list an open dagre issue with sub-flow nodes connected outside the sub-flow; elkjs has no such caveat. Dify uses a two-pass ELK layout. Neither is installed yet. | [React Flow layouting](https://reactflow.dev/learn/layouting/layouting), [Dify ELK layout](https://raw.githubusercontent.com/langgenius/dify/main/web/app/components/workflow/utils/elk-layout.ts) |
| U7 | **Children stay inside their box** with `parentId` and `extent:'parent'`; `expandParent` grows it. | Standard React Flow. Our version (`@xyflow/react` 12.10.1) supports `parentId` and `extent`. | [React Flow node API](https://reactflow.dev/api-reference/types/node) |
| U8 | **Canvas position never affects execution.** | n8n's position-dependent branch order is what we avoid. | [n8n execution order](https://docs.n8n.io/flow-logic/execution-order/) |
| U9 | **Don't infer loops from cycles.** Loop stays an explicit box with a mandatory limit. | Langflow's detected cycles and n8n's back-edges are harder to read and resume; Langflow documents If-Else not working with Loop. | [Langflow loop](https://docs.langflow.org/loop) |

## What this changes in our code

**Frontend only**, for building and editing:
- `lib/workflows/`: tree model, depth-first order, move helpers.
- `components/workflow-builder/`: a `container` node kind, lanes, ELK layout, drop-to-lane, refusing cross-block edges. `isStepNode` must not count lane nodes as steps.
- `refresh-pages/WorkflowEditorPage.tsx`: Run inside and Branch pickers, safe reorder and delete.

**Engine scheduling: no change.** `parent_key`, `branch_index` and `config` already round-trip through the API. The nesting combinations (loop in parallel, loop in loop, router in a branch) are allowed at save but have no end-to-end tests yet; item 3g adds them.

## Not verified
- How Sim maps `data.parentId` to React Flow's top-level field, and how `loops`/`parallels` are derived.
- Flowise Loop's appearance beyond its components; whether its fan-out runs serially (the queue in `buildAgentflow.ts` suggests so).
- "Columns" in Power Automate appear to be from screenshots only.
- These pages could not be fetched: `dify/.../utils/layout.ts`, `dify/api/core/workflow/nodes/iteration/iteration_node.py`, and two Power Automate guidance pages (`use-scopes`, `use-parallelism`).
