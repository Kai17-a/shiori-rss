export interface NewsSiteCreateRequest {
  url: string;
  title?: string | null;
  description?: string | null;
  webhook_ids?: number[];
  icon_url?: string | null;
}

export interface NewsSiteUpdateRequest {
  url?: string | null;
  title?: string | null;
  description?: string | null;
  notify_webhook_enabled?: boolean | null;
  webhook_ids?: number[] | null;
  reanalyze?: boolean;
  icon_url?: string | null;
}

export interface NewsSiteResponse {
  id: number;
  url: string;
  title: string;
  description: string | null;
  notify_webhook_enabled: boolean;
  webhook_ids: number[];
  icon_url: string | null;
  icon_uploaded: boolean;
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
  summary: string | null;
  published: string | null;
  webhook_notified: boolean;
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
