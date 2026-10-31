"use client";

import { useCallback, useEffect, useRef } from "react";
import { useUser } from "@/providers/UserProvider";

/**
 * Pinned workflows, saved on the user's account (`preferences.pinned_workflows`)
 * so they follow the user across browsers and devices.
 *
 * Pins used to live only in localStorage; the first time this hook sees an
 * empty server list and leftover local pins, it uploads them once and clears
 * the local key.
 */
const LEGACY_STORAGE_KEY = "workflow-pinned-ids";
const EMPTY: number[] = [];

function readLegacy(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? parsed.filter((x): x is number => typeof x === "number")
      : [];
  } catch {
    return [];
  }
}

export function usePinnedWorkflows() {
  const { user, updateUserPinnedWorkflows } = useUser();
  const pinnedIds = user?.preferences?.pinned_workflows ?? EMPTY;
  const loaded = !!user?.id;
  const importedRef = useRef(false);

  useEffect(() => {
    if (!loaded || importedRef.current) return;
    importedRef.current = true;
    const legacy = readLegacy();
    if (legacy.length === 0) return;
    if (pinnedIds.length === 0) {
      void updateUserPinnedWorkflows(legacy);
    }
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded]);

  const isPinned = useCallback(
    (id: number) => pinnedIds.includes(id),
    [pinnedIds]
  );

  const togglePin = useCallback(
    (id: number) => {
      const next = pinnedIds.includes(id)
        ? pinnedIds.filter((x) => x !== id)
        : [...pinnedIds, id];
      void updateUserPinnedWorkflows(next);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pinnedIds]
  );

  // Drop pins for workflows that no longer exist. No-op when nothing is stale.
  const prune = useCallback(
    (validIds: number[]) => {
      const valid = new Set(validIds);
      const next = pinnedIds.filter((id) => valid.has(id));
      if (next.length !== pinnedIds.length) {
        void updateUserPinnedWorkflows(next);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pinnedIds]
  );

  return { pinnedIds, isPinned, togglePin, prune };
}
