import {
  cronToPreset,
  defaultFrequencyState,
  FrequencyState,
  normalizeCron,
  presetSentence,
  presetToSpec,
  specToPreset,
  utcIsoToZonedWallTime,
  zonedWallTimeToUtcIso,
} from "@/lib/schedules/cron";

const NOW = new Date(2026, 9, 26, 11, 5); // Mon 26 Oct 2026, 11:05 local
const base = defaultFrequencyState(NOW);
const state = (patch: Partial<FrequencyState>): FrequencyState => ({
  ...base,
  ...patch,
});

function specOf(s: FrequencyState, tz = "UTC") {
  const r = presetToSpec(s, tz);
  if (r.error !== null) throw new Error(r.error);
  return r.spec;
}

describe("presetToSpec", () => {
  it("maps interval presets to interval_seconds", () => {
    expect(specOf(state({ preset: "everyNMinutes", everyN: 15 }))).toEqual({
      schedule_type: "interval",
      interval_seconds: 900,
      timezone: "UTC",
    });
    expect(
      specOf(state({ preset: "everyNHours", everyN: 2 })).interval_seconds
    ).toBe(7200);
  });

  it("rejects intervals longer than 366 days (server returns 422)", () => {
    expect(
      presetToSpec(state({ preset: "everyNHours", everyN: 366 * 24 }), "UTC")
        .error
    ).toBeNull();
    expect(
      presetToSpec(
        state({ preset: "everyNHours", everyN: 366 * 24 + 1 }),
        "UTC"
      ).error
    ).toMatch(/366 days/);
  });

  it("maps cron presets to the documented expressions", () => {
    expect(
      specOf(state({ preset: "hourly", minute: 15 })).cron_expression
    ).toBe("15 * * * *");
    expect(
      specOf(state({ preset: "daily", time: "09:30" })).cron_expression
    ).toBe("30 9 * * *");
    expect(
      specOf(state({ preset: "weekdays", time: "08:00" })).cron_expression
    ).toBe("0 8 * * 1-5");
    expect(
      specOf(state({ preset: "weekly", time: "06:00", weekdays: [4, 1, 1, 7] }))
        .cron_expression
    ).toBe("0 6 * * 0,1,4");
    expect(
      specOf(state({ preset: "monthly", time: "10:00", monthDay: 1 }))
        .cron_expression
    ).toBe("0 10 1 * *");
    expect(
      specOf(state({ preset: "monthly", time: "23:59", monthDay: "L" }))
        .cron_expression
    ).toBe("59 23 L * *");
  });

  it("normalises custom cron whitespace", () => {
    expect(
      specOf(state({ preset: "custom", cron: "  */15   *  * * * " }))
        .cron_expression
    ).toBe("*/15 * * * *");
  });

  it("converts a one-time wall time in the schedule timezone to UTC", () => {
    const spec = specOf(
      state({ preset: "once", onceDate: "2026-10-27", onceTime: "10:00" }),
      "Asia/Kolkata"
    );
    expect(spec.schedule_type).toBe("once");
    expect(spec.run_at).toBe("2026-10-27T04:30:00.000Z");
  });

  it("returns errors for incomplete input", () => {
    expect(
      presetToSpec(state({ preset: "weekly", weekdays: [] }), "UTC").error
    ).toMatch(/day of the week/);
    expect(
      presetToSpec(state({ preset: "daily", time: "" }), "UTC").error
    ).toMatch(/time/);
    expect(
      presetToSpec(state({ preset: "hourly", minute: 75 }), "UTC").error
    ).toMatch(/Minute/);
    expect(
      presetToSpec(state({ preset: "everyNMinutes", everyN: 0 }), "UTC").error
    ).toBeTruthy();
    expect(
      presetToSpec(state({ preset: "custom", cron: "   " }), "UTC").error
    ).toBeTruthy();
    expect(
      presetToSpec(
        state({ preset: "once", onceDate: "", onceTime: "10:00" }),
        "UTC"
      ).error
    ).toBeTruthy();
  });
});

describe("specToPreset round-trip", () => {
  const cases: Partial<FrequencyState>[] = [
    { preset: "everyNMinutes", everyN: 30 },
    { preset: "everyNHours", everyN: 6 },
    { preset: "hourly", minute: 0 },
    { preset: "hourly", minute: 45 },
    { preset: "daily", time: "09:00" },
    { preset: "weekdays", time: "18:30" },
    { preset: "weekly", time: "07:15", weekdays: [1] },
    { preset: "weekly", time: "07:15", weekdays: [0, 3, 6] },
    { preset: "monthly", time: "10:00", monthDay: 28 },
    { preset: "monthly", time: "10:00", monthDay: "L" },
  ];

  it.each(cases)("round-trips %o", (patch) => {
    const original = state(patch);
    const spec = specOf(original, "Europe/London");
    const back = specToPreset(spec, NOW);
    expect(back.preset).toBe(original.preset);
    for (const key of Object.keys(patch) as (keyof FrequencyState)[]) {
      expect(back[key]).toEqual(original[key]);
    }
    // And the regenerated spec is identical.
    expect(specOf(back, "Europe/London")).toEqual(spec);
  });

  it("round-trips a one-time schedule across timezones", () => {
    for (const tz of [
      "Asia/Kolkata",
      "America/New_York",
      "UTC",
      "Europe/London",
    ]) {
      const original = state({
        preset: "once",
        onceDate: "2026-11-01",
        onceTime: "01:30",
      });
      const spec = specOf(original, tz);
      const back = specToPreset(spec, NOW);
      expect(back.preset).toBe("once");
      expect(back.onceDate).toBe("2026-11-01");
      expect(back.onceTime).toBe("01:30");
    }
  });

  it("round-trips custom cron unchanged", () => {
    const spec = specOf(state({ preset: "custom", cron: "*/10 9-17 * * 1-5" }));
    const back = specToPreset(spec, NOW);
    expect(back.preset).toBe("custom");
    expect(back.cron).toBe("*/10 9-17 * * 1-5");
  });
});

