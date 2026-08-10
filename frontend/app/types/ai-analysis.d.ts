export type AIAnalysisSourceType = "rss" | "custom";
export type AIAnalysisStatus = "completed" | "failed";

export interface AIArticleAnalysisResponse {
  id: number;
  source_type: AIAnalysisSourceType;
  article_id: number;
  source_id: number;
  source_title: string;
  article_title: string;
  article_url: string;
  article_published: string | null;
  model: string;
  prompt_version: string;
  ai_summary: string | null;
  key_points: string[];
  topics: string[];
  keywords: string[];
  entities: string[];
  input_tokens: number;
  output_tokens: number;
  status: AIAnalysisStatus;
  error_message: string | null;
  attempt_count: number;
  analyzed_at: string;
  updated_at: string;
}

export interface AIArticleAnalysisListResponse {
  items: AIArticleAnalysisResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
