// WS-M — tenant-admin API DTOs (mirror backend om/tenancy/models.py).

export interface TenantSummary {
  tenant_id: string;
  active_user_count: number;
  total_user_count: number;
}

export interface TenantListResponse {
  tenants: TenantSummary[];
}

export interface TenantActionResponse {
  tenant_id: string;
  success: boolean;
  detail: string | null;
}

export const TENANTS_ADMIN_URL = "/api/admin/tenants";
