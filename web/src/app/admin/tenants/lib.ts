// WS-M — tenant-admin API client helpers.

import { TENANTS_ADMIN_URL, TenantActionResponse } from "./types";

async function parseAction(response: Response): Promise<TenantActionResponse> {
  const body = (await response.json()) as TenantActionResponse;
  if (!response.ok || !body.success) {
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return body;
}

export async function createTenant(
  adminEmail: string
): Promise<TenantActionResponse> {
  const response = await fetch(TENANTS_ADMIN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ admin_email: adminEmail }),
  });
  return parseAction(response);
}

export async function assignUserToTenant(
  tenantId: string,
  email: string,
  moveIfAssigned: boolean
): Promise<TenantActionResponse> {
  const response = await fetch(
    `${TENANTS_ADMIN_URL}/${encodeURIComponent(tenantId)}/users`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, move_if_assigned: moveIfAssigned }),
    }
  );
  return parseAction(response);
}

export async function deactivateTenant(
  tenantId: string
): Promise<TenantActionResponse> {
  const response = await fetch(
    `${TENANTS_ADMIN_URL}/${encodeURIComponent(tenantId)}/deactivate`,
    { method: "POST" }
  );
  return parseAction(response);
}

export async function deleteTenant(
  tenantId: string
): Promise<TenantActionResponse> {
  const response = await fetch(
    `${TENANTS_ADMIN_URL}/${encodeURIComponent(tenantId)}`,
    { method: "DELETE" }
  );
  return parseAction(response);
}
