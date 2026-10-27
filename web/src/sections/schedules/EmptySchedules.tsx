"use client";

import React from "react";
import type { IconProps } from "@opal/types";
import Button from "@/refresh-components/buttons/Button";
import Text from "@/refresh-components/texts/Text";
import { Card } from "@/refresh-components/cards";
import { SvgBarChart, SvgClock, SvgFileText, SvgBell } from "@opal/icons";
import type { ScheduleTemplate } from "@/sections/schedules/ScheduleModal";
import {
  ACCENT,
  ACCENT_GLOW,
  AccentIconTile,
} from "@/sections/schedules/StatusPill";

interface TemplateCard {
  key: string;
  icon: React.FunctionComponent<IconProps>;
  title: string;
  description: string;
  frequencyLabel: string;
  template: ScheduleTemplate;
}

export const SCHEDULE_TEMPLATES: TemplateCard[] = [
  {
    key: "daily",
    icon: SvgFileText,
    title: "Daily brief at 09:00",
    description:
      "Collect news and internal docs since the last run and write a one-page brief.",
    frequencyLabel: "Every day at 09:00",
    template: {
      workflowNameHint: "brief",
      frequency: { preset: "daily", time: "09:00" },
      inputMode: "window",
      message:
        "Brief for {{date}}. Only include items newer than {{window_start}}.",
    },
  },
  {
    key: "hourly",
    icon: SvgBell,
    title: "Hourly inbox triage",
    description:
      "Sort new mail every hour, draft replies and flag anything urgent.",
    frequencyLabel: "Every hour at :00",
    template: {
      workflowNameHint: "triage",
      frequency: { preset: "hourly", minute: 0 },
      inputMode: "window",
      message:
        "Triage emails received since {{window_start}}. Draft replies and flag anything urgent.",
    },
  },
  {
    key: "weekly",
    icon: SvgBarChart,
    title: "Weekly report every Monday",
    description:
      "Compare last week's numbers and write a short report for the team.",
    frequencyLabel: "Mondays at 09:00",
    template: {
      workflowNameHint: "research",
      frequency: { preset: "weekly", weekdays: [1], time: "09:00" },
      inputMode: "fixed",
      message:
        "Weekly report for the week ending {{date}}. Compare with the previous week.",
    },
  },
];

function EmptyIllustration() {
  return (
    <svg width="168" height="120" viewBox="0 0 168 120" fill="none" aria-hidden>
      <ellipse
        cx="84"
        cy="60"
        rx="78"
        ry="44"
        stroke="var(--border-02)"
        strokeDasharray="3 6"
      />
      <circle cx="84" cy="60" r="38" fill={ACCENT_GLOW} />
      <circle
        cx="84"
        cy="60"
        r="30"
        fill="var(--virtualai-accent-subtle, var(--background-tint-02))"
        stroke={ACCENT}
        strokeWidth="2.5"
      />
      <path
        d="M84 42v18l11 7"
        stroke={ACCENT}
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="10" cy="56" r="5" fill={ACCENT} />
      <circle cx="150" cy="35" r="4" fill={ACCENT} opacity=".6" />
      <circle cx="128" cy="100" r="3.5" fill={ACCENT} opacity=".4" />
      <path
        d="M138 70l-5 7h4l-1 6 5-7h-4z"
        stroke={ACCENT}
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export interface EmptySchedulesProps {
  onUseTemplate: (template: ScheduleTemplate) => void;
}

export default function EmptySchedules({ onUseTemplate }: EmptySchedulesProps) {
  return (
    <Card padding={2}>
      <div className="w-full flex flex-col items-center text-center pt-4">
        <EmptyIllustration />
        <div className="pt-3.5 pb-1">
          <Text as="p" headingH3 text05>
            No schedules yet
          </Text>
        </div>
        <Text as="p" mainUiBody text03 className="max-w-[28rem]">
          Pick a workflow and how often it should run. Pulse runs it in the
          background and every run lands as its own chat you can open, reply to
          or share.
        </Text>
        <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-3 pt-6 text-left">
          {SCHEDULE_TEMPLATES.map((t) => (
            <div
              key={t.key}
              className="flex flex-col gap-2 p-4 rounded-12 border border-border-01 bg-background-tint-00 transition-all hover:bg-background-tint-01 hover:shadow-[0_4px_24px_var(--virtualai-accent-glow)]"
            >
              <AccentIconTile
                icon={t.icon}
                size={36}
                iconSize={18}
                glow={false}
              />
              <Text as="p" mainUiAction text05>
                {t.title}
              </Text>
              <Text as="p" secondaryBody text03 className="flex-1">
                {t.description}
              </Text>
              <div className="flex items-center gap-1">
                <SvgClock className="w-3 h-3 stroke-text-03" />
                <Text as="span" secondaryBody text03>
                  {t.frequencyLabel}
                </Text>
              </div>
              <div className="pt-1">
                <Button
                  secondary
                  size="md"
                  onClick={() => onUseTemplate(t.template)}
                >
                  Use template
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
