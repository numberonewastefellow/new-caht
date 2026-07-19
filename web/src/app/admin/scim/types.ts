export interface ScimTokenInfo {
  id: number;
  name: string;
  token_display: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface ScimTokenCreatedResponse extends ScimTokenInfo {
  // The raw token — returned exactly once, at creation. Never retrievable again.
  raw_token: string;
}

export interface ScimStatus {
  base_url: string;
  multi_tenant: boolean;
  active_token_count: number;
  user_mapping_count: number;
  team_mapping_count: number;
}
