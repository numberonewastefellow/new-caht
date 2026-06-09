"use client";

import React, { createContext, useContext } from "react";
import { usePageVersion, PageVersion } from "@/hooks/usePageVersion";

/**
 * Reusable wrapper that renders the NEW or the LEGACY version of a page based
 * on usePageVersion(). It owns the version state and exposes a switch via
 * `useVersionSwitch()` so the rendered page can offer a "Classic view" /
 * "Try the new view" toggle that actually swaps what's shown.
 *
 * Usage (in a page.tsx):
 *   <VersionedPage versionKey="agentic-ai" current={<NewPage/>} legacy={<OldPage/>} />
 *
 * Web-only backward-compat mechanism — see AGENTIC_AI_REBRAND_PLAN.md.
 */
interface VersionSwitch {
  version: PageVersion;
  setVersion: (next: PageVersion) => void;
}

const VersionSwitchContext = createContext<VersionSwitch | null>(null);

export function useVersionSwitch(): VersionSwitch {
  const ctx = useContext(VersionSwitchContext);
  // Graceful no-op fallback so a page rendered outside <VersionedPage> (e.g. in
  // isolation/tests) doesn't crash.
  if (!ctx) return { version: "new", setVersion: () => {} };
  return ctx;
}

export default function VersionedPage({
  versionKey,
  current,
  legacy,
}: {
  versionKey: string;
  current: React.ReactNode;
  legacy: React.ReactNode;
}) {
  const { version, setVersion } = usePageVersion(versionKey);
  return (
    <VersionSwitchContext.Provider value={{ version, setVersion }}>
      {version === "legacy" ? legacy : current}
    </VersionSwitchContext.Provider>
  );
}
