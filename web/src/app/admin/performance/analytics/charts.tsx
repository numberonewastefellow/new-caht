"use client";

import React, { memo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * Theme-aware chart palette.
 *
 * Colors are CSS variables (not hardcoded hex), so every series automatically
 * adapts to the user's accent theme (Default / Ocean / Emerald / Violet) and to
 * light/dark mode — see project CLAUDE.md accent-theme rules. Recharts accepts
 * any CSS color string, so `var(--...)` works directly for stroke/fill.
 */
export const CHART_COLORS = [
  "var(--virtualai-accent)",
  "var(--theme-primary-04)",
  "var(--theme-primary-06)",
];

// Shared axis / grid / tooltip styling (also CSS-var driven for theming).
const AXIS_COLOR = "var(--theme-primary-05)";
const GRID_COLOR = "var(--theme-primary-04)";

const TOOLTIP_CONTENT_STYLE: React.CSSProperties = {
  backgroundColor: "var(--background-neutral-00)",
  border: "1px solid var(--theme-primary-04)",
  borderRadius: 8,
  fontSize: 12,
  color: "var(--theme-primary-05)",
};

export interface SeriesDef {
  key: string;
  label: string;
  color?: string;
}

interface ChartProps {
  data: Record<string, unknown>[];
  index: string;
  series: SeriesDef[];
  height?: number;
  allowDecimals?: boolean;
  xAxisFormatter?: (value: string) => string;
  yAxisFormatter?: (value: number) => string;
}

/**
 * Responsive, theme-aware multi-series line chart.
 *
 * Follows recharts perf guidance: ResponsiveContainer inside an explicitly-sized
 * parent with a resize `debounce`, animation disabled, and a stable `dataKey`
 * per series (callers pass memoized `data`).
 */
export const TimeSeriesChart = memo(function TimeSeriesChart({
  data,
  index,
  series,
  height = 300,
  allowDecimals = false,
  xAxisFormatter,
  yAxisFormatter,
}: ChartProps) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%" debounce={100}>
        <LineChart data={data} margin={{ top: 10, right: 24, left: 0, bottom: 0 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={GRID_COLOR}
            strokeOpacity={0.2}
          />
          <XAxis
            dataKey={index}
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            stroke={AXIS_COLOR}
            fontSize={12}
            tickFormatter={xAxisFormatter}
          />
          <YAxis
            width={48}
            tickLine={false}
            axisLine={false}
            stroke={AXIS_COLOR}
            fontSize={12}
            allowDecimals={allowDecimals}
            tickFormatter={yAxisFormatter}
          />
          <Tooltip contentStyle={TOOLTIP_CONTENT_STYLE} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s, i) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color ?? CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
});

/**
 * Responsive, theme-aware grouped bar chart.
 */
export const CategoryBarChart = memo(function CategoryBarChart({
  data,
  index,
  series,
  height = 300,
  allowDecimals = false,
  xAxisFormatter,
  yAxisFormatter,
}: ChartProps) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%" debounce={100}>
        <BarChart data={data} margin={{ top: 10, right: 24, left: 0, bottom: 0 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={GRID_COLOR}
            strokeOpacity={0.2}
            vertical={false}
          />
          <XAxis
            dataKey={index}
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            stroke={AXIS_COLOR}
            fontSize={12}
            tickFormatter={xAxisFormatter}
          />
          <YAxis
            width={48}
            tickLine={false}
            axisLine={false}
            stroke={AXIS_COLOR}
            fontSize={12}
            allowDecimals={allowDecimals}
            tickFormatter={yAxisFormatter}
          />
          <Tooltip
            cursor={{ fill: "var(--virtualai-accent-subtle)" }}
            contentStyle={TOOLTIP_CONTENT_STYLE}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s, i) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.label}
              fill={s.color ?? CHART_COLORS[i % CHART_COLORS.length]}
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
});
