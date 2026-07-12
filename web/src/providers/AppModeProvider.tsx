"use client";

import React, { createContext, useCallback, useContext, useState } from "react";
import { useUser } from "@/providers/UserProvider";

export type AppMode = "auto" | "search" | "chat";

interface AppModeContextValue {
  appMode: AppMode;
  setAppMode: (mode: AppMode) => void;
}

export const AppModeContext = createContext<AppModeContextValue>({
  appMode: "chat",
  setAppMode: () => undefined,
});

export function useAppMode(): AppModeContextValue {
  return useContext(AppModeContext);
}

export interface AppModeProviderProps {
  children: React.ReactNode;
}

/**
 * Provider for application mode (Search/Chat).
 *
 * This controls how user queries are handled:
 * - **search**: Forces search mode - quick document lookup
 * - **chat**: Forces chat mode - conversation with follow-up questions
 *
 * The initial mode is read from the user's persisted `default_app_mode` preference.
 */
export function AppModeProvider({ children }: AppModeProviderProps) {
  const { user } = useUser();

  const persistedMode = user?.preferences?.default_app_mode;
  const initialMode: AppMode = persistedMode
    ? (persistedMode.toLowerCase() as AppMode)
    : "chat";

  const [appMode, setAppModeState] = useState<AppMode>(initialMode);

  const setAppMode = useCallback((mode: AppMode) => {
    setAppModeState(mode);
  }, []);

  return (
    <AppModeContext.Provider value={{ appMode, setAppMode }}>
      {children}
    </AppModeContext.Provider>
  );
}
