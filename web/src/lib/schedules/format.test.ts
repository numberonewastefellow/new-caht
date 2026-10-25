import {
  formatDurationMs,
  formatRelative,
  plainTextPreview,
} from "@/lib/schedules/format";
import { needsAttention, scheduleDot } from "@/lib/schedules/status";

const NOW = new Date("2026-10-26T11:00:00Z");
const at = (minutes: number) =>
  new Date(NOW.getTime() + minutes * 60000).toISOString();

describe("formatRelative", () => {
  it("formats future and past times", () => {
    expect(formatRelative(at(5), NOW)).toBe("in 5 min");
    expect(formatRelative(at(180), NOW)).toBe("in 3 h");
    expect(formatRelative(at(60 * 72), NOW)).toBe("in 3 d");
    expect(formatRelative(at(-50), NOW)).toBe("50 min ago");
    expect(formatRelative(at(-300), NOW)).toBe("5 h ago");
    expect(formatRelative(at(0), NOW)).toBe("just now");
    expect(formatRelative(null, NOW)).toBe("—");
  });
});

describe("formatDurationMs", () => {
  it("formats durations", () => {
    expect(formatDurationMs(248000)).toBe("4m 08s");
    expect(formatDurationMs(41000)).toBe("41s");
    expect(formatDurationMs(3_725_000)).toBe("1h 02m");
    expect(formatDurationMs(null)).toBe("—");
  });
});

describe("status helpers", () => {
  it("flags schedules that need attention", () => {
    expect(
      needsAttention({
        disabled_reason: "auto_paused_failures",
        last_run_status: null,
      })
    ).toBe(true);
    expect(
      needsAttention({ disabled_reason: null, last_run_status: "failed" })
    ).toBe(true);
    expect(
      needsAttention({ disabled_reason: null, last_run_status: "needs_input" })
    ).toBe(true);
    expect(
      needsAttention({
        disabled_reason: "completed_once",
        last_run_status: "succeeded",
      })
    ).toBe(false);
    expect(
      needsAttention({ disabled_reason: null, last_run_status: "succeeded" })
    ).toBe(false);
  });

  it("picks sidebar dots", () => {
    expect(
      scheduleDot({
        enabled: true,
        disabled_reason: null,
        last_run_status: "succeeded",
      })
    ).toBe("ok");
    expect(
      scheduleDot({
        enabled: false,
        disabled_reason: null,
        last_run_status: "succeeded",
      })
    ).toBe("muted");
    expect(
      scheduleDot({
        enabled: false,
        disabled_reason: "auto_paused_failures",
        last_run_status: "failed",
      })
    ).toBe("warning");
    expect(
      scheduleDot({
        enabled: false,
        disabled_reason: "access_revoked",
        last_run_status: null,
      })
    ).toBe("error");
    expect(
      scheduleDot({
        enabled: true,
        disabled_reason: null,
        last_run_status: "running",
      })
    ).toBe("running");
  });
});

describe("plainTextPreview", () => {
  it("strips markdown to one line of plain text", () => {
    expect(
      plainTextPreview(
        "**Executive Summary**\n\n1. **Point** one\n- see [docs](http://x)\n## Next `code`"
      )
    ).toBe("Executive Summary Point one see docs Next code");
    expect(plainTextPreview(null)).toBe("");
    expect(plainTextPreview("snake_case_name stays")).toBe(
      "snake_case_name stays"
    );
  });
});
