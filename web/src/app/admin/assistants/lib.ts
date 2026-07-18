import {
  MinimalAgentSnapshot,
  Agent,
  StarterMessage,
} from "@/app/admin/assistants/interfaces";

interface AgentUpsertRequest {
  name: string;
  description: string;
  system_prompt: string;
  task_prompt: string;
  datetime_aware: boolean;
  document_set_ids: number[];
  num_chunks: number | null;
  is_public: boolean;
  recency_bias: string;
  llm_filter_extraction: boolean;
  llm_relevance_filter: boolean | null;
  llm_model_provider_override: string | null;
  llm_model_version_override: string | null;
  starter_messages: StarterMessage[] | null;
  users?: string[];
  groups: number[];
  tool_ids: number[];
  remove_image?: boolean;
  uploaded_image_id: string | null;
  icon_name: string | null;
  search_start_date: Date | null;
  is_default_agent: boolean;
  display_priority: number | null;
  label_ids: number[] | null;
  knowledge_file_ids: string[] | null;
  replace_base_system_prompt: boolean;
  max_output_tokens?: number | null;
  // Hierarchy nodes (folders, spaces, channels) for scoped search
  hierarchy_node_ids: number[];
  // Individual documents for scoped search
  document_ids: string[];
}

export interface AgentUpsertParameters {
  name: string;
  description: string;
  system_prompt: string;
  replace_base_system_prompt: boolean;
  task_prompt: string;
  datetime_aware: boolean;
  document_set_ids: number[];
  num_chunks: number | null;
  is_public: boolean;
  llm_relevance_filter: boolean | null;
  llm_model_provider_override: string | null;
  llm_model_version_override: string | null;
  starter_messages: StarterMessage[] | null;
  users?: string[];
  groups: number[];
  tool_ids: number[];
  remove_image?: boolean;
  search_start_date: Date | null;
  uploaded_image_id: string | null;
  icon_name: string | null;
  is_default_agent: boolean;
  label_ids: number[] | null;
  knowledge_file_ids: string[];
  max_output_tokens?: number | null;
  // Hierarchy nodes (folders, spaces, channels) for scoped search
  hierarchy_node_ids?: number[];
  // Individual documents for scoped search
  document_ids?: string[];
}

function buildAgentUpsertRequest({
  name,
  description,
  system_prompt,
  task_prompt,
  document_set_ids,
  num_chunks,
  is_public,
  groups,
  datetime_aware,
  users,
  tool_ids,
  remove_image,
  search_start_date,
  knowledge_file_ids,
  hierarchy_node_ids,
  document_ids,
  icon_name,
  uploaded_image_id,
  is_default_agent,
  llm_relevance_filter,
  llm_model_provider_override,
  llm_model_version_override,
  starter_messages,
  label_ids,
  replace_base_system_prompt,
  max_output_tokens,
}: AgentUpsertParameters): AgentUpsertRequest {
  return {
    name,
    description,
    system_prompt,
    task_prompt,
    document_set_ids,
    num_chunks,
    is_public,
    uploaded_image_id,
    icon_name,
    groups,
    users,
    tool_ids,
    remove_image,
    search_start_date,
    datetime_aware,
    is_default_agent: is_default_agent ?? false,
    recency_bias: "base_decay",
    llm_filter_extraction: false,
    llm_relevance_filter: llm_relevance_filter ?? null,
    llm_model_provider_override: llm_model_provider_override ?? null,
    llm_model_version_override: llm_model_version_override ?? null,
    starter_messages: starter_messages ?? null,
    display_priority: null,
    label_ids: label_ids ?? null,
    knowledge_file_ids: knowledge_file_ids ?? null,
    replace_base_system_prompt,
    max_output_tokens: max_output_tokens ?? null,
    hierarchy_node_ids: hierarchy_node_ids ?? [],
    document_ids: document_ids ?? [],
  };
}

export async function uploadFile(file: File): Promise<string | null> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/admin/agent/upload-image", {
    method: "POST",
    body: formData,
    credentials: "include",
  });

  if (!response.ok) {
    console.error("Failed to upload file");
    return null;
  }

  const responseJson = await response.json();
  return responseJson.file_id;
}

export async function createAgent(
  agentUpsertParams: AgentUpsertParameters
): Promise<Response | null> {
  const createAgentResponse = await fetch("/api/agent", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildAgentUpsertRequest(agentUpsertParams)),
    credentials: "include",
  });

  return createAgentResponse;
}

export async function updateAgent(
  id: number,
  agentUpsertParams: AgentUpsertParameters
): Promise<Response | null> {
  const updateAgentResponse = await fetch(`/api/agent/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildAgentUpsertRequest(agentUpsertParams)),
    credentials: "include",
  });

  return updateAgentResponse;
}

export function deleteAgent(agentId: number) {
  return fetch(`/api/agent/${agentId}`, {
    method: "DELETE",
    credentials: "include",
  });
}

function smallerNumberFirstComparator(a: number, b: number) {
  return a > b ? 1 : -1;
}

function closerToZeroNegativesFirstComparator(a: number, b: number) {
  if (a < 0 && b > 0) {
    return -1;
  }
  if (a > 0 && b < 0) {
    return 1;
  }

  const absA = Math.abs(a);
  const absB = Math.abs(b);

  if (absA === absB) {
    return a > b ? 1 : -1;
  }

  return absA > absB ? 1 : -1;
}

export function agentComparator(
  a: MinimalAgentSnapshot | Agent,
  b: MinimalAgentSnapshot | Agent
) {
  if (a.display_priority === null && b.display_priority === null) {
    return closerToZeroNegativesFirstComparator(a.id, b.id);
  }

  if (a.display_priority !== b.display_priority) {
    if (a.display_priority === null) {
      return 1;
    }
    if (b.display_priority === null) {
      return -1;
    }

    return smallerNumberFirstComparator(a.display_priority, b.display_priority);
  }

  return closerToZeroNegativesFirstComparator(a.id, b.id);
}

export async function toggleAgentDefault(
  agentId: number,
  isDefault: boolean
) {
  const response = await fetch(`/api/admin/agent/${agentId}/default`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      is_default_agent: !isDefault,
    }),
    credentials: "include",
  });
  return response;
}

export async function toggleAgentVisibility(
  agentId: number,
  isVisible: boolean
) {
  const response = await fetch(`/api/admin/agent/${agentId}/visible`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      is_visible: !isVisible,
    }),
    credentials: "include",
  });
  return response;
}
