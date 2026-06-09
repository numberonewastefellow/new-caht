"use client";

import { createContext, useContext, JSX } from "react";

/**
 * Web-only, runtime UI configuration injected from the server layout.
 *
 * `defaultUiVersion` is read from the plain (NON-public) `DEFAULT_UI_VERSION`
 * env var in `app/layout.tsx` (a `force-dynamic` server component) and passed
 * down here as a prop. Because it is NOT a `NEXT_PUBLIC_*` var, it is read at
 * request time on the server — changing it only requires a container restart,
 * not a rebuild. See AGENTIC_AI_REBRAND_PLAN.md.
 */
export type UiVersion = "new" | "legacy";

interface UiConfig {
  defaultUiVersion: UiVersion;
}

const UiConfigContext = createContext<UiConfig>({ defaultUiVersion: "new" });

export function UiConfigProvider({
  children,
  defaultUiVersion,
}: {
  children: React.ReactNode | JSX.Element;
  defaultUiVersion: UiVersion;
}) {
  return (
    <UiConfigContext.Provider value={{ defaultUiVersion }}>
      {children}
    </UiConfigContext.Provider>
  );
}

export function useUiConfig(): UiConfig {
  return useContext(UiConfigContext);
}
