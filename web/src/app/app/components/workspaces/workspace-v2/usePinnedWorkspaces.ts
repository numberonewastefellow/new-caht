"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Client-only pinned-workspace state (no backend support for pinning).
 * Persisted to localStorage so it survives reloads and stays in sync across tabs.
 */
const STORAGE_KEY = "workspace-pinned-ids";

function readStored(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? parsed.filter((x): x is number => typeof x === "number")
      : [];
  } catch {
    return [];
  }
}

function writeStored(next: number[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}

export function usePinnedWorkspaces() {
  // Start empty so SSR/first client render match; hydrate in an effect.
  const [pinnedIds, setPinnedIds] = useState<number[]>([]);

  useEffect(() => {
    setPinnedIds(readStored());
  }, []);

  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === STORAGE_KEY) setPinnedIds(readStored());
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const persist = useCallback((next: number[]) => {
    setPinnedIds(next);
    writeStored(next);
  }, []);

  const isPinned = useCallback(
    (id: number) => pinnedIds.includes(id),
    [pinnedIds]
  );

  const togglePin = useCallback(
    (id: number) => {
      const next = pinnedIds.includes(id)
        ? pinnedIds.filter((x) => x !== id)
        : [...pinnedIds, id];
      setPinnedIds(next);
      writeStored(next);
    },
    [pinnedIds]
  );

  // Drop pins for workspaces that no longer exist so localStorage can't grow
  // unbounded. No-op (and no re-render) when nothing is stale, so it's safe to
  // call from an effect on every workspaces change.
  const prune = useCallback(
    (validIds: number[]) => {
      const valid = new Set(validIds);
      const next = pinnedIds.filter((id) => valid.has(id));
      if (next.length !== pinnedIds.length) {
        setPinnedIds(next);
        writeStored(next);
      }
    },
    [pinnedIds]
  );

  return { pinnedIds, isPinned, togglePin, persist, prune };
}
