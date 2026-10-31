/**
 * Client-side view of the backend node type registry.
 *
 * Pure helpers over the catalog served by `GET /workflow/node-types` (see
 * `useNodeTypes`). Both workflow editors use these, so a node type the backend
 * adds shows up in their palettes without frontend changes. Node types with a
 * dedicated editor UI are listed in `SPECIALIZED_EDITORS`; every other type is
 * edited generically from its JSON-schema config.
 */

import type {
  NodeTypeInfo,
  NodeTypeVersionInfo,
  OrchestrationMode,
} from "./interfaces";

/** A node type catalog as returned by the backend. */
export type NodeCatalog = readonly NodeTypeInfo[];

export const AGENT_NODE_TYPE = "agent";
export const ROUTER_NODE_TYPE = "conditional_router";

/**
 * How an editor presents a node type:
 * - `agent` / `router`: a dedicated UI built into the editors;
 * - `schema`: a generic form generated from the type's config JSON schema;
 * - `container`: like `schema`, but it holds steps (parallel, loop);
 * - `unsupported`: the type is not in the catalog; shown read-only.
 */
export type NodeEditorKind =
  | "agent"
  | "router"
  | "schema"
  | "container"
  | "unsupported";

const SPECIALIZED_EDITORS: Readonly<Record<string, NodeEditorKind>> = {
  [AGENT_NODE_TYPE]: "agent",
  [ROUTER_NODE_TYPE]: "router",
};

// ── Lookups ──────────────────────────────────────────────────────────────

export function findNodeType(
  catalog: NodeCatalog,
  type: string
): NodeTypeInfo | undefined {
  return catalog.find((t) => t.type === type);
}

/** One version of a type, or undefined when either is unknown. */
export function versionInfo(
  catalog: NodeCatalog,
  type: string,
  version: number
): NodeTypeVersionInfo | undefined {
  return findNodeType(catalog, type)?.versions.find(
    (v) => v.version === version
  );
}

/** The latest registered version of a type. */
export function latestVersion(
  catalog: NodeCatalog,
  type: string
): NodeTypeVersionInfo | undefined {
  const info = findNodeType(catalog, type);
  return info ? versionInfo(catalog, type, info.latest_version) : undefined;
}

/** The version info for a step: its pinned version, else the latest. */
export function resolveVersion(
  catalog: NodeCatalog,
  type: string,
  version: number | null | undefined
): NodeTypeVersionInfo | undefined {
  return version == null
    ? latestVersion(catalog, type)
    : versionInfo(catalog, type, version);
}

// ── Capabilities ─────────────────────────────────────────────────────────

/**
 * Whether a node type may be used in an orchestration mode. Unknown types
 * (or a catalog that has not loaded) are not flagged; the server has the
 * final say when the workflow is saved.
 */
export function isAllowedInMode(
  catalog: NodeCatalog,
  type: string,
  version: number | null | undefined,
  mode: OrchestrationMode
): boolean {
  const info = resolveVersion(catalog, type, version);
  return info ? info.modes.includes(mode) : true;
}

/** Whether the node type holds child nodes (parallel, loop). */
export function isContainer(
  catalog: NodeCatalog,
  type: string,
  version?: number | null
): boolean {
  return resolveVersion(catalog, type, version)?.is_container ?? false;
}

/**
 * Node types that can be added in `mode`, in catalog order: the latest
 * version must not be deprecated and must support the mode.
 */
export function paletteTypes(
  catalog: NodeCatalog,
  mode: OrchestrationMode
): NodeTypeInfo[] {
  return catalog.filter((t) => {
    const latest = latestVersion(catalog, t.type);
    return !!latest && !latest.deprecated && latest.modes.includes(mode);
  });
}

// ── Presentation ─────────────────────────────────────────────────────────

/** "code_runner" -> "Code runner"; used for types the catalog lacks. */
export function humanizeNodeType(type: string): string {
  const words = type.replace(/[_-]+/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Step";
}

/** Display label of a node type (version-specific when given). */
export function labelFor(
  catalog: NodeCatalog,
  type: string,
  version?: number | null
): string {
  return (
    resolveVersion(catalog, type, version)?.label ?? humanizeNodeType(type)
  );
}

/** Which editor UI a step of this type gets (see NodeEditorKind). */
export function editorKindFor(
  catalog: NodeCatalog,
  type: string
): NodeEditorKind {
  const specialized = SPECIALIZED_EDITORS[type];
  if (specialized) return specialized;
  if (!findNodeType(catalog, type)) return "unsupported";
  return isContainer(catalog, type) ? "container" : "schema";
}
