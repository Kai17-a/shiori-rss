from datetime import datetime, timedelta, timezone

from api.database import get_db
from api.model.models import DashboardArticle, DashboardResponse, DashboardSummary


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DashboardService:
    def get(self, limit: int = 100) -> DashboardResponse:
        accessed_at = _utc_now()
        window_started_at = accessed_at - timedelta(hours=24)
        window_start = window_started_at.isoformat()
        window_end = accessed_at.isoformat()
        with get_db() as conn:
            summary_row = conn.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM rss_feeds) AS rss_feed_count,
                  (SELECT COUNT(*) FROM news_sites) AS custom_feed_count,
                  (
                    SELECT COUNT(*) FROM rss_feed_articles
                    WHERE datetime(coalesce(published, created_at)) >= datetime(?)
                      AND datetime(coalesce(published, created_at)) <= datetime(?)
                  ) + (
                    SELECT COUNT(*) FROM news_site_articles
                    WHERE datetime(coalesce(published, created_at)) >= datetime(?)
                      AND datetime(coalesce(published, created_at)) <= datetime(?)
                  ) AS recent_article_count,
                  (
                    SELECT COUNT(*) FROM rss_feed_articles
                    WHERE webhook_notified = 0
                  ) + (
                    SELECT COUNT(*) FROM news_site_articles
                    WHERE webhook_notified = 0
                  ) AS pending_notification_count
                """,
                (window_start, window_end, window_start, window_end),
            ).fetchone()
            article_rows = conn.execute(
                """
                SELECT source_type, source_id, source_title, source_icon_url, url, title, summary,
                       published, created_at, webhook_notified
                FROM (
                  SELECT 'rss' AS source_type, feeds.id AS source_id,
                         feeds.title AS source_title, feeds.icon_url AS source_icon_url,
                         articles.url, articles.title,
                         articles.summary, articles.published, articles.created_at,
                         articles.webhook_notified
                  FROM rss_feed_articles AS articles
                  JOIN rss_feeds AS feeds ON feeds.id = articles.feed_id
                  WHERE datetime(coalesce(articles.published, articles.created_at)) >= datetime(?)
                    AND datetime(coalesce(articles.published, articles.created_at)) <= datetime(?)
                  UNION ALL
                  SELECT 'custom' AS source_type, sites.id AS source_id,
                         sites.title AS source_title, sites.icon_url AS source_icon_url,
                         articles.url, articles.title,
                         articles.summary, articles.published, articles.created_at,
                         articles.webhook_notified
                  FROM news_site_articles AS articles
                  JOIN news_sites AS sites ON sites.id = articles.site_id
                  WHERE datetime(coalesce(articles.published, articles.created_at)) >= datetime(?)
                    AND datetime(coalesce(articles.published, articles.created_at)) <= datetime(?)
                )
                ORDER BY datetime(coalesce(published, created_at)) DESC, source_type, source_id
                LIMIT ?
                """,
                (window_start, window_end, window_start, window_end, limit),
            ).fetchall()

        assert summary_row is not None
        return DashboardResponse(
            generated_at=accessed_at,
            window_started_at=window_started_at,
            summary=DashboardSummary(**dict(summary_row)),
            articles=[DashboardArticle(**dict(row)) for row in article_rows],
        )
