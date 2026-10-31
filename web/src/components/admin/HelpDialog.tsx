"use client";

import { useRef, useState } from "react";
import Modal from "@/refresh-components/Modal";
import Text from "@/refresh-components/texts/Text";
import IconButton from "@/refresh-components/buttons/IconButton";
import CopyIconButton from "@/refresh-components/buttons/CopyIconButton";
import { SvgInfoSmall } from "@opal/icons";

export interface HelpRow {
  name: string;
  /** A default or expected value, shown next to the name. */
  value?: string;
  detail: string;
}

export interface HelpCode {
  label: string;
  command: string;
}

export interface HelpSection {
  title: string;
  text?: string;
  steps?: string[];
  rows?: HelpRow[];
  code?: HelpCode[];
  /** Shown after everything else in the section. */
  note?: string;
}

export interface HelpContent {
  title: string;
  summary: string;
  sections: HelpSection[];
}

function HelpRows({ rows }: { rows: HelpRow[] }) {
  return (
    <dl className="flex flex-col rounded-08 border border-border-01 divide-y divide-border-01">
      {rows.map((row) => (
        <div
          key={row.name}
          className="grid grid-cols-1 sm:grid-cols-[minmax(0,17rem)_minmax(0,1fr)] gap-x-4 gap-y-0.5 px-3 py-2"
        >
          <dt className="flex flex-wrap items-baseline gap-x-2 min-w-0">
            <span className="font-mono text-[12px] text-text-05 break-all">{row.name}</span>
            {row.value && (
              <span className="font-mono text-[12px] text-text-03">{row.value}</span>
            )}
          </dt>
          <dd>
            <Text as="span" secondaryBody text04>
              {row.detail}
            </Text>
          </dd>
        </div>
      ))}
    </dl>
  );
}

function HelpCommand({ code }: { code: HelpCode }) {
  return (
    <div className="flex flex-col gap-1">
      <Text as="span" secondaryBody text03>
        {code.label}
      </Text>
      <div className="flex items-start gap-1 rounded-08 border border-border-01 bg-background-tint-01 pl-3 pr-1 py-1">
        <pre className="flex-1 min-w-0 overflow-x-auto py-1 text-[12px] text-text-04 font-mono whitespace-pre">
          {code.command}
        </pre>
        <CopyIconButton tooltip="Copy" getCopyText={() => code.command} />
      </div>
    </div>
  );
}

function HelpSectionView({ section }: { section: HelpSection }) {
  return (
    <section className="flex flex-col gap-2">
      <h3>
        <Text as="span" mainUiAction text05>
          {section.title}
        </Text>
      </h3>
      {section.text && (
        <Text as="p" mainUiBody text04>
          {section.text}
        </Text>
      )}
      {section.steps && (
        <ol className="flex flex-col gap-1 list-decimal pl-5 text-text-04">
          {section.steps.map((step) => (
            <li key={step}>
              <Text as="span" mainUiBody text04>
                {step}
              </Text>
            </li>
          ))}
        </ol>
      )}
      {section.rows && <HelpRows rows={section.rows} />}
      {section.code?.map((code) => <HelpCommand key={code.label} code={code} />)}
      {section.note && (
        <Text as="p" secondaryBody text03>
          {section.note}
        </Text>
      )}
    </section>
  );
}

/**
 * An (i) button that opens longer help for one item on a page.
 *
 * Keep it outside any link: a button inside `<a>` is invalid, and clicking it would navigate.
 */
export default function HelpDialog({ content }: { content: HelpContent }) {
  const [open, setOpen] = useState(false);
  const opener = useRef<HTMLElement | null>(null);

  return (
    <>
      <IconButton
        secondary
        small
        icon={SvgInfoSmall}
        iconClassName="!h-5 !w-5"
        tooltip="How this works"
        aria-label={`How this works: ${content.title}`}
        onClick={(e) => {
          opener.current = e.currentTarget;
          setOpen(true);
        }}
      />
      <Modal open={open} onOpenChange={setOpen}>
        {/* Opened from our own button, so the dialog can't return focus to it by itself. */}
        <Modal.Content
          width="md"
          height="lg"
          onCloseAutoFocus={() => opener.current?.focus()}
        >
          <Modal.Header
            icon={SvgInfoSmall}
            title={content.title}
            description={content.summary}
            onClose={() => setOpen(false)}
          />
          <Modal.Body twoTone={false}>
            <div className="flex flex-col gap-5 w-full">
              {content.sections.map((section) => (
                <HelpSectionView key={section.title} section={section} />
              ))}
            </div>
          </Modal.Body>
        </Modal.Content>
      </Modal>
    </>
  );
}
