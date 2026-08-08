from datetime import date

from api.database import get_db
from api.model.models import DashboardArticle, DashboardResponse, DashboardSummary


class DashboardService:
    def get(self, access_date: date, limit: int = 100) -> DashboardResponse:
        date_value = access_date.isoformat()
        with get_db() as conn:
            summary_row = conn.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM rss_feeds) AS rss_feed_count,
                  (SELECT COUNT(*) FROM news_sites) AS custom_feed_count,
                  (
                    SELECT COUNT(*) FROM rss_feed_articles
                    WHERE substr(coalesce(published, created_at), 1, 10) = ?
                  ) + (
                    SELECT COUNT(*) FROM news_site_articles
                    WHERE substr(coalesce(published, created_at), 1, 10) = ?
                  ) AS today_article_count,
                  (
                    SELECT COUNT(*) FROM rss_feed_articles
                    WHERE webhook_notified = 0
                  ) + (
                    SELECT COUNT(*) FROM news_site_articles
                    WHERE webhook_notified = 0
                  ) AS pending_notification_count
                """,
                (date_value, date_value),
            ).fetchone()
            article_rows = conn.execute(
                """
                SELECT source_type, source_id, source_title, url, title, summary,
                       published, created_at, webhook_notified
                FROM (
                  SELECT 'rss' AS source_type, feeds.id AS source_id,
                         feeds.title AS source_title, articles.url, articles.title,
                         articles.summary, articles.published, articles.created_at,
                         articles.webhook_notified
                  FROM rss_feed_articles AS articles
                  JOIN rss_feeds AS feeds ON feeds.id = articles.feed_id
                  WHERE substr(coalesce(articles.published, articles.created_at), 1, 10) = ?
                  UNION ALL
                  SELECT 'custom' AS source_type, sites.id AS source_id,
                         sites.title AS source_title, articles.url, articles.title,
                         articles.summary, articles.published, articles.created_at,
                         articles.webhook_notified
                  FROM news_site_articles AS articles
                  JOIN news_sites AS sites ON sites.id = articles.site_id
                  WHERE substr(coalesce(articles.published, articles.created_at), 1, 10) = ?
                )
                ORDER BY coalesce(published, created_at) DESC, source_type, source_id
                LIMIT ?
                """,
                (date_value, date_value, limit),
            ).fetchall()

        assert summary_row is not None
        return DashboardResponse(
            date=access_date,
            summary=DashboardSummary(**dict(summary_row)),
            articles=[DashboardArticle(**dict(row)) for row in article_rows],
        )
