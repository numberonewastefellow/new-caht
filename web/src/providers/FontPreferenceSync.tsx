"use client";

import { useEffect, useRef } from "react";
import { useUser } from "@/providers/UserProvider";
import {
  useVirtualAITheme,
  VIRTUALAI_FONTS,
  VirtualAIFont,
} from "@/providers/VirtualAIThemeProvider";

/**
 * Reconciles the server-persisted font preference
 * (`user.preferences.font_preference`) with the DOM font class owned by
 * `VirtualAIThemeProvider`.
 *
 * `VirtualAIThemeProvider` sits ABOVE `UserProvider`, so it can't read the user
 * directly. This bridge is mounted INSIDE `UserProvider` (has the user) but below
 * the theme provider (whose `setFont` applies the class + localStorage), letting
 * the account's font apply on load / cross-device. Local picker changes already
 * persist via `updateUserFontPreference`, keeping the user object in sync; the
 * `appliedRef` guard prevents reverting a fresh local change to a stale value.
 * Renders nothing.
 */
export default function FontPreferenceSync() {
  const { user } = useUser();
  const { font, setFont } = useVirtualAITheme();
  const serverFont = user?.preferences?.font_preference ?? null;
  const appliedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!serverFont) return;
    if (!(VIRTUALAI_FONTS as string[]).includes(serverFont)) return;
    if (serverFont === font) return;
    if (appliedRef.current === serverFont) return;
    appliedRef.current = serverFont;
    setFont(serverFont as VirtualAIFont);
  }, [serverFont, font, setFont]);

  return null;
}
