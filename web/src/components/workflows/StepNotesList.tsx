"use client";

import { useCallback, useMemo } from "react";
import Link from "next/link";
import type { Route } from "next";
import useSWR from "swr";

import MinimalMarkdown from "@/components/chat/MinimalMarkdown";
import Text from "@/refresh-components/texts/Text";
import { errorHandlingFetcher } from "@/lib/fetcher";
import { workflowNotesUrl, type WorkflowNote } from "@/lib/workflows/notes";
import "@/components/workflow-builder/notes/StickyNote.css";

/** Looks up a step's linked notes. Fetched on their own: a workflow cached after a save
 * doesn't carry its notes. */
export function useStepNotes(workflowId: number | undefined) {
  const { data } = useSWR<WorkflowNote[]>(
    workflowId ? workflowNotesUrl(workflowId) : null,
    errorHandlingFetcher,
    { revalidateOnFocus: false }
  );
  const byStep = useMemo(() => {
    const map = new Map<string, WorkflowNote[]>();
    for (const note of data ?? []) {
      if (!note.step_node_key) continue;
      map.set(note.step_node_key, [...(map.get(note.step_node_key) ?? []), note]);
    }
    return map;
  }, [data]);
  return useCallback(
    (stepNodeKey: string) => {
      const items = byStep.get(stepNodeKey);
      return workflowId && items ? { workflowId, items } : undefined;
    },
    [byStep, workflowId]
  );
}

interface StepNotesListProps {
  notes: WorkflowNote[];
  workflowId: number;
}

/** A step's linked canvas notes, read only. They're written in the visual builder. */
export default function StepNotesList({ notes, workflowId }: StepNotesListProps) {
  if (notes.length === 0) return null;
  return (
    <div className="flex flex-col gap-2" data-testid="step-notes">
      <div className="flex items-center justify-between gap-2">
        <Text mainContentEmphasis text04>
          {notes.length === 1 ? "Note" : `Notes (${notes.length})`}
        </Text>
        <Link
          href={`/admin/workflows/visual/${workflowId}` as Route}
          className="text-[12px] text-text-03 hover:underline"
        >
          Edit in visual builder
        </Link>
      </div>
      {notes.map((note) => (
        <div key={note.id} className="wfb-note wfb-note-readonly" data-color={note.color}>
          <div className="wfb-note-body">
            {note.text.trim() ? (
              <MinimalMarkdown content={note.text} />
            ) : (
              <span className="wfb-note-placeholder">Empty note</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
