import re

from fastapi import HTTPException

from api.database import get_db
from api.model.models import ArticleListItem, ArticleListResponse

_SOURCE_PATTERN = re.compile(r"^(rss|custom):([1-9]\d*)$")

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
        sources: list[str] | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> ArticleListResponse:
        selected_rss_ids: list[int] = []
        selected_custom_ids: list[int] = []
        for raw in sources or []:
            match = _SOURCE_PATTERN.match(raw)
            if not match:
                raise HTTPException(
                    status_code=422,
                    detail="Each source must be 'rss:<id>' or 'custom:<id>'",
                )
            target = selected_rss_ids if match.group(1) == "rss" else selected_custom_ids
            target.append(int(match.group(2)))
        has_selection = bool(selected_rss_ids or selected_custom_ids)

        query = (q or "").strip().lower()
        branches: list[tuple[str, list[object]]] = []

        if not has_selection or selected_rss_ids:
            conditions = []
            params: list[object] = []
            if selected_rss_ids:
                placeholders = ", ".join("?" for _ in selected_rss_ids)
                conditions.append(f"feeds.id IN ({placeholders})")
                params.extend(selected_rss_ids)
            if query:
                conditions.append("LOWER(articles.title) LIKE ? ESCAPE '\\'")
                params.append(f"%{_escape_like(query)}%")
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            branches.append((_RSS_SELECT.format(where=where), params))

        if not has_selection or selected_custom_ids:
            conditions = []
            params = []
            if selected_custom_ids:
                placeholders = ", ".join("?" for _ in selected_custom_ids)
                conditions.append(f"sites.id IN ({placeholders})")
                params.extend(selected_custom_ids)
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
