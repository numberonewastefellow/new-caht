"use client";

import { useEffect, useRef } from "react";
import { useUser } from "@/providers/UserProvider";
import {
  useVirtualAITheme,
  VirtualAIAccent,
} from "@/providers/VirtualAIThemeProvider";

// Same key VirtualAIThemeProvider uses for its first-paint fast path.
const ACCENT_STORAGE_KEY = "virtualai-accent-theme";
const ACCENTS: VirtualAIAccent[] = ["ocean", "emerald", "violet", "neonai"];

/**
 * Reconciles the server-persisted accent theme
 * (`user.preferences.accent_theme`) with the DOM class owned by
 * `VirtualAIThemeProvider`; same bridge pattern as `FontPreferenceSync`.
 *
 * - Server has an accent: apply it (account choice wins across devices).
 * - Server has none but this browser has one (picked before accents were
 *   saved to the account): upload it once so it survives from now on.
 * Renders nothing.
 */
export default function AccentPreferenceSync() {
  const { user, updateUserAccentTheme } = useUser();
  const { setAccent } = useVirtualAITheme();
  const serverAccent = user?.preferences?.accent_theme ?? null;
  const loaded = !!user?.id;
  const reconciledRef = useRef(false);

  useEffect(() => {
    if (!loaded || reconciledRef.current) return;
    reconciledRef.current = true;

    if (serverAccent && (ACCENTS as string[]).includes(serverAccent)) {
      setAccent(serverAccent as VirtualAIAccent);
      return;
    }
    // Read localStorage directly: this effect runs before the theme provider's
    // own mount effect, so its `accent` state is still the initial "none".
    const local = localStorage.getItem(ACCENT_STORAGE_KEY);
    if (local && (ACCENTS as string[]).includes(local)) {
      void updateUserAccentTheme(local);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, serverAccent]);

  return null;
}
