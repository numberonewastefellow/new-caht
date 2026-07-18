import { Agent } from "@/app/admin/assistants/interfaces";
import { DocumentSetSummary, ValidSources } from "./types";
import { getSourcesForAgent } from "./sources";

export function computeAvailableFilters({
  selectedAgent,
  availableSources,
  availableDocumentSets,
}: {
  selectedAgent: Agent | undefined | null;
  availableSources: ValidSources[];
  availableDocumentSets: DocumentSetSummary[];
}): [ValidSources[], DocumentSetSummary[]] {
  const finalAvailableSources =
    selectedAgent && selectedAgent.document_sets.length
      ? getSourcesForAgent(selectedAgent)
      : availableSources;

  // only display document sets that are available to the agent
  // in filters
  const agentDocumentSetIds =
    selectedAgent && selectedAgent.document_sets.length
      ? selectedAgent.document_sets.map((documentSet) => documentSet.id)
      : null;
  const finalAvailableDocumentSets = agentDocumentSetIds
    ? availableDocumentSets.filter((documentSet) =>
        agentDocumentSetIds.includes(documentSet.id)
      )
    : availableDocumentSets;

  return [finalAvailableSources, finalAvailableDocumentSets];
}
