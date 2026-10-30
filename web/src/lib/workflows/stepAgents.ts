/**
 * Which agents a workflow step may run.
 *
 * Workflow steps run dedicated agents. Two kinds are excluded, in both editors
 * and on the server:
 * - the default "Assistant" (id 0), the general chat agent;
 * - a workflow's own wrapper agent (agent.workflow_id is set), which would
 *   make a step call another workflow's chat entry point.
 */

export const DEFAULT_ASSISTANT_AGENT_ID = 0;

interface StepAgentCandidate {
  id: number;
  workflow_id?: number | null;
}

export function isSelectableStepAgent(agent: StepAgentCandidate): boolean {
  return agent.id !== DEFAULT_ASSISTANT_AGENT_ID && !agent.workflow_id;
}

export function selectableStepAgents<T extends StepAgentCandidate>(agents: T[]): T[] {
  return agents.filter(isSelectableStepAgent);
}
