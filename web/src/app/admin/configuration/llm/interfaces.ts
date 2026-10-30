export enum LLMProviderName {
  OPENAI = "openai",
  ANTHROPIC = "anthropic",
  OLLAMA_CHAT = "ollama_chat",
  LM_STUDIO = "lm_studio",
  OPENAI_COMPATIBLE = "openai_compatible",
  AZURE = "azure",
  OPENROUTER = "openrouter",
  VERTEX_AI = "vertex_ai",
  BEDROCK = "bedrock",
  CUSTOM = "custom",
}

export interface ModelConfiguration {
  name: string;
  is_visible: boolean;
  max_input_tokens: number | null;
  supports_image_input: boolean | null;
  supports_reasoning?: boolean;
  display_name?: string;
  provider_display_name?: string;
  vendor?: string;
  version?: string;
  region?: string;
}

export interface SimpleKnownModel {
  name: string;
  display_name: string | null;
}

export interface WellKnownLLMProviderDescriptor {
  name: string;
  known_models: ModelConfiguration[];

  recommended_default_model: SimpleKnownModel | null;
}

export interface LLMModelDescriptor {
  modelName: string;
  provider: string;
  maxTokens: number;
}

export interface LLMProvider {
  name: string;
  provider: string;
  api_key: string | null;
  api_base: string | null;
  api_version: string | null;
  custom_config: { [key: string]: string } | null;
  default_model_name: string;
  is_public: boolean;
  is_auto_mode: boolean;
  groups: number[];
  agents: number[];
  deployment_name: string | null;
  default_vision_model: string | null;
  is_default_vision_provider: boolean | null;
  model_configurations: ModelConfiguration[];
}

export interface LLMProviderView extends LLMProvider {
  id: number;
  is_default_provider: boolean | null;
}

export interface VisionProvider extends LLMProviderView {
  vision_models: string[];
}

export interface LLMProviderDescriptor {
  name: string;
  provider: string;
  provider_display_name?: string;
  default_model_name: string;
  is_default_provider: boolean | null;
  is_default_vision_provider?: boolean | null;
  default_vision_model?: string | null;
  is_public?: boolean;
  groups?: number[];
  agents?: number[];
  model_configurations: ModelConfiguration[];
}

export interface OllamaModelResponse {
  name: string;
  display_name: string;
  max_input_tokens: number | null;
  supports_image_input: boolean;
}

export interface LMStudioModelResponse {
  name: string;
  display_name: string;
  max_input_tokens: number | null;
  supports_image_input: boolean;
  supports_reasoning: boolean;
}

export interface OpenAICompatibleModelResponse {
  name: string;
  display_name: string;
  max_input_tokens: number | null;
  supports_image_input: boolean;
  supports_reasoning: boolean;
}

export interface OpenRouterModelResponse {
  name: string;
  display_name: string;
  max_input_tokens: number | null;
  supports_image_input: boolean;
}

export interface BedrockModelResponse {
  name: string;
  display_name: string;
  max_input_tokens: number;
  supports_image_input: boolean;
}

export interface LLMProviderFormProps {
  existingLlmProvider?: LLMProviderView;
  shouldMarkAsDefault?: boolean;
  /** When true, renders no card/button UI — only the modal. Parent controls visibility. */
  renderless?: boolean;
  /** Controlled modal open state (used with renderless) */
  isOpen?: boolean;
  /** Callback when the modal requests close */
  onOpenChange?: (open: boolean) => void;
}

// Param types for model fetching functions - use snake_case to match API structure
export interface BedrockFetchParams {
  aws_region_name: string;
  aws_access_key_id?: string;
  aws_secret_access_key?: string;
  aws_bearer_token_bedrock?: string;
  provider_name?: string;
}

export interface OllamaFetchParams {
  api_base?: string;
  /** Optional key (Ollama behind an auth proxy / Ollama Cloud) */
  api_key?: string;
  /** false = api_key is the masked stored value; the backend resolves it */
  api_key_changed?: boolean;
  provider_name?: string;
}

export interface LMStudioFetchParams {
  api_base?: string;
  api_key?: string;
  /** false = api_key is the masked stored value; the backend resolves it */
  api_key_changed?: boolean;
  provider_name?: string;
}

export interface OpenAICompatibleFetchParams {
  api_base?: string;
  api_key?: string;
  /** false = api_key is the masked stored value; the backend resolves it */
  api_key_changed?: boolean;
  provider_name?: string;
}

export interface OpenRouterFetchParams {
  api_base?: string;
  api_key?: string;
  provider_name?: string;
}

export interface VertexAIFetchParams {
  model_configurations?: ModelConfiguration[];
}

export type FetchModelsParams =
  | BedrockFetchParams
  | OllamaFetchParams
  | LMStudioFetchParams
  | OpenAICompatibleFetchParams
  | OpenRouterFetchParams
  | VertexAIFetchParams;
