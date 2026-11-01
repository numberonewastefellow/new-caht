/**
 * Which agents a workflow step may run.
 *
 * Workflow steps run dedicated agents. The server enforces this on save and at
 * run time (load_step_agent in backend/om/workflows/nodes/agent.py); these
 * helpers keep the two kinds it refuses out of both editors' pickers:
 * - the default "Assistant" (id 0): admins change its tools and prompt globally
 *   for chat, which would silently change every workflow using it;
 * - a workflow's own wrapper agent (agent.workflow_id is set): it has no tools
 *   or prompt of its own, so as a step it is an empty LLM call, not its workflow.
 */

export const DEFAULT_ASSISTANT_AGENT_ID = 0;

interface StepAgentCandidate {
  id: number;
  workflow_id?: number | null;
}

export function isSelectableStepAgent(agent: StepAgentCandidate): boolean {
  return agent.id !== DEFAULT_ASSISTANT_AGENT_ID && !agent.workflow_id;
}

/**
 * A step's overrides were chosen for its agent, so changing the agent clears them. Both
 * editors use this, so a step behaves the same whichever one changed it.
 */
export const OVERRIDES_CLEARED_ON_AGENT_CHANGE = {
  llm_provider_override: null,
  llm_model_override: null,
  max_output_tokens_override: null,
  system_prompt_override: null,
  task_prompt_override: null,
  tool_ids_override: null,
  document_set_ids_override: null,
  replace_base_system_prompt_override: null,
} as const;

export function selectableStepAgents<T extends StepAgentCandidate>(agents: T[]): T[] {
  return agents.filter(isSelectableStepAgent);
}
