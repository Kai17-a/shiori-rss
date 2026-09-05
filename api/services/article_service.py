from fastapi import HTTPException

from api.database import get_db
from api.model.models import ArticleListItem, ArticleListResponse

_RSS_SELECT = """
  SELECT 'rss' AS source_type, feeds.id AS source_id, feeds.title AS source_title,
         CASE WHEN feeds.icon_data IS NOT NULL
           THEN '/api/rss-feeds/' || feeds.id || '/icon'
           ELSE feeds.icon_url
         END AS source_icon_url,
         articles.id AS article_id, articles.url, articles.title,
         articles.summary, articles.published, articles.created_at,
         articles.webhook_notified, articles.effective_published_at
  FROM rss_feed_articles AS articles
  JOIN rss_feeds AS feeds ON feeds.id = articles.feed_id
  {where}
"""

_CUSTOM_SELECT = """
  SELECT 'custom' AS source_type, sites.id AS source_id, sites.title AS source_title,
         CASE WHEN sites.icon_data IS NOT NULL
           THEN '/api/news-sites/' || sites.id || '/icon'
           ELSE sites.icon_url
         END AS source_icon_url,
         articles.id AS article_id, articles.url, articles.title,
         articles.summary, articles.published, articles.created_at,
         articles.webhook_notified, articles.effective_published_at
  FROM news_site_articles AS articles
  JOIN news_sites AS sites ON sites.id = articles.site_id
  {where}
"""


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ArticleService:
    def list_articles(
        self,
        q: str | None = None,
        source_type: str | None = None,
        source_id: int | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> ArticleListResponse:
        if source_type is not None and source_type not in ("rss", "custom"):
            raise HTTPException(
                status_code=422, detail="source_type must be 'rss' or 'custom'"
            )
        if source_id is not None and source_type is None:
            raise HTTPException(
                status_code=422,
                detail="source_type is required when source_id is provided",
            )

        query = (q or "").strip().lower()
        branches: list[tuple[str, list[object]]] = []

        if source_type in (None, "rss"):
            conditions = []
            params: list[object] = []
            if source_id is not None:
                conditions.append("feeds.id = ?")
                params.append(source_id)
            if query:
                conditions.append("LOWER(articles.title) LIKE ? ESCAPE '\\'")
                params.append(f"%{_escape_like(query)}%")
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            branches.append((_RSS_SELECT.format(where=where), params))

        if source_type in (None, "custom"):
            conditions = []
            params = []
            if source_id is not None:
                conditions.append("sites.id = ?")
                params.append(source_id)
            if query:
                conditions.append("LOWER(articles.title) LIKE ? ESCAPE '\\'")
                params.append(f"%{_escape_like(query)}%")
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            branches.append((_CUSTOM_SELECT.format(where=where), params))

        cte_sql = " UNION ALL ".join(branch_sql for branch_sql, _ in branches)
        cte_params: list[object] = [param for _, params in branches for param in params]

        page = max(page, 1)
        offset = (page - 1) * per_page

        with get_db() as conn:
            total = conn.execute(
                f"WITH filtered AS ({cte_sql}) SELECT COUNT(*) AS total FROM filtered",
                cte_params,
            ).fetchone()["total"]

            total_pages = ((total + per_page - 1) // per_page) if total else 0
            if page > max(total_pages, 1):
                page = max(total_pages, 1)
                offset = (page - 1) * per_page

            rows = conn.execute(
                f"""
                WITH filtered AS ({cte_sql})
                SELECT source_type, source_id, source_title, source_icon_url,
                       article_id, url, title, summary, published, created_at,
                       webhook_notified
                FROM filtered
                ORDER BY effective_published_at DESC, source_type, source_id,
                         article_id DESC
                LIMIT ? OFFSET ?
                """,
                [*cte_params, per_page, offset],
            ).fetchall()

        return ArticleListResponse(
            items=[ArticleListItem(**dict(row)) for row in rows],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )
