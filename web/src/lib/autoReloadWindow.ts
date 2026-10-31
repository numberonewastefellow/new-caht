export const AUTO_RELOAD_INTERVAL_MS = 5_000;
export const AUTO_RELOAD_WINDOW_MS = 2 * 60_000;
// A first-failure time older than this belongs to an earlier outage.
export const AUTO_RELOAD_RESET_MS = 10 * 60_000;

const FIRST_FAILURE_KEY = "virtualai-backend-first-failure";

/**
 * Whether the outage page should keep reloading itself. Bounded so that a backend
 * which is up but keeps failing can't put the tab in an endless reload loop. The
 * time is stored because each reload loses component state.
 */
export function shouldAutoReload(
  storage: Pick<Storage, "getItem" | "setItem">,
  now: number
): boolean {
  const firstFailure = Number(storage.getItem(FIRST_FAILURE_KEY));
  if (!firstFailure || now - firstFailure > AUTO_RELOAD_RESET_MS) {
    storage.setItem(FIRST_FAILURE_KEY, String(now));
    return true;
  }
  return now - firstFailure < AUTO_RELOAD_WINDOW_MS;
}
