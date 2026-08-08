export interface DashboardSummary {
  rss_feed_count: number;
  custom_feed_count: number;
  today_article_count: number;
  pending_notification_count: number;
}

export interface DashboardArticle {
  source_type: "rss" | "custom";
  source_id: number;
  source_title: string;
  url: string;
  title: string | null;
  summary: string | null;
  published: string | null;
  created_at: string;
  webhook_notified: boolean;
}

export interface DashboardResponse {
  date: string;
  summary: DashboardSummary;
  articles: DashboardArticle[];
}

