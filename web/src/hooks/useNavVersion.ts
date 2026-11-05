"use client";

import { useSettingsContext } from "@/providers/SettingsProvider";
import { useUiConfig } from "@/providers/UiConfigProvider";
import {
  NAV_V2_FLAG,
  resolveNavVersion,
  type NavVersion,
} from "@/lib/navVersion";

/**
 * Which navigation view to render. See `lib/navVersion.ts` for the contract.
 *
 * Both inputs are already available during server rendering — settings are
 * injected into `SettingsProvider` from the server layout, and the env default
 * comes through `UiConfigProvider` — so this returns the final answer in the
 * first paint: no flash, no effect, no storage read, no network.
 *
 * Deliberately does NOT read the query string. Doing so would pull in
 * `useSearchParams()`, which forces every caller under a `<Suspense>` boundary
 * and opts the subtree into a client-render bailout — far too costly for
 * persistent chrome, in exchange for a support-only override.
 */
export default function useNavVersion(): NavVersion {
  const settings = useSettingsContext();
  const { defaultNavVersion } = useUiConfig();

  const flag = settings?.enterpriseSettings?.feature_flags?.[NAV_V2_FLAG];

  return resolveNavVersion({
    flagEnabled: typeof flag === "boolean" ? flag : undefined,
    envDefault: defaultNavVersion,
  });
}
