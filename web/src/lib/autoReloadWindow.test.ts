import {
  AUTO_RELOAD_RESET_MS,
  AUTO_RELOAD_WINDOW_MS,
  shouldAutoReload,
} from "@/lib/autoReloadWindow";

function fakeStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => {
      values.set(key, value);
    },
  };
}

describe("shouldAutoReload", () => {
  const start = 1_000_000;

  it("reloads on the first failure and within the window", () => {
    const storage = fakeStorage();
    expect(shouldAutoReload(storage, start)).toBe(true);
    expect(shouldAutoReload(storage, start + AUTO_RELOAD_WINDOW_MS - 1)).toBe(
      true
    );
  });

  it("stops once the window has passed", () => {
    const storage = fakeStorage();
    shouldAutoReload(storage, start);
    expect(shouldAutoReload(storage, start + AUTO_RELOAD_WINDOW_MS)).toBe(false);
    expect(shouldAutoReload(storage, start + AUTO_RELOAD_RESET_MS)).toBe(false);
  });

  it("treats a failure after the reset time as a new outage", () => {
    const storage = fakeStorage();
    shouldAutoReload(storage, start);
    const later = start + AUTO_RELOAD_RESET_MS + 1;
    expect(shouldAutoReload(storage, later)).toBe(true);
    expect(shouldAutoReload(storage, later + AUTO_RELOAD_WINDOW_MS)).toBe(false);
  });
});
