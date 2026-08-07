export interface NewsSiteCreateRequest {
  url: string;
  title?: string | null;
  description?: string | null;
  webhook_ids?: number[];
}

export interface NewsSiteUpdateRequest {
  url?: string | null;
  title?: string | null;
  description?: string | null;
  notify_webhook_enabled?: boolean | null;
  webhook_ids?: number[] | null;
  reanalyze?: boolean;
}

export interface NewsSiteResponse {
  id: number;
  url: string;
  title: string;
  description: string | null;
  notify_webhook_enabled: boolean;
  webhook_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface NewsSiteListResponse {
  items: NewsSiteResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface NewsSiteArticleResponse {
  id: number;
  site_id: number;
  url: string;
  title: string | null;
  published: string | null;
  created_at: string;
}

export interface NewsSiteArticleListResponse {
  items: NewsSiteArticleResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface NewsSiteExecuteResponse {
  site_id: number;
  title: string;
  delivered: boolean;
  delivered_count: number;
  message?: string | null;
}
