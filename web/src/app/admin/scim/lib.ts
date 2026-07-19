import { ScimTokenCreatedResponse } from "./types";

const TOKENS_URL = "/api/admin/scim/tokens";

export async function createScimToken(
  name: string
): Promise<ScimTokenCreatedResponse> {
  const response = await fetch(TOKENS_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Failed to create SCIM token");
  }
  return (await response.json()) as ScimTokenCreatedResponse;
}

export async function revokeScimToken(tokenId: number): Promise<Response> {
  return fetch(`${TOKENS_URL}/${tokenId}`, { method: "DELETE" });
}
