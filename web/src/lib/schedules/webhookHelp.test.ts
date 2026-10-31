import { readFileSync } from "fs";
import { join } from "path";
import { WEBHOOK_SERVICE_HELP } from "./webhookHelp";

const pulseConfigs = readFileSync(
  join(process.cwd(), "..", "backend", "om", "configs", "pulse_configs.py"),
  "utf-8"
);

/** Reads `_int_env("NAME", default)`, allowing the arguments to span lines. */
function configDefault(name: string): string | undefined {
  return pulseConfigs.match(new RegExp(`_int_env\\(\\s*"${name}",\\s*([^)\\n]+?)\\s*\\)`))?.[1];
}

describe("webhook help", () => {
  const settings = WEBHOOK_SERVICE_HELP.sections
    .flatMap((section) => section.rows ?? [])
    .filter((row) => row.name.startsWith("PULSE_") && row.value)
    // Set in the compose file, not pulse_configs.py
    .filter((row) => row.name !== "PULSE_WEBHOOK_WORKER_CONCURRENCY");

  it("covers the settings", () => {
    expect(settings.length).toBeGreaterThanOrEqual(10);
  });

  it.each(settings.map((row) => [row.name, row.value]))(
    "%s has the default the backend uses",
    (name, value) => {
      const actual = configDefault(name as string);
      expect(actual).toBeDefined();
      const normalized = actual === "1024 * 1024" ? "1048576" : actual;
      expect(normalized).toBe(value);
    }
  );
});
