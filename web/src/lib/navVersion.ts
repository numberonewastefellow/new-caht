/**
 * Navigation version — which *view* of the navigation a client sees.
 *
 * Both versions show the SAME menu, built by the same catalogs
 * (`components/admin/adminNavItems.ts`, `sections/sidebar/appNavItems.ts`).
 * Only the chrome differs:
 *
 *   v1 — classic: admin top bar with dropdown tabs, admin entry inside the
 *        user-avatar popup, flat sidebar action list.
 *   v2 — modern:  admin left rail with expandable sections, admin entry pinned
 *        in the sidebar, grouped sidebar action list.
 *
 * The version must never be an input to the nav catalogs. Keeping it purely a
 * rendering concern is what makes a new menu item a one-line change that shows
 * up in both views.
 *
 * This is deliberately separate from `UiVersion` / `DEFAULT_UI_VERSION`
 * (`hooks/usePageVersion.ts`), which versions page *bodies* such as the
 * workflows list. Sharing one switch would mean flipping the workflows page
 * also flipped the entire navigation.
 */
export type NavVersion = "v1" | "v2";

/** Key inside `app_settings.feature_flags` (JSONB, per tenant). */
export const NAV_V2_FLAG = "nav_v2";

export const DEFAULT_NAV_VERSION: NavVersion = "v1";

export function isNavVersion(value: unknown): value is NavVersion {
  return value === "v1" || value === "v2";
}

/** Parse the `DEFAULT_NAV_VERSION` env var. Anything unrecognised → v1. */
export function parseNavVersionEnv(raw: string | undefined): NavVersion {
  return raw?.toLowerCase() === "v2" ? "v2" : DEFAULT_NAV_VERSION;
}

export interface ResolveNavVersionArgs {
  /** `feature_flags.nav_v2` for this tenant. `undefined` when unset. */
  flagEnabled?: boolean;
  /** Per-deployment default from the server env. */
  envDefault?: NavVersion;
}

/**
 * Resolution order (highest wins):
 *   1. the tenant's `feature_flags.nav_v2`
 *   2. the deployment's `DEFAULT_NAV_VERSION`
 *   3. "v1"
 *
 * Both inputs are known during server rendering, so the correct chrome is in
 * the first paint — no flash, unlike a localStorage-backed preference.
 */
export function resolveNavVersion({
  flagEnabled,
  envDefault,
}: ResolveNavVersionArgs): NavVersion {
  if (typeof flagEnabled === "boolean") return flagEnabled ? "v2" : "v1";
  return envDefault ?? DEFAULT_NAV_VERSION;
}
