import type { CSSProperties } from "react";
import type { Workspace } from "@/app/app/workspaces/workspacesService";

/**
 * Per-workspace identity colors. These are decorative/categorical swatches
 * defined in `colors.css` (`--ws-swatch-N-from/to`, with light + dark variants),
 * NOT the user's accent theme. Each workspace deterministically maps to one
 * swatch by its id so the same workspace always shows the same color.
 */
/** The three tabs of the new workspace detail surface. */
export type WorkspaceTab = "overview" | "files" | "chats";

const SWATCH_COUNT = 6;

export interface Swatch {
  from: string; // CSS var() reference
  to: string; // CSS var() reference
}

export function swatchForId(id: number): Swatch {
  const n = (Math.abs(Math.trunc(id)) % SWATCH_COUNT) + 1;
  return {
    from: `var(--ws-swatch-${n}-from)`,
    to: `var(--ws-swatch-${n}-to)`,
  };
}

/**
 * Deterministic swatch index (1..SWATCH_COUNT) for an arbitrary string key (e.g.
 * a chat UUID), so the same key always maps to the same `--ws-swatch-N-*` color.
 */
export function swatchIndexForKey(key: string): number {
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = (hash * 31 + key.charCodeAt(i)) | 0;
  }
  return (Math.abs(hash) % SWATCH_COUNT) + 1;
}

/** Inline gradient background for a workspace glyph/icon. */
export function swatchGradientStyle(id: number): CSSProperties {
  const { from, to } = swatchForId(id);
  return { backgroundImage: `linear-gradient(135deg, ${from}, ${to})` };
}

/**
 * "Updated" timestamp for a workspace: the most recent chat activity, falling
 * back to the workspace's creation time. Returns an ISO string.
 */
export function workspaceUpdatedAt(workspace: Workspace): string {
  let latestMs = new Date(workspace.created_at).getTime();
  let latestIso = workspace.created_at;
  for (const cs of workspace.chat_sessions ?? []) {
    const ms = new Date(cs.time_updated).getTime();
    if (!Number.isNaN(ms) && ms > latestMs) {
      latestMs = ms;
      latestIso = cs.time_updated;
    }
  }
  return latestIso;
}