describe("specToPreset fallbacks", () => {
  const cron = (expr: string) =>
    specToPreset(
      { schedule_type: "cron", cron_expression: expr, timezone: "UTC" },
      NOW
    );

  it("falls back to custom for shapes the UI does not generate", () => {
    for (const expr of [
      "*/15 * * * *",
      "0 9 * * MON",
      "0 9 1-7 * 1",
      "0 9 * 1 *",
      "0 */2 * * *",
      "0 9 31 * *",
      "60 9 * * *",
      "0 24 * * *",
      "0 9 * * 1-6",
      "0 9 *",
      "@daily",
    ]) {
      const s = cron(expr);
      expect(s.preset).toBe("custom");
      expect(s.cron).toBe(normalizeCron(expr));
    }
  });

  it("treats weekday 7 as Sunday", () => {
    const s = cron("0 9 * * 7");
    expect(s.preset).toBe("weekly");
    expect(s.weekdays).toEqual([0]);
  });

  it("tolerates extra whitespace in stored cron", () => {
    const s = cron("  30   8 * *   1-5 ");
    expect(s.preset).toBe("weekdays");
    expect(s.time).toBe("08:30");
  });

  it("maps non-hour-multiple intervals to minutes", () => {
    const s = specToPreset(
      { schedule_type: "interval", interval_seconds: 5400, timezone: "UTC" },
      NOW
    );
    expect(s.preset).toBe("everyNMinutes");
    expect(s.everyN).toBe(90);
  });

  it("keeps defaults when the spec is empty", () => {
    const s = specToPreset(
      { schedule_type: "cron", cron_expression: null, timezone: "UTC" },
      NOW
    );
    expect(s.preset).toBe("custom");
    expect(s.cron).toBe("");
  });

  it("cronToPreset keeps base fields it does not touch", () => {
    const s = cronToPreset("0 9 * * *", state({ everyN: 42 }));
    expect(s.preset).toBe("daily");
    expect(s.everyN).toBe(42);
  });
});

describe("timezone helpers", () => {
  it("handles DST transitions (America/New_York)", () => {
    // Before the fall-back change (EDT, UTC-4) and after it (EST, UTC-5)
    expect(
      zonedWallTimeToUtcIso("2026-10-31", "09:00", "America/New_York")
    ).toBe("2026-10-31T13:00:00.000Z");
    expect(
      zonedWallTimeToUtcIso("2026-11-02", "09:00", "America/New_York")
    ).toBe("2026-11-02T14:00:00.000Z");
  });

  it("returns null for bad input", () => {
    expect(zonedWallTimeToUtcIso("2026-13-01", "09:00", "UTC")).toBeNull();
    expect(zonedWallTimeToUtcIso("2026-10-01", "9am", "UTC")).toBeNull();
    expect(
      zonedWallTimeToUtcIso("2026-10-01", "09:00", "Not/AZone")
    ).toBeNull();
    expect(utcIsoToZonedWallTime("nope", "UTC")).toBeNull();
  });

  it("converts UTC back to wall time", () => {
    expect(
      utcIsoToZonedWallTime("2026-10-27T04:30:00Z", "Asia/Kolkata")
    ).toEqual({
      date: "2026-10-27",
      time: "10:00",
    });
  });
});

describe("presetSentence", () => {
  it("describes presets", () => {
    expect(presetSentence(state({ preset: "everyNMinutes", everyN: 1 }))).toBe(
      "Every minute"
    );
    expect(presetSentence(state({ preset: "everyNHours", everyN: 3 }))).toBe(
      "Every 3 hours"
    );
    expect(presetSentence(state({ preset: "hourly", minute: 5 }))).toBe(
      "Every hour at :05"
    );
    expect(
      presetSentence(state({ preset: "weekly", weekdays: [1], time: "09:00" }))
    ).toBe("Mondays at 09:00");
    expect(
      presetSentence(
        state({ preset: "weekly", weekdays: [0, 1], time: "09:00" })
      )
    ).toBe("Mon, Sun at 09:00");
    expect(
      presetSentence(state({ preset: "monthly", monthDay: "L", time: "09:00" }))
    ).toBe("Monthly on the last day at 09:00");
    expect(
      presetSentence(state({ preset: "monthly", monthDay: 2, time: "09:00" }))
    ).toBe("Monthly on the 2nd at 09:00");
  });
});
