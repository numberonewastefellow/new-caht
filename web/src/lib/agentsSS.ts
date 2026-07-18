import { MinimalAgentSnapshot } from "@/app/admin/assistants/interfaces";
import { fetchSS } from "./utilsSS";

export type FetchAssistantsResponse = [MinimalAgentSnapshot[], string | null];

// Fetch assistants server-side
export async function fetchAssistantsSS(): Promise<FetchAssistantsResponse> {
  const response = await fetchSS("/agent");
  if (response.ok) {
    return [(await response.json()) as MinimalAgentSnapshot[], null];
  }
  return [[], (await response.json()).detail || "Unknown Error"];
}
