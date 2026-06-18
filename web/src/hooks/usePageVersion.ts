"use client";

import { useCallback, useEffect, useState } from "react";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useUiConfig, UiVersion } from "@/providers/UiConfigProvider";

/**
 * Generic, reusable old/new page version switch — web-only, no backend.
 *
 * Resolution order (highest wins):
 *   1. URL `?legacy=1|0`  (explicit override / deep-link)
 *   2. per-user localStorage (`ui-version:<key>`)
 *   3. server-injected default (`DEFAULT_UI_VERSION` via useUiConfig)
 *   4. hardcoded "new"
 *
 * Mirrors the localStorage pattern in VirtualAIThemeProvider (lazy read on the
 * client + effect to avoid SSR hydration mismatch).
 */
export type PageVersion = UiVersion;

const STORAGE_PREFIX = "ui-version:";

function readStored(key: string): PageVersion | null {
  if (typeof window === "undefined") return null;
  const v = window.localStorage.getItem(STORAGE_PREFIX + key);
  return v === "new" || v === "legacy" ? v : null;
}

export function usePageVersion(
  key: string,
  defaultVersion?: PageVersion
): {
  version: PageVersion;
  setVersion: (next: PageVersion) => void;
  isLegacy: boolean;
} {
  const { defaultUiVersion } = useUiConfig();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const legacyParam = searchParams?.get("legacy") ?? null;
  const paramVersion: PageVersion | null =
    legacyParam == null
      ? null
      : legacyParam === "1" || legacyParam === "true"
        ? "legacy"
        : "new";

  // Start null so the first client render matches SSR; hydrate from
  // localStorage in an effect.
  const [stored, setStored] = useState<PageVersion | null>(null);
  useEffect(() => {
    setStored(readStored(key));
  }, [key]);

  const version: PageVersion =
    paramVersion ?? stored ?? defaultVersion ?? defaultUiVersion ?? "new";

  const setVersion = useCallback(
    (next: PageVersion) => {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_PREFIX + key, next);
      }
      setStored(next);
      // If a `?legacy=` param is currently forcing the version, strip it so the
      // freshly-stored preference actually takes effect (param has priority).
      if (legacyParam != null) {
        const sp = new URLSearchParams(
          Array.from(searchParams?.entries() ?? [])
        );
        sp.delete("legacy");
        const qs = sp.toString();
        router.replace((qs ? `${pathname}?${qs}` : pathname) as Route);
      }
    },
    [key, legacyParam, pathname, router, searchParams]
  );

  return { version, setVersion, isLegacy: version === "legacy" };
}
