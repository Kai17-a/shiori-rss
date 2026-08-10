export interface RSSFeedCreateRequest {
  url: string;
  title: string;
  description?: string | null;
  notify_webhook_enabled?: boolean;
  webhook_ids?: number[];
  icon_url?: string | null;
}

export interface RSSFeedUpdateRequest {
  url?: string | null;
  title?: string | null;
  description?: string | null;
  notify_webhook_enabled?: boolean | null;
  webhook_ids?: number[] | null;
  icon_url?: string | null;
}

export interface RSSFeedResponse {
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

export interface RSSFeedArticleResponse {
  id: number;
  feed_id: number;
  url: string;
  title: string | null;
  summary: string | null;
  published: string | null;
  webhook_notified: boolean;
  created_at: string;
}

export interface RSSFeedArticleListResponse {
  items: RSSFeedArticleResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface RSSFeedListResponse {
  items: RSSFeedResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface RSSFeedExecuteResponse {
  feed_id: number;
  title: string;
  delivered: boolean;
  delivered_count: number;
  message?: string | null;
}
