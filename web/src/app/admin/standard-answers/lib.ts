// API client for the Standard Answers admin screen (WS-D, clean-room).
// Base path preserved for contract compatibility: /api/nexus/admin/standard-answer.

const BASE = "/api/nexus/admin/standard-answer";

const jsonHeaders = { "Content-Type": "application/json" } as const;

// --- categories ---------------------------------------------------------------

export interface StandardAnswerCategoryCreationRequest {
  name: string;
}

export const createStandardAnswerCategory = (
  request: StandardAnswerCategoryCreationRequest
) =>
  fetch(`${BASE}/category`, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify({ name: request.name }),
  });

export const updateStandardAnswerCategory = (
  id: number,
  request: StandardAnswerCategoryCreationRequest
) =>
  fetch(`${BASE}/category/${id}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify({ name: request.name }),
  });

export const deleteStandardAnswerCategory = (id: number) =>
  fetch(`${BASE}/category/${id}`, { method: "DELETE", headers: jsonHeaders });

// --- answers ------------------------------------------------------------------

export interface StandardAnswerCreationRequest {
  keyword: string;
  answer: string;
  categories: number[];
  matchRegex: boolean;
  matchAnyKeywords: boolean;
}

const answerBody = (request: StandardAnswerCreationRequest) =>
  JSON.stringify({
    keyword: request.keyword,
    answer: request.answer,
    categories: request.categories,
    match_regex: request.matchRegex,
    match_any_keywords: request.matchAnyKeywords,
  });

export const createStandardAnswer = (request: StandardAnswerCreationRequest) =>
  fetch(BASE, { method: "POST", headers: jsonHeaders, body: answerBody(request) });

export const updateStandardAnswer = (
  id: number,
  request: StandardAnswerCreationRequest
) =>
  fetch(`${BASE}/${id}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: answerBody(request),
  });

export const deleteStandardAnswer = (id: number) =>
  fetch(`${BASE}/${id}`, { method: "DELETE", headers: jsonHeaders });

// --- feature config -----------------------------------------------------------

export interface StandardAnswerConfig {
  enabled: boolean;
  max_matches_per_message: number;
  match_input_char_limit: number;
}

export type StandardAnswerConfigUpdate = Partial<StandardAnswerConfig>;

export const updateStandardAnswerConfig = (update: StandardAnswerConfigUpdate) =>
  fetch(`${BASE}/config`, {
    method: "PUT",
    headers: jsonHeaders,
    body: JSON.stringify(update),
  });
