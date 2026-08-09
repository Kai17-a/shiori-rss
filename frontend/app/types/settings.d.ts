export interface SettingsWebhookCreateRequest {
  name: string;
  webhook_url: string;
}

export interface SettingsWebhookResponse {
  id: number;
  name: string;
  webhook_url: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface SettingsWebhookUpdateRequest {
  enabled: boolean;
}

export interface SettingsWebhookListResponse {
  items: SettingsWebhookResponse[];
}

export interface SettingsWebhookPingResponse {
  pong: boolean;
}

export interface SettingsRssExecutionResponse {
  enabled: boolean;
}

export interface SettingsRssWebhookNotificationResponse {
  enabled: boolean;
}

export interface SettingsWebhookSummaryResponse {
  enabled: boolean;
}

export interface SettingsAIArticleAnalysisResponse {
  enabled: boolean;
  max_articles_per_run: number;
  daily_token_limit: number;
  lookback_days: number;
}

export interface SettingsAIArticleAnalysisRunResponse {
  processed: number;
  succeeded: number;
  failed: number;
  skipped_current: number;
  stopped_by_token_limit: boolean;
}

export type LLMProvider = "vllm" | "ollama" | "openai";

export interface LLMSettingsResponse {
  provider: LLMProvider;
  base_url: string;
  api_key_configured: boolean;
  model: string;
}

export interface LLMSettingsUpdateRequest {
  provider: LLMProvider;
  base_url: string;
  api_key?: string | null;
  clear_api_key?: boolean;
  model: string;
}

export interface LLMSettingsTestResponse {
  ok: boolean;
  reply: string | null;
}
