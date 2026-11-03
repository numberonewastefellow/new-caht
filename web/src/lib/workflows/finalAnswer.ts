/**
 * Which step's answer the chat shows. With no step on "Show as Message", it's the
 * answer of the last top-level step that runs. Turning the option on for an earlier
 * step shows that step's text instead, and the last step's answer is left out.
 */
import type { EditorStep } from "./editorModel";

/** The last top-level step that runs: the one whose answer ends the workflow. */
export function lastRunningStep(steps: readonly EditorStep[]): EditorStep | undefined {
  const running = steps.filter((s) => !s.parent_key && !s.disabled);
  return running[running.length - 1];
}

/** Whether this step's "Show as Message" keeps the last step's answer out of the chat. */
export function hidesFinalAnswer(step: EditorStep, steps: readonly EditorStep[]): boolean {
  if (!step.promote_output || step.parent_key || step.disabled) return false;
  const last = lastRunningStep(steps);
  return !!last && last.node_key !== step.node_key && !last.promote_output;
}

export const HIDES_FINAL_ANSWER_NOTE =
  "The last step's answer won't appear in the chat. Turn this on for the last step too, or off here.";
