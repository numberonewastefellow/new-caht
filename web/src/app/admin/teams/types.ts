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
}
