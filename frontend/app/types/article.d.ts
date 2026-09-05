export interface ArticleListItem {
  source_type: "rss" | "custom";
  article_id: number;
  source_id: number;
  source_title: string;
  source_icon_url: string | null;
  url: string;
  title: string | null;
  summary: string | null;
  published: string | null;
  created_at: string;
  webhook_notified: boolean;
}

export interface ArticleListResponse {
  items: ArticleListItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
