import { TeamMemberRole } from "@/lib/types";

export interface TeamUpdate {
  user_ids: string[];
  cc_pair_ids: number[];
}

export interface SetCuratorRequest {
  user_id: string;
  is_curator: boolean;
}

export interface TeamCreate {
  name: string;
  user_ids: string[];
  cc_pair_ids: number[];

  // Enriched create fields (Contract 1). The current backend ignores unknown
  // fields, so these are forward-compatible with the upgraded endpoint.
  description?: string;
  is_public?: boolean;
  tags?: string[];
}

// Settings persisted via PATCH /api/teams/{id}. Only user_ids / cc_pair_ids are
// wired server-side today; the remaining fields are forward-compatible.
export interface TeamSettingsUpdate {
  is_public?: boolean;
  default_member_role?: TeamMemberRole;
  allow_guest_access?: boolean;
  description?: string;
  tags?: string[];
  name?: string;
}
