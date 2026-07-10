"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

// ─── Accent Theme ────────────────────────────────────────────────────────

export type VirtualAIAccent = "none" | "ocean" | "emerald" | "violet" | "neonai";

const ACCENT_STORAGE_KEY = "virtualai-accent-theme";
const ACCENT_CLASS_PREFIX = "virtualai-";

function getStoredAccent(): VirtualAIAccent {
  if (typeof window === "undefined") return "none";
  const stored = localStorage.getItem(ACCENT_STORAGE_KEY);
  if (
    stored === "ocean" ||
    stored === "emerald" ||
    stored === "violet" ||
    stored === "neonai"
  ) {
    return stored;
  }
  return "none";
}

function applyAccentClass(accent: VirtualAIAccent) {
  const html = document.documentElement;
  html.classList.forEach((cls) => {
    if (cls.startsWith(ACCENT_CLASS_PREFIX)) {
      html.classList.remove(cls);
    }
  });
  if (accent !== "none") {
    html.classList.add(`${ACCENT_CLASS_PREFIX}${accent}`);
  }
}

// ─── Font Preference ─────────────────────────────────────────────────────

export type VirtualAIFont =
  | "inter"
  | "geist"
  | "system"
  | "plus-jakarta"
  | "hanken"
  | "space-grotesk";

export const VIRTUALAI_FONTS: VirtualAIFont[] = [
  "inter",
  "geist",
  "system",
  "plus-jakarta",
  "hanken",
  "space-grotesk",
];

const FONT_STORAGE_KEY = "virtualai-font-preference";
const FONT_CLASS_PREFIX = "font-pref-";

function getStoredFont(): VirtualAIFont {
  if (typeof window === "undefined") return "inter";
  const stored = localStorage.getItem(FONT_STORAGE_KEY);
  if (stored && (VIRTUALAI_FONTS as string[]).includes(stored)) {
    return stored as VirtualAIFont;
  }
  return "inter";
}

function applyFontClass(font: VirtualAIFont) {
  const html = document.documentElement;
  html.classList.forEach((cls) => {
    if (cls.startsWith(FONT_CLASS_PREFIX)) {
      html.classList.remove(cls);
    }
  });
  // "inter" is the default (no class needed — :root already uses Inter)
  if (font !== "inter") {
    html.classList.add(`${FONT_CLASS_PREFIX}${font}`);
  }
}

// ─── Context ─────────────────────────────────────────────────────────────

interface VirtualAIThemeContextValue {
  accent: VirtualAIAccent;
  setAccent: (accent: VirtualAIAccent) => void;
  font: VirtualAIFont;
  setFont: (font: VirtualAIFont) => void;
}

const VirtualAIThemeContext = createContext<VirtualAIThemeContextValue>({
  accent: "none",
  setAccent: () => {},
  font: "inter",
  setFont: () => {},
});

export function useVirtualAITheme() {
  return useContext(VirtualAIThemeContext);
}

// ─── Provider ────────────────────────────────────────────────────────────

export function VirtualAIThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [accent, setAccentState] = useState<VirtualAIAccent>("none");
  const [font, setFontState] = useState<VirtualAIFont>("inter");

  // Load from localStorage on mount
  useEffect(() => {
    const storedAccent = getStoredAccent();
    setAccentState(storedAccent);
    applyAccentClass(storedAccent);

    const storedFont = getStoredFont();
    setFontState(storedFont);
    applyFontClass(storedFont);
  }, []);

  const setAccent = useCallback((newAccent: VirtualAIAccent) => {
    setAccentState(newAccent);
    localStorage.setItem(ACCENT_STORAGE_KEY, newAccent);
    applyAccentClass(newAccent);
  }, []);

  const setFont = useCallback((newFont: VirtualAIFont) => {
    setFontState(newFont);
    localStorage.setItem(FONT_STORAGE_KEY, newFont);
    applyFontClass(newFont);
  }, []);

  return (
    <VirtualAIThemeContext.Provider value={{ accent, setAccent, font, setFont }}>
      {children}
    </VirtualAIThemeContext.Provider>
  );
}
