"use client";

import { createContext, useContext, JSX } from "react";
import { DEFAULT_NAV_VERSION, type NavVersion } from "@/lib/navVersion";

/**
 * Web-only, runtime UI configuration injected from the server layout.
 *
 * `defaultUiVersion` is read from the plain (NON-public) `DEFAULT_UI_VERSION`
 * env var in `app/layout.tsx` (a `force-dynamic` server component) and passed
 * down here as a prop. Because it is NOT a `NEXT_PUBLIC_*` var, it is read at
 * request time on the server — changing it only requires a container restart,
 * not a rebuild. See AGENTIC_AI_REBRAND_PLAN.md.
 *
 * `defaultNavVersion` is the same idea for the navigation chrome, read from
 * `DEFAULT_NAV_VERSION`. It is a separate var on purpose: `DEFAULT_UI_VERSION`
 * versions page bodies, and sharing one switch would mean flipping the
 * workflows page also flipped the whole nav. See `lib/navVersion.ts`.
 */
export type UiVersion = "new" | "legacy";

interface UiConfig {
  defaultUiVersion: UiVersion;
  defaultNavVersion: NavVersion;
}

const UiConfigContext = createContext<UiConfig>({
  defaultUiVersion: "new",
  defaultNavVersion: DEFAULT_NAV_VERSION,
});

export function UiConfigProvider({
  children,
  defaultUiVersion,
  defaultNavVersion,
}: {
  children: React.ReactNode | JSX.Element;
  defaultUiVersion: UiVersion;
  defaultNavVersion: NavVersion;
}) {
  return (
    <UiConfigContext.Provider value={{ defaultUiVersion, defaultNavVersion }}>
      {children}
    </UiConfigContext.Provider>
  );
}

export function useUiConfig(): UiConfig {
  return useContext(UiConfigContext);
}
