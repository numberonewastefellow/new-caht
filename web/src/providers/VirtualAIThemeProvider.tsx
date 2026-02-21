"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

export type VirtualAIAccent = "none" | "ocean" | "emerald" | "violet";

const ACCENT_STORAGE_KEY = "virtualai-accent-theme";
const ACCENT_CLASS_PREFIX = "virtualai-";

interface VirtualAIThemeContextValue {
  accent: VirtualAIAccent;
  setAccent: (accent: VirtualAIAccent) => void;
}

const VirtualAIThemeContext = createContext<VirtualAIThemeContextValue>({
  accent: "none",
  setAccent: () => {},
});

export function useVirtualAITheme() {
  return useContext(VirtualAIThemeContext);
}

function getStoredAccent(): VirtualAIAccent {
  if (typeof window === "undefined") return "none";
  const stored = localStorage.getItem(ACCENT_STORAGE_KEY);
  if (
    stored === "ocean" ||
    stored === "emerald" ||
    stored === "violet"
  ) {
    return stored;
  }
  return "none";
}

function applyAccentClass(accent: VirtualAIAccent) {
  const html = document.documentElement;
  // Remove all existing accent classes
  html.classList.forEach((cls) => {
    if (cls.startsWith(ACCENT_CLASS_PREFIX)) {
      html.classList.remove(cls);
    }
  });
  // Add the new one (if not "none")
  if (accent !== "none") {
    html.classList.add(`${ACCENT_CLASS_PREFIX}${accent}`);
  }
}

export function VirtualAIThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [accent, setAccentState] = useState<VirtualAIAccent>("none");

  // Load from localStorage on mount
  useEffect(() => {
    const stored = getStoredAccent();
    setAccentState(stored);
    applyAccentClass(stored);
  }, []);

  const setAccent = useCallback((newAccent: VirtualAIAccent) => {
    setAccentState(newAccent);
    localStorage.setItem(ACCENT_STORAGE_KEY, newAccent);
    applyAccentClass(newAccent);
  }, []);

  return (
    <VirtualAIThemeContext.Provider value={{ accent, setAccent }}>
      {children}
    </VirtualAIThemeContext.Provider>
  );
}
